#!/usr/bin/env node
// PostToolUse and PostToolUseFailure hook for Bash|PowerShell|Monitor: the after-the-fact check
// behind guard-bash.mjs (review BOOT-001-r2 F3; owner decision 2026-10-19). guard-bash judges the
// command TEXT before a command runs and cannot model everything (programs that open files
// themselves, shell syntax it does not parse). This hook judges the RESULT. After each shell
// command, successful or failed, it looks at the repository and reports protected changes that
// were not there at the previous check in this session:
//   - uncommitted changes to locked paths (scripts/controls/rules.mjs)
//   - uncommitted rewrites of append-only files (a committed hypothesis edited or removed,
//     registry records changed instead of appended)
//   - commits made since the previous check that touch locked or append-only paths, unless the
//     same content was already reported while uncommitted
//   - changes to locked files that git ignores (.claude/settings.local.json, CLAUDE.local.md)
// It cannot undo anything: exit 2 sends the report to Claude, which must stop and tell the owner.
// Each state is reported once per session. A file cannot tell who changed it, so changes the
// owner or Codex made between commands are reported too. CI control-gate stays the merge gate.
//
// With --baseline (PreToolUse, same matcher) it only records the starting state of the session
// when none exists yet, so the first command is compared with its own starting point (review
// BOOT-001-r3). Baseline mode never blocks a command.
import { execFileSync } from 'node:child_process';
import crypto from 'node:crypto';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { evaluateAppendOnly, evaluateLocked, parseNameStatusZ } from '../../scripts/controls/check-locked-paths.mjs';

const HOOK = '.claude/hooks/check-locked-after.mjs';
const IGNORED_LOCKED = ['.claude/settings.local.json', 'CLAUDE.local.md'];
const COMMIT_CLOCK_SLACK_MS = 5000; // commits older than the previous check came from a branch switch, not this command

function report(lines) {
  process.stderr.write(`${lines.join('\n')}\n`);
  process.exit(2);
}

const baselineOnly = process.argv.includes('--baseline');
let input;
try {
  input = JSON.parse(fs.readFileSync(0, 'utf8'));
} catch {
  if (baselineOnly) process.exit(0);
  report([`Locked-path check after the command (${HOOK}): cannot parse the hook input, so protected files were not checked.`,
    'Tell the owner.']);
}

const git = (args, cwd, encoding = 'utf8') => execFileSync('git', ['-c', 'core.quotePath=false', ...args],
  { cwd, encoding, stdio: ['ignore', 'pipe', 'ignore'], maxBuffer: 64 * 1024 * 1024 });
const tryGit = (args, cwd, encoding) => { try { return git(args, cwd, encoding); } catch { return null; } };
const digest = (buf) => (buf === null ? 'none' : crypto.createHash('sha256').update(buf).digest('hex').slice(0, 16));

function topLevel(dir) {
  if (!dir) return null;
  const out = tryGit(['rev-parse', '--show-toplevel'], dir);
  return out ? path.resolve(out.trim()) : null;
}

function stateFile(root, session) {
  const key = crypto.createHash('sha256').update(process.platform === 'win32' ? root.toLowerCase() : root).digest('hex').slice(0, 16);
  const name = String(session || 'no-session').replace(/[^A-Za-z0-9_-]/g, '_').slice(0, 64);
  return path.join(os.tmpdir(), 'sochron1k-after', `${key}-${name}.json`);
}

function readState(file) {
  try { return JSON.parse(fs.readFileSync(file, 'utf8')); } catch { return null; }
}

function writeState(file, state) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  const tmp = `${file}.${process.pid}.tmp`;
  fs.writeFileSync(tmp, JSON.stringify(state));
  fs.renameSync(tmp, file);
}

const readFileIn = (root) => (p) => { try { return fs.readFileSync(path.join(root, p)); } catch { return null; } };
const headOf = (root) => tryGit(['rev-parse', '--verify', '-q', 'HEAD'], root)?.trim() || null;
const localKeys = (root) => IGNORED_LOCKED.map((p) => `l|${p}|${digest(readFileIn(root)(p))}`);

/** Record the starting state of this session, unless a check already recorded one. */
function baseline(root, session) {
  const file = stateFile(root, session);
  if (fs.existsSync(file)) return;
  // Only commits and ignored local files get a baseline; a dirty locked path is still reported
  // once at the first check, as it would be without a baseline.
  writeState(file, { head: headOf(root), checkedAt: Date.now(), entries: localKeys(root) });
}

