#!/usr/bin/env node
// PreToolUse hook for Edit|Write|MultiEdit|NotebookEdit. Blocks writes to locked and append-only
// paths (rules: scripts/controls/rules.mjs). Exit code 2 blocks the tool call and shows stderr to
// Claude. Fails closed: if the input cannot be read, the write is blocked.
// This is a local guard (Handbook v5 App.O); CI (check-locked-paths.mjs) is the enforcing layer.
import { execFileSync } from 'node:child_process';
import { existsSync, readFileSync } from 'node:fs';
import path from 'node:path';
import { matchAppendOnly, matchLocked, resolvePath, toRepoRelative } from '../../scripts/controls/rules.mjs';

function block(message) {
  process.stderr.write(`Blocked by .claude/hooks/protect-paths.mjs: ${message}\n`);
  process.exit(2);
}

function isTracked(absPath) {
  let dir = path.dirname(absPath);
  while (!existsSync(dir)) {
    const up = path.dirname(dir);
    if (up === dir) return false;
    dir = up;
  }
  try {
    execFileSync('git', ['ls-files', '--error-unmatch', '--', absPath], { cwd: dir, stdio: 'ignore' });
    return true;
  } catch {
    return false;
  }
}

let input;
try {
  input = JSON.parse(readFileSync(0, 'utf8'));
} catch {
  block('cannot parse the hook input; failing closed.');
}

const toolInput = input?.tool_input ?? {};
const target = toolInput.file_path ?? toolInput.notebook_path ?? toolInput.path;
if (typeof target !== 'string' || target.trim() === '') {
  block(`no target path in the ${input?.tool_name ?? 'tool'} input; failing closed.`);
}

const projectDir = process.env.CLAUDE_PROJECT_DIR || input.cwd || process.cwd();
const baseDir = input.cwd || projectDir;
const rel = toRepoRelative(target, projectDir, baseDir);
if (rel === null) process.exit(0); // outside this project: not governed by these rules

const locked = matchLocked(rel);
if (locked) {
  block(`${rel} is a locked path (${locked.why}). The implementer may not change it. `
    + 'Stop and ask the owner; do not work around this block.');
}

const appendOnly = matchAppendOnly(rel);
if (appendOnly?.mode === 'append') {
  block(`${rel} is append-only (${appendOnly.why}). Only the experiment runner writes it.`);
}
if (appendOnly?.mode === 'immutable' && isTracked(resolvePath(target, baseDir))) {
  block(`${rel} is a committed hypothesis (${appendOnly.why}). Register a new H number instead of editing it.`);
}

process.exit(0);
