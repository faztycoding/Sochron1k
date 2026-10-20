#!/usr/bin/env node
// PreToolUse hook for Bash|PowerShell|Monitor. Blocks shell commands that would break the
// project's controls (Handbook v5 ch.13, ch.14, Appendix O):
//   unsafe or unproved git push · reset --hard · clean · hook bypass (--no-verify, commit -n, core.hooksPath)
//   commits, merges or rebases on main, including after a branch switch earlier in the command
//   discarding all local changes · force-deleting branches · dropping stashes
//   writes to locked or append-only paths (scripts/controls/rules.mjs) at their REAL destination:
//     cd/pushd/Set-Location and subshells inside the command, copies into folders (cp x . / -t /
//     -Destination), redirects, tee, output flags (curl -o, wget -O, sort -o, -OutFile), archive
//     extraction, the target files listed inside patches (git apply, git am, patch), nested shell
//     strings (bash -c, eval, $(...)) and arguments from xargs (cannot be inspected)
//   credential reads (.env, SSH keys, Codex auth) · recursive deletes outside the project
//   destructive SQL · piping downloads into a shell
// Exit code 2 blocks the call and tells Claude why. Unreadable input fails closed.
// Limits: a text-level guard cannot see what a program does once it runs (python x.py or
// node x.mjs opening files themselves). Deny rules and CI (control-gate) are the other layers,
// and AGENTS.md forbids routing around a block.
import { execFileSync } from 'node:child_process';
import { readFileSync, statSync, realpathSync } from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import { containsProtected, matchAppendOnly, matchLocked, resolvePath, toRepoRelative } from '../../scripts/controls/rules.mjs';

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
const flat = command.replace(/\\/g, '/');
const home = os.homedir().replace(/\\/g, '/');

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
// Keep parentheses as scope boundaries. Braces group commands in the caller's directory.
// Quotes, POSIX backticks, ${var} and @{hashtable} keep their existing contents together.
function posixEscape(s, i, quote, syntax) {
  return syntax === 'posix' && s[i] === '\\' && i + 1 < s.length && quote !== "'"
    && (quote !== '"' || '$`"\\\n'.includes(s[i + 1]));
}

function nextLogical(s, i, syntax) {
  while (syntax === 'posix' && s[i] === '\\' && s[i + 1] === '\n') i += 2;
  return i;
}

const POSIX_WORD_BREAK = /[ \t\n;&|()<>]/;

function splitSegments(s, syntax) {
  const segs = [];
  let cur = '';
  let quote = null;
  let braceDepth = 0;
  const parameterQuotes = [];
  let wordStart = true;
  for (let i = 0; i < s.length; i++) {
    const c = s[i];
    if (syntax === 'posix' && !quote && braceDepth === 0 && wordStart && c === '#') {
      // Comments end at the physical newline; none of their contents are shell syntax.
      const end = s.indexOf('\n', i);
      i = end < 0 ? s.length : end - 1;
      continue;
    }
    if (posixEscape(s, i, quote, syntax)) {
      // Keep quoting for token decoding; a line continuation contributes no character.
      if (s[i + 1] !== '\n') { cur += c + s[i + 1]; wordStart = false; }
      i++;
      continue;
    }
    const next = nextLogical(s, i + 1, syntax);
    if (syntax === 'posix' && ((quote !== "'" && quote !== '`' && c === '$')
      || (!quote && braceDepth === 0 && (c === '<' || c === '>'))) && s[next] === '(') {
      const end = substitutionEnd(s, next + 1, syntax);
      cur += c + '(' + s.slice(next + 1, end + 1);
      i = end;
      wordStart = false;
      continue;
    }
    if (syntax === 'posix' && quote !== "'" && quote !== '`' && c === '$' && s[next] === '{') {
      braceDepth++;
      parameterQuotes.push(quote);
      quote = null;
      cur += '${';
      i = next;
      wordStart = false;
      continue;
    }
    if (quote) {
      cur += c;
      if (c === quote) quote = null;
      continue;
    }
    // An apostrophe in a parameter default under double quotes is literal.
    if (c === '"' || (c === "'" && !parameterQuotes.includes('"')) || (c === '`' && syntax === 'posix')) { quote = c; cur += c; wordStart = false; continue; }
    if (syntax !== 'posix' && c === '{' && (s[i - 1] === '$' || s[i - 1] === '@')) { braceDepth++; cur += c; continue; }
    if (c === '}' && braceDepth > 0) {
      braceDepth--;
      if (syntax === 'posix') quote = parameterQuotes.pop();
      cur += c;
      wordStart = false;
      continue;
    }
    if (syntax === 'posix' && braceDepth > 0) { cur += c; wordStart = false; continue; }
    wordStart = braceDepth === 0 && POSIX_WORD_BREAK.test(c);
    const pairOp = (c === '&' || c === '|') && s[next] === c;
    if (c === ';' || c === '\n' || c === '|' || pairOp || c === '(' || c === ')' || c === '{' || c === '}') {
      segs.push(cur);
      cur = '';
      if (c === '(' || c === ')') segs.push(c);
      if (pairOp) i = next;
      continue;
    }
    cur += c;
  }
  if (parameterQuotes.length) block('unterminated parameter expansion');
  segs.push(cur);
  return segs.filter((x) => x.trim() !== '');
}

