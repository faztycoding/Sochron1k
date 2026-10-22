"""CORE-001 AC-07: static package boundaries and explicit clock/I/O prohibition.

Run from the repository root. Same-package imports support the contract's planned
multi-file timebase package; its only other project dependency is sochron.core.
This is an AST check, not a general proof about arbitrary Python execution.
"""

import ast
from importlib.util import resolve_name
from pathlib import Path
import sys


def _qualified(node, bindings):
    if isinstance(node, ast.Name):
        return bindings.get(node.id, node.id)
    if isinstance(node, ast.Attribute):
        parent = _qualified(node.value, bindings)
        return f"{parent}.{node.attr}" if parent else None
    return None


def _within(name, package):
    return name == package or name.startswith(package + ".")


def _allowed_import(name, package):
    if name.split(".")[0] in sys.stdlib_module_names:
        return name.split(".")[0] != "socket"
    return _within(name, "sochron.core") or _within(name, package)


def _inspect_source(source, package, current_package):
    """Return line-numbered findings; resolve imports/aliases without executing source."""
    tree = ast.parse(source)
    clocks = {
        "datetime.now", "datetime.utcnow", "datetime.today", "datetime.date.today",
        "datetime.datetime.now", "datetime.datetime.utcnow", "datetime.datetime.today",
        "time.time", "time.time_ns", "time.monotonic", "time.monotonic_ns",
        "time.perf_counter", "time.perf_counter_ns", "time.process_time", "time.process_time_ns",
    }
    direct_io = {
        "open", "builtins.open", "io.open", "os.open", "os.getenv", "os.putenv", "os.unsetenv",
        "print", "builtins.print", "input", "builtins.input", "urllib.request.urlopen",
        "os.stat", "os.listdir", "os.scandir", "os.read", "os.write", "os.system",
    }
    file_methods = {"open", "read_text", "read_bytes", "write_text", "write_bytes", "stat", "lstat"}
    dynamic_imports = {"__import__", "builtins.__import__", "importlib.import_module"}

    class Inspector(ast.NodeVisitor):
        def __init__(self):
            self.bindings = {}
            self.findings = []

        def report(self, node, message):
            self.findings.append(f"line {node.lineno}: {message}")

        def check_import(self, node, module):
            if not _allowed_import(module, package):
                self.report(node, f"forbidden import {module}")

        def check_reference(self, node):
            qualified = _qualified(node, self.bindings)
            if qualified and (_within(qualified, "os.environ") or _within(qualified, "socket")):
                self.report(node, f"forbidden environment/network access {qualified}")

        def visit_Import(self, node):
            for alias in node.names:
                self.check_import(node, alias.name)
                self.bindings[alias.asname or alias.name.split(".")[0]] = (
                    alias.name if alias.asname else alias.name.split(".")[0]
                )

        def visit_ImportFrom(self, node):
            module = node.module or ""
            if node.level:
                try:
                    module = resolve_name("." * node.level + module, current_package)
                except ImportError:
                    self.report(node, "relative import escapes its package")
                    return
            for alias in node.names:
                qualified = f"{module}.{alias.name}"
                self.check_import(node, qualified if module == "sochron" else module)
                if alias.name == "*":
                    self.report(node, "wildcard import prevents alias verification")
                else:
                    self.bindings[alias.asname or alias.name] = qualified
                    if _within(qualified, "os.environ") or _within(qualified, "socket"):
                        self.report(node, f"forbidden environment/network access {qualified}")

        def visit_Name(self, node):
            self.check_reference(node)

        def visit_Attribute(self, node):
            self.check_reference(node)
            self.generic_visit(node)

        def visit_Call(self, node):
            called = _qualified(node.func, self.bindings)
            if called in clocks or called in direct_io:
                self.report(node, f"forbidden clock/I/O call {called}")
            elif isinstance(node.func, ast.Attribute) and node.func.attr in file_methods:
                self.report(node, f"forbidden file I/O call .{node.func.attr}")
            if called in dynamic_imports:
                self.report(node, "dynamic import prevents static boundary verification")
            self.generic_visit(node)

        def visit_Assign(self, node):
            self.generic_visit(node)
            qualified = _qualified(node.value, self.bindings)
            for target in node.targets:
                if isinstance(target, ast.Name):
                    self.bindings[target.id] = qualified

        def visit_AnnAssign(self, node):
            self.generic_visit(node)
            if isinstance(node.target, ast.Name):
                self.bindings[node.target.id] = _qualified(node.value, self.bindings)

        def visit_FunctionDef(self, node):
            # Defaults/decorators execute in the containing scope; body aliases stay local.
            for expression in node.decorator_list + node.args.defaults + node.args.kw_defaults:
                if expression is not None:
                    self.visit(expression)
            self.bindings[node.name] = None
            parent = self.bindings
            self.bindings = dict(parent)
            args = node.args.posonlyargs + node.args.args + node.args.kwonlyargs
            args += [arg for arg in (node.args.vararg, node.args.kwarg) if arg is not None]
            for arg in args:
                self.bindings[arg.arg] = None
            for statement in node.body:
                self.visit(statement)
            self.bindings = parent

        visit_AsyncFunctionDef = visit_FunctionDef

        def visit_ClassDef(self, node):
            for expression in node.decorator_list + node.bases:
                self.visit(expression)
            parent = self.bindings
            self.bindings = dict(parent)
            for statement in node.body:
                self.visit(statement)
            self.bindings = parent
            self.bindings[node.name] = None

    inspector = Inspector()
    inspector.visit(tree)
    return sorted(set(inspector.findings))


