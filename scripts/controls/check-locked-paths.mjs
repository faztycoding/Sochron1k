#!/usr/bin/env node
// Locked-path and append-only check: the CI layer that enforces locked paths (Handbook v5
// ch.19, Appendix O). Local hooks are only a convenience layer; this check runs on every PR.
// It fails when a change touches a locked path or rewrites an append-only file, unless the owner
// approved the control change. CI sets CONTROL_CHANGE_APPROVED=true only when the PR carries
// the label in rules.mjs (APPROVAL_LABEL).
//
// Usage: node scripts/controls/check-locked-paths.mjs [BASE]   (default BASE: main)
// Scope: committed and uncommitted changes since merge-base(BASE, HEAD), plus untracked files.
// Exit:  0 = clean or approved · 1 = unapproved control change · 2 = git or usage error
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

/**
 * Decide which changes violate the locked or append-only rules.
 * @param {{status: string, path: string, from?: string}[]} changes  status A, M, D, R, C or T
 * @param {{readOld: (p: string) => Buffer|null, readNew: (p: string) => Buffer|null}} io
 */
export function evaluate(changes, io) {
  const violations = [];
  for (const ch of changes) {
    const touched = ch.from ? [ch.from, ch.path] : [ch.path];
    const lockedHit = touched.map((p) => [p, matchLocked(p)]).find(([, rule]) => rule);
    if (lockedHit) {
      violations.push({ kind: 'locked', status: ch.status, path: lockedHit[0], why: lockedHit[1].why });
      continue;
    }
    const srcRule = matchAppendOnly(ch.from ?? ch.path);
    const dstRule = matchAppendOnly(ch.path);
    if ((ch.status === 'D' || ch.status === 'R') && srcRule) {
      violations.push({ kind: 'append-only', status: ch.status, path: ch.from ?? ch.path,
        why: `${srcRule.why}: existing file removed or renamed` });
      continue;
    }
    if ((ch.status === 'M' || ch.status === 'T') && dstRule) {
      if (dstRule.mode === 'immutable') {
        violations.push({ kind: 'append-only', status: ch.status, path: ch.path,
          why: `${dstRule.why}: committed file modified` });
        continue;
      }
      const oldBuf = io.readOld(ch.path) ?? Buffer.alloc(0);
      const newBuf = io.readNew(ch.path) ?? Buffer.alloc(0);
      const oldEndsWithNewline = oldBuf.length === 0 || oldBuf[oldBuf.length - 1] === 0x0a;
      const prefixKept = newBuf.length >= oldBuf.length && newBuf.subarray(0, oldBuf.length).equals(oldBuf);
      if (!oldEndsWithNewline || !prefixKept) {
        violations.push({ kind: 'append-only', status: ch.status, path: ch.path,
          why: `${dstRule.why}: existing records changed (only appending whole lines is allowed)` });
      }
    }
  }
  return violations;
}

function git(args, cwd, encoding = 'utf8') {
  return execFileSync('git', args, { cwd, encoding, stdio: ['ignore', 'pipe', 'pipe'], maxBuffer: 256 * 1024 * 1024 });
}

function main() {
  const base = process.argv[2] ?? 'main';
  const approved = process.env.CONTROL_CHANGE_APPROVED === 'true';
  let root;
  let mergeBase;
  try {
    root = git(['rev-parse', '--show-toplevel'], process.cwd()).trim();
    mergeBase = git(['merge-base', base, 'HEAD'], root).trim();
  } catch (err) {
    console.error(`check-locked-paths: cannot find the merge-base with ${base}: ${String(err.message).split('\n')[0]}`);
    process.exit(2);
  }
  const diff = git(['-c', 'core.quotePath=false', 'diff', '--name-status', '-M', '-z', mergeBase], root);
  const untracked = git(['-c', 'core.quotePath=false', 'ls-files', '--others', '--exclude-standard', '-z'], root)
    .split('\0').filter(Boolean).map((p) => ({ status: 'A', path: p }));
  const changes = [...parseNameStatusZ(diff), ...untracked];

  const violations = evaluate(changes, {
    readOld: (p) => { try { return git(['show', `${mergeBase}:${p}`], root, 'buffer'); } catch { return null; } },
    readNew: (p) => { try { return fs.readFileSync(path.join(root, p)); } catch { return null; } },
  });

  console.log(`Locked-path check · base ${base} · merge-base ${mergeBase.slice(0, 7)} · ${changes.length} changed path(s)`);
  for (const v of violations) {
    console.log(`!! ${v.kind.padEnd(11)} ${v.status}  ${v.path}  (${v.why})`);
  }
  if (violations.length === 0) {
    console.log('Result: PASS: no locked path changed and no append-only file was rewritten.');
    process.exit(0);
  }
  if (approved) {
    console.log(`Result: PASS (owner approval present): ${violations.length} control change(s) listed above for the audit trail.`);
    process.exit(0);
  }
  console.log(`Result: FAIL: ${violations.length} control change(s) need owner approval (PR label "${APPROVAL_LABEL}").`);
  console.log('Implementers must not change these paths; if the change is intended, the owner reviews it and applies the label.');
  process.exit(1);
}

const invokedDirectly = process.argv[1]
  && path.resolve(process.argv[1]).toLowerCase() === path.resolve(fileURLToPath(import.meta.url)).toLowerCase();
if (invokedDirectly) main();
