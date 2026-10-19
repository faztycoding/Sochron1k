#!/usr/bin/env node
// PreToolUse hook for Bash|PowerShell|Monitor. Blocks shell commands that would break the
// project's controls (Handbook v5 ch.13, ch.14, Appendix O):
//   git push · reset --hard · clean -f · hook bypass (--no-verify, commit -n, core.hooksPath)
//   commits, merges or rebases on main · discarding all local changes · deleting branches or stashes
//   writes to locked or append-only paths (scripts/controls/rules.mjs)
//   credential reads (.env, SSH keys, Codex auth) · recursive deletes outside the project
//   destructive SQL · piping downloads into a shell
// Exit code 2 blocks the call and tells Claude why. Unreadable input fails closed.
// This is a local guard built on text heuristics. Deny rules and CI are the other layers, and
// AGENTS.md forbids routing around a block.
import { execFileSync } from 'node:child_process';
import { readFileSync } from 'node:fs';
import { containsProtected, matchAppendOnly, matchLocked, toRepoRelative } from '../../scripts/controls/rules.mjs';

function block(reason, hint = '') {
  process.stderr.write(`Blocked by .claude/hooks/guard-bash.mjs: ${reason}.${hint ? ` ${hint}` : ''}\n`);
  process.exit(2);
}

let input;
try {
  input = JSON.parse(readFileSync(0, 'utf8'));
} catch {
  block('cannot parse the hook input', 'Failing closed.');
}

const tool = String(input?.tool_name ?? '');
const command = input?.tool_input?.command;
if (typeof command !== 'string' || command.trim() === '') {
  if (tool === 'Bash' || tool === 'PowerShell') block(`no command in the ${tool} input`, 'Failing closed.');
  process.exit(0);
}

const projectDir = process.env.CLAUDE_PROJECT_DIR || input.cwd || process.cwd();
const cwd = input.cwd || projectDir;
const flat = command.replace(/\\/g, '/');

const LOCKED_FRAGMENTS = [
  'agents.md', 'agents.override.md', 'claude.md', 'claude.local.md', '.claude/settings',
  '.claude/hooks', '.claude/agents', '.claude/skills', '.claude/rules', '.claude/commands',
  '.agents/', '.codex/', '.github/', 'tests/acceptance', 'tests/golden', 'tests/architecture',
  'handbook-core.md', 'scripts/controls', '.gitattributes', 'research/registry', 'docs/hypotheses',
];

