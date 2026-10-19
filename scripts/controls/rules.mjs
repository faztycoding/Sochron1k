// Locked and append-only path rules for Sochron1k: the single source of truth used by the
// Claude Code hooks (.claude/hooks/*.mjs) and by CI (scripts/controls/check-locked-paths.mjs).
// Handbook v5 ch.9, ch.13, ch.19, ch.34 and Appendix O. Changing this file is a control change
// (Q6): it needs owner approval and the PR label below.
import fs from 'node:fs';
import path from 'node:path';

export const APPROVAL_LABEL = 'owner-approved-control-change';

/** Paths the implementer may not change (files, and folders including the folder itself).
 *  Matched against repo-relative POSIX paths, case-insensitively. */
export const LOCKED_RULES = [
  { id: 'instructions', re: /(^|\/)(AGENTS(\.override)?|CLAUDE(\.local)?)\.md$/i,
    why: 'agent instruction file' },
  { id: 'claude-config', re: /^\.claude\/(settings(\.local)?\.json$|CLAUDE\.md$|(hooks|agents|skills|rules|commands)(\/|$))/i,
    why: 'Claude Code settings, hooks, agents or skills' },
  { id: 'codex-config', re: /^\.(agents|codex)(\/|$)/i, why: 'Codex skills or configuration' },
  { id: 'ci', re: /^\.github(\/|$)/i, why: 'CI workflow or PR template' },
  { id: 'locked-tests', re: /^tests\/(acceptance|golden|architecture)(\/|$)/i,
    why: 'locked acceptance, golden or architecture tests' },
  { id: 'process-rules', re: /^docs\/HANDBOOK-CORE\.md$/i, why: 'process rules (HANDBOOK-CORE)' },
  { id: 'verifiers', re: /^scripts\/controls(\/|$)/i, why: 'control-plane verifier scripts' },
  { id: 'line-endings', re: /^\.gitattributes$/i, why: 'line-ending policy for scripts' },
];

/** Concrete protected locations, used to stop deleting or moving a folder that contains them. */
export const PROTECTED_ANCHORS = [
  'AGENTS.md', 'CLAUDE.md', '.claude/settings.json', '.claude/settings.local.json', '.claude/hooks',
  '.claude/agents', '.claude/skills', '.claude/rules', '.claude/commands', '.agents', '.codex', '.github',
  'tests/acceptance', 'tests/golden', 'tests/architecture', 'docs/HANDBOOK-CORE.md', 'docs/hypotheses',
  'scripts/controls', 'research/registry', '.gitattributes',
];

/** Paths that may only grow. 'immutable': never changes once committed. 'append': only gains lines. */
export const APPEND_ONLY_RULES = [
  { id: 'hypotheses', re: /^docs\/hypotheses\/H\d{3,}[^/]*\.md$/i, mode: 'immutable',
    why: 'registered hypothesis (a changed idea gets a new H number)' },
  { id: 'registry', re: /^research\/registry\/[^/]+\.jsonl$/i, mode: 'append',
    why: 'experiment variant registry (written only by the experiment runner)' },
];

const WORKTREE_PREFIX = /^\.claude\/worktrees\/[^/]+\//i;

/** Strip Claude Code worktree prefixes (.claude/worktrees/<name>/) so the rules apply inside worktrees too. */
export function stripWorktree(rel) {
  let out = rel;
  while (WORKTREE_PREFIX.test(out)) out = out.replace(WORKTREE_PREFIX, '');
  return out;
}

export function matchLocked(rel) {
  const p = stripWorktree(rel);
  return LOCKED_RULES.find((rule) => rule.re.test(p)) ?? null;
}

export function matchAppendOnly(rel) {
  const p = stripWorktree(rel);
  return APPEND_ONLY_RULES.find((rule) => rule.re.test(p)) ?? null;
}

/** For deletes and moves: is `rel` the project root, or a folder that is or contains a protected location? */
export function containsProtected(rel) {
  const p = stripWorktree(rel).replace(/\/+$/, '').toLowerCase();
  if (p === '') return { id: 'project-root', why: 'the project root' };
  const hit = PROTECTED_ANCHORS.find((a) => a.toLowerCase() === p || a.toLowerCase().startsWith(`${p}/`));
  return hit ? { id: 'protected-folder', why: `is or contains the protected path ${hit}` } : null;
}

/** Git Bash style /c/Users/... becomes C:/Users/... on Windows. */
function fromMsysPath(p) {
  if (process.platform === 'win32') {
    const m = /^\/([a-zA-Z])(\/|$)/.exec(p);
    if (m) return `${m[1].toUpperCase()}:/${p.slice(3)}`;
  }
  return p;
}

/** Resolve symlinks and junctions on the deepest existing ancestor; keep the not-yet-existing tail. */
function realish(p) {
  const tail = [];
  let cur = p;
  for (;;) {
    try {
      const real = fs.realpathSync.native(cur);
      return tail.length ? path.join(real, ...tail.reverse()) : real;
    } catch {
      const parent = path.dirname(cur);
      if (parent === cur) return p;
      tail.push(path.basename(cur));
      cur = parent;
    }
  }
}

/** Absolute, symlink-resolved, NFC-normalized path of `target` (absolute or relative to `baseDir`).
 *  Backslashes are treated as separators on every platform (agents often pass Windows paths). */
export function resolvePath(target, baseDir) {
  const norm = (s) => fromMsysPath(String(s).normalize('NFC').replace(/\\/g, '/'));
  const abs = path.resolve(norm(baseDir), norm(target));
  return realish(abs).normalize('NFC');
}

/**
 * Repo-relative POSIX path of `target`, or null when it lies outside `projectDir`.
 * '' means the project root itself. Comparison is case-insensitive on Windows.
 */
export function toRepoRelative(target, projectDir, baseDir = projectDir) {
  // A Windows drive path can never be inside the project when running on POSIX (e.g. CI).
  if (process.platform !== 'win32' && /^[a-zA-Z]:[\\/]/.test(String(target))) return null;
  const root = resolvePath(projectDir, projectDir);
  const abs = resolvePath(target, baseDir);
  const rel = path.relative(root, abs);
  if (rel === '') return '';
  if (rel === '..' || rel.startsWith(`..${path.sep}`) || path.isAbsolute(rel)) return null;
  return rel.split(path.sep).join('/');
}