def test_ac07_timebase_and_core_import_boundaries_and_no_clock_or_io():
    source_root = Path.cwd() / "src"
    findings = []
    for package in ("sochron.timebase", "sochron.core"):
        directory = source_root.joinpath(*package.split("."))
        assert directory.is_dir(), f"AC-07: {directory} does not exist; implementation missing"
        files = sorted(directory.rglob("*.py"))
        assert files, f"AC-07: {directory} contains no Python source; implementation missing"
        for path in files:
            relative = path.relative_to(source_root)
            current_package = ".".join(relative.parent.parts)
            try:
                violations = _inspect_source(path.read_text(encoding="utf-8-sig"), package, current_package)
            except SyntaxError as error:
                findings.append(f"{relative}:{error.lineno}: invalid Python syntax: {error.msg}")
                continue
            findings.extend(f"{relative}: {violation}" for violation in violations)
    assert not findings, "AC-07: forbidden dependencies or side effects:\n" + "\n".join(findings)


def _inspect_costs_source(source, current_package):
    """Reuse CORE-001 checks; inspect the entire AST for costs-only prohibitions."""
    findings = _inspect_source(source, "sochron.costs", current_package)
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Name) and node.id == "float":
            findings.append(f"line {node.lineno}: forbidden float name")
        if isinstance(node, ast.Constant) and type(node.value) is float:
            findings.append(f"line {node.lineno}: forbidden float literal")
        if isinstance(node, ast.Import):
            for alias in node.names:
                if _within(alias.name, "random"):
                    findings.append(f"line {node.lineno}: forbidden random import")
        if isinstance(node, ast.ImportFrom) and node.level == 0:
            if _within(node.module or "", "random"):
                findings.append(f"line {node.lineno}: forbidden random import")
    return sorted(set(findings))


def test_ac07_costs_import_boundaries_no_clock_io_random_or_float():
    source_root = Path.cwd() / "src"
    directory = source_root / "sochron" / "costs"
    assert directory.is_dir(), f"AC-07: {directory} does not exist; implementation missing"
    files = sorted(directory.rglob("*.py"))
    assert files, f"AC-07: {directory} contains no Python source; implementation missing"
    findings = []
    for path in files:
        relative = path.relative_to(source_root)
        current_package = ".".join(relative.parent.parts)
        try:
            violations = _inspect_costs_source(path.read_text(encoding="utf-8-sig"), current_package)
        except SyntaxError as error:
            findings.append(f"{relative}:{error.lineno}: invalid Python syntax: {error.msg}")
            continue
        findings.extend(f"{relative}: {violation}" for violation in violations)
    assert not findings, "AC-07: forbidden dependencies or side effects:\n" + "\n".join(findings)