// ---- Whole-command checks ------------------------------------------------------------------
if (/(^|[\s"'=:/(<])\.env(\.(?!example\b)[\w-]+)*(?=$|[\s"';|&)<>])/i.test(flat)) {
  block('the command references a .env file', 'Agents never read credentials; use .env.example for variable names.');
}
if (/(\.codex\/auth\.json|\.credentials\.json|(^|[\s"'/])\.ssh\/|\bid_(rsa|ed25519|ecdsa)\b|\.aws\/credentials|(^|[\s"'/])\.netrc\b|\.git-credentials)/i.test(flat)) {
  block('the command touches a credential store', 'Agents never read credentials.');
}
if (/\b(curl|wget|iwr|irm|invoke-webrequest|invoke-restmethod)\b[^|]*\|\s*(sudo\s+)?(sh|bash|zsh|dash|pwsh|powershell|iex|invoke-expression|python[0-9.]*|node)\b/i.test(flat)
  || /\b(iex|invoke-expression)\b/i.test(flat)) {
  block('downloading code and executing it directly is not allowed', 'Propose the dependency through the dependency-admission review instead.');
}
if (/\b(drop\s+(table|database|schema|view|index)|truncate\s+table)\b/i.test(flat)) {
  block('destructive SQL (DROP/TRUNCATE) in a shell command', 'Schema changes go through a reviewed migration; if you only meant to search text, use the Grep tool.');
}
if (/core\.hookspath/i.test(flat)) block('changing core.hooksPath bypasses checks');
if (/-encodedcommand\b/i.test(flat)) block('encoded PowerShell commands are not allowed');

// ---- Tokenizing ----------------------------------------------------------------------------
function splitSegments(s) {
  const segs = [];
  let cur = '';
  let quote = null;
  for (let i = 0; i < s.length; i++) {
    const c = s[i];
    if (quote) {
      cur += c;
      if (c === quote) quote = null;
      continue;
    }
    if (c === '"' || c === "'") { quote = c; cur += c; continue; }
    if (c === ';' || c === '\n' || c === '|' || (c === '&' && s[i + 1] === '&')) {
      segs.push(cur);
      cur = '';
      if ((c === '&' || c === '|') && s[i + 1] === c) i++;
      continue;
    }
    cur += c;
  }
  segs.push(cur);
  return segs.map((x) => x.trim()).filter(Boolean);
}

function tokenize(seg) {
  const out = [];
  let cur = '';
  let quote = null;
  let started = false;
  const flush = () => { if (started) out.push(cur); cur = ''; started = false; };
  for (let i = 0; i < seg.length; i++) {
    const c = seg[i];
    if (quote) {
      if (c === quote) quote = null; else cur += c;
      continue;
    }
    if (c === '"' || c === "'") { quote = c; started = true; continue; }
    if (/\s/.test(c)) { flush(); continue; }
    if (c === '>') {
      let op = '>';
      if (/^[0-9&]$/.test(cur)) { op = cur + op; cur = ''; started = false; } else flush();
      if (seg[i + 1] === '>') { op += '>'; i++; }
      if (seg[i + 1] === '&' && /[0-9-]/.test(seg[i + 2] ?? '')) { op += `&${seg[i + 2]}`; i += 2; }
      out.push(op);
      continue;
    }
    cur += c;
    started = true;
  }
  flush();
  return out;
}

// destructive: deleting or moving a folder that contains a protected path also counts.
function protectedRule(rawToken, { destructive = false } = {}) {
  let t = String(rawToken);
  if (t.startsWith('-')) {
    const eq = t.indexOf('=');
    if (eq < 0) return null;
    t = t.slice(eq + 1);
  }
  if (/^(of|if)=/.test(t)) t = t.slice(3);
  t = t.replace(/\\/g, '/');
  if (!t || /^[a-z][a-z0-9+.-]*:\/\//i.test(t)) return null;
  const rel = toRepoRelative(t, projectDir, cwd);
  if (rel === null) return null;
  if (rel === '') return destructive ? { why: 'the project root' } : null;
  return matchLocked(rel) ?? matchAppendOnly(rel) ?? (destructive ? containsProtected(rel) : null);
}

function dangerousDeleteTarget(rawToken) {
  const t = String(rawToken).replace(/\\/g, '/');
  if (/^(\/|~|~\/.*|\.|\.\/|\.\.|\.\.\/.*|\.?\/?\*|[a-zA-Z]:\/?|%[a-z]+%.*)$/i.test(t)) return true;
  if (t.startsWith('$')) return true; // unexpanded variable: cannot prove it stays inside the project
  const rel = toRepoRelative(t, projectDir, cwd);
  return rel === null || rel === '';
}

let branchCache;
function currentBranch() {
  if (branchCache === undefined) {
    try {
      branchCache = execFileSync('git', ['rev-parse', '--abbrev-ref', 'HEAD'], {
        cwd, encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'],
      }).trim();
    } catch {
      branchCache = null;
    }
  }
  return branchCache;
}

const WRAPPERS = new Set(['sudo', 'command', 'exec', 'time', 'nohup', 'env', 'xargs', 'then', 'do', 'else', '{', '(', '!']);
// Removing or moving: a folder that contains a protected path counts as protected too.
const DESTRUCTIVE = new Set(['rm', 'rmdir', 'unlink', 'shred', 'mv', 'del', 'erase', 'rd', 'move', 'ren', 'rename']);
const PS_DESTRUCTIVE = /^(remove-item|ri|move-item|rename-item)$/i;
// Creating or rewriting in place: only the exact protected path counts.
const CREATIVE = new Set(['truncate', 'touch', 'mkdir', 'chmod', 'chown', 'chattr', 'dd', 'patch', 'icacls', 'attrib', 'tee']);
const PS_CREATIVE = /^(set-content|add-content|out-file|new-item|clear-content|set-item|set-itemproperty|copy-item|ni|sc|ac)$/i;
const WRITE_DEST = new Set(['cp', 'install', 'rsync', 'ln', 'copy', 'xcopy', 'robocopy']);
// Subcommands that can rewrite working-tree files (reset without --hard only moves HEAD/index).
const GIT_PATH_WRITERS = new Set(['checkout', 'restore', 'rm', 'mv', 'apply', 'am', 'stash', 'clean',
  'update-index', 'read-tree', 'filter-branch', 'filter-repo']);
const INTERPRETER = /^(node|nodejs|deno|bun|python[0-9.]*|py|pypy[0-9.]*|ruby|perl|php|pwsh|powershell)(\.exe)?$/i;
const INLINE_FLAG = /^(-c|-e|--eval|-p|--print|-command|-c(o(m(m(a(n(d)?)?)?)?)?)?)$/i;

function analyzeGit(tokens, start) {
  let i = start + 1;
  while (i < tokens.length) {
    const t = tokens[i];
    if (['-C', '-c', '--git-dir', '--work-tree', '--namespace', '--exec-path'].includes(t)) { i += 2; continue; }
    if (t.startsWith('-')) { i++; continue; }
    break;
  }
  const sub = (tokens[i] ?? '').toLowerCase();
  const args = tokens.slice(i + 1);
  const shortFlags = args.filter((a) => /^-[a-zA-Z]+$/.test(a)).join('');

  if (sub === 'push') block('git push is reserved for the owner (Handbook App.O deny list)', 'Commit locally and tell the owner the branch is ready.');
  if (args.includes('--no-verify')) block('--no-verify bypasses hooks and checks');
  if (sub === 'commit' && shortFlags.includes('n')) block('git commit -n bypasses hooks and checks');
  if (sub === 'reset' && args.includes('--hard')) block('git reset --hard can destroy work that is not this task\'s', 'Ask the owner.');
  if (sub === 'clean' && !(args.includes('-n') || args.includes('--dry-run'))) block('git clean deletes untracked files', 'Ask the owner; use --dry-run to inspect.');
  if ((sub === 'checkout' || sub === 'restore')
    && (args.includes('.') || args.includes(':/') || args.includes('*') || args.includes('-f') || args.includes('--force'))
    && !(sub === 'restore' && args.includes('--staged') && !args.includes('--worktree'))) {
    block(`git ${sub} on everything discards all local changes, possibly other people's work`, 'Restore only the files of this task.');
  }
  if (sub === 'branch' && (args.includes('-D') || (args.includes('--delete') && args.includes('--force')))) {
    block('force-deleting a branch can lose unmerged work', 'Ask the owner.');
  }
  if (sub === 'stash' && ['drop', 'clear'].includes((args[0] ?? '').toLowerCase())) block('dropping stashes loses work', 'Ask the owner.');
  if (['commit', 'merge', 'cherry-pick', 'rebase', 'am', 'revert'].includes(sub)) {
    const branch = currentBranch();
    if (branch === 'main' || branch === 'master') {
      block(`git ${sub} on ${branch}`, 'Create a task branch first: git switch -c <type>/<TASK-ID>-<slug>.');
    }
  }
  const unstageOnly = sub === 'restore' && args.includes('--staged') && !args.includes('--worktree');
  if (GIT_PATH_WRITERS.has(sub) && !unstageOnly) {
    const hit = args.map((a) => [a, protectedRule(a, { destructive: true })]).find(([, r]) => r);
    if (hit) block(`git ${sub} would change ${hit[0]} (${hit[1].why})`, 'Ask the owner.');
  }
}

for (const seg of splitSegments(command)) {
  const tokens = tokenize(seg);
  if (tokens.length === 0) continue;

  // Redirect targets: > file, >> file, 2> file
  for (let i = 0; i < tokens.length; i++) {
    const op = tokens[i];
    if (/^[0-9&]?>>?$/.test(op) && tokens[i + 1] !== undefined) {
      const rule = protectedRule(tokens[i + 1]);
      if (rule) block(`redirecting output into ${tokens[i + 1]} (${rule.why})`, 'Ask the owner.');
    }
  }

  let k = 0;
  while (k < tokens.length && (WRAPPERS.has(tokens[k]) || /^[A-Za-z_][A-Za-z0-9_]*=/.test(tokens[k]))) k++;
  const name = (tokens[k] ?? '').replace(/^.*[\\/]/, '').replace(/\.exe$/i, '').toLowerCase();
  const args = tokens.slice(k + 1);

  if (name === 'git') { analyzeGit(tokens, k); continue; }

  // Recursive deletes outside the project, or of the whole project
  const recursiveRm = name === 'rm' && args.some((a) => /^-[a-zA-Z]*[rR][a-zA-Z]*$/.test(a) || a === '--recursive');
  const recursivePs = /^(remove-item|ri|del|erase|rd|rmdir)$/i.test(name)
    && args.some((a) => /^-recurse$/i.test(a) || /^\/s$/i.test(a));
  if (recursiveRm || recursivePs) {
    const targets = args.filter((a) => !/^-/.test(a) && !/^\/[a-z]$/i.test(a));
    const bad = targets.find(dangerousDeleteTarget);
    if (bad !== undefined) block(`recursive delete of ${bad}, which is outside the project or the project root itself`, 'Delete only paths inside the task scope.');
  }

  // Writes to locked or append-only paths
  const findProtected = (list, destructive) => list.map((a) => [a, protectedRule(a, { destructive })]).find(([, r]) => r);
  const destructive = DESTRUCTIVE.has(name) || PS_DESTRUCTIVE.test(name)
    || (name === 'find' && args.some((a) => a === '-delete' || a === '-exec' || a === '-execdir'));
  const creative = CREATIVE.has(name) || PS_CREATIVE.test(name)
    || ((name === 'sed' || name === 'perl') && args.some((a) => /^-i/.test(a) || a === '--in-place'));
  if (destructive || creative) {
    const hit = findProtected(args, destructive);
    if (hit) block(`${name} would change ${hit[0]} (${hit[1].why})`, 'The implementer may not change locked paths; ask the owner.');
  }
  if (WRITE_DEST.has(name)) {
    const operands = args.filter((a) => !a.startsWith('-'));
    const dest = operands[operands.length - 1];
    const rule = dest !== undefined ? protectedRule(dest) : null;
    if (rule) block(`${name} would write into ${dest} (${rule.why})`, 'Ask the owner.');
  }

  // Inline interpreter code that mentions a locked path
  for (let i = k; i < tokens.length; i++) {
    const base = tokens[i].replace(/^.*[\\/]/, '');
    if (!INTERPRETER.test(base)) continue;
    for (let j = i + 1; j < tokens.length - 1; j++) {
      if (INLINE_FLAG.test(tokens[j])) {
        const code = tokens[j + 1].replace(/\\/g, '/').toLowerCase();
        const frag = LOCKED_FRAGMENTS.find((f) => code.includes(f));
        if (frag) block(`inline ${base} code references a locked path (${frag})`, 'Use the Read tool to read files; locked paths are owner-only.');
        break;
      }
    }
  }
}

process.exit(0);