function substitutionEnd(s, start, syntax, level = 0) {
  if (level > 4) block('command substitution nests too deeply to inspect');
  let quote = null;
  let depth = 1;
  let braceDepth = 0;
  const parameterQuotes = [];
  let wordStart = true;
  for (let i = start; i < s.length; i++) {
    const c = s[i];
    if (syntax === 'posix' && !quote && braceDepth === 0 && wordStart && c === '#') {
      const end = s.indexOf('\n', i);
      i = end < 0 ? s.length : end - 1;
      continue;
    }
    if (posixEscape(s, i, quote, syntax)) {
      if (s[i + 1] !== '\n') wordStart = false;
      i++;
      continue;
    }
    if (quote === "'") { if (c === quote) quote = null; continue; }
    const next = nextLogical(s, i + 1, syntax);
    if ((c === '$' || (syntax === 'posix' && !quote && braceDepth === 0 && (c === '<' || c === '>')))
      && s[next] === '(') { i = substitutionEnd(s, next + 1, syntax, level + 1); wordStart = false; continue; }
    if (syntax === 'posix' && c === '$' && s[next] === '{') {
      braceDepth++;
      parameterQuotes.push(quote);
      quote = null;
      i = next;
      wordStart = false;
      continue;
    }
    if (quote) { if (c === quote) quote = null; continue; }
    if (c === '"' || (c === "'" && !parameterQuotes.includes('"'))) { quote = c; wordStart = false; continue; }
    if (c === '}' && braceDepth > 0) { braceDepth--; quote = parameterQuotes.pop(); wordStart = false; continue; }
    if (braceDepth > 0) { wordStart = false; continue; }
    wordStart = braceDepth === 0 && POSIX_WORD_BREAK.test(c);
    if (c === '(') depth++;
    else if (c === ')' && --depth === 0) return i;
  }
  block('unterminated command substitution');
}

// Command substitutions that splitSegments cannot see: $(...) inside double quotes, and `...`.
function substitutions(s, syntax) {
  if (syntax === 'cmd') return [];
  const out = [];
  let single = false;
  let double = false;
  for (let i = 0; i < s.length; i++) {
    const c = s[i];
    if (posixEscape(s, i, single ? "'" : double ? '"' : null, syntax)) { i++; continue; }
    if (c === "'" && !double) { single = !single; continue; }
    if (single) continue;
    if (c === '"') { double = !double; continue; }
    const next = nextLogical(s, i + 1, syntax);
    if (((double || syntax === 'posix') && c === '$'
      || (syntax === 'posix' && !double && (c === '<' || c === '>'))) && s[next] === '(') {
      const j = substitutionEnd(s, next + 1, syntax);
      out.push(s.slice(next + 1, j));
      i = j;
    } else if (c === '`' && syntax !== 'powershell') {
      const j = s.indexOf('`', i + 1);
      if (j < 0) break;
      if (syntax === 'posix' && s.slice(i + 1, j).includes('\\')) {
        block('escaped legacy backtick substitution cannot be inspected reliably', 'Use $(...) with an explicit shell.');
      }
      out.push(s.slice(i + 1, j));
      i = j;
    }
  }
  return out;
}

function tokenize(seg, syntax) {
  const out = [];
  let cur = '';
  let quote = null;
  let started = false;
  const flush = () => { if (started) out.push({ value: cur, operator: false }); cur = ''; started = false; };
  for (let i = 0; i < seg.length; i++) {
    const c = seg[i];
    if (posixEscape(seg, i, quote, syntax)) {
      if (seg[i + 1] !== '\n') { cur += seg[i + 1]; started = true; }
      i++;
      continue;
    }
    const next = nextLogical(seg, i + 1, syntax);
    if (syntax === 'posix' && ((quote !== "'" && c === '$') || (!quote && (c === '<' || c === '>')))
      && seg[next] === '(') {
      const end = substitutionEnd(seg, next + 1, syntax);
      cur += c + '(' + seg.slice(next + 1, end + 1);
      started = true;
      i = end;
      continue;
    }
    if (quote) {
      if (c === quote) quote = null; else cur += c;
      continue;
    }
    if (c === '"' || c === "'") { quote = c; started = true; continue; }
    if (/\s/.test(c)) { flush(); continue; }
    if (c === '>' || c === '<') {
      let op = c;
      if (c === '>' && /^[0-9&]$/.test(cur)) { op = cur + op; cur = ''; started = false; } else flush();
      while (seg[i + 1] === c) { op += c; i++; }
      if (c === '>' && seg[i + 1] === '&' && /[0-9-]/.test(seg[i + 2] ?? '')) { op += `&${seg[i + 2]}`; i += 2; }
      out.push({ value: op, operator: true });
      continue;
    }
    cur += c;
    started = true;
  }
  flush();
  return out;
}