/** Report lines for one working tree: what is new since the previous check of this session. */
function check(root, session) {
  const readAt = (rev) => (p) => tryGit(['show', `${rev}:${p}`], root, 'buffer');
  const readFile = readFileIn(root);
  const head = headOf(root);
  const tracked = head ? parseNameStatusZ(git(['diff', '--name-status', '--no-renames', '-z', 'HEAD'], root)) : [];
  const untracked = git(['ls-files', '--others', '--exclude-standard', '-z'], root)
    .split('\0').filter(Boolean).map((p) => ({ status: 'A', path: p }));
  const violations = [
    ...evaluateLocked([...tracked, ...untracked]),
    ...evaluateAppendOnly(tracked, { readOld: readAt('HEAD'), readNew: readFile }, 'uncommitted'),
  ];

  // Entries carry a content digest, so a further change to an already reported file is new again.
  const current = new Map();
  for (const v of violations) {
    current.set(`v|${v.path}|${digest(readFile(v.path))}`, `  uncommitted  ${v.status}  ${v.path}  (${v.why})`);
  }
  const locals = localKeys(root);
  IGNORED_LOCKED.forEach((p, i) => current.set(locals[i], `  local file   ${p}  (ignored by git but locked; it changed)`));

  const file = stateFile(root, session);
  const prev = readState(file);
  const seen = new Set(prev?.entries ?? []);
  // On the first check of a session, ignored local files only set the baseline.
  const lines = [...current].filter(([key]) => !seen.has(key) && (prev !== null || key.startsWith('v|'))).map(([, line]) => line);

  if (prev?.head && head && prev.head !== head && tryGit(['cat-file', '-e', `${prev.head}^{commit}`], root) !== null) {
    const log = git(['log', '--format=%H%x09%P%x09%ct%x09%s', `${prev.head}..${head}`], root);
    for (const row of log.split(/\r?\n/).filter(Boolean)) {
      const [sha, parents, ct, subject] = row.split('\t');
      if (Number(ct) * 1000 < prev.checkedAt - COMMIT_CLOCK_SLACK_MS) continue;
      const parent = parents.split(' ')[0] || null;
      const diffArgs = parent ? [parent, sha] : ['--root', sha];
      const changes = parseNameStatusZ(git(['diff-tree', '-r', '--no-renames', '--name-status', '-z', ...diffArgs], root));
      const found = [
        ...evaluateLocked(changes),
        ...evaluateAppendOnly(changes, { readOld: parent ? readAt(parent) : () => null, readNew: readAt(sha) }, `commit ${sha.slice(0, 7)}`),
      ];
      for (const v of found) {
        if (seen.has(`v|${v.path}|${digest(readAt(sha)(v.path))}`)) continue; // reported while it was uncommitted
        lines.push(`  commit ${sha.slice(0, 7)} "${subject}"  ${v.status}  ${v.path}  (${v.why})`);
      }
    }
  }

  writeState(file, { head, checkedAt: Date.now(), entries: [...current.keys()] });
  return lines;
}

const projectDir = process.env.CLAUDE_PROJECT_DIR || input.cwd || process.cwd();
if (baselineOnly) {
  try {
    for (const root of new Set([topLevel(projectDir), topLevel(input.cwd)].filter(Boolean))) baseline(root, input.session_id);
  } catch {
    // The post-run check still runs; without a baseline it compares with HEAD as on a first check.
  }
  process.exit(0);
}
let lines;
try {
  const roots = [...new Set([topLevel(projectDir), topLevel(input.cwd)].filter(Boolean))];
  lines = roots.flatMap((root) => check(root, input.session_id).map((l) => (roots.length > 1 ? `${l}  [${root}]` : l)));
} catch (err) {
  report([`Locked-path check after the command (${HOOK}): the check failed (${String(err?.message ?? err).split('\n')[0]}), `
    + 'so protected files were not verified.', 'Tell the owner.']);
}
if (lines.length === 0) process.exit(0);
report([
  `Locked-path check after the command (${HOOK}): protected files changed since the previous check.`,
  ...lines,
  'guard-bash checks the command text before it runs; this check looks at what actually changed and cannot undo it.',
  'Stop. Tell the owner which command ran and what changed. Do not edit, revert or commit these files yourself.',
  'If the owner made or asked for exactly this change, say so, and continue only as the owner instructs.',
]);
