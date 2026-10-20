#!/usr/bin/env node
// Locked-path and append-only check: the CI gate for locked paths (Handbook v5 ch.19, Appendix O).
// Local hooks are only a convenience layer; this check is what blocks a merge.
// It fails when a change touches a locked path, or when ANY commit in the range rewrites an
// append-only file (a hypothesis is immutable once committed; the registry only gains lines),
// unless the owner approved the control change: CI sets CONTROL_CHANGE_APPROVED=true only when
// the PR carries the label in rules.mjs (APPROVAL_LABEL).
//
// In CI this script must come from a TRUSTED revision (the base branch), never from the PR it
// judges. See .github/workflows/control-gate.yml.
//
// Usage:
//   node scripts/controls/check-locked-paths.mjs [BASE]
//       local: commits since merge-base(BASE, HEAD), plus uncommitted and untracked files
//   node scripts/controls/check-locked-paths.mjs --base <rev> --head <rev>
//       CI: commits only, read from git objects; the working tree is never consulted
// Exit: 0 = clean or approved · 1 = unapproved control change · 2 = git or usage error
import { execFileSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { APPROVAL_LABEL, matchAppendOnly, matchLocked } from './rules.mjs';

/** Parse `git diff --name-status -z` output into {status, path, from?} records. */
export function parseNameStatusZ(text) {
  const tok = text.split('\0').filter((t) => t !== '');
  const out = [];
  for (let i = 0; i < tok.length; ) {
    const code = tok[i][0];
    if (code === 'R' || code === 'C') {
      out.push({ status: code, from: tok[i + 1], path: tok[i + 2] });
      i += 3;
    } else {
      out.push({ status: code, path: tok[i + 1] });
      i += 2;
    }
  }
  return out;
}

/** Locked-path violations in one change set. */
export function evaluateLocked(changes) {
  const violations = [];
  for (const ch of changes) {
    const touched = ch.from ? [ch.from, ch.path] : [ch.path];
    const hit = touched.map((p) => [p, matchLocked(p)]).find(([, rule]) => rule);
    if (hit) violations.push({ kind: 'locked', status: ch.status, path: hit[0], why: hit[1].why });
  }
  return violations;
}

/**
 * Append-only violations in one change set.
 * @param {{status: string, path: string, from?: string}[]} changes  status A, M, D, R, C or T
 * @param {{readOld: (p: string) => Buffer|null, readNew: (p: string) => Buffer|null}} io
 */
export function evaluateAppendOnly(changes, io, where = '') {
  const violations = [];
  const at = where ? ` (${where})` : '';
  for (const ch of changes) {
    const srcRule = matchAppendOnly(ch.from ?? ch.path);
    const dstRule = matchAppendOnly(ch.path);
    if ((ch.status === 'D' || ch.status === 'R') && srcRule) {
      violations.push({ kind: 'append-only', status: ch.status, path: ch.from ?? ch.path,
        why: `${srcRule.why}: existing file removed or renamed${at}` });
      continue;
    }
    if ((ch.status === 'M' || ch.status === 'T') && dstRule) {
      if (dstRule.mode === 'immutable') {
        violations.push({ kind: 'append-only', status: ch.status, path: ch.path,
          why: `${dstRule.why}: committed file modified${at}` });
        continue;
      }
      const oldBuf = io.readOld(ch.path) ?? Buffer.alloc(0);
      const newBuf = io.readNew(ch.path) ?? Buffer.alloc(0);
      const oldEndsWithNewline = oldBuf.length === 0 || oldBuf[oldBuf.length - 1] === 0x0a;
      const prefixKept = newBuf.length >= oldBuf.length && newBuf.subarray(0, oldBuf.length).equals(oldBuf);
      if (!oldEndsWithNewline || !prefixKept) {
        violations.push({ kind: 'append-only', status: ch.status, path: ch.path,
          why: `${dstRule.why}: existing records changed, only appending whole lines is allowed${at}` });
      }
    }
  }
  return violations;
}

/** Final-state evaluation of one change set: locked paths plus append-only rules. */
export function evaluate(changes, io) {
  return [...evaluateLocked(changes), ...evaluateAppendOnly(changes, io)];
}

/**
 * Commit-by-commit evaluation of append-only rules (F2: a file added and then edited inside the
 * same branch shows up as "added" in the combined diff, so every commit is checked on its own).
 * @param {{sha: string, parents: string[], changes: {status: string, path: string, from?: string}[]}[]} commits
 * @param {(rev: string, p: string) => Buffer|null} readAt
 */
export function evaluateHistory(commits, readAt) {
  const violations = [];
  for (const c of commits) {
    const short = c.sha.slice(0, 7);
    if (c.parents.length <= 1) {
      const parent = c.parents[0];
      violations.push(...evaluateAppendOnly(c.changes, {
        readOld: (p) => (parent ? readAt(parent, p) : null),
        readNew: (p) => readAt(c.sha, p),
      }, `commit ${short}`));
      continue;
    }
    // Merge commit: the result must equal one of the parents for every append-only path it touches.
    for (const ch of c.changes) {
      const p = ch.path;
      const rule = matchAppendOnly(ch.from ?? p) ?? matchAppendOnly(p);
      if (!rule) continue;
      if (ch.status === 'D' || ch.status === 'R') {
        violations.push({ kind: 'append-only', status: ch.status, path: ch.from ?? p,
          why: `${rule.why}: removed or renamed in merge commit ${short}` });
        continue;
      }
      const merged = readAt(c.sha, p);
      const matchesParent = c.parents.some((parent) => {
        const b = readAt(parent, p);
        return b !== null && merged !== null && b.equals(merged);
      });
      if (!matchesParent) {
        violations.push({ kind: 'append-only', status: 'M', path: p,
          why: `${rule.why}: changed inside merge commit ${short}` });
      }
    }
  }
  return violations;
}

function dedupe(violations) {
  const seen = new Set();
  return violations.filter((v) => {
    const key = `${v.kind}|${v.path}|${v.why}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

function git(args, cwd, encoding = 'utf8') {
  return execFileSync('git', args, { cwd, encoding, stdio: ['ignore', 'pipe', 'pipe'], maxBuffer: 256 * 1024 * 1024 });
}

function parseArgs(argv) {
  const out = { base: 'main', head: null };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === '--base') out.base = argv[++i];
    else if (a === '--head') out.head = argv[++i];
    else if (!a.startsWith('-')) out.base = a;
    else throw new Error(`unknown option ${a}`);
  }
  if (!out.base || (out.head !== null && !out.head)) throw new Error('missing revision value');
  return out;
}

function main() {
  let opts;
  try {
    opts = parseArgs(process.argv.slice(2));
  } catch (err) {
    console.error(`check-locked-paths: ${err.message}`);
    process.exit(2);
  }
  const approved = process.env.CONTROL_CHANGE_APPROVED === 'true';
  const headRev = opts.head ?? 'HEAD';
  let root;
  let mergeBase;
  try {
    root = git(['rev-parse', '--show-toplevel'], process.cwd()).trim();
    mergeBase = git(['merge-base', opts.base, headRev], root).trim();
  } catch (err) {
    console.error(`check-locked-paths: cannot find the merge-base of ${opts.base} and ${headRev}: ${String(err.message).split('\n')[0]}`);
    process.exit(2);
  }
  const readAt = (rev, p) => { try { return git(['show', `${rev}:${p}`], root, 'buffer'); } catch { return null; } };
  const readFile = (p) => { try { return fs.readFileSync(path.join(root, p)); } catch { return null; } };
  const quiet = ['-c', 'core.quotePath=false'];

  // 1. Final state: merge-base against the head revision (CI) or the working tree (local).
  const finalDiff = opts.head
    ? git([...quiet, 'diff', '--name-status', '-M', '-z', mergeBase, headRev], root)
    : git([...quiet, 'diff', '--name-status', '-M', '-z', mergeBase], root);
  const untracked = opts.head ? [] : git([...quiet, 'ls-files', '--others', '--exclude-standard', '-z'], root)
    .split('\0').filter(Boolean).map((p) => ({ status: 'A', path: p }));
  const finalChanges = [...parseNameStatusZ(finalDiff), ...untracked];
  const violations = evaluate(finalChanges, {
    readOld: (p) => readAt(mergeBase, p),
    readNew: (p) => (opts.head ? readAt(headRev, p) : readFile(p)),
  });

  // 2. History: every commit in mergeBase..head, so later edits inside the same branch are caught.
  const commitLines = git(['rev-list', '--reverse', '--parents', `${mergeBase}..${headRev}`], root)
    .split(/\r?\n/).filter(Boolean);
  const commits = commitLines.map((line) => {
    const [sha, ...parents] = line.split(' ');
    const changes = parents.length
      ? parseNameStatusZ(git([...quiet, 'diff-tree', '-r', '-M', '--name-status', '-z', parents[0], sha], root))
      : [];
    return { sha, parents, changes };
  });
  violations.push(...evaluateHistory(commits, readAt));

  // 3. Local only: uncommitted edits to files that are already committed.
  if (!opts.head) {
    const pending = parseNameStatusZ(git([...quiet, 'diff', '--name-status', '-M', '-z', 'HEAD'], root));
    violations.push(...evaluateAppendOnly(pending, { readOld: (p) => readAt('HEAD', p), readNew: readFile }, 'uncommitted'));
  }

  const unique = dedupe(violations);
  console.log(`Locked-path check · base ${opts.base} · head ${opts.head ?? 'working tree'} · merge-base ${mergeBase.slice(0, 7)} · `
    + `${finalChanges.length} changed path(s) · ${commits.length} commit(s) checked`);
  for (const v of unique) {
    console.log(`!! ${v.kind.padEnd(11)} ${v.status}  ${v.path}  (${v.why})`);
  }
  if (unique.length === 0) {
    console.log('Result: PASS: no locked path changed and no append-only file was rewritten.');
    process.exit(0);
  }
  if (approved) {
    console.log(`Result: PASS (owner approval present): ${unique.length} control change(s) listed above for the audit trail.`);
    process.exit(0);
  }
  console.log(`Result: FAIL: ${unique.length} control change(s) need owner approval (PR label "${APPROVAL_LABEL}").`);
  console.log('Implementers must not change these paths; if the change is intended, the owner reviews it and applies the label.');
  process.exit(1);
}

const invokedDirectly = process.argv[1]
  && path.resolve(process.argv[1]).toLowerCase() === path.resolve(fileURLToPath(import.meta.url)).toLowerCase();
if (invokedDirectly) main();