function splitRedirects(tokens) {
  const words = [];
  const outputs = [];
  const inputs = [];
  for (let i = 0; i < tokens.length; i++) {
    const { value: t, operator } = tokens[i];
    if (!operator) { words.push(t); continue; }
    if (/^[0-9&]?>>?&[0-9-]$/.test(t)) continue; // 2>&1
    if (/^[0-9&]?>>?$/.test(t)) { if (tokens[i + 1] !== undefined) outputs.push(tokens[++i].value); continue; }
    if (t === '<') { if (tokens[i + 1] !== undefined) inputs.push(tokens[++i].value); continue; }
    if (/^<<<?$/.test(t)) { i++; continue; } // heredoc delimiter or here-string
    words.push(t);
  }
  return { words, outputs, inputs };
}

// ---- Paths ---------------------------------------------------------------------------------
let cwd = input.cwd || projectDir; // effective directory; null once it cannot be known
const dirStack = [];
const branchStates = new Map(); // effective branches by worktree root; null means unknown
let unknownBranchSwitch = false;

function locate(rawToken, dir = cwd) {
  let t = String(rawToken).replace(/\\/g, '/');
  if (!t || /^[a-z][a-z0-9+.-]*:\/\//i.test(t)) return { kind: 'url' };
  t = t.replace(/^~(?=\/|$)/, home);
  if (/^[$%]/.test(t) || t.includes('$(') || t.includes('`')) return { kind: 'unknown' };
  if (/^[a-zA-Z]:\//.test(t) && process.platform !== 'win32') return { kind: 'outside' };
  const absolute = /^([a-zA-Z]:\/|\/)/.test(t);
  if (dir === null && !absolute) return { kind: 'unknown' };
  const abs = resolvePath(t, dir ?? projectDir);
  const rel = toRepoRelative(abs, projectDir);
  return rel === null ? { kind: 'outside', abs } : { kind: 'inside', abs, rel };
}

// destructive: deleting or moving a folder that contains a protected path also counts.
function protectedRule(rawToken, { destructive = false, dir = cwd } = {}) {
  let t = String(rawToken);
  if (t.startsWith('-')) {
    const eq = t.indexOf('=');
    if (eq < 0) return null;
    t = t.slice(eq + 1);
  }
  if (/^if=/i.test(t)) return null; // dd input file is only read
  if (/^of=/i.test(t)) t = t.slice(3);
  const loc = locate(t, dir);
  if (loc.kind === 'url' || loc.kind === 'outside') return null;
  if (loc.kind === 'unknown') return { why: 'a path that cannot be resolved here (variable or unknown directory)' };
  if (loc.rel === '') return destructive ? { why: 'the project root' } : null;
  return matchLocked(loc.rel) ?? matchAppendOnly(loc.rel) ?? (destructive ? containsProtected(loc.rel) : null);
}

function dangerousDeleteTarget(rawToken) {
  const t = String(rawToken).replace(/\\/g, '/');
  if (/^(\/|~|~\/.*|\.|\.\/|\.\.|\.\.\/.*|\.?\/?\*|[a-zA-Z]:\/?|%[a-z]+%.*)$/i.test(t)) return true;
  const loc = locate(t);
  if (loc.kind === 'url') return false;
  if (loc.kind !== 'inside') return true;
  return loc.rel === '';
}

function cwdIsSensitive() {
  if (cwd === null) return true;
  const rel = toRepoRelative(cwd, projectDir);
  if (rel === null || rel === '') return false;
  return Boolean(matchLocked(rel) || containsProtected(rel));
}

const CD = new Set(['cd', 'chdir', 'pushd', 'set-location', 'sl', 'push-location']);
const POP = new Set(['popd', 'pop-location']);
function changeDirectory(name, args) {
  if (POP.has(name)) { cwd = dirStack.length ? dirStack.pop() : null; return; }
  if (name === 'pushd' || name === 'push-location') dirStack.push(cwd);
  const operands = args.filter((a) => !a.startsWith('-') && !/^\/d$/i.test(a));
  const target = operands[0];
  if (target === undefined) { cwd = home; return; }
  if (target === '-') { cwd = null; return; }
  const loc = locate(target);
  cwd = loc.abs ?? null;
}

// ---- Git -----------------------------------------------------------------------------------
function gitOut(args, dir) {
  if (dir === null) return null;
  try {
    return execFileSync('git', args, { cwd: dir, encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'] }).trim();
  } catch {
    return null;
  }
}
function repositoryRoot(dir) {
  const root = gitOut(['rev-parse', '--show-toplevel'], dir)?.replace(/\\/g, '/');
  return root && process.platform === 'win32' ? root.toLowerCase() : root;
}
function currentBranch(dir) {
  const root = repositoryRoot(dir);
  // A later textual switch may fail at runtime; uncertainty lasts for this whole call.
  if (!root || unknownBranchSwitch) return null;
  if (!branchStates.has(root)) branchStates.set(root, gitOut(['rev-parse', '--abbrev-ref', 'HEAD'], dir));
  return branchStates.get(root);
}
// Branch after `git switch|checkout ...`: a name, '(detached)', null (unknown) or undefined (no change).
function branchAfterSwitch(sub, args, dir) {
  const valueOf = (flags) => {
    const j = args.findIndex((a) => flags.includes(a));
    return j >= 0 ? (args[j + 1] ?? null) : undefined;
  };
  const created = sub === 'switch' ? valueOf(['-c', '-C', '--create', '--force-create']) : valueOf(['-b', '-B']);
  if (created !== undefined) return created;
  if (args.includes('--detach') || (sub === 'switch' && args.includes('-d'))) return '(detached)';
  if (sub === 'checkout' && args.includes('--')) return undefined; // paths only
  const operand = args.find((a) => a === '-' || !a.startsWith('-'));
  if (operand === undefined) return undefined;
  if (operand === '-') return null; // "previous branch": cannot be known from the text
  if (sub === 'switch') return operand;
  const isBranch = operand === 'main' || operand === 'master'
    || gitOut(['rev-parse', '--verify', '--quiet', `refs/heads/${operand}`], dir) !== null;
  return isBranch ? operand : undefined; // `git checkout <path>` keeps the branch
}

function patchTargets(text) {
  const out = new Set();
  for (const line of text.split(/\r?\n/)) {
    let m;
    if ((m = /^diff --git a\/(.+?) b\/(.+)$/.exec(line))) { out.add(m[1]); out.add(m[2]); continue; }
    if ((m = /^(?:---|\+\+\+) (.+?)(?:\t.*)?$/.exec(line))) {
      const p = m[1].replace(/^[ab]\//, '');
      if (p !== '/dev/null') out.add(p);
      continue;
    }
    if ((m = /^(?:rename|copy) (?:from|to) (.+)$/.exec(line))) out.add(m[1]);
  }
  return [...out];
}
function checkPatchFile(file, dir, label) {
  const loc = locate(file, dir);
  if (!loc.abs) block(`${label}: cannot locate the patch file ${file}`, 'Save the patch to a known file first.');
  let text;
  try {
    text = readFileSync(loc.abs, 'utf8');
  } catch {
    block(`${label}: cannot read the patch file ${file}`);
  }
  for (const target of patchTargets(text)) {
    for (const base of [dir, projectDir]) { // git resolves patch paths from the repository top
      const rule = protectedRule(target, { destructive: true, dir: base });
      if (rule) block(`${label} would change ${target} (${rule.why})`, 'Locked paths are owner-only; ask the owner to apply this patch.');
    }
  }
}

// D-006 is deliberately a small, literal grammar, not a general shell permission.
// An exception is available only for one top-level action without wrappers or expansions.
function standaloneGit(sub, words, k, i, dir) {
  if (!['Bash', 'PowerShell'].includes(tool) || k !== 0 || i !== 1
    || !new RegExp(`^git(?:\\.exe)?[ \\t]+${sub}(?:[ \\t]|$)`).test(command)
    || /[\r\n;&|<>(){}$`\\*?!#%~\[\]]/.test(command)
    || !/^(?:[^'"\s]+|'[^']*'|"[^"]*")(?:[ \t]+(?:[^'"\s]+|'[^']*'|"[^"]*"))*[ \t]*$/.test(command)) return false;
  // No -C, alternate Git directory, assignment, nested shell or grouped action can use this path.
  return repositoryRoot(dir) !== null && repositoryRoot(dir) === repositoryRoot(projectDir);
}

function pushConfig(key, dir) {
  try {
    return execFileSync('git', ['config', '--get-all', key], {
      cwd: dir, encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'],
    }).trim().split('\n');
  } catch (error) {
    if (error.status === 1) return []; // Missing is different from unreadable configuration.
    block('git push configuration cannot be inspected');
  }
}

function checkTaskPush(words, k, i, args, dir) {
  const refuse = () => block('git push requires one explicit non-force push of the current task branch',
    'Use git push origin HEAD:refs/heads/<current-task-branch> as a separate command.');
  if (!standaloneGit('push', words, k, i, dir)) refuse();
  const branch = currentBranch(dir);
  if (!branch || !/^(feat|fix|chore|spike|research)\/[A-Z][A-Z0-9]*-\d+-[A-Za-z0-9][A-Za-z0-9._/-]*$/.test(branch)) refuse();
  const operands = [...args];
  if (operands[0] === '-u' || operands[0] === '--set-upstream') operands.shift();
  if (operands.length !== 2) refuse();
  const [remote, ref] = operands;
  if (!/^[A-Za-z0-9][A-Za-z0-9._-]*$/.test(remote)) refuse();
  if (!(gitOut(['remote'], dir)?.split('\n') ?? []).includes(remote)) refuse();
  const full = `refs/heads/${branch}`;
  // A source-only ref can inherit a destination from remote.<name>.push.
  const shorthand = ref === branch && pushConfig(`remote.${remote}.push`, dir).length === 0;
  if (!shorthand && !['HEAD', branch, full].some(src => ref === `${src}:${full}`)) refuse();
  for (const key of [`remote.${remote}.mirror`, 'push.followTags', 'push.useForceIfIncludes',
    'submodule.recurse']) {
    if (pushConfig(key, dir).some(value => !/^(false|no|off|0)$/i.test(value))) refuse();
  }
  if (pushConfig('push.recurseSubmodules', dir).some(value => !/^(no|check)$/i.test(value))) refuse();
  if (pushConfig('push.gpgSign', dir).some(value => !/^(false|no|off|0)$/i.test(value))) refuse();
  if (pushConfig('push.pushOption', dir).length > 0) refuse();
}

function proposalApply(words, k, i, args, dir, stdinFiles) {
  if (!standaloneGit('apply', words, k, i, dir) || stdinFiles.length > 0) return false;
  const files = args[0] === '--' ? args.slice(1) : args;
  if (files.length === 0 || files.some(file => file.startsWith('-'))) return false;
  try {
    const root = realpathSync(projectDir);
    const proposalDir = path.join(root, 'docs', 'proposals');
    // Do not let a symlink or junction move the permitted directory itself.
    if (realpathSync(proposalDir) !== proposalDir) return false;
    return files.every(file => {
      const loc = locate(file, dir);
      if (!loc.abs) return false;
      const actual = realpathSync(loc.abs);
      return path.dirname(actual) === proposalDir && statSync(actual).isFile();
    });
  } catch {
    return false; // Missing, unreadable, directory or unresolved patch: no locked-path exception.
  }
}

const GIT_PATH_WRITERS = new Set(['checkout', 'restore', 'rm', 'mv', 'stash', 'clean', 'update-index', 'read-tree',
  'filter-branch', 'filter-repo']);

function analyzeGit(words, k, stdinFiles) {
  let i = k + 1;
  let dir = cwd;
  while (i < words.length) {
    const t = words[i];
    if (t === '-C') { dir = locate(words[i + 1] ?? '', dir).abs ?? null; i += 2; continue; }
    if (['-c', '--git-dir', '--work-tree', '--namespace', '--exec-path'].includes(t)) { i += 2; continue; }
    if (t.startsWith('-')) { i++; continue; }
    break;
  }
  const sub = (words[i] ?? '').toLowerCase();
  const args = words.slice(i + 1);
  const shortFlags = args.filter((a) => /^-[a-zA-Z]+$/.test(a)).join('');

  if (sub === 'push') { checkTaskPush(words, k, i, args, dir); return; }
  if (args.includes('--no-verify')) block('--no-verify bypasses hooks and checks');
  if (sub === 'commit' && shortFlags.includes('n')) block('git commit -n bypasses hooks and checks');
  if (sub === 'reset' && args.includes('--hard')) block('git reset --hard can destroy work that is not this task\'s', 'Ask the owner.');
  if (sub === 'clean' && !(args.includes('-n') || args.includes('--dry-run'))) block('git clean deletes untracked files', 'Ask the owner; use --dry-run to inspect.');
  const unstageOnly = sub === 'restore' && args.includes('--staged') && !args.includes('--worktree');
  if ((sub === 'checkout' || sub === 'restore') && !unstageOnly
    && (args.includes('.') || args.includes(':/') || args.includes('*') || args.includes('-f') || args.includes('--force'))) {
    block(`git ${sub} on everything discards all local changes, possibly other people's work`, 'Restore only the files of this task.');
  }
  if (sub === 'branch' && (args.includes('-D') || (args.includes('--delete') && args.includes('--force')))) {
    block('force-deleting a branch can lose unmerged work', 'Ask the owner.');
  }
  if (sub === 'stash' && ['drop', 'clear'].includes((args[0] ?? '').toLowerCase())) block('dropping stashes loses work', 'Ask the owner.');

  if (sub === 'switch' || sub === 'checkout') {
    const next = branchAfterSwitch(sub, args, dir);
    if (next !== undefined) {
      const root = repositoryRoot(dir);
      if (!root) { unknownBranchSwitch = true; branchStates.clear(); }
      else branchStates.set(root, next);
    }
  }
  if (['commit', 'merge', 'cherry-pick', 'rebase', 'am', 'revert'].includes(sub)) {
    const branch = currentBranch(dir);
    if (branch === null) block(`git ${sub} after the current branch became unknown in this command`, 'Run the branch switch and the commit as separate commands.');
    if (branch === 'main' || branch === 'master') {
      block(`git ${sub} on ${branch}`, 'Create a task branch first: git switch -c <type>/<TASK-ID>-<slug>.');
    }
  }
  if (sub === 'apply' && !standaloneGit('apply', words, k, i, dir)) {
    block('git apply must be one standalone literal command', 'Run each action separately.');
  }
  if (sub === 'apply' || sub === 'am') {
    const inspectOnly = ['--check', '--stat', '--numstat', '--summary'].some((f) => args.includes(f)) && !args.includes('--apply');
    if (!inspectOnly) {
      const files = [...args.filter((a) => !a.startsWith('-')), ...stdinFiles];
      if (files.length === 0) block(`git ${sub} reads a patch from standard input, which cannot be inspected`, 'Save the patch to a file first.');
      const proposal = sub === 'apply' && proposalApply(words, k, i, args, dir, stdinFiles);
      if (!proposal) for (const f of files) checkPatchFile(f, dir, `git ${sub}`);
    }
  }
  if (GIT_PATH_WRITERS.has(sub) && !unstageOnly) {
    const hit = args.map((a) => [a, protectedRule(a, { destructive: true, dir })]).find(([, r]) => r);
    if (hit) block(`git ${sub} would change ${hit[0]} (${hit[1].why})`, 'Ask the owner.');
  }
}

// ---- Command classes -----------------------------------------------------------------------
const WRAPPERS = new Set(['sudo', 'command', 'exec', 'time', 'nohup', 'env', 'xargs', 'then', 'do', 'else', '!', 'nice']);
const DELETE_LIKE = new Set(['rm', 'rmdir', 'unlink', 'shred', 'del', 'erase', 'rd', 'remove-item', 'ri']);
const CREATIVE = new Set(['truncate', 'touch', 'mkdir', 'chmod', 'chown', 'chattr', 'dd', 'icacls', 'attrib', 'tee',
  'set-content', 'add-content', 'out-file', 'new-item', 'ni', 'clear-content', 'set-item', 'set-itemproperty', 'sc', 'ac']);
const COPY_LIKE = new Set(['cp', 'install', 'rsync', 'ln', 'copy', 'xcopy', 'robocopy', 'copy-item', 'cpi']);
const MOVE_LIKE = new Set(['mv', 'move', 'move-item', 'mi']);
const RENAME_LIKE = new Set(['ren', 'rename', 'rename-item', 'rni']);
const CMD_STYLE = new Set(['copy', 'xcopy', 'robocopy', 'move', 'del', 'erase', 'rd']);
const SHELLS = new Set(['bash', 'sh', 'zsh', 'dash', 'ksh', 'cmd', 'pwsh', 'powershell']);
const INTERPRETER = /^(node|nodejs|deno|bun|python[0-9.]*|py|pypy[0-9.]*|ruby|perl|php)$/i;
const INLINE_FLAG = /^(-c|-e|--eval|-p|--print)$/i;
const SHELL_FLAG = /^(-c|\/c|\/k|-command|-c(o(m(m(a(n(d)?)?)?)?)?)?)$/i;
const OUTPUT_FLAGS = new Map([
  ['curl', ['-o', '--output']], ['wget', ['-O', '--output-document']], ['sort', ['-o', '--output']],
  ['invoke-webrequest', ['-outfile']], ['iwr', ['-outfile']], ['invoke-restmethod', ['-outfile']], ['irm', ['-outfile']],
]);

function looksLikeDir(dest) {
  if (dest === '.' || dest === '..' || /[\\/]$/.test(dest)) return true;
  const loc = locate(dest);
  if (!loc.abs) return false;
  try { return statSync(loc.abs).isDirectory(); } catch { return false; }
}
function joinTarget(dest, src) {
  const base = String(src).replace(/\\/g, '/').replace(/\/+$/, '').split('/').pop();
  return `${String(dest).replace(/\\/g, '/').replace(/\/+$/, '')}/${base}`;
}
// Where a copy or move really writes: the destination itself, or <dest>/<source name> for folders.
function copyPlan(name, args) {
  const cmdStyle = CMD_STYLE.has(name);
  const posix = ['cp', 'install', 'rsync', 'ln', 'mv'].includes(name);
  const recursive = name === 'robocopy' || name === 'xcopy'
    || (posix && args.some((a) => /^-[a-zA-Z]*[rRa][a-zA-Z]*$/.test(a) || a === '--recursive' || a === '--archive'))
    || (!posix && !cmdStyle && args.some((a) => /^-recurse$/i.test(a)))
    || (cmdStyle && args.some((a) => /^\/[se]$/i.test(a)));
  let targetDir;
  let destParam;
  let noTargetDir = false;
  const operands = [];
  for (let i = 0; i < args.length; i++) {
    const a = args[i];
    if (a === '-t' || a === '--target-directory') { targetDir = args[++i]; continue; }
    if (a.startsWith('--target-directory=')) { targetDir = a.slice(a.indexOf('=') + 1); continue; }
    if (a === '-T' || a === '--no-target-directory') { noTargetDir = true; continue; }
    if (/^-(destination|dest)$/i.test(a)) { destParam = args[++i]; continue; }
    if (/^-(path|literalpath)$/i.test(a)) { operands.push(args[++i]); continue; }
    if (a === '-S' || a === '--suffix') { i++; continue; }
    if (a.startsWith('-') || (cmdStyle && /^\/[a-z]+(:\S*)?$/i.test(a))) continue;
    operands.push(a);
  }
  let dest;
  let sources;
  if (targetDir !== undefined) { dest = targetDir; sources = operands; }
  else if (destParam !== undefined) { dest = destParam; sources = operands; }
  else if (name === 'robocopy') { dest = operands[1]; sources = []; }
  else { dest = operands[operands.length - 1]; sources = operands.slice(0, -1); }
  if (dest === undefined) return { checks: [], sources };
  const filesLandInDest = name === 'robocopy' || name === 'xcopy';
  const destIsDir = !noTargetDir && (targetDir !== undefined || filesLandInDest || sources.length > 1 || looksLikeDir(dest));
  const checks = [{ path: dest, destructive: filesLandInDest }];
  if (destIsDir && !filesLandInDest) {
    for (const s of sources) checks.push({ path: joinTarget(dest, s), destructive: recursive || MOVE_LIKE.has(name) });
  }
  return { checks, sources };
}

function outputFlagTargets(name, args) {
  const flags = OUTPUT_FLAGS.get(name);
  if (!flags) return [];
  const ps = name.startsWith('invoke-') || name === 'iwr' || name === 'irm';
  const out = [];
  for (let i = 0; i < args.length; i++) {
    const a = args[i];
    for (const f of flags) {
      const same = ps ? a.toLowerCase() === f : a === f;
      if (same) out.push(args[i + 1]);
      else if (f.startsWith('--') && a.startsWith(`${f}=`)) out.push(a.slice(f.length + 1));
      else if (!ps && /^-[A-Za-z]$/.test(f) && a.startsWith(f) && a.length > f.length) out.push(a.slice(f.length));
    }
  }
  return out.filter((x) => x !== undefined);
}

function extractionTargets(name, args) {
  if (name === 'tar' && args.some((a, j) => a === '--extract' || a === '--get'
    || ((j === 0 || a.startsWith('-')) && !a.startsWith('--') && /^-?[a-zA-Z]*x[a-zA-Z]*$/.test(a)))) {
    const j = args.findIndex((a) => a === '-C' || a === '--directory');
    const eq = args.find((a) => a.startsWith('--directory='));
    return [j >= 0 ? args[j + 1] : eq ? eq.slice(12) : '.'];
  }
  if (name === 'unzip') {
    const j = args.indexOf('-d');
    return [j >= 0 ? args[j + 1] : '.'];
  }
  if (name === 'expand-archive') {
    const j = args.findIndex((a) => /^-destinationpath$/i.test(a));
    return [j >= 0 ? args[j + 1] : '.'];
  }
  if (name === '7z' && (args[0] === 'x' || args[0] === 'e')) {
    const o = args.find((a) => a.startsWith('-o'));
    return [o ? o.slice(2) : '.'];
  }
  return [];
}

// ---- Main analysis -------------------------------------------------------------------------
function analyzeSegment(seg, depth, syntax) {
  const { words, outputs, inputs } = splitRedirects(tokenize(seg, syntax));
  for (const target of outputs) {
    const rule = protectedRule(target);
    if (rule) block(`redirecting output into ${target} (${rule.why})`, 'Ask the owner.');
  }
  let k = 0;
  while (k < words.length && (WRAPPERS.has(words[k]) || /^[A-Za-z_][A-Za-z0-9_]*=/.test(words[k]))) k++;
  if (k >= words.length) return;
  const viaXargs = words.slice(0, k).includes('xargs');
  const name = words[k].replace(/^.*[\\/]/, '').replace(/\.exe$/i, '').toLowerCase();
  const args = words.slice(k + 1);

  if (CD.has(name) || POP.has(name)) { changeDirectory(name, args); return; }
  if (name === 'git') { analyzeGit(words, k, inputs); return; }

  const writes = DELETE_LIKE.has(name) || CREATIVE.has(name) || COPY_LIKE.has(name) || MOVE_LIKE.has(name)
    || RENAME_LIKE.has(name) || name === 'patch' || ((name === 'sed' || name === 'perl') && args.some((a) => /^-i/.test(a)));
  if (viaXargs && writes) block(`${name} receives its paths from xargs, which cannot be inspected`, 'List the paths explicitly.');

  // Recursive deletes outside the project, or of the whole project
  const recursiveRm = name === 'rm' && args.some((a) => /^-[a-zA-Z]*[rR][a-zA-Z]*$/.test(a) || a === '--recursive');
  const recursivePs = /^(remove-item|ri|del|erase|rd|rmdir)$/.test(name) && args.some((a) => /^-recurse$/i.test(a) || /^\/s$/i.test(a));
  if (recursiveRm || recursivePs) {
    const targets = args.filter((a) => !a.startsWith('-') && !/^\/[a-z]$/i.test(a));
    const bad = targets.find(dangerousDeleteTarget);
    if (bad !== undefined) block(`recursive delete of ${bad}, which is outside the project or the project root itself`, 'Delete only paths inside the task scope.');
  }

  const findProtected = (list, destructive) => list
    .filter((a) => !(CMD_STYLE.has(name) && /^\/[a-z]+$/i.test(a)))
    .map((a) => [a, protectedRule(a, { destructive })]).find(([, r]) => r);
  const deleting = DELETE_LIKE.has(name) || RENAME_LIKE.has(name)
    || (name === 'find' && args.some((a) => a === '-delete' || a === '-exec' || a === '-execdir'));
  const creative = CREATIVE.has(name) || ((name === 'sed' || name === 'perl') && args.some((a) => /^-i/.test(a) || a === '--in-place'));
  if (deleting || creative) {
    const hit = findProtected(args, deleting);
    if (hit) block(`${name} would change ${hit[0]} (${hit[1].why})`, 'The implementer may not change locked paths; ask the owner.');
  }

  if (COPY_LIKE.has(name) || MOVE_LIKE.has(name)) {
    const plan = copyPlan(name, args);
    for (const c of plan.checks) {
      const rule = protectedRule(c.path, { destructive: c.destructive });
      if (rule) block(`${name} would write ${c.path} (${rule.why})`, 'Ask the owner.');
    }
    if (MOVE_LIKE.has(name)) {
      for (const s of plan.sources) {
        const rule = protectedRule(s, { destructive: true });
        if (rule) block(`${name} would remove ${s} (${rule.why})`, 'Ask the owner.');
      }
    }
  }

  for (const target of outputFlagTargets(name, args)) {
    const rule = protectedRule(target);
    if (rule) block(`${name} would write ${target} (${rule.why})`, 'Ask the owner.');
  }
  for (const dest of extractionTargets(name, args)) {
    const rule = protectedRule(dest, { destructive: true });
    if (rule) block(`${name} would extract into ${dest} (${rule.why})`, 'Extract into a folder outside protected paths.');
  }

  if (name === 'patch') {
    const patchFiles = [...inputs];
    const operands = [];
    for (let i = 0; i < args.length; i++) {
      const a = args[i];
      if (a === '-i' || a === '--input') { patchFiles.push(args[++i]); continue; }
      if (a.startsWith('--input=')) { patchFiles.push(a.slice(8)); continue; }
      if (/^-(p|d|D|o|r|B|z|F|V|Y|g)$/.test(a)) { i++; continue; }
      if (a.startsWith('-')) continue;
      operands.push(a);
    }
    if (operands[0] !== undefined) {
      const rule = protectedRule(operands[0], { destructive: true });
      if (rule) block(`patch would change ${operands[0]} (${rule.why})`, 'Ask the owner.');
    }
    if (operands[1] !== undefined) patchFiles.push(operands[1]);
    if (!args.includes('--dry-run')) {
      if (patchFiles.length === 0) block('patch reads from standard input, which cannot be inspected', 'Save the patch to a file first.');
      for (const f of patchFiles) checkPatchFile(f, cwd, 'patch');
    }
  }

  // Nested shell strings are analyzed as commands; inline interpreter code is checked for locked paths.
  if (SHELLS.has(name) || name === 'eval') {
    const j = name === 'eval' ? -1 : args.findIndex((a) => SHELL_FLAG.test(a)
      || (name === 'cmd' && /^\/\/[ck]$/i.test(a)));
    const nested = name === 'eval' ? args.join(' ') : (j >= 0 ? args.slice(j + 1).join(' ') : null);
    if (nested !== null && nested !== '') {
      if (name === 'eval') analyzeCommand(nested, depth + 1, syntax);
      else {
        const childSyntax = name === 'cmd' ? 'cmd' : /^(pwsh|powershell)$/.test(name) ? 'powershell' : 'posix';
        analyzeChildCommand(nested, depth + 1, childSyntax);
      }
    }
  }
  for (let i = k; i < words.length; i++) {
    const base = words[i].replace(/^.*[\\/]/, '').replace(/\.exe$/i, '');
    if (!INTERPRETER.test(base)) continue;
    for (let j = i + 1; j < words.length - 1; j++) {
      if (!INLINE_FLAG.test(words[j])) continue;
      const code = words[j + 1].replace(/\\/g, '/').toLowerCase();
      const frag = LOCKED_FRAGMENTS.find((f) => code.includes(f));
      if (frag) block(`inline ${base} code references a locked path (${frag})`, 'Use the Read tool to read files; locked paths are owner-only.');
      if (cwdIsSensitive()) block(`inline ${base} code running inside a protected folder`, 'Run it from the project root or a task folder.');
      break;
    }
  }
}

function analyzeChildCommand(text, depth, syntax) {
  const savedCwd = cwd;
  const savedStack = [...dirStack];
  try { analyzeCommand(text, depth, syntax); }
  finally {
    cwd = savedCwd;
    dirStack.splice(0, dirStack.length, ...savedStack);
  }
  // Git switches alter that worktree, so its branch forecast remains visible to the parent.
}

function analyzeCommand(text, depth = 0, syntax = 'unknown') {
  if (depth > 4) block('the command nests shells too deeply to inspect', 'Split it into separate commands.');
  const groups = [];
  for (const seg of splitSegments(text, syntax)) {
    if (seg === '(') {
      if (syntax === 'unknown') block('cannot determine directory scope of this grouped command', 'Use an explicit shell.');
      groups.push(syntax === 'posix' ? [cwd, [...dirStack]] : null);
      continue;
    }
    if (seg === ')') {
      if (groups.length === 0) block('unmatched closing parenthesis in the command', 'Split it into separate commands.');
      const saved = groups.pop();
      if (saved) { cwd = saved[0]; dirStack.splice(0, dirStack.length, ...saved[1]); }
      continue;
    }
    // Analyze substitutions where they occur, after directory changes in earlier segments.
    for (const sub of substitutions(seg, syntax)) {
      if (syntax === 'unknown') block('cannot determine directory scope of this substitution', 'Use an explicit shell.');
      if (syntax === 'posix') analyzeChildCommand(sub, depth + 1, syntax);
      else analyzeCommand(sub, depth + 1, syntax);
    }
    analyzeSegment(seg, depth, syntax);
  }
  if (groups.length) block('unmatched opening parenthesis in the command', 'Split it into separate commands.');
}

analyzeCommand(command, 0, tool === 'Bash' ? 'posix' : tool === 'PowerShell' ? 'powershell' : 'unknown');
process.exit(0);
