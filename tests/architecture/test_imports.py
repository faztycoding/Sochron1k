"""CORE-001 AC-07: static package boundaries and explicit clock/I/O prohibition.

Run from the repository root. Same-package imports support the contract's planned
multi-file timebase package; its only other project dependency is sochron.core.
This is an AST check, not a general proof about arbitrary Python execution.
FIX-001 adds the clock, randomness, process, console-stream and network names in
_SIDE_EFFECTS to every pure package's check. Dynamic access such as
getattr(time, "localtime")() is not detected. FIX-001 r3: the CORE-001 rules also
run under their original name resolution, so every finding of the checker before
FIX-001 is still reported. CORE-005 AC-06 runs the same checker over sochron.core and
sochron.data.snapshot: the latter may import sochron.core, sochron.timebase, itself and
side-effect-free stdlib only, and neither may import the random module. CORE-005 v1.1
also checks src/sochron/data/__init__.py under the snapshot import rules and bans float
names and literals in sochron.data.snapshot, as in costs and risk. CORE-006 AC-06 runs the
same checker over sochron.strategy: it may import sochron.core, sochron.timebase, itself and
side-effect-free stdlib only, with no random module and no float names or literals. CORE-006
tests r2 (review F4) narrows that stdlib to an explicit list, _STRATEGY_STDLIB, for strategy only.
CORE-007 AC-06 runs the same checker over sochron.backtest: it may import sochron.core,
sochron.timebase, sochron.strategy, sochron.costs, itself and the stdlib modules of
_BACKTEST_STDLIB only, with no random module, no float names or literals, no zoneinfo import and
no astimezone (time is converted only through sochron.timebase). Every earlier function and table
is unchanged.
CORE-007 tests r2 (review F6, contract v1.5) adds a second backtest checker,
_inspect_backtest_zoneinfo_source: the round-1 backtest checks plus a finding for every import of
a name ZoneInfo from any module (sochron.timebase internals included) and every other reference
to the name ZoneInfo. The round-1 functions, tables and test are unchanged.
CORE-008 AC-06 runs the same checker over sochron.research: it may import sochron.core,
sochron.timebase, sochron.strategy, sochron.costs, sochron.backtest, itself and the stdlib modules
of _RESEARCH_STDLIB only (no data package, risk, broker, execution, journal or MetaTrader5; no os,
clock, float, network, process or console), draws randomness only from a seeded random.Random
through randrange, does file I/O only in src/sochron/research/registry.py (binary reads and
appends there) and never deletes, renames or truncates a file. Every earlier function, table and
test is unchanged.
ENV-002 AC-06 runs every research, backtest and strategy checker over imports of sochron.app,
sochron.broker and sochron.data.acquire, scans the three packages and src/sochron/__init__.py for them,
and imports the three packages in a fresh interpreter to see that none of the three is loaded. It also
gives sochron.app.envcheck its own checker: no process, network or file-writing module or call, ctypes and
winreg only for the functions the contract lists, and nothing Windows-only at import time. Every earlier
function, table and test is unchanged.
"""

import ast
from importlib.util import resolve_name
from pathlib import Path
import re
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
    if package == "sochron.risk" and _within(name, "sochron.costs"):
        return True
    # CORE-005 AC-06: data.snapshot may use timebase (docs/architecture.md section 8).
    if package == "sochron.data.snapshot" and _within(name, "sochron.timebase"):
        return True
    # CORE-006 AC-06: strategy may use timebase (docs/architecture.md section 8).
    if package == "sochron.strategy" and _within(name, "sochron.timebase"):
        return True
    return _within(name, "sochron.core") or _within(name, package)


# FIX-001: names reported in every pure package when reached by a call or any other reference,
# an `import x as y` alias or a `from x import y` binding; a name covers its attributes. Clock
# names are reported with or without arguments: given None or a variable they may read the
# clock, which a static check cannot tell apart. socket keeps its CORE-001 rules.
_SIDE_EFFECTS = {
    "clock": (
        "time.localtime", "time.gmtime", "time.ctime", "time.asctime", "time.strftime",
        "time.mktime", "time.clock_gettime", "time.clock_gettime_ns", "time.thread_time",
        "time.thread_time_ns",
    ),
    "randomness": ("os.urandom", "os.getrandom", "secrets", "uuid", "random.SystemRandom"),
    "process": ("subprocess", "multiprocessing", "os.system", "os.popen", "os.fork", "os.kill"),
    "console stream": ("sys.stdout", "sys.stderr", "sys.stdin", "sys.__stdout__", "sys.__stderr__"),
    "network": ("http", "ssl"),
}
_OS_PROCESS_FAMILIES = ("exec", "spawn")  # os.exec* and os.spawn*


def _side_effect(qualified):
    """Return the FIX-001 category of a resolved name, or None."""
    if not qualified:
        return None
    for category, names in _SIDE_EFFECTS.items():
        if any(_within(qualified, name) for name in names):
            return category
    module, _, attribute = qualified.partition(".")
    if module == "os" and attribute.startswith(_OS_PROCESS_FAMILIES):
        return "process"
    return None


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
        def __init__(self, late=False):
            self.bindings = {}
            self.findings = []
            # FIX-001 r2: the scope that a nested function, lambda, class or comprehension starts
            # from. Python skips class bodies, so inside a class body this is the enclosing scope.
            self.enclosing = self.bindings
            # FIX-001 r3: the module scope; the scope that each global or nonlocal name of the
            # current body binds in; each Name or Attribute as resolved when Python evaluates it;
            # and, in the late pass, the function bodies that run after their scope has ended.
            self.module = self.bindings
            self.declared = {}
            self.resolved = {}
            self.late = late
            self.pending = []

        def report(self, node, message):
            self.findings.append(f"line {node.lineno}: {message}")

        def check_import(self, node, module):
            if not _allowed_import(module, package):
                self.report(node, f"forbidden import {module}")

        def check_reference(self, node):
            # Assigning or deleting a bare name binds it; it does not use a module (a field uuid).
            # FIX-001 r3: OriginalInspector still reports such a store of socket or os.environ.
            if isinstance(node, ast.Name) and not isinstance(node.ctx, ast.Load):
                return
            qualified = self.resolved[node] = _qualified(node, self.bindings)
            if qualified and (_within(qualified, "os.environ") or _within(qualified, "socket")):
                self.report(node, f"forbidden environment/network access {qualified}")
            category = _side_effect(qualified)
            if category:
                self.report(node, f"forbidden {category} access {qualified}")

        def check_side_effect_import(self, node, name):
            category = _side_effect(name)
            if category:
                self.report(node, f"forbidden {category} import {name}")

        def visit_Import(self, node):
            for alias in node.names:
                self.check_import(node, alias.name)
                self.check_side_effect_import(node, alias.name)
                self.bind(
                    alias.asname or alias.name.split(".")[0],
                    alias.name if alias.asname else alias.name.split(".")[0],
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
                self.check_side_effect_import(node, qualified)
                if alias.name == "*":
                    self.report(node, "wildcard import prevents alias verification")
                else:
                    self.bind(alias.asname or alias.name, qualified)
                    if _within(qualified, "os.environ") or _within(qualified, "socket"):
                        self.report(node, f"forbidden environment/network access {qualified}")

        def bind(self, name, qualified):
            # FIX-001 r3 (review r2 F8): a global or nonlocal name also binds in the scope it names,
            # but only to a module there: the function may never run, so it hides no module.
            self.bindings[name] = qualified
            scope = self.declared.get(name)
            if scope is not None and qualified:
                scope[name] = qualified

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
            # FIX-001 r3 (review r2 F6): Python runs the value first, then the targets in order.
            for child in [node.value, *node.targets]:
                self.visit(child)
            # FIX-001 r2: unpacked names are bound too; every value resolves before any binding.
            bound = [pair for target in node.targets for pair in self.assigned(target, node.value)]
            for name, qualified in bound:
                self.bind(name, qualified)

        def assigned(self, target, value):
            """Yield (name, resolved value) pairs; a same-length tuple or list pairs by position."""
            # FIX-001 r3: a value resolves as it was when Python ran it, before any later walrus.
            if isinstance(target, ast.Name):
                yield target.id, self.resolved.get(value)
            elif isinstance(target, ast.Starred):
                yield from self.assigned(target.value, None)
            elif isinstance(target, (ast.Tuple, ast.List)):
                values = value.elts if isinstance(value, (ast.Tuple, ast.List)) else []
                starred = any(isinstance(item, ast.Starred) for item in values + target.elts)
                if starred or len(values) != len(target.elts):
                    values = [None] * len(target.elts)
                for element, item in zip(target.elts, values):
                    yield from self.assigned(element, item)

        def visit_AnnAssign(self, node):
            # FIX-001 r3 (review r2 F6): the value runs first, then the target and the annotation.
            for child in (node.value, node.target, node.annotation):
                if child is not None:
                    self.visit(child)
            # FIX-001 r2: an annotation without a value binds nothing (a dataclass field time: int).
            if isinstance(node.target, ast.Name) and node.value is not None:
                self.bind(node.target.id, self.resolved.get(node.value))

        def visit_NamedExpr(self, node):
            # FIX-001 r2: a walrus binds its name like an assignment, once its value has run.
            self.visit(node.value)
            self.bind(node.target.id, self.resolved.get(node.value))

        def visit_For(self, node):
            # FIX-001 r3 (review r2 F6): the iterable runs before the target is assigned.
            for child in [node.iter, node.target, *node.body, *node.orelse]:
                self.visit(child)

        visit_AsyncFor = visit_For

        def visit_Dict(self, node):
            # FIX-001 r3 (review r2 F6): each key runs before its value, pair by pair (** has none).
            for key, value in zip(node.keys, node.values):
                for child in (key, value):
                    if child is not None:
                        self.visit(child)

        def visit_Module(self, node):
            self.visit_scope(node.body)

        def visit_FunctionDef(self, node):
            # Defaults/decorators execute in the containing scope; body aliases stay local.
            for expression in node.decorator_list + node.args.defaults + node.args.kw_defaults:
                if expression is not None:
                    self.visit(expression)
            self.bind(node.name, None)
            self.visit_function_body(node.args, node.body)

        visit_AsyncFunctionDef = visit_FunctionDef

        def visit_Lambda(self, node):
            # FIX-001 r2: defaults run in the containing scope; parameters bind only in the body.
            for expression in node.args.defaults + node.args.kw_defaults:
                if expression is not None:
                    self.visit(expression)
            self.visit_function_body(node.args, [node.body])

        def visit_function_body(self, arguments, body):
            # FIX-001 r3 (review r2 F8): a body runs when it is called, which can be after a later
            # import. The late pass therefore runs it once its module or function body has ended.
            if self.late:
                self.pending.append((arguments, body, self.enclosing))
            else:
                self.run_function_body(arguments, body, self.enclosing)

        def run_function_body(self, arguments, body, enclosing):
            """FIX-001 r2: a body sees its parameters and the enclosing scope, not a class body."""
            saved = self.bindings, self.enclosing, self.declared
            self.bindings = self.enclosing = dict(enclosing)
            args = arguments.posonlyargs + arguments.args + arguments.kwonlyargs
            args += [arg for arg in (arguments.vararg, arguments.kwarg) if arg is not None]
            for arg in args:
                self.bindings[arg.arg] = None
            self.declared = self.declarations(body, enclosing)
            self.visit_scope(body)
            self.bindings, self.enclosing, self.declared = saved

        def visit_scope(self, statements):
            """FIX-001 r3: visit a module or function body, then the bodies the late pass held."""
            outer, self.pending = self.pending, []
            for statement in statements:
                self.visit(statement)
            pending, self.pending = self.pending, outer
            for arguments, body, enclosing in pending:
                self.run_function_body(arguments, body, enclosing)

        def declarations(self, body, enclosing):
            """FIX-001 r3 (review r2 F8): map each global or nonlocal name of a body to its scope.

            The body reads such a name from that scope. A nonlocal name is taken to be the nearest
            enclosing function's.
            """
            declared = {}
            nested = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)
            stack = list(body)
            while stack:
                node = stack.pop()
                if isinstance(node, (ast.Global, ast.Nonlocal)):
                    scope = self.module if isinstance(node, ast.Global) else enclosing
                    declared.update(dict.fromkeys(node.names, scope))
                elif not isinstance(node, nested):
                    stack.extend(ast.iter_child_nodes(node))
            for name, scope in declared.items():
                if name in scope:
                    self.bindings[name] = scope[name]
                else:
                    self.bindings.pop(name, None)
            return declared

        def visit_ClassDef(self, node):
            for expression in node.decorator_list + node.bases:
                self.visit(expression)
            parent, declared = self.bindings, self.declared
            # FIX-001 r2: a class body starts from the enclosing scope, not an outer class body.
            self.bindings = dict(self.enclosing)
            self.declared = self.declarations(node.body, self.enclosing)
            for statement in node.body:
                self.visit(statement)
            self.bindings, self.declared = parent, declared
            self.bind(node.name, None)

        def visit_ListComp(self, node):
            # FIX-001 r3 (review r2 F6): in evaluation order. The first iterable runs in the current
            # scope, then each target, condition and later iterable, and the element runs last.
            # FIX-001 r2: inside a class body only the first iterable sees class-body names.
            first, *later = node.generators
            self.visit(first.iter)
            parent, enclosing = self.bindings, self.enclosing
            if parent is not enclosing:
                self.bindings = self.enclosing = dict(enclosing)
            rest = [first.target, *first.ifs]
            for generator in later:
                rest += [generator.iter, generator.target, *generator.ifs]
            rest += [node.key, node.value] if isinstance(node, ast.DictComp) else [node.elt]
            for child in rest:
                self.visit(child)
            self.bindings, self.enclosing = parent, enclosing

        visit_SetComp = visit_DictComp = visit_GeneratorExp = visit_ListComp

        def visit_ExceptHandler(self, node):
            # FIX-001 r2: `except E as name` binds the exception inside the handler only.
            if node.type is not None:
                self.visit(node.type)
            self.visit_with_names({node.name: None} if node.name else {}, node.body)

        def visit_Match(self, node):
            # FIX-001 r2: a capture binds only inside its case; r3: captures() says what it holds.
            self.visit(node.subject)
            subject = self.resolved.get(node.subject)
            for case in node.cases:
                self.visit(case.pattern)
                names = {}
                self.captures(case.pattern, subject, names)
                guard = [] if case.guard is None else [case.guard]
                self.visit_with_names(names, guard + case.body)

        def captures(self, pattern, value, names):
            """FIX-001 r3 (review r2 F7, F8): bind each capture of a pattern matched against value.

            An `as` name and each or-pattern alternative hold the whole value, a keyword of a class
            pattern holds that attribute of it, and any other capture holds a part of it (None).
            Where alternatives capture one name, the first binding to a module is kept.
            """
            if isinstance(pattern, ast.MatchAs):
                parts = [] if pattern.pattern is None else [(pattern.pattern, value)]
            elif isinstance(pattern, ast.MatchOr):
                parts = [(alternative, value) for alternative in pattern.patterns]
            elif isinstance(pattern, ast.MatchClass):
                parts = [(item, None) for item in pattern.patterns]
                for attribute, item in zip(pattern.kwd_attrs, pattern.kwd_patterns):
                    parts.append((item, f"{value}.{attribute}" if value else None))
            else:
                children = ast.iter_child_nodes(pattern)
                parts = [(item, None) for item in children if isinstance(item, ast.pattern)]
            name = getattr(pattern, "name", None) or getattr(pattern, "rest", None)
            if name:
                whole = value if isinstance(pattern, ast.MatchAs) else None
                names[name] = names.get(name) or whole
            for part, held in parts:
                self.captures(part, held, names)

        def visit_with_names(self, names, nodes):
            # Afterwards a name still bound to no module gets its old binding back: Python deletes
            # an except-as name, and a capture binds only when its case matches.
            missing = object()
            previous = {name: self.bindings.get(name, missing) for name in names}
            for name, qualified in names.items():
                self.bind(name, qualified)
            for child in nodes:
                self.visit(child)
            for name, old in previous.items():
                if self.bindings.get(name) is None:
                    if old is missing:
                        self.bindings.pop(name, None)
                    else:
                        self.bindings[name] = old

    # FIX-001 r3 (review r2 F9, owner option b): the Inspector exactly as it was before FIX-001.
    # It runs only the CORE-001 rules, under their original name resolution. Its findings are
    # kept with the others, so no source loses a finding that the checker reported before FIX-001.
    class OriginalInspector(ast.NodeVisitor):
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

    # FIX-001 r3: one pass binds names where each body is defined, one runs function bodies after
    # their scope has ended (review r2 F8), and OriginalInspector adds the CORE-001 findings (F9).
    findings = set()
    for inspector in (Inspector(), Inspector(late=True), OriginalInspector()):
        inspector.visit(tree)
        findings.update(inspector.findings)
    return sorted(findings)


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


def _inspect_risk_source(source, current_package):
    """Reuse CORE-001 checks; inspect the entire AST for risk-only prohibitions."""
    findings = _inspect_source(source, "sochron.risk", current_package)
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


def test_ac07_risk_import_boundaries_no_clock_io_random_or_float():
    source_root = Path.cwd() / "src"
    directory = source_root / "sochron" / "risk"
    assert directory.is_dir(), f"AC-07: {directory} does not exist; implementation missing"
    files = sorted(directory.rglob("*.py"))
    assert files, f"AC-07: {directory} contains no Python source; implementation missing"
    findings = []
    for path in files:
        relative = path.relative_to(source_root)
        current_package = ".".join(relative.parent.parts)
        try:
            violations = _inspect_risk_source(path.read_text(encoding="utf-8-sig"), current_package)
        except SyntaxError as error:
            findings.append(f"{relative}:{error.lineno}: invalid Python syntax: {error.msg}")
            continue
        findings.extend(f"{relative}: {violation}" for violation in violations)
    assert not findings, "AC-07: forbidden dependencies or side effects:\n" + "\n".join(findings)


def _inspect_data_snapshot_source(source, package, current_package):
    """CORE-005 AC-06: reuse the pure-package checks; also forbid any import of random."""
    findings = _inspect_source(source, package, current_package)
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if _within(alias.name, "random"):
                    findings.append(f"line {node.lineno}: forbidden random import")
        if isinstance(node, ast.ImportFrom) and node.level == 0:
            if _within(node.module or "", "random"):
                findings.append(f"line {node.lineno}: forbidden random import")
    return sorted(set(findings))


def _inspect_core_source(source, current_package):
    """CORE-005 AC-06 on sochron.core: the snapshot checker under the core package's rules."""
    return _inspect_data_snapshot_source(source, "sochron.core", current_package)


def _inspect_data_snapshot_float_source(source, current_package):
    """CORE-005 v1.1 AC-06 (tests-r1 question 8): the snapshot checks plus the costs/risk float ban."""
    findings = _inspect_data_snapshot_source(source, "sochron.data.snapshot", current_package)
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Name) and node.id == "float":
            findings.append(f"line {node.lineno}: forbidden float name")
        if isinstance(node, ast.Constant) and type(node.value) is float:
            findings.append(f"line {node.lineno}: forbidden float literal")
    return sorted(set(findings))


def _inspect_data_package_source(source, current_package):
    """CORE-005 v1.1 AC-06 (tests-r1 F10): sochron/data/__init__.py runs on every import of the
    snapshot, so it may import only what the snapshot may (sochron.data.snapshot included)."""
    return _inspect_data_snapshot_source(source, "sochron.data.snapshot", current_package)


def test_ac06_core_and_data_snapshot_import_boundaries_no_clock_io_random_or_broker():
    source_root = Path.cwd() / "src"
    findings = []
    checks = []
    for package, inspect in (
        ("sochron.core", _inspect_core_source),
        ("sochron.data.snapshot", _inspect_data_snapshot_float_source),
    ):
        directory = source_root.joinpath(*package.split("."))
        assert directory.is_dir(), f"AC-06: {directory} does not exist; implementation missing"
        files = sorted(directory.rglob("*.py"))
        assert files, f"AC-06: {directory} contains no Python source; implementation missing"
        checks += [(path, inspect) for path in files]
    # v1.1: the data package's own __init__.py, when present, runs before the snapshot does. A
    # namespace package (no __init__.py) runs no code of its own, so it has nothing to check.
    package_init = source_root / "sochron" / "data" / "__init__.py"
    if package_init.is_file():
        checks.append((package_init, _inspect_data_package_source))
    for path, inspect in checks:
        relative = path.relative_to(source_root)
        current_package = ".".join(relative.parent.parts)
        try:
            violations = inspect(path.read_text(encoding="utf-8-sig"), current_package)
        except SyntaxError as error:
            findings.append(f"{relative}:{error.lineno}: invalid Python syntax: {error.msg}")
            continue
        findings.extend(f"{relative}: {violation}" for violation in violations)
    assert not findings, "AC-06: forbidden dependencies or side effects:\n" + "\n".join(findings)


# FIX-001 self-tests: synthetic sources go to the inspection function of every pure package.

_PURE_CHECKERS = (
    ("sochron.timebase", lambda source: _inspect_source(source, "sochron.timebase", "sochron.timebase")),
    ("sochron.core", lambda source: _inspect_source(source, "sochron.core", "sochron.core")),
    ("sochron.costs", lambda source: _inspect_costs_source(source, "sochron.costs")),
    ("sochron.risk", lambda source: _inspect_risk_source(source, "sochron.risk")),
)
_HEADER = '"""Synthetic pure module."""\n'
_OS_FAMILY = (
    "execl", "execle", "execlp", "execlpe", "execv", "execve", "execvp", "execvpe",
    "spawnl", "spawnle", "spawnlp", "spawnlpe", "spawnv", "spawnve", "spawnvp", "spawnvpe",
)
# Contract items reached as module attributes: (name, use); "{p}" is how a form reaches the module.
_ATTRIBUTE_ITEMS = (
    ("time.localtime", "{p}localtime()"),
    ("time.gmtime", "{p}gmtime()"),
    ("time.ctime", "{p}ctime()"),
    ("time.asctime", "{p}asctime()"),
    ("time.strftime", '{p}strftime("%H:%M")'),
    ("time.mktime", "{p}mktime({p}localtime())"),
    ("time.clock_gettime", "{p}clock_gettime(0)"),
    ("time.clock_gettime_ns", "{p}clock_gettime_ns(0)"),
    ("time.thread_time", "{p}thread_time()"),
    ("time.thread_time_ns", "{p}thread_time_ns()"),
    ("os.urandom", "{p}urandom(16)"),
    ("os.getrandom", "{p}getrandom(16)"),
    ("random.SystemRandom", "{p}SystemRandom().random()"),
    ("os.system", '{p}system("echo")'),
    ("os.popen", '{p}popen("echo")'),
    ("os.fork", "{p}fork()"),
    ("os.kill", "{p}kill(1, 15)"),
    *((f"os.{name}", f"{{p}}{name}()") for name in _OS_FAMILY),
    ("sys.stdout", '{p}stdout.write("x")'),
    ("sys.stderr", '{p}stderr.write("x")'),
    ("sys.stdin", "{p}stdin.readline()"),
    ("sys.__stdout__", '{p}__stdout__.write("x")'),
    ("sys.__stderr__", '{p}__stderr__.write("x")'),
)
# Contract items whose whole module is forbidden: (module, use of one of its attributes).
_MODULE_ITEMS = (
    ("secrets", "{p}token_hex(8)"),
    ("uuid", "{p}uuid4()"),
    ("uuid", "{p}uuid1()"),
    ("subprocess", '{p}run(["echo"])'),
    ("multiprocessing", "{p}Process()"),
    ("socket", '{p}create_connection(("example.invalid", 80))'),
    ("http", '{p}client.HTTPConnection("example.invalid")'),
    ("ssl", "{p}create_default_context()"),
)
_SUBMODULE_IMPORTS = ("multiprocessing.pool", "http.client")


def _use(template, prefix):
    return f"\n\ndef use():\n    return {template.format(p=prefix)}\n"


def _forms(module, template):
    """Yield (form, source, import line) for each form the contract names; the use is on line 6."""
    imported = ", ".join(sorted(set(re.findall(r"\{p\}(\w+)", template))))
    body = f"\n\ndef use():\n    import {module}\n    return {template.format(p=module + '.')}\n"
    yield "direct", f"{_HEADER}import {module}\n{_use(template, module + '.')}", 2
    yield "alias", f"{_HEADER}import {module} as renamed\n{_use(template, 'renamed.')}", 2
    yield "from-import", f"{_HEADER}from {module} import {imported}\n{_use(template, '')}", 2
    yield "import in function body", f"{_HEADER}{body}", 5


def _forbidden_cases():
    """Yield (label, source, expected); each (line, name) in expected must be reported."""
    for name, template in _ATTRIBUTE_ITEMS:
        for form, source, _ in _forms(name.split(".")[0], template):
            yield f"{name} {form}", source, [(6, name)] + ([(2, name)] if form == "from-import" else [])
    for module in sorted({module for module, _ in _MODULE_ITEMS} | set(_SUBMODULE_IMPORTS)):
        yield f"import {module} alone", f"{_HEADER}import {module}\n", [(2, module)]
    for module, template in _MODULE_ITEMS:
        attribute = re.findall(r"\{p\}(\w+)", template)[0]
        name = f"{module}.{attribute}"
        for form, source, import_line in _forms(module, template):
            imported = name if form == "from-import" else module
            yield f"{name} {form}", source, [(import_line, imported), (6, name)]


def _reported(findings, line, name):
    return any(f.startswith(f"line {line}: forbidden ") and f.endswith(f" {name}") for f in findings)


def test_fix001_ac01_listed_side_effects_reported_with_line_in_every_pure_package():
    missing = []
    checked = 0
    for label, source, expected in _forbidden_cases():
        for package, inspect in _PURE_CHECKERS:
            findings = inspect(source)
            for line, name in expected:
                checked += 1
                if not _reported(findings, line, name):
                    missing.append(f"{package} | {label}: line {line} lacks {name}; got {findings}")
    summary = f"AC-01: {len(missing)} of {checked} expected findings missing:\n"
    assert not missing, summary + "\n".join(missing)


# FIX-001 r2 (review r1 F1): names follow Python scoping. A class-body name is not seen by the
# class's methods, lambdas, nested classes or comprehension bodies, so it hides no module there;
# a parameter or local name hides a module only inside its own function, handler or case.
# (label, source lines, [(line, name), ...]); line 1 is _HEADER, so the first source line is 2.
_SCOPED_CASES = (
    ("class field time, method calls time.localtime() (review r1 F1)", (
        "import time",
        "class Bar:",
        "    time: int = 0",
        "    def label(self):",
        "        return time.localtime()",
    ), [(6, "time.localtime")]),
    ("frozen dataclass field time, method calls time.strftime()", (
        "import time",
        "from dataclasses import dataclass",
        "@dataclass(frozen=True)",
        "class Bar:",
        "    time: int",
        "    def label(self):",
        '        return time.strftime("%H")',
    ), [(8, "time.strftime")]),
    ("class field time, method calls the CORE-001 clock time.time()", (
        "import time",
        "class Bar:",
        "    time: int = 0",
        "    def stamp(self):",
        "        return time.time()",
    ), [(6, "time.time")]),
    ("class attribute sys, method writes to sys.stdout", (
        "import sys",
        "class Job:",
        "    sys = None",
        "    def log(self):",
        '        return sys.stdout.write("x")',
    ), [(6, "sys.stdout")]),
    ("method named time, async method, nested function in a static method", (
        "import time",
        "class Clock:",
        "    time = None",
        "    def time(self):",
        "        return time.localtime()",
        "    async def label(self):",
        "        return time.ctime()",
        "    @staticmethod",
        "    def later():",
        "        def inner():",
        "            return time.gmtime()",
        "        return inner",
    ), [(6, "time.localtime"), (8, "time.ctime"), (12, "time.gmtime")]),
    ("lambda, comprehension and nested class in a class body", (
        "import time",
        "class Bar:",
        "    time = None",
        "    label = lambda self: time.localtime()",
        "    stamps = [time.asctime() for _ in range(1)]",
        "    class Inner:",
        "        STAMP = time.time()",
    ), [(5, "time.localtime"), (6, "time.asctime"), (8, "time.time")]),
    ("alias and from-import hidden by class attributes", (
        "import os as system",
        "from uuid import uuid4",
        "class Ids:",
        "    system = None",
        "    uuid4 = None",
        "    def make(self):",
        "        return system.urandom(16), uuid4()",
    ), [(8, "os.urandom"), (8, "uuid.uuid4")]),
    ("an annotation without a value binds nothing; a first iterable runs in the class body", (
        "import time",
        "class Bar:",
        "    time: int",
        "    STAMP = time.localtime()",
        "    PARTS = [part for part in time.gmtime()]",
    ), [(5, "time.localtime"), (6, "time.gmtime")]),
    ("a parameter or local name hides the module only inside its own function", (
        "import time",
        "def minute_of(time):",
        "    return time.hour",
        "KEY = lambda time: time.hour",
        "def wall(moment):",
        "    time = moment.time()",
        "    return time.hour",
        "def label():",
        "    return time.localtime()",
        'STAMP = time.strftime("%H")',
    ), [(10, "time.localtime"), (11, "time.strftime")]),
    ("unpacked, walrus, except-as and capture names end with their function, handler or case", (
        "import ssl",
        "import uuid",
        "def unpack(row):",
        "    ssl, rest = row",
        "    return rest",
        "def walrus(make):",
        "    if (uuid := make()):",
        "        return uuid",
        "try:",
        "    pass",
        "except ValueError as ssl:",
        "    pass",
        "match 0:",
        "    case [uuid]:",
        "        pass",
        "CONTEXT = ssl.create_default_context()",
        "ID = uuid.uuid4()",
    ), [(17, "ssl.create_default_context"), (18, "uuid.uuid4")]),
    ("an unpacked, walrus or captured name that holds the module still reports it", (
        "import time",
        "clock, other = time, 0",
        "STAMP = clock.localtime()",
        "if (alias := time):",
        "    LABEL = alias.ctime()",
        "match time:",
        "    case module:",
        "        ZONE = module.gmtime()",
        "match 0:",
        "    case found:",
        "        found = time",
        "DAY = found.localtime()",
    ), [(4, "time.localtime"), (6, "time.ctime"), (9, "time.gmtime"), (13, "time.localtime")]),
)


def test_fix001_ac01_class_bodies_and_local_names_do_not_hide_listed_names():
    missing = []
    for label, lines, expected in _SCOPED_CASES:
        source = _HEADER + "\n".join(lines) + "\n"
        for package, inspect in _PURE_CHECKERS:
            findings = inspect(source)
            for line, name in expected:
                if not _reported(findings, line, name):
                    missing.append(f"{package} | {label}: line {line} lacks {name}; got {findings}")
    assert not missing, "AC-01: listed names hidden by a binding:\n" + "\n".join(missing)


_LEGITIMATE_SOURCES = (
    ("date literals", (
        "import datetime",
        "from datetime import date",
        "START = datetime.date(2026, 1, 1)",
        "END = date(2026, 12, 31)",
        "OPEN = datetime.datetime(2026, 1, 1, 12, 0, tzinfo=datetime.timezone.utc)",
    )),
    ("time zones", (
        "import datetime",
        "from datetime import UTC, timedelta, timezone",
        "ZONES = (datetime.timezone.utc, timezone.utc, UTC, timezone(timedelta(hours=7)))",
    )),
    ("ZoneInfo", (
        "import zoneinfo",
        "from zoneinfo import ZoneInfo",
        'NEW_YORK = zoneinfo.ZoneInfo("America/New_York")',
        'BANGKOK = ZoneInfo("Asia/Bangkok")',
    )),
    ("names time that are not the time module", (
        "import datetime",
        "from datetime import time",
        "OPEN = time(3, 0)",
        "LAST = time.max",
        'CLOSE = time.fromisoformat("15:59")',
        'LABEL = time.strftime(OPEN, "%H:%M")',
        "LATE = datetime.time(23, 0)",
        "def minute_of(time):",
        "    return time.hour * 60 + time.minute",
        "def wall_label(moment):",
        "    time = moment.time()",
        '    return time.strftime("%H:%M")',
        "def bar_label(bar):",
        "    return bar.time.isoformat()",
    )),
    ("fields, parameters and attributes that share a forbidden name", (
        "from dataclasses import dataclass",
        "from decimal import localcontext",
        "@dataclass(frozen=True)",
        "class Record:",
        "    uuid: str",
        "    stdout: str",
        'uuid = "00000000-0000-0000-0000-000000000000"',
        "def describe(record, http, ssl, secrets):",
        "    with localcontext() as context:",
        "        context.prec = 28",
        "    return (record.uuid, record.stdout, http.status, ssl.version, secrets.count, uuid.upper())",
    )),
    ("parameters, unpacked names, walrus, except-as and captures named like modules (r1 F2)", (
        "import sys",
        "import time",
        'KEY = lambda time: time.strftime("%H")',
        "PICK = lambda uuid, *secrets, sys=None, **ssl: (uuid.hex, secrets, sys.stdout, ssl)",
        "def send(socket, sys, subprocess):",
        "    return socket.send(sys.stdout), subprocess.run",
        "def label(row):",
        "    time, price = row",
        "    (uuid, *secrets), sys = price",
        '    return time.strftime("%H"), uuid.hex, secrets, sys.stdout',
        "def key(make):",
        "    if (uuid := make()):",
        "        return uuid.hex",
        "def safe():",
        "    try:",
        "        pass",
        "    except ValueError as ssl:",
        "        return ssl.args",
        "def pick(subject):",
        "    match subject:",
        "        case [time, *secrets]:",
        '            return time.strftime("%H"), secrets',
        '        case {"sys": sys, **http}:',
        "            return sys.stdout, http",
        "        case uuid:",
        "            return uuid.hex",
    )),
    # FIX-001 r3 (owner option b): the socket names of these two r2 sources became secrets and
    # http, because OriginalInspector reports socket there, as before FIX-001; _ORIGINAL_CASES
    # now requires those socket findings.
    ("a field or variable named http, and a class body that uses its own name time", (
        "import datetime",
        "import time",
        "from dataclasses import dataclass",
        "@dataclass(frozen=True)",
        "class Endpoint:",
        "    http: str",
        'http = "tcp://example.invalid:80"',
        "def host(endpoint):",
        '    return endpoint.http, http.partition(":")',
        "class Session:",
        "    time = datetime.time(9, 0)",
        '    LABEL = time.strftime("%H:%M")',
        '    PARTS = [part for part in time.strftime("%H:%M").split(":")]',
    )),
    ("a late call, a global name and class-pattern keywords that hold no module (review r2 F8)", (
        "from datetime import time",
        "uuid = None",
        "def label(moment):",
        '    return time.strftime(moment, "%H:%M")',
        "def remember(value):",
        "    global uuid",
        "    uuid = value",
        "    return uuid.hex",
        "def kind(event):",
        "    match event:",
        "        case object(id=uuid, mode=ssl) | object(key=uuid, mode=ssl):",
        "            return uuid.hex, ssl.version",
        "OPEN = time(9, 0)",
    )),
)


def test_fix001_ac02_legitimate_dates_zones_and_names_not_reported():
    reported = []
    for label, lines in _LEGITIMATE_SOURCES:
        source = _HEADER + "\n".join(lines) + "\n"
        for package, inspect in _PURE_CHECKERS:
            findings = inspect(source)
            if findings:
                reported.append(f"{package} | {label}: {findings}")
    assert not reported, "AC-02: legitimate code reported:\n" + "\n".join(reported)


# FIX-001 r3 (review r2 F6-F8): evaluation order, match captures, global and nonlocal names, and
# function bodies that run after later imports. (label, source lines, [(line, name)] that must be
# reported, [(line, name)] that must not be, because a walrus has already replaced the module).
_BINDING_CASES = (
    ("a value, a key or an iterable runs before a later walrus (review r2 F6)", (
        "import time",
        "D = {1: time.localtime(), (time := 0): 2}",
        "import time",
        "X = {}",
        "X[(time := 0)] = time.gmtime()",
        "import time",
        "X[(time := 0)]: int = time.ctime()",
        "import time",
        "for X[(time := 0)] in [time.asctime()]:",
        "    pass",
        "import time",
        'L = [(time := 0) for _ in [time.strftime("%H")]]',
        "import time",
        "S = {(time := 0) for _ in [time.thread_time()]}",
        "import time",
        "G = list((time := 0) for _ in [time.thread_time_ns()])",
        "import time",
        "C = {(time := 0): 0 for _ in [time.mktime(time.localtime())]}",
        "import time",
        "clock, other = time, (time := 0)",
        "STAMP = clock.localtime()",
        "import time",
        "class Bar:",
        "    X = {}",
        "    X[(time := 0)] = time.ctime()",
    ), [(3, "time.localtime"), (6, "time.gmtime"), (8, "time.ctime"), (10, "time.asctime"),
        (13, "time.strftime"), (15, "time.thread_time"), (17, "time.thread_time_ns"),
        (19, "time.mktime"), (22, "time.localtime"), (26, "time.ctime")], []),
    ("a walrus that runs first leaves no module to report (review r2 F6)", (
        "import time",
        "X = [(time := 0), time.localtime()]",
        "import time",
        "Y = {}",
        "Y[time.gmtime()] = (time := 0)",
        "import time",
        "D = {(time := 0): time.ctime() for _ in [0]}",
    ), [], [(3, "time.localtime"), (6, "time.gmtime"), (8, "time.ctime")]),
    ("an or-pattern alternative or a nested as-pattern captures the subject (review r2 F7)", (
        "import time",
        "match time:",
        "    case (int() as time) | (object() as time):",
        "        STAMP = time.localtime()",
        "match time:",
        "    case (object() as clock) as other:",
        "        STAMP = clock.gmtime(), other.ctime()",
        "match time:",
        "    case [found] | found:",
        "        STAMP = found.asctime()",
    ), [(5, "time.localtime"), (8, "time.gmtime"), (8, "time.ctime"), (11, "time.asctime")], []),
    ("a class-pattern keyword captures that attribute of the subject (review r2 F8)", (
        "import sys",
        "import time",
        "match time:",
        "    case object(localtime=clock, gmtime=(object() as utc)):",
        "        STAMP = clock(), utc()",
        "match sys:",
        "    case object(stdout=out, stderr=object(write=log)):",
        '        out.write("x")',
        '        log("x")',
    ), [(6, "time.localtime"), (6, "time.gmtime"), (9, "sys.stdout"), (10, "sys.stderr.write")],
        []),
    ("global and nonlocal names bind in the scope they name (review r2 F8)", (
        "import os",
        "import time as zone",
        "time = None",
        "def setup():",
        "    global time",
        "    import time",
        "def label():",
        "    return time.localtime()",
        "class Clock:",
        "    global clock",
        "    import time as clock",
        "    def stamp(self):",
        "        return clock.gmtime()",
        "def outer():",
        "    zone = None",
        "    def inner():",
        "        global zone",
        "        return zone.ctime()",
        "    return inner",
        "def counter():",
        "    tick = None",
        "    def setup():",
        "        nonlocal tick",
        "        tick = os",
        "    setup()",
        "    return tick.urandom(1)",
        "import uuid",
        "def reset():",
        "    global uuid",
        "    uuid = None",
        "def make():",
        "    return uuid.uuid4()",
    ), [(9, "time.localtime"), (14, "time.gmtime"), (19, "time.ctime"), (27, "os.urandom"),
        (33, "uuid.uuid4")], []),
    ("a function body runs when called, after a later import (review r2 F8)", (
        "import time",
        "try:",
        "    raise ValueError",
        "except ValueError as time:",
        "    def later():",
        "        return time.localtime()",
        "import time",
        "def label():",
        "    return clock.gmtime()",
        "import time as clock",
        "KEY = lambda: zone.ctime()",
        "import time as zone",
    ), [(7, "time.localtime"), (10, "time.gmtime"), (12, "time.ctime")], []),
)


def test_fix001_ac01_walrus_order_captures_globals_and_late_calls_keep_listed_names():
    wrong = []
    for label, lines, expected, absent in _BINDING_CASES:
        source = _HEADER + "\n".join(lines) + "\n"
        for package, inspect in _PURE_CHECKERS:
            findings = inspect(source)
            wrong += [f"{package} | {label}: line {line} lacks {name}; got {findings}"
                      for line, name in expected if not _reported(findings, line, name)]
            wrong += [f"{package} | {label}: line {line} reports {name}; got {findings}"
                      for line, name in absent if _reported(findings, line, name)]
    assert not wrong, "AC-01: listed names hidden, or reported after a walrus:\n" + "\n".join(wrong)


# FIX-001 r3 (review r2 F9, owner option b): each finding below is exactly what this checker
# reported before FIX-001 (HEAD c852b0a, the same file as main 2e3e03d) for that source, and must
# still be reported. (label, source lines, findings in every pure package, extra costs/risk ones)
_ORIGINAL_CASES = (
    ("CORE-001 rules, each once", (
        "import builtins",
        "import datetime",
        "import importlib",
        "import os",
        "import time",
        "from pathlib import Path",
        "import socket",
        "import numpy",
        "from os import environ",
        "from os.path import *",
        "from ... import outside",
        "STAMPS = (time.time(), time.monotonic(), datetime.datetime.now(), datetime.date.today())",
        'TEXT = (open("x"), builtins.print(1), input(), os.getenv("X"), os.system("echo"))',
        'LINES = Path("x").read_text()',
        'HOME = os.environ["HOME"]',
        'PLUGINS = (__import__("json"), importlib.import_module("json"))',
        'CONNECTION = socket.create_connection(("example.invalid", 80))',
    ), (
        "line 8: forbidden import socket",
        "line 9: forbidden import numpy",
        "line 10: forbidden environment/network access os.environ",
        "line 11: wildcard import prevents alias verification",
        "line 12: relative import escapes its package",
        "line 13: forbidden clock/I/O call datetime.date.today",
        "line 13: forbidden clock/I/O call datetime.datetime.now",
        "line 13: forbidden clock/I/O call time.monotonic",
        "line 13: forbidden clock/I/O call time.time",
        "line 14: forbidden clock/I/O call builtins.print",
        "line 14: forbidden clock/I/O call input",
        "line 14: forbidden clock/I/O call open",
        "line 14: forbidden clock/I/O call os.getenv",
        "line 14: forbidden clock/I/O call os.system",
        "line 15: forbidden file I/O call .read_text",
        "line 16: forbidden environment/network access os.environ",
        "line 17: dynamic import prevents static boundary verification",
        "line 18: forbidden environment/network access socket",
        "line 18: forbidden environment/network access socket.create_connection",
    ), ()),
    ("socket and os.environ stored or read as a value (review r2 F9 A and B)", (
        "from dataclasses import dataclass",
        "from os import environ",
        "@dataclass(frozen=True)",
        "class Endpoint:",
        "    socket: str",
        "PICK = lambda *socket: socket",
        "def split(row):",
        "    (host, *socket), port = row",
        "    return socket",
        "def pick(subject):",
        "    match subject:",
        "        case [*socket]:",
        "            return socket",
        'socket = "tcp://example.invalid:80"',
        "environ = {}",
    ), (
        "line 3: forbidden environment/network access os.environ",
        "line 6: forbidden environment/network access socket",
        "line 7: forbidden environment/network access socket",
        "line 9: forbidden environment/network access socket",
        "line 10: forbidden environment/network access socket",
        "line 14: forbidden environment/network access socket",
        "line 15: forbidden environment/network access socket",
        "line 16: forbidden environment/network access os.environ",
    ), ()),
    ("the module passed into a binding, a walrus that does not run (review r2 F9 C and D)", (
        "import time",
        "FIRST = (lambda time: time.time())(time)",
        "SECOND = (lambda time=time: time.monotonic())()",
        "*rest, time = 0, time",
        "THIRD = time.perf_counter()",
        "X = 0 and (time := 0)",
        "FOURTH = time.process_time()",
    ), (
        "line 3: forbidden clock/I/O call time.time",
        "line 4: forbidden clock/I/O call time.monotonic",
        "line 6: forbidden clock/I/O call time.perf_counter",
        "line 8: forbidden clock/I/O call time.process_time",
    ), ()),
    ("evaluation order and captures with CORE-001 clocks (review r2 F6 and F7)", (
        "import time",
        "D = {1: time.time(), (time := 0): 2}",
        "import time",
        "X = {}",
        "X[(time := 0)] = time.time_ns()",
        "import time",
        "L = [(time := 0) for _ in [time.monotonic_ns()]]",
        "import time",
        "for X[(time := 0)] in [time.perf_counter_ns()]:",
        "    pass",
        "import time",
        "X[(time := 0)]: int = time.process_time_ns()",
        "import time",
        "match time:",
        "    case (int() as time) | (object() as time):",
        "        STAMP = time.time()",
        "match time:",
        "    case (object() as time) as other:",
        "        STAMP = time.monotonic()",
    ), (
        "line 3: forbidden clock/I/O call time.time",
        "line 6: forbidden clock/I/O call time.time_ns",
        "line 8: forbidden clock/I/O call time.monotonic_ns",
        "line 10: forbidden clock/I/O call time.perf_counter_ns",
        "line 13: forbidden clock/I/O call time.process_time_ns",
        "line 17: forbidden clock/I/O call time.time",
        "line 20: forbidden clock/I/O call time.monotonic",
    ), ()),
    ("a global in a class body, a function in an except-as handler (review r2 F8)", (
        "class Clock:",
        "    global clock",
        "    import time as clock",
        "    def stamp(self):",
        "        return clock.time()",
        "try:",
        "    raise ValueError",
        "except ValueError as time:",
        "    def later():",
        "        return time.time()",
        "import time",
        "STAMP = (later(), Clock().stamp())",
    ), (
        "line 6: forbidden clock/I/O call time.time",
        "line 11: forbidden clock/I/O call time.time",
    ), ()),
    ("float and random, reported in costs and risk only", (
        "import random",
        "from random import choice",
        'RATE = float("1.5")',
        "SPREAD = 0.25",
    ), (), (
        "line 2: forbidden random import",
        "line 3: forbidden random import",
        "line 4: forbidden float name",
        "line 5: forbidden float literal",
    )),
)


def test_fix001_ac04_every_finding_of_the_checker_before_fix001_is_still_reported():
    missing = []
    for label, lines, common, money in _ORIGINAL_CASES:
        source = _HEADER + "\n".join(lines) + "\n"
        for package, inspect in _PURE_CHECKERS:
            findings = inspect(source)
            expected = common + (money if package in ("sochron.costs", "sochron.risk") else ())
            missing += [f"{package} | {label}: lacks {finding!r}; got {findings}"
                        for finding in expected if finding not in findings]
    assert not missing, "AC-04: findings of the checker before FIX-001 lost:\n" + "\n".join(missing)


# CORE-005 AC-06 self-tests for the data.snapshot checker. Sources are inspected as
# sochron.data.snapshot (package and current package), so a relative import resolves there.
# (label, source lines, exact findings); line 1 is _HEADER, so the first source line is 2.
_SNAPSHOT_FORBIDDEN_IMPORTS = (
    ("broker", ("import sochron.broker",), ("line 2: forbidden import sochron.broker",)),
    ("broker adapter", ("from sochron.broker.mt5 import connect",),
     ("line 2: forbidden import sochron.broker.mt5",)),
    ("broker via the top package", ("from sochron import broker",),
     ("line 2: forbidden import sochron.broker",)),
    ("data.acquire", ("import sochron.data.acquire",),
     ("line 2: forbidden import sochron.data.acquire",)),
    ("data.acquire via the data package", ("from sochron.data import acquire",),
     ("line 2: forbidden import sochron.data",)),
    ("data.acquire by relative import", ("from ..acquire import pull_rates",),
     ("line 2: forbidden import sochron.data.acquire",)),
    ("execution", ("from sochron.execution import send",),
     ("line 2: forbidden import sochron.execution",)),
    ("journal", ("import sochron.journal",), ("line 2: forbidden import sochron.journal",)),
    ("research", ("from sochron import research",),
     ("line 2: forbidden import sochron.research",)),
    ("MetaTrader5", ("import MetaTrader5",), ("line 2: forbidden import MetaTrader5",)),
    ("MetaTrader5 aliased", ("import MetaTrader5 as mt5",),
     ("line 2: forbidden import MetaTrader5",)),
    ("a third-party package", ("import numpy",), ("line 2: forbidden import numpy",)),
    ("costs, which the module map does not grant", ("from sochron.costs import H001_COSTS",),
     ("line 2: forbidden import sochron.costs",)),
    ("random, imported", ("import random",), ("line 2: forbidden random import",)),
    ("random, from-imported", ("from random import choice",),
     ("line 2: forbidden random import",)),
    ("a clock", ("import time", "STAMP = time.time()",),
     ("line 3: forbidden clock/I/O call time.time",)),
    ("file I/O", ("from pathlib import Path", 'ROWS = Path("bars.parquet").read_bytes()',),
     ("line 3: forbidden file I/O call .read_bytes",)),
)
_SNAPSHOT_ALLOWED_IMPORTS = (
    ("core", ("import sochron.core", "from sochron.core import Bar", "from sochron import core")),
    ("timebase", ("import sochron.timebase", "from sochron.timebase import bar_open, to_utc",
                  "from sochron import timebase")),
    ("its own package", ("from . import validate", "from .validate import validate_m1",
                         "from sochron.data.snapshot.aggregate import aggregate")),
    ("side-effect-free stdlib", ("from collections.abc import Mapping, Sequence",
                                 "from dataclasses import dataclass, field",
                                 "from datetime import UTC, date, datetime, time, timedelta",
                                 "from decimal import Decimal", "from types import MappingProxyType",
                                 "from typing import Literal", "from zoneinfo import ZoneInfo",
                                 "import bisect", "import math")),
)


def _inspect_as_snapshot(source):
    return _inspect_data_snapshot_source(source, "sochron.data.snapshot", "sochron.data.snapshot")


def test_ac06_data_snapshot_checker_reports_forbidden_packages_and_admits_core_timebase_stdlib():
    wrong = []
    for label, lines, expected in _SNAPSHOT_FORBIDDEN_IMPORTS:
        findings = _inspect_as_snapshot(_HEADER + "\n".join(lines) + "\n")
        if findings != list(expected):
            wrong.append(f"{label}: expected {list(expected)}, got {findings}")
    for label, lines in _SNAPSHOT_ALLOWED_IMPORTS:
        findings = _inspect_as_snapshot(_HEADER + "\n".join(lines) + "\n")
        if findings:
            wrong.append(f"{label}: legitimate import reported: {findings}")
    # sochron.core keeps its own rule: it may import nothing from sochron, timebase included.
    findings = _inspect_data_snapshot_source(
        _HEADER + "from sochron.timebase import to_utc\n", "sochron.core", "sochron.core"
    )
    if findings != ["line 2: forbidden import sochron.timebase"]:
        wrong.append(f"core importing timebase: got {findings}")
    assert not wrong, "AC-06: snapshot import rules:\n" + "\n".join(wrong)


def test_ac06_data_snapshot_checker_keeps_every_fix001_and_core001_rule():
    wrong = []
    for label, source, expected in _forbidden_cases():
        findings = _inspect_as_snapshot(source)
        wrong += [f"{label}: line {line} lacks {name}; got {findings}"
                  for line, name in expected if not _reported(findings, line, name)]
    for label, lines, expected in _SCOPED_CASES:
        findings = _inspect_as_snapshot(_HEADER + "\n".join(lines) + "\n")
        wrong += [f"{label}: line {line} lacks {name}; got {findings}"
                  for line, name in expected if not _reported(findings, line, name)]
    for label, lines in _LEGITIMATE_SOURCES:
        findings = _inspect_as_snapshot(_HEADER + "\n".join(lines) + "\n")
        if findings:
            wrong.append(f"{label}: legitimate code reported: {findings}")
    for label, lines, expected, absent in _BINDING_CASES:
        findings = _inspect_as_snapshot(_HEADER + "\n".join(lines) + "\n")
        wrong += [f"{label}: line {line} lacks {name}; got {findings}"
                  for line, name in expected if not _reported(findings, line, name)]
        wrong += [f"{label}: line {line} reports {name}; got {findings}"
                  for line, name in absent if _reported(findings, line, name)]
    for label, lines, common, _ in _ORIGINAL_CASES:
        findings = _inspect_as_snapshot(_HEADER + "\n".join(lines) + "\n")
        for finding in common:
            if finding.endswith("relative import escapes its package"):
                # Three dots stay inside the deeper sochron.data.snapshot (sochron.outside),
                # which the same line reports as a forbidden import instead.
                line = finding.partition(":")[0]
                if not any(item.startswith(f"{line}: forbidden import ") for item in findings):
                    wrong.append(f"{label}: {line} lacks a finding; got {findings}")
            elif finding not in findings:
                wrong.append(f"{label}: lacks {finding!r}; got {findings}")
    assert not wrong, "AC-06: the snapshot checker lost a rule:\n" + "\n".join(wrong)


# CORE-005 v1.1 AC-06 self-tests (owner 2026-10-24: tests-r1 question 8 and F10).
# (label, source lines, exact findings); line 1 is _HEADER, so the first source line is 2.
_SNAPSHOT_FLOAT_CASES = (
    ("a float call", ('RATE = float("1.5")',), ("line 2: forbidden float name",)),
    ("a float literal", ("SPREAD = 0.25",), ("line 2: forbidden float literal",)),
    ("an exponent float literal", ("POINT = 1e-3",), ("line 2: forbidden float literal",)),
    ("float as a return type, a float literal in the body",
     ("def ratio(points: int) -> float:", "    return points / 1000.0"),
     ("line 2: forbidden float name", "line 3: forbidden float literal")),
    ("a float check next to planted random and file I/O",
     ("import random", 'NOISE = isinstance(open("x").read(), float)'),
     ("line 2: forbidden random import", "line 3: forbidden clock/I/O call open",
      "line 3: forbidden float name")),
    ("Decimal, int and str values are not float",
     ("from decimal import Decimal", 'POINT = Decimal("0.001")', "DIGITS = 3", 'LABEL = "0.25"'),
     ()),
)
# Inspected as src/sochron/data/__init__.py: package rules of sochron.data.snapshot, current
# package sochron.data, so a relative import resolves inside sochron.data.
_DATA_PACKAGE_CASES = (
    ("a docstring only", (), ()),
    ("re-exports from the snapshot", ("from .snapshot import aggregate, validate_m1",
                                      "from sochron.data.snapshot import H001_CLOSURES",
                                      "import sochron.data.snapshot"), ()),
    ("data.acquire through the package", ("from . import acquire",),
     ("line 2: forbidden import sochron.data",)),
    ("data.acquire by a relative module", ("from .acquire import pull_rates",),
     ("line 2: forbidden import sochron.data.acquire",)),
    ("data.acquire by an absolute import", ("import sochron.data.acquire",),
     ("line 2: forbidden import sochron.data.acquire",)),
    ("broker", ("from sochron import broker",), ("line 2: forbidden import sochron.broker",)),
    ("MetaTrader5", ("import MetaTrader5 as mt5",), ("line 2: forbidden import MetaTrader5",)),
    ("random", ("import random",), ("line 2: forbidden random import",)),
    ("file I/O at import", ('SEED = open("seed.txt").read()',),
     ("line 2: forbidden clock/I/O call open",)),
    ("a clock at import", ("import time", "LOADED = time.time()"),
     ("line 3: forbidden clock/I/O call time.time",)),
)


def _synthetic(lines):
    return _HEADER + "\n".join(lines) + "\n"


def _float_only(findings):
    return all(item.endswith((": forbidden float name", ": forbidden float literal")) for item in findings)


def test_ac06_v11_snapshot_checker_bans_float_names_and_literals_and_keeps_every_rule():
    wrong = []
    for label, lines, expected in _SNAPSHOT_FLOAT_CASES:
        findings = _inspect_data_snapshot_float_source(_synthetic(lines), "sochron.data.snapshot")
        if findings != list(expected):
            wrong.append(f"{label}: expected {list(expected)}, got {findings}")
    # The float ban only adds float findings to what the snapshot checker reports.
    sources = [(label, source) for label, source, _ in _forbidden_cases()]
    for table in (_SCOPED_CASES, _LEGITIMATE_SOURCES, _BINDING_CASES, _ORIGINAL_CASES,
                  _SNAPSHOT_FORBIDDEN_IMPORTS, _SNAPSHOT_ALLOWED_IMPORTS):
        sources += [(row[0], _synthetic(row[1])) for row in table]
    for label, source in sources:
        base = _inspect_as_snapshot(source)
        findings = _inspect_data_snapshot_float_source(source, "sochron.data.snapshot")
        if not set(base) <= set(findings) or not _float_only(set(findings) - set(base)):
            wrong.append(f"{label}: snapshot checker {base}; with the float ban {findings}")
    # The FIX-001 float and random row is now reported in snapshot as in costs and risk.
    for label, lines, _, money in _ORIGINAL_CASES:
        findings = _inspect_data_snapshot_float_source(_synthetic(lines), "sochron.data.snapshot")
        wrong += [f"{label}: lacks {finding!r}; got {findings}" for finding in money
                  if finding not in findings]
    assert not wrong, "AC-06: snapshot float ban:\n" + "\n".join(wrong)


def test_ac06_v11_data_package_init_checker_reports_acquire_io_random_and_admits_the_snapshot():
    wrong = []
    for label, lines, expected in _DATA_PACKAGE_CASES:
        findings = _inspect_data_package_source(_synthetic(lines), "sochron.data")
        if findings != list(expected):
            wrong.append(f"{label}: expected {list(expected)}, got {findings}")
    for label, source, expected in _forbidden_cases():
        findings = _inspect_data_package_source(source, "sochron.data")
        wrong += [f"{label}: line {line} lacks {name}; got {findings}"
                  for line, name in expected if not _reported(findings, line, name)]
    for label, lines in _LEGITIMATE_SOURCES:
        findings = _inspect_data_package_source(_synthetic(lines), "sochron.data")
        if findings:
            wrong.append(f"{label}: legitimate code reported: {findings}")
    assert not wrong, "AC-06: data package __init__ rules:\n" + "\n".join(wrong)


# CORE-006 AC-06: sochron.strategy (docs/architecture.md section 8, row strategy) may import
# sochron.core, sochron.timebase, itself and side-effect-free stdlib only: no broker,
# data.acquire, data.snapshot, execution, journal, backtest, research, risk or costs, no
# MetaTrader5, no I/O, clock, randomness, process, console or network, and no float.
def _inspect_strategy_source(source, current_package):
    """CORE-006 AC-06: the snapshot checks (random ban included) under the strategy package's
    rules, plus the costs/risk float ban."""
    findings = _inspect_data_snapshot_source(source, "sochron.strategy", current_package)
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Name) and node.id == "float":
            findings.append(f"line {node.lineno}: forbidden float name")
        if isinstance(node, ast.Constant) and type(node.value) is float:
            findings.append(f"line {node.lineno}: forbidden float literal")
    return sorted(set(findings))


def _inspect_as_strategy(source):
    return _inspect_strategy_source(source, "sochron.strategy")


# (label, source lines, exact findings); line 1 is _HEADER, so the first source line is 2.
_STRATEGY_FORBIDDEN = (
    ("broker", ("import sochron.broker",), ("line 2: forbidden import sochron.broker",)),
    ("broker adapter", ("from sochron.broker.mt5 import connect",),
     ("line 2: forbidden import sochron.broker.mt5",)),
    ("broker via the top package", ("from sochron import broker",),
     ("line 2: forbidden import sochron.broker",)),
    ("data.acquire", ("import sochron.data.acquire",),
     ("line 2: forbidden import sochron.data.acquire",)),
    ("data.acquire via the data package", ("from sochron.data import acquire",),
     ("line 2: forbidden import sochron.data",)),
    ("data.snapshot, which the module map does not grant",
     ("from sochron.data.snapshot import AggregatedBar",),
     ("line 2: forbidden import sochron.data.snapshot",)),
    ("execution", ("from sochron.execution import send",),
     ("line 2: forbidden import sochron.execution",)),
    ("journal", ("import sochron.journal",), ("line 2: forbidden import sochron.journal",)),
    ("backtest", ("from sochron.backtest import run",),
     ("line 2: forbidden import sochron.backtest",)),
    ("research", ("from sochron import research",),
     ("line 2: forbidden import sochron.research",)),
    ("risk", ("from sochron.risk import size_position",),
     ("line 2: forbidden import sochron.risk",)),
    ("costs", ("from sochron.costs import H001_COSTS",),
     ("line 2: forbidden import sochron.costs",)),
    ("MetaTrader5", ("import MetaTrader5",), ("line 2: forbidden import MetaTrader5",)),
    ("MetaTrader5 aliased", ("import MetaTrader5 as mt5",),
     ("line 2: forbidden import MetaTrader5",)),
    ("a third-party package", ("import numpy",), ("line 2: forbidden import numpy",)),
    ("random, imported", ("import random",), ("line 2: forbidden random import",)),
    ("random, from-imported", ("from random import Random",),
     ("line 2: forbidden random import",)),
    ("a seeded generator is still random", ("import random", "RNG = random.Random(7)"),
     ("line 2: forbidden random import",)),
    ("a clock", ("import time", "STAMP = time.time()"),
     ("line 3: forbidden clock/I/O call time.time",)),
    ("the current date", ("from datetime import datetime", "NOW = datetime.now()"),
     ("line 3: forbidden clock/I/O call datetime.datetime.now",)),
    ("file I/O", ("from pathlib import Path", 'ROWS = Path("bars.parquet").read_bytes()'),
     ("line 3: forbidden file I/O call .read_bytes",)),
    ("console output", ('print("decision")',), ("line 2: forbidden clock/I/O call print",)),
    ("the environment", ("import os", 'KEY = os.environ["MT5_LOGIN"]'),
     ("line 3: forbidden environment/network access os.environ",)),
    ("a process", ("import subprocess",), ("line 2: forbidden process import subprocess",)),
    ("a socket", ("import socket",), ("line 2: forbidden import socket",)),
    ("http", ("import http.client",), ("line 2: forbidden network import http.client",)),
    ("a float call", ('THETA = float("0.5")',), ("line 2: forbidden float name",)),
    ("a float literal", ("THETA = 0.5",), ("line 2: forbidden float literal",)),
    ("a float return type", ("def ratio(a, b) -> float:", "    return a / b"),
     ("line 2: forbidden float name",)),
)
_STRATEGY_ALLOWED = (
    ("core", ("import sochron.core", "from sochron.core import Bar", "from sochron import core")),
    ("timebase", ("import sochron.timebase",
                  "from sochron.timebase import NY_ENTRY_WINDOW, in_entry_window",
                  "from sochron import timebase")),
    ("its own package", ("from . import params", "from .indicators import indicators",
                         "from sochron.strategy.h001 import decide")),
    ("side-effect-free stdlib", ("from collections.abc import Mapping, Sequence",
                                 "from dataclasses import dataclass",
                                 "from datetime import datetime",
                                 "from decimal import ROUND_HALF_EVEN, Context, Decimal, localcontext",
                                 "from types import MappingProxyType", "from typing import Literal",
                                 "import bisect", "import math")),
    ("Decimal values in a module context", ("from decimal import ROUND_HALF_EVEN, Context, Decimal",
                                            "CONTEXT = Context(prec=28, rounding=ROUND_HALF_EVEN)",
                                            'THETA = Decimal("0.50")',
                                            "WARM = max(3 * 64, 96 + 1, 48 + 1, 97, 20 + 1)")),
)


def test_ac06_strategy_import_boundaries_no_io_clock_random_float_or_forbidden_package():
    wrong = []
    # The checker first: exact findings for forbidden sources, none for the granted imports.
    for label, lines, expected in _STRATEGY_FORBIDDEN:
        findings = _inspect_as_strategy(_synthetic(lines))
        if findings != list(expected):
            wrong.append(f"{label}: expected {list(expected)}, got {findings}")
    for label, lines in _STRATEGY_ALLOWED:
        findings = _inspect_as_strategy(_synthetic(lines))
        if findings:
            wrong.append(f"{label}: legitimate import reported: {findings}")
    # The new timebase grant is for strategy only: core, costs and risk still may not use it.
    source = _synthetic(("from sochron.timebase import to_utc",))
    for package, findings in (
        ("sochron.core", _inspect_core_source(source, "sochron.core")),
        ("sochron.costs", _inspect_costs_source(source, "sochron.costs")),
        ("sochron.risk", _inspect_risk_source(source, "sochron.risk")),
    ):
        if findings != ["line 2: forbidden import sochron.timebase"]:
            wrong.append(f"{package} importing timebase: got {findings}")
    # Every FIX-001 and CORE-001 rule, and the float and random row, hold for strategy too.
    for label, source, expected in _forbidden_cases():
        findings = _inspect_as_strategy(source)
        wrong += [f"{label}: line {line} lacks {name}; got {findings}"
                  for line, name in expected if not _reported(findings, line, name)]
    for label, lines, expected in _SCOPED_CASES:
        findings = _inspect_as_strategy(_synthetic(lines))
        wrong += [f"{label}: line {line} lacks {name}; got {findings}"
                  for line, name in expected if not _reported(findings, line, name)]
    for label, lines in _LEGITIMATE_SOURCES:
        findings = _inspect_as_strategy(_synthetic(lines))
        if findings:
            wrong.append(f"{label}: legitimate code reported: {findings}")
    for label, lines, expected, absent in _BINDING_CASES:
        findings = _inspect_as_strategy(_synthetic(lines))
        wrong += [f"{label}: line {line} lacks {name}; got {findings}"
                  for line, name in expected if not _reported(findings, line, name)]
        wrong += [f"{label}: line {line} reports {name}; got {findings}"
                  for line, name in absent if _reported(findings, line, name)]
    for label, lines, common, money in _ORIGINAL_CASES:
        findings = _inspect_as_strategy(_synthetic(lines))
        wrong += [f"{label}: lacks {finding!r}; got {findings}" for finding in common + money
                  if finding not in findings]
    assert not wrong, "AC-06: the strategy checker:\n" + "\n".join(wrong)

    # Then the package itself, which must exist.
    source_root = Path.cwd() / "src"
    directory = source_root / "sochron" / "strategy"
    assert directory.is_dir(), f"AC-06: {directory} does not exist; implementation missing"
    files = sorted(directory.rglob("*.py"))
    assert files, f"AC-06: {directory} contains no Python source; implementation missing"
    findings = []
    for path in files:
        relative = path.relative_to(source_root)
        current_package = ".".join(relative.parent.parts)
        try:
            violations = _inspect_strategy_source(path.read_text(encoding="utf-8-sig"), current_package)
        except SyntaxError as error:
            findings.append(f"{relative}:{error.lineno}: invalid Python syntax: {error.msg}")
            continue
        findings.extend(f"{relative}: {violation}" for violation in violations)
    assert not findings, "AC-06: forbidden dependencies or side effects:\n" + "\n".join(findings)


# CORE-006 tests r2 (review docs/reviews/CORE-006-tests-r1.md F4, owner 2026-10-24): the strategy
# scan uses an explicit stdlib list instead of "any stdlib module except socket". sochron.strategy
# may import exactly these stdlib modules (by full name), sochron.core, sochron.timebase and
# itself; every other import is a finding. _inspect_strategy_source and every table above stay as
# they were, so the round-1 test keeps its meaning and no other package's check changes: the new
# checker runs every round-1 strategy check and adds one finding per stdlib import not listed.
_STRATEGY_STDLIB = frozenset({
    "bisect", "collections", "collections.abc", "dataclasses", "datetime", "decimal", "enum",
    "functools", "itertools", "operator", "types", "typing",
})


def _inspect_strategy_listed_source(source, current_package):
    """CORE-006 tests r2 (F4): _inspect_strategy_source plus one finding for each absolute import of
    a stdlib module that is not in _STRATEGY_STDLIB, wherever the import statement stands."""
    findings = list(_inspect_strategy_source(source, current_package))
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            names = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.level == 0:
            names = [node.module or ""]
        else:
            continue
        for name in names:
            if name.split(".")[0] in sys.stdlib_module_names and name not in _STRATEGY_STDLIB:
                findings.append(f"line {node.lineno}: forbidden stdlib import {name}")
    return sorted(set(findings))


def _inspect_as_listed_strategy(source):
    return _inspect_strategy_listed_source(source, "sochron.strategy")


# (label, source lines, exact findings); line 1 is _HEADER, so the first source line is 2.
_STRATEGY_UNLISTED = (
    ("logging", ("import logging", 'LOG = logging.getLogger("strategy")'),
     ("line 2: forbidden stdlib import logging",)),
    ("a logging submodule", ("import logging.handlers",),
     ("line 2: forbidden stdlib import logging.handlers",)),
    ("logging, from-imported", ("from logging import getLogger",),
     ("line 2: forbidden stdlib import logging",)),
    ("sqlite3", ("import sqlite3", 'DB = sqlite3.connect("bars.db")'),
     ("line 2: forbidden stdlib import sqlite3",)),
    ("sqlite3, aliased", ("import sqlite3 as db",), ("line 2: forbidden stdlib import sqlite3",)),
    ("threading", ("import threading", "LOCK = threading.Lock()"),
     ("line 2: forbidden stdlib import threading",)),
    ("threading, from-imported", ("from threading import Thread",),
     ("line 2: forbidden stdlib import threading",)),
    ("asyncio", ("import asyncio", "LOOP = asyncio.new_event_loop()"),
     ("line 2: forbidden stdlib import asyncio",)),
    ("asyncio inside a function", ("def run(job):", "    import asyncio", "    return asyncio.run(job)"),
     ("line 3: forbidden stdlib import asyncio",)),
    ("shutil", ("import shutil", 'COPY = shutil.copyfile("a.csv", "b.csv")'),
     ("line 2: forbidden stdlib import shutil",)),
    ("shutil, from-imported", ("from shutil import rmtree",), ("line 2: forbidden stdlib import shutil",)),
    ("pathlib", ("import pathlib", 'HERE = pathlib.Path("bars")'),
     ("line 2: forbidden stdlib import pathlib",)),
    ("pathlib, from-imported", ("from pathlib import Path",), ("line 2: forbidden stdlib import pathlib",)),
    ("three in one statement", ("import logging, sqlite3, threading",),
     ("line 2: forbidden stdlib import logging", "line 2: forbidden stdlib import sqlite3",
      "line 2: forbidden stdlib import threading")),
    ("os.path", ("from os import path",), ("line 2: forbidden stdlib import os",)),
    ("math is free of side effects but not listed", ("import math",),
     ("line 2: forbidden stdlib import math",)),
    ("zoneinfo: strategy reads New York time through sochron.timebase", ("from zoneinfo import ZoneInfo",),
     ("line 2: forbidden stdlib import zoneinfo",)),
    ("__future__ is not listed either", ("from __future__ import annotations",),
     ("line 2: forbidden stdlib import __future__",)),
    ("next to a round-1 finding", ("import socket", "import logging"),
     ("line 2: forbidden import socket", "line 2: forbidden stdlib import socket",
      "line 3: forbidden stdlib import logging")),
)
_STRATEGY_LISTED = (
    ("each listed module", tuple(f"import {name}" for name in sorted(_STRATEGY_STDLIB))),
    ("each listed module, aliased",
     tuple(f"import {name} as listed_{index}" for index, name in enumerate(sorted(_STRATEGY_STDLIB)))),
    ("from-imports of listed modules", (
        "from bisect import bisect_left, bisect_right", "from collections import deque",
        "from collections.abc import Mapping, Sequence", "from dataclasses import dataclass, fields",
        "from datetime import UTC, datetime, timedelta",
        "from decimal import ROUND_HALF_EVEN, Context, Decimal, localcontext", "from enum import Enum",
        "from functools import cache, reduce", "from itertools import accumulate, islice",
        "from operator import attrgetter", "from types import MappingProxyType",
        "from typing import Final, Literal",
    )),
    ("a listed import inside a function", ("def window(rows):", "    from itertools import islice",
                                           "    return list(islice(rows, 96))")),
    ("core, timebase and the strategy package itself", (
        "import sochron.core", "from sochron.core import Bar", "from sochron import core",
        "import sochron.timebase", "from sochron.timebase import NY_ENTRY_WINDOW, in_entry_window",
        "from sochron import timebase", "from . import params", "from .indicators import indicators",
        "from sochron.strategy.h001 import decide",
    )),
)


def test_ac06_r2_strategy_imports_only_listed_stdlib_modules_core_timebase_and_itself():
    wrong = []
    # The checker first: exact findings for unlisted stdlib imports, none for the listed ones.
    for label, lines, expected in _STRATEGY_UNLISTED:
        findings = _inspect_as_listed_strategy(_synthetic(lines))
        if findings != list(expected):
            wrong.append(f"{label}: expected {list(expected)}, got {findings}")
    for label, lines in _STRATEGY_LISTED:
        findings = _inspect_as_listed_strategy(_synthetic(lines))
        if findings:
            wrong.append(f"{label}: listed import reported: {findings}")
    # The list only adds stdlib-import findings: every round-1 strategy finding stays, on every table.
    sources = [(label, source) for label, source, _ in _forbidden_cases()]
    for table in (_SCOPED_CASES, _LEGITIMATE_SOURCES, _BINDING_CASES, _ORIGINAL_CASES, _STRATEGY_FORBIDDEN,
                  _STRATEGY_ALLOWED, _STRATEGY_UNLISTED, _STRATEGY_LISTED):
        sources += [(row[0], _synthetic(row[1])) for row in table]
    for label, source in sources:
        base = _inspect_as_strategy(source)
        findings = _inspect_as_listed_strategy(source)
        added = set(findings) - set(base)
        listed_only = all(": forbidden stdlib import " in item for item in added)
        if not set(base) <= set(findings) or not listed_only:
            wrong.append(f"{label}: round-1 strategy checker {base}; with the list {findings}")
    assert not wrong, "AC-06: the strategy stdlib list:\n" + "\n".join(wrong)

    # Then the package itself, which must exist.
    source_root = Path.cwd() / "src"
    directory = source_root / "sochron" / "strategy"
    assert directory.is_dir(), f"AC-06: {directory} does not exist; implementation missing"
    files = sorted(directory.rglob("*.py"))
    assert files, f"AC-06: {directory} contains no Python source; implementation missing"
    findings = []
    for path in files:
        relative = path.relative_to(source_root)
        current_package = ".".join(relative.parent.parts)
        try:
            text = path.read_text(encoding="utf-8-sig")
            violations = _inspect_strategy_listed_source(text, current_package)
        except SyntaxError as error:
            findings.append(f"{relative}:{error.lineno}: invalid Python syntax: {error.msg}")
            continue
        findings.extend(f"{relative}: {violation}" for violation in violations)
    assert not findings, "AC-06: unlisted or forbidden imports or side effects:\n" + "\n".join(findings)


# CORE-007 AC-06: sochron.backtest (docs/architecture.md section 8, row backtest; contract
# docs/contracts/CORE-007-backtest.md v1.4, the time item of its input checks, r3 F38) may import
# sochron.core, sochron.timebase, sochron.strategy, sochron.costs, itself and the side-effect-free
# stdlib modules of _BACKTEST_STDLIB only: no data (data.snapshot included), risk, broker,
# execution, journal or research, no MetaTrader5, no I/O, clock, randomness, process, console or
# network, no float, no zoneinfo import and no astimezone (time is converted only through
# sochron.timebase). Every function and table above stays as it was: the backtest checker runs the
# snapshot checks (_inspect_source plus the random ban) unchanged, drops only the "forbidden import"
# findings of the three granted packages, and adds the float, zoneinfo, astimezone and stdlib-list
# findings. The stdlib list is the strategy list (CORE-006 tests r2, F4), kept under its own name.
_BACKTEST_GRANTS = ("sochron.timebase", "sochron.strategy", "sochron.costs")
_BACKTEST_STDLIB = frozenset({
    "bisect", "collections", "collections.abc", "dataclasses", "datetime", "decimal", "enum",
    "functools", "itertools", "operator", "types", "typing",
})
_IMPORT_FINDING = re.compile(r"line \d+: forbidden import (?P<module>\S+)")
_BACKTEST_ADDED = (": forbidden random import", ": forbidden float name", ": forbidden float literal",
                   ": forbidden zoneinfo import", ": forbidden astimezone use", ": forbidden stdlib import ")


def _granted_to_backtest(finding):
    """Whether a finding is only the import of sochron.timebase, sochron.strategy or sochron.costs."""
    match = _IMPORT_FINDING.fullmatch(finding)
    return bool(match) and any(_within(match["module"], grant) for grant in _BACKTEST_GRANTS)


def _inspect_backtest_source(source, current_package):
    """CORE-007 AC-06: the snapshot checks (random ban included) under the backtest package's rules
    and grants, plus the float ban, one finding per zoneinfo import, per astimezone attribute or
    "astimezone" string, and per absolute import of a stdlib module not in _BACKTEST_STDLIB."""
    findings = [item for item in _inspect_data_snapshot_source(source, "sochron.backtest", current_package)
                if not _granted_to_backtest(item)]
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Name) and node.id == "float":
            findings.append(f"line {node.lineno}: forbidden float name")
        if isinstance(node, ast.Constant) and type(node.value) is float:
            findings.append(f"line {node.lineno}: forbidden float literal")
        if isinstance(node, ast.Attribute) and node.attr == "astimezone":
            findings.append(f"line {node.lineno}: forbidden astimezone use")
        if isinstance(node, ast.Constant) and type(node.value) is str and node.value == "astimezone":
            findings.append(f"line {node.lineno}: forbidden astimezone use")
        if isinstance(node, ast.Import):
            names = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.level == 0:
            names = [node.module or ""]
        else:
            continue
        for name in names:
            if _within(name, "zoneinfo"):
                findings.append(f"line {node.lineno}: forbidden zoneinfo import")
            if name.split(".")[0] in sys.stdlib_module_names and name not in _BACKTEST_STDLIB:
                findings.append(f"line {node.lineno}: forbidden stdlib import {name}")
    return sorted(set(findings))


def _inspect_as_backtest(source):
    return _inspect_backtest_source(source, "sochron.backtest")


# (label, source lines, exact findings); line 1 is _HEADER, so the first source line is 2.
_BACKTEST_FORBIDDEN = (
    ("data.snapshot", ("from sochron.data.snapshot import AggregatedBar",),
     ("line 2: forbidden import sochron.data.snapshot",)),
    ("data via the top package", ("from sochron import data",), ("line 2: forbidden import sochron.data",)),
    ("data.acquire", ("import sochron.data.acquire",), ("line 2: forbidden import sochron.data.acquire",)),
    ("risk", ("from sochron.risk import size_position",), ("line 2: forbidden import sochron.risk",)),
    ("risk via the top package", ("from sochron import risk",), ("line 2: forbidden import sochron.risk",)),
    ("broker", ("import sochron.broker",), ("line 2: forbidden import sochron.broker",)),
    ("broker adapter", ("from sochron.broker.mt5 import connect",),
     ("line 2: forbidden import sochron.broker.mt5",)),
    ("execution", ("from sochron.execution import send",), ("line 2: forbidden import sochron.execution",)),
    ("journal", ("import sochron.journal",), ("line 2: forbidden import sochron.journal",)),
    ("research", ("from sochron import research",), ("line 2: forbidden import sochron.research",)),
    ("a package that only shares a granted prefix", ("import sochron.costsx",),
     ("line 2: forbidden import sochron.costsx",)),
    ("MetaTrader5", ("import MetaTrader5 as mt5",), ("line 2: forbidden import MetaTrader5",)),
    ("a third-party package", ("import numpy",), ("line 2: forbidden import numpy",)),
    ("zoneinfo", ("import zoneinfo",),
     ("line 2: forbidden stdlib import zoneinfo", "line 2: forbidden zoneinfo import")),
    ("ZoneInfo, from-imported", ("from zoneinfo import ZoneInfo",),
     ("line 2: forbidden stdlib import zoneinfo", "line 2: forbidden zoneinfo import")),
    ("zoneinfo inside a function", ("def wall(moment):", "    from zoneinfo import ZoneInfo",
                                    '    return ZoneInfo("America/New_York")'),
     ("line 3: forbidden stdlib import zoneinfo", "line 3: forbidden zoneinfo import")),
    ("an astimezone call", ("from datetime import UTC, datetime",
                            "OPEN = datetime(2026, 3, 10, tzinfo=UTC).astimezone(UTC)"),
     ("line 3: forbidden astimezone use",)),
    ("astimezone in a function", ("def wall(moment, zone):", "    return moment.astimezone(zone)"),
     ("line 3: forbidden astimezone use",)),
    ("astimezone kept as a reference", ("from datetime import datetime", "CONVERT = datetime.astimezone"),
     ("line 3: forbidden astimezone use",)),
    ("astimezone by name", ("def wall(moment, zone):", '    return getattr(moment, "astimezone")(zone)'),
     ("line 3: forbidden astimezone use",)),
    ("random", ("import random",), ("line 2: forbidden random import", "line 2: forbidden stdlib import random")),
    ("random, from-imported", ("from random import Random",),
     ("line 2: forbidden random import", "line 2: forbidden stdlib import random")),
    ("a clock", ("import time", "STAMP = time.time()"),
     ("line 2: forbidden stdlib import time", "line 3: forbidden clock/I/O call time.time")),
    ("the current date", ("from datetime import datetime", "NOW = datetime.now()"),
     ("line 3: forbidden clock/I/O call datetime.datetime.now",)),
    ("file I/O", ("from pathlib import Path", 'ROWS = Path("bars.parquet").read_bytes()'),
     ("line 2: forbidden stdlib import pathlib", "line 3: forbidden file I/O call .read_bytes")),
    ("console output", ('print("trade")',), ("line 2: forbidden clock/I/O call print",)),
    ("the environment", ("import os", 'KEY = os.environ["MT5_LOGIN"]'),
     ("line 2: forbidden stdlib import os", "line 3: forbidden environment/network access os.environ")),
    ("a process", ("import subprocess",),
     ("line 2: forbidden process import subprocess", "line 2: forbidden stdlib import subprocess")),
    ("a socket", ("import socket",), ("line 2: forbidden import socket", "line 2: forbidden stdlib import socket")),
    ("http", ("import http.client",),
     ("line 2: forbidden network import http.client", "line 2: forbidden stdlib import http.client")),
    ("logging", ("import logging",), ("line 2: forbidden stdlib import logging",)),
    ("math is free of side effects but not listed", ("import math",), ("line 2: forbidden stdlib import math",)),
    ("a float call", ('RATE = float("1.5")',), ("line 2: forbidden float name",)),
    ("a float literal", ("SPREAD = 0.24",), ("line 2: forbidden float literal",)),
    ("a float return type", ("def ratio(a, b) -> float:", "    return a / b"), ("line 2: forbidden float name",)),
)
_BACKTEST_ALLOWED = (
    ("core", ("import sochron.core", "from sochron.core import Bar", "from sochron import core")),
    ("timebase", ("import sochron.timebase", "from sochron.timebase import TimeRule, bar_open, to_utc, to_zone",
                  "from sochron import timebase")),
    ("strategy", ("import sochron.strategy", "from sochron.strategy import STRATEGY_VERSION, decide, indicators",
                  "from sochron import strategy", "from sochron.strategy.h001 import decide")),
    ("costs", ("import sochron.costs", "from sochron.costs import CONTEXT, check_volume, r_multiple, round_trip_cost",
               "from sochron import costs", "from sochron.costs.charges import CostBreakdown")),
    ("its own package", ("from . import fills", "from .fills import simulate_trade",
                         "from sochron.backtest.engine import run")),
    ("each listed stdlib module", tuple(f"import {name}" for name in sorted(_BACKTEST_STDLIB))),
    ("from-imports of listed modules", (
        "from collections.abc import Callable, Sequence", "from dataclasses import dataclass, field",
        "from datetime import UTC, datetime, time, timedelta",
        "from decimal import ROUND_HALF_EVEN, Context, Decimal, localcontext", "from typing import Literal",
    )),
    ("time through timebase, money in the costs context", (
        "from datetime import time",
        "from decimal import Decimal, localcontext",
        "from sochron.costs import CONTEXT",
        "from sochron.timebase import to_zone",
        "ROLLOVER = time(17, 0)",
        "def wall(moment):",
        '    return to_zone(moment, "America/New_York")',
        "def money(price, lots):",
        "    with localcontext(CONTEXT):",
        '        return price * Decimal("100") * lots',
    )),
)
# The grants are for backtest only: (package, checker, an import it must still report).
_BACKTEST_GRANTS_ELSEWHERE = (
    ("sochron.timebase", lambda source: _inspect_source(source, "sochron.timebase", "sochron.timebase"),
     ("sochron.strategy", "sochron.costs")),
    ("sochron.core", lambda source: _inspect_core_source(source, "sochron.core"), ("sochron.strategy", "sochron.costs")),
    ("sochron.costs", lambda source: _inspect_costs_source(source, "sochron.costs"), ("sochron.strategy",)),
    ("sochron.risk", lambda source: _inspect_risk_source(source, "sochron.risk"), ("sochron.strategy",)),
    ("sochron.data.snapshot", _inspect_as_snapshot, ("sochron.strategy", "sochron.costs")),
    ("sochron.strategy", _inspect_as_strategy, ("sochron.costs",)),
)


def test_ac06_core007_backtest_imports_only_core_timebase_strategy_costs_and_listed_stdlib():
    wrong = []
    # The checker first: exact findings for forbidden sources, none for the granted imports.
    for label, lines, expected in _BACKTEST_FORBIDDEN:
        findings = _inspect_as_backtest(_synthetic(lines))
        if findings != list(expected):
            wrong.append(f"{label}: expected {list(expected)}, got {findings}")
    for label, lines in _BACKTEST_ALLOWED:
        findings = _inspect_as_backtest(_synthetic(lines))
        if findings:
            wrong.append(f"{label}: legitimate import reported: {findings}")
    for package, inspect, modules in _BACKTEST_GRANTS_ELSEWHERE:
        for module in modules:
            findings = inspect(_synthetic((f"import {module}",)))
            if f"line 2: forbidden import {module}" not in findings:
                wrong.append(f"{package} importing {module}: got {findings}")
    # Every FIX-001 and CORE-001 rule, and the float and random row, hold for backtest too: the
    # findings of _inspect_source (less the three grants) all stay, and anything added is a
    # random, float, zoneinfo, astimezone or stdlib-list finding.
    sources = [(label, source) for label, source, _ in _forbidden_cases()]
    for table in (_SCOPED_CASES, _LEGITIMATE_SOURCES, _BINDING_CASES, _ORIGINAL_CASES, _SNAPSHOT_FORBIDDEN_IMPORTS,
                  _SNAPSHOT_ALLOWED_IMPORTS, _STRATEGY_FORBIDDEN, _STRATEGY_ALLOWED, _STRATEGY_UNLISTED,
                  _STRATEGY_LISTED, _BACKTEST_FORBIDDEN, _BACKTEST_ALLOWED):
        sources += [(row[0], _synthetic(row[1])) for row in table]
    for label, source in sources:
        base = [item for item in _inspect_source(source, "sochron.backtest", "sochron.backtest")
                if not _granted_to_backtest(item)]
        findings = _inspect_as_backtest(source)
        added = set(findings) - set(base)
        if not set(base) <= set(findings) or not all(any(kind in item for kind in _BACKTEST_ADDED) for item in added):
            wrong.append(f"{label}: the CORE-001 checker {base}; the backtest checker {findings}")
    for label, source, expected in _forbidden_cases():
        findings = _inspect_as_backtest(source)
        wrong += [f"{label}: line {line} lacks {name}; got {findings}"
                  for line, name in expected if not _reported(findings, line, name)]
    for label, lines, expected in _SCOPED_CASES:
        findings = _inspect_as_backtest(_synthetic(lines))
        wrong += [f"{label}: line {line} lacks {name}; got {findings}"
                  for line, name in expected if not _reported(findings, line, name)]
    for label, lines, expected, absent in _BINDING_CASES:
        findings = _inspect_as_backtest(_synthetic(lines))
        wrong += [f"{label}: line {line} lacks {name}; got {findings}"
                  for line, name in expected if not _reported(findings, line, name)]
        wrong += [f"{label}: line {line} reports {name}; got {findings}"
                  for line, name in absent if _reported(findings, line, name)]
    for label, lines, common, money in _ORIGINAL_CASES:
        findings = _inspect_as_backtest(_synthetic(lines))
        wrong += [f"{label}: lacks {finding!r}; got {findings}" for finding in common + money
                  if finding not in findings]
    assert not wrong, "AC-06: the backtest checker:\n" + "\n".join(wrong)

    # Then the package itself, which must exist.
    source_root = Path.cwd() / "src"
    directory = source_root / "sochron" / "backtest"
    assert directory.is_dir(), f"AC-06: {directory} does not exist; implementation missing"
    files = sorted(directory.rglob("*.py"))
    assert files, f"AC-06: {directory} contains no Python source; implementation missing"
    findings = []
    for path in files:
        relative = path.relative_to(source_root)
        current_package = ".".join(relative.parent.parts)
        try:
            violations = _inspect_backtest_source(path.read_text(encoding="utf-8-sig"), current_package)
        except SyntaxError as error:
            findings.append(f"{relative}:{error.lineno}: invalid Python syntax: {error.msg}")
            continue
        findings.extend(f"{relative}: {violation}" for violation in violations)
    assert not findings, "AC-06: forbidden dependencies or side effects in sochron.backtest:\n" + "\n".join(findings)


# CORE-007 tests r2 (review docs/reviews/CORE-007-tests-r1.md F6; contract v1.5, the time item of
# "Input และการตรวจ" and AC-06): sochron.backtest may not name ZoneInfo at all, wherever it would
# come from, sochron.timebase internals included. The contract builds the rollover instant T from
# the tzinfo of timebase.to_zone's result: datetime.combine(day, rollover.at,
# tzinfo=to_zone(...).tzinfo). _inspect_backtest_source and every table above stay as they were, so
# the round-1 test keeps its meaning. The new checker runs every round-1 backtest check and adds
# one finding per import statement that brings in a name ZoneInfo (from any module, at any
# relative level, aliased or not, or another name imported as ZoneInfo) and one per line that
# references the name: a bare name ZoneInfo, an attribute .ZoneInfo or the string "ZoneInfo".
_ZONEINFO_NAME = "ZoneInfo"
_ZONEINFO_ADDED = (": forbidden ZoneInfo import", ": forbidden ZoneInfo reference")


def _inspect_backtest_zoneinfo_source(source, current_package):
    """CORE-007 tests r2 (F6): _inspect_backtest_source plus the ZoneInfo import and reference
    findings, wherever the statement or expression stands."""
    findings = list(_inspect_backtest_source(source, current_package))
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            if any(_ZONEINFO_NAME in (alias.name.rpartition(".")[2], alias.asname) for alias in node.names):
                findings.append(f"line {node.lineno}: forbidden ZoneInfo import")
        elif ((isinstance(node, ast.Name) and node.id == _ZONEINFO_NAME)
              or (isinstance(node, ast.Attribute) and node.attr == _ZONEINFO_NAME)
              or (isinstance(node, ast.Constant) and type(node.value) is str and node.value == _ZONEINFO_NAME)):
            findings.append(f"line {node.lineno}: forbidden ZoneInfo reference")
    return sorted(set(findings))


def _inspect_as_backtest_zoneinfo(source):
    return _inspect_backtest_zoneinfo_source(source, "sochron.backtest")


# (label, source lines, exact findings); line 1 is _HEADER, so the first source line is 2.
_BACKTEST_ZONEINFO_FORBIDDEN = (
    ("ZoneInfo from timebase internals for the rollover instant (review F6 probe)",
     ("from datetime import datetime", "from sochron.timebase.convert import ZoneInfo",
      "def rollover_instant(day, at, zone):", "    return datetime.combine(day, at, tzinfo=ZoneInfo(zone))"),
     ("line 3: forbidden ZoneInfo import", "line 5: forbidden ZoneInfo reference")),
    ("ZoneInfo from timebase internals, aliased", ("from sochron.timebase.convert import ZoneInfo as Zone",
                                                   'TOKYO = Zone("Asia/Tokyo")'),
     ("line 2: forbidden ZoneInfo import",)),
    ("ZoneInfo from the timebase package", ("from sochron.timebase import ZoneInfo",),
     ("line 2: forbidden ZoneInfo import",)),
    ("ZoneInfo from timebase internals by a relative import", ("from ..timebase.sessions import ZoneInfo",),
     ("line 2: forbidden ZoneInfo import",)),
    ("ZoneInfo from timebase internals inside a function",
     ("def rollover_instant(day, at, zone):", "    from datetime import datetime",
      "    from sochron.timebase.convert import ZoneInfo",
      "    return datetime.combine(day, at, tzinfo=ZoneInfo(zone))"),
     ("line 4: forbidden ZoneInfo import", "line 5: forbidden ZoneInfo reference")),
    ("ZoneInfo as an attribute of a timebase module", ("from sochron.timebase import convert",
                                                       'NEW_YORK = convert.ZoneInfo("America/New_York")'),
     ("line 3: forbidden ZoneInfo reference",)),
    ("ZoneInfo by the full module path", ("import sochron.timebase.convert",
                                          'NEW_YORK = sochron.timebase.convert.ZoneInfo("America/New_York")'),
     ("line 3: forbidden ZoneInfo reference",)),
    ("ZoneInfo by name", ("from sochron.timebase import convert", 'ZONE = getattr(convert, "ZoneInfo")'),
     ("line 3: forbidden ZoneInfo reference",)),
    ("ZoneInfo from zoneinfo", ("from zoneinfo import ZoneInfo",),
     ("line 2: forbidden ZoneInfo import", "line 2: forbidden stdlib import zoneinfo",
      "line 2: forbidden zoneinfo import")),
    ("ZoneInfo as an attribute of zoneinfo", ("import zoneinfo", 'NEW_YORK = zoneinfo.ZoneInfo("America/New_York")'),
     ("line 2: forbidden stdlib import zoneinfo", "line 2: forbidden zoneinfo import",
      "line 3: forbidden ZoneInfo reference")),
    ("a bare name ZoneInfo in an annotation", ("def wall(moment, zone: ZoneInfo):", "    return moment"),
     ("line 2: forbidden ZoneInfo reference",)),
    ("another name imported as ZoneInfo", ("from datetime import timezone as ZoneInfo",),
     ("line 2: forbidden ZoneInfo import",)),
)
_BACKTEST_ZONEINFO_ALLOWED = (
    ("T from the tzinfo of timebase.to_zone (contract v1.5)", (
        "from datetime import datetime, time",
        "from sochron.timebase import to_zone",
        "ROLLOVER = time(17, 0)",
        "def rollover_instant(day, moment, zone):",
        "    return datetime.combine(day, ROLLOVER, tzinfo=to_zone(moment, zone).tzinfo)",
    )),
    ("the timebase functions the contract names", ("from sochron.timebase import bar_open, to_utc, to_zone",
                                                   "import sochron.timebase", "from sochron import timebase")),
    ("words and names that only contain ZoneInfo", (
        '"""T uses the tzinfo of to_zone, never ZoneInfo."""',
        'ZONE_INFO = "America/New_York"',
        'NOTE = "no ZoneInfo here"',
        "ZoneInfoText = ZONE_INFO",
    )),
)


def test_ac06_r2_core007_backtest_never_names_zoneinfo():
    wrong = []
    # The checker first: exact findings for every way to reach ZoneInfo, none for the contract's form.
    for label, lines, expected in _BACKTEST_ZONEINFO_FORBIDDEN:
        findings = _inspect_as_backtest_zoneinfo(_synthetic(lines))
        if findings != list(expected):
            wrong.append(f"{label}: expected {list(expected)}, got {findings}")
    for label, lines in _BACKTEST_ZONEINFO_ALLOWED:
        findings = _inspect_as_backtest_zoneinfo(_synthetic(lines))
        if findings:
            wrong.append(f"{label}: legitimate source reported: {findings}")
    # The new findings only add to the round-1 backtest checker: every round-1 finding stays, on
    # every table, and anything added is a ZoneInfo finding.
    sources = [(label, source) for label, source, _ in _forbidden_cases()]
    for table in (_SCOPED_CASES, _LEGITIMATE_SOURCES, _BINDING_CASES, _ORIGINAL_CASES, _SNAPSHOT_FORBIDDEN_IMPORTS,
                  _SNAPSHOT_ALLOWED_IMPORTS, _STRATEGY_FORBIDDEN, _STRATEGY_ALLOWED, _STRATEGY_UNLISTED,
                  _STRATEGY_LISTED, _BACKTEST_FORBIDDEN, _BACKTEST_ALLOWED, _BACKTEST_ZONEINFO_FORBIDDEN,
                  _BACKTEST_ZONEINFO_ALLOWED):
        sources += [(row[0], _synthetic(row[1])) for row in table]
    for label, source in sources:
        base = _inspect_as_backtest(source)
        findings = _inspect_as_backtest_zoneinfo(source)
        added = set(findings) - set(base)
        if not set(base) <= set(findings) or not all(item.endswith(_ZONEINFO_ADDED) for item in added):
            wrong.append(f"{label}: the round-1 backtest checker {base}; with the ZoneInfo rule {findings}")
    assert not wrong, "AC-06: the backtest ZoneInfo checker:\n" + "\n".join(wrong)

    # Then the package itself, which must exist.
    source_root = Path.cwd() / "src"
    directory = source_root / "sochron" / "backtest"
    assert directory.is_dir(), f"AC-06: {directory} does not exist; implementation missing"
    files = sorted(directory.rglob("*.py"))
    assert files, f"AC-06: {directory} contains no Python source; implementation missing"
    findings = []
    for path in files:
        relative = path.relative_to(source_root)
        current_package = ".".join(relative.parent.parts)
        try:
            violations = _inspect_backtest_zoneinfo_source(path.read_text(encoding="utf-8-sig"), current_package)
        except SyntaxError as error:
            findings.append(f"{relative}:{error.lineno}: invalid Python syntax: {error.msg}")
            continue
        findings.extend(f"{relative}: {violation}" for violation in violations)
    assert not findings, "AC-06: ZoneInfo or other forbidden names in sochron.backtest:\n" + "\n".join(findings)


# CORE-008 AC-06: sochron.research (docs/contracts/CORE-008-research.md v1.5, Invariants; the
# contract narrows docs/architecture.md section 8, row research: no data package at all) may import
# sochron.core, sochron.timebase, sochron.strategy, sochron.costs, sochron.backtest, itself and the
# stdlib modules of _RESEARCH_STDLIB only: no data (data.snapshot included), risk, broker, execution
# or journal, no MetaTrader5, no os, clock, float, network, process or console. Randomness only from
# random.Random built with a seed, drawn with randrange: the module-level functions of random, an
# unseeded Random and the other generator methods are findings. File I/O only in
# src/sochron/research/registry.py, and there only open(path, "ab" or "rb"), path.open("ab" or "rb")
# and path.read_bytes() with a literal mode (the contract appends with open(path, "ab") and reads
# bytes); nothing in research deletes, renames or truncates a file. Every function and table above
# stays as it was: the research checker runs _inspect_source unchanged, drops only the "forbidden
# import" findings of the four granted packages and, in registry.py only, the I/O finding of each
# allowed call on its own line, and adds its own findings.
_RESEARCH_GRANTS = ("sochron.timebase", "sochron.strategy", "sochron.costs", "sochron.backtest")
_RESEARCH_STDLIB = frozenset({
    "bisect", "collections", "collections.abc", "dataclasses", "datetime", "decimal", "enum", "functools",
    "hashlib", "itertools", "json", "operator", "pathlib", "random", "types", "typing",
})
_RESEARCH_RNG_METHODS = frozenset({
    "random", "uniform", "triangular", "gauss", "normalvariate", "lognormvariate", "expovariate",
    "vonmisesvariate", "gammavariate", "betavariate", "paretovariate", "weibullvariate", "binomialvariate",
    "choice", "choices", "shuffle", "sample", "seed", "getrandbits", "randint", "randbytes", "getstate",
    "setstate",
})
_RESEARCH_FILE_CHANGES = frozenset({"unlink", "rmdir", "truncate", "rename", "touch", "mkdir"})
_RESEARCH_MODES = frozenset({"ab", "rb"})
_RESEARCH_IO = (": forbidden clock/I/O call open", ": forbidden file I/O call .open",
                ": forbidden file I/O call .read_bytes")
_RESEARCH_ADDED = (": forbidden float name", ": forbidden float literal", ": forbidden stdlib import ",
                   ": forbidden random use ", ": forbidden random import ", ": forbidden unseeded Random",
                   ": forbidden random method ", ": forbidden file change ")


def _granted_to_research(finding):
    """Whether a finding is only the import of one of the four packages granted to sochron.research."""
    match = _IMPORT_FINDING.fullmatch(finding)
    return bool(match) and any(_within(match["module"], grant) for grant in _RESEARCH_GRANTS)


def _research_mode(node, position):
    """The mode of an open call when it is a str literal (positional or mode=), else None."""
    mode = node.args[position] if len(node.args) > position else next(
        (keyword.value for keyword in node.keywords if keyword.arg == "mode"), None)
    return mode.value if isinstance(mode, ast.Constant) and type(mode.value) is str else None


def _research_allowed_io(tree):
    """(line, finding suffix) of each binary read or append registry.py may make."""
    allowed = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Name) and func.id == "open" and _research_mode(node, 1) in _RESEARCH_MODES:
            allowed.add((node.lineno, _RESEARCH_IO[0]))
        elif isinstance(func, ast.Attribute) and func.attr == "open" and _research_mode(node, 0) in _RESEARCH_MODES:
            allowed.add((node.lineno, _RESEARCH_IO[1]))
        elif isinstance(func, ast.Attribute) and func.attr == "read_bytes" and not node.args and not node.keywords:
            allowed.add((node.lineno, _RESEARCH_IO[2]))
    return allowed


def _inspect_research_source(source, current_package, registry=False):
    """CORE-008 AC-06: _inspect_source under the research package's rules and grants (registry.py may
    make the allowed binary reads and appends), plus the float ban, the random rules, the file-change
    ban and one finding per absolute import of a stdlib module not in _RESEARCH_STDLIB."""
    tree = ast.parse(source)
    findings = [item for item in _inspect_source(source, "sochron.research", current_package)
                if not _granted_to_research(item)]
    if registry:
        allowed = {f"line {line}{suffix}" for line, suffix in _research_allowed_io(tree)}
        findings = [item for item in findings if item not in allowed]
    modules, constructors = set(), set()  # names bound to the random module and to random.Random
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.asname or "random" for alias in node.names if alias.name == "random")
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module == "random":
            constructors.update(alias.asname or "Random" for alias in node.names if alias.name == "Random")
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id == "float":
            findings.append(f"line {node.lineno}: forbidden float name")
        if isinstance(node, ast.Constant) and type(node.value) is float:
            findings.append(f"line {node.lineno}: forbidden float literal")
        on_module = isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id in modules
        if on_module and node.attr != "Random":
            findings.append(f"line {node.lineno}: forbidden random use random.{node.attr}")
        if isinstance(node, ast.Call):
            func = node.func
            from_module = isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name) and func.value.id in modules
            generator = (from_module and func.attr == "Random") or (isinstance(func, ast.Name) and func.id in constructors)
            if generator and not node.args and not node.keywords:
                findings.append(f"line {node.lineno}: forbidden unseeded Random")
            if isinstance(func, ast.Attribute) and func.attr in _RESEARCH_RNG_METHODS and not from_module:
                findings.append(f"line {node.lineno}: forbidden random method .{func.attr}")
            if isinstance(func, ast.Attribute) and func.attr in _RESEARCH_FILE_CHANGES:
                findings.append(f"line {node.lineno}: forbidden file change .{func.attr}")
        if isinstance(node, ast.Import):
            names = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.level == 0:
            names = [node.module or ""]
            if node.module == "random":
                findings += [f"line {node.lineno}: forbidden random import random.{alias.name}"
                             for alias in node.names if alias.name != "Random"]
        else:
            continue
        for name in names:
            if name.split(".")[0] in sys.stdlib_module_names and name not in _RESEARCH_STDLIB:
                findings.append(f"line {node.lineno}: forbidden stdlib import {name}")
    return sorted(set(findings))


def _inspect_as_research(source):
    return _inspect_research_source(source, "sochron.research")


def _inspect_as_registry(source):
    return _inspect_research_source(source, "sochron.research", registry=True)


# (label, source lines, exact findings); line 1 is _HEADER, so the first source line is 2.
_RESEARCH_FORBIDDEN = (
    ("data.snapshot", ("from sochron.data.snapshot import AggregatedBar",),
     ("line 2: forbidden import sochron.data.snapshot",)),
    ("the data package", ("import sochron.data",), ("line 2: forbidden import sochron.data",)),
    ("data via the top package", ("from sochron import data",), ("line 2: forbidden import sochron.data",)),
    ("data.acquire", ("import sochron.data.acquire",), ("line 2: forbidden import sochron.data.acquire",)),
    ("risk", ("from sochron.risk import size_position",), ("line 2: forbidden import sochron.risk",)),
    ("risk via the top package", ("from sochron import risk",), ("line 2: forbidden import sochron.risk",)),
    ("broker", ("import sochron.broker",), ("line 2: forbidden import sochron.broker",)),
    ("broker adapter", ("from sochron.broker.mt5 import connect",),
     ("line 2: forbidden import sochron.broker.mt5",)),
    ("execution", ("from sochron.execution import send",), ("line 2: forbidden import sochron.execution",)),
    ("journal", ("import sochron.journal",), ("line 2: forbidden import sochron.journal",)),
    ("a package that only shares a granted prefix", ("import sochron.backtests",),
     ("line 2: forbidden import sochron.backtests",)),
    ("MetaTrader5", ("import MetaTrader5 as mt5",), ("line 2: forbidden import MetaTrader5",)),
    ("a third-party package", ("import numpy",), ("line 2: forbidden import numpy",)),
    ("os", ("import os",), ("line 2: forbidden stdlib import os",)),
    ("os.path", ("import os.path",), ("line 2: forbidden stdlib import os.path",)),
    ("os, from-imported", ("from os import path",), ("line 2: forbidden stdlib import os",)),
    ("the environment", ("import os", 'KEY = os.environ["MT5_LOGIN"]'),
     ("line 2: forbidden stdlib import os", "line 3: forbidden environment/network access os.environ")),
    ("a clock", ("import time", "STAMP = time.time()"),
     ("line 2: forbidden stdlib import time", "line 3: forbidden clock/I/O call time.time")),
    ("the current date", ("from datetime import datetime", "NOW = datetime.now()"),
     ("line 3: forbidden clock/I/O call datetime.datetime.now",)),
    ("a binary read outside registry.py", ("from pathlib import Path", 'ROWS = Path("r.jsonl").read_bytes()'),
     ("line 3: forbidden file I/O call .read_bytes",)),
    ("an append outside registry.py", ('HANDLE = open("r.jsonl", "ab")',), ("line 2: forbidden clock/I/O call open",)),
    ("console output", ('print("run")',), ("line 2: forbidden clock/I/O call print",)),
    ("a console stream", ("import sys", 'sys.stdout.write("x")'),
     ("line 2: forbidden stdlib import sys", "line 3: forbidden console stream access sys.stdout",
      "line 3: forbidden console stream access sys.stdout.write")),
    ("a process", ("import subprocess",),
     ("line 2: forbidden process import subprocess", "line 2: forbidden stdlib import subprocess")),
    ("a socket", ("import socket",), ("line 2: forbidden import socket", "line 2: forbidden stdlib import socket")),
    ("http", ("import http.client",),
     ("line 2: forbidden network import http.client", "line 2: forbidden stdlib import http.client")),
    ("urllib", ("import urllib.request",), ("line 2: forbidden stdlib import urllib.request",)),
    ("secrets", ("import secrets",),
     ("line 2: forbidden randomness import secrets", "line 2: forbidden stdlib import secrets")),
    ("logging", ("import logging",), ("line 2: forbidden stdlib import logging",)),
    ("math is free of side effects but not listed", ("import math",), ("line 2: forbidden stdlib import math",)),
    ("zoneinfo: time goes through sochron.timebase", ("from zoneinfo import ZoneInfo",),
     ("line 2: forbidden stdlib import zoneinfo",)),
    ("shutil", ("import shutil",), ("line 2: forbidden stdlib import shutil",)),
    ("tempfile", ("import tempfile",), ("line 2: forbidden stdlib import tempfile",)),
    ("a float call", ('RATE = float("1.5")',), ("line 2: forbidden float name",)),
    ("a float literal", ("SPREAD = 0.24",), ("line 2: forbidden float literal",)),
    ("a float return type", ("def ratio(a, b) -> float:", "    return a / b"), ("line 2: forbidden float name",)),
    ("the module-level generator", ("import random", "DRAW = random.random()"),
     ("line 3: forbidden random use random.random",)),
    ("module-level randrange", ("import random", "def draw(n):", "    return random.randrange(n)"),
     ("line 4: forbidden random use random.randrange",)),
    ("seeding the module-level generator", ("import random", "random.seed(7)"),
     ("line 3: forbidden random use random.seed",)),
    ("module-level randrange, aliased", ("import random as rnd", "DRAW = rnd.randrange(10)"),
     ("line 3: forbidden random use random.randrange",)),
    ("randrange from-imported", ("from random import randrange",),
     ("line 2: forbidden random import random.randrange",)),
    ("choice from-imported, aliased", ("from random import choice as pick",),
     ("line 2: forbidden random import random.choice",)),
    ("an unseeded generator", ("import random", "RNG = random.Random()"), ("line 3: forbidden unseeded Random",)),
    ("an unseeded generator, from-imported", ("from random import Random", "RNG = Random()"),
     ("line 3: forbidden unseeded Random",)),
    ("SystemRandom", ("import random", "RNG = random.SystemRandom()"),
     ("line 3: forbidden random use random.SystemRandom", "line 3: forbidden randomness access random.SystemRandom")),
    ("a float draw from a generator", ("def draw(rng):", "    return rng.random()"),
     ("line 3: forbidden random method .random",)),
    ("choice from a generator", ("def pick(rng, pool):", "    return rng.choice(pool)"),
     ("line 3: forbidden random method .choice",)),
    ("shuffle", ("def mix(rng, pool):", "    rng.shuffle(pool)"), ("line 3: forbidden random method .shuffle",)),
    ("reseeding a generator", ("def again(rng):", "    rng.seed(1)"), ("line 3: forbidden random method .seed",)),
    ("deleting a file", ("def drop(path):", "    path.unlink()"), ("line 3: forbidden file change .unlink",)),
    ("truncating a file", ("def cut(handle):", "    handle.truncate(0)"), ("line 3: forbidden file change .truncate",)),
    ("renaming a file", ("def move(path, other):", "    path.rename(other)"), ("line 3: forbidden file change .rename",)),
)
_RESEARCH_ALLOWED = (
    ("core", ("import sochron.core", "from sochron.core import Bar", "from sochron import core")),
    ("timebase", ("import sochron.timebase", "from sochron.timebase import TimeRule, bar_open, to_utc",
                  "from sochron import timebase")),
    ("strategy", ("import sochron.strategy", "from sochron.strategy import entry_blockers, indicators",
                  "from sochron import strategy", "from sochron.strategy.params import H001Params")),
    ("costs", ("import sochron.costs", "from sochron.costs import CONTEXT, CostModel", "from sochron import costs")),
    ("backtest", ("import sochron.backtest", "from sochron.backtest import Result, SizedLots, run, simulate_trade",
                  "from sochron import backtest", "from sochron.backtest.trade import simulate_trade")),
    ("its own package", ("from . import registry", "from .registry import append_record",
                         "from sochron.research.model import RunRecord")),
    ("each listed stdlib module", tuple(f"import {name}" for name in sorted(_RESEARCH_STDLIB))),
    ("from-imports of listed modules", (
        "from bisect import bisect_right", "from collections.abc import Mapping, Sequence",
        "from dataclasses import dataclass, fields, replace", "from datetime import UTC, datetime",
        "from decimal import ROUND_CEILING, ROUND_HALF_UP, Decimal, localcontext", "from hashlib import sha256",
        "from itertools import islice", "from json import dumps, loads", "from pathlib import Path",
        "from random import Random", "from typing import Literal",
    )),
    ("a seeded generator and randrange", ("import random", "def generator(seed):", "    return random.Random(seed)",
                                          "def draw(rng, pool):", "    return pool.pop(rng.randrange(len(pool)))")),
    ("a seeded generator, from-imported", ("from random import Random", "RNG = Random(7)", "VALUE = RNG.randrange(10)")),
    ("a path check without I/O", ("from pathlib import Path", "def is_registry(path: Path) -> bool:",
                                  '    return path.name.endswith(".jsonl")')),
    ("hashing canonical JSON", ("import hashlib", "import json", "def run_id(obj):",
                                '    text = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True)',
                                '    return hashlib.sha256(text.encode("ascii")).hexdigest()')),
    ("Decimal in the costs context", ("from decimal import Decimal, localcontext", "from sochron.costs import CONTEXT",
                                      "def mean(values):", "    with localcontext(CONTEXT):",
                                      "        return sum(values, Decimal(0)) / len(values)")),
    ("a field named seed is no generator method", ("def seed_of(record):", "    return record.seed")),
)
# Inspected as src/sochron/research/registry.py: (label, source lines, exact findings).
_RESEARCH_REGISTRY_CASES = (
    ("an append with open(path, 'ab')", ("def append(path, line):", '    with open(path, "ab") as handle:',
                                         "        handle.write(line)", "        handle.flush()"), ()),
    ("a binary read with read_bytes", ("def read(path):", "    return path.read_bytes()"), ()),
    ("a binary read with open(path, 'rb')", ("def read(path):", '    with open(path, "rb") as handle:',
                                             "        return handle.read()"), ()),
    ("path.open('ab') and mode= forms", ("def append(path, line):", '    with path.open("ab") as handle:',
                                         "        handle.write(line)", "def append_too(path, line):",
                                         '    with open(path, mode="ab") as handle:', "        handle.write(line)",
                                         "def read(path):", '    with path.open(mode="rb") as handle:',
                                         "        return handle.read()"), ()),
    ("a text append (CRLF on Windows)", ("def append(path, text):", '    with open(path, "a") as handle:',
                                         "        handle.write(text)"), ("line 3: forbidden clock/I/O call open",)),
    ("an overwrite", ("def write(path, line):", '    return open(path, "w")'), ("line 3: forbidden clock/I/O call open",)),
    ("a binary overwrite", ("def write(path):", '    return open(path, "wb")'), ("line 3: forbidden clock/I/O call open",)),
    ("read and write", ("def change(path):", '    return open(path, "r+b")'), ("line 3: forbidden clock/I/O call open",)),
    ("the default text mode", ("def read(path):", "    return open(path)"), ("line 3: forbidden clock/I/O call open",)),
    ("a mode that is no literal", ("def append(path, mode):", "    return open(path, mode)"),
     ("line 3: forbidden clock/I/O call open",)),
    ("open through another name", ("OPEN = open", "def append(path):", '    return OPEN(path, "ab")'),
     ("line 4: forbidden clock/I/O call open",)),
    ("path.open in text mode", ("def append(path):", '    return path.open("a")'),
     ("line 3: forbidden file I/O call .open",)),
    ("read_text", ("def read(path):", "    return path.read_text()"), ("line 3: forbidden file I/O call .read_text",)),
    ("write_bytes", ("def write(path, data):", "    path.write_bytes(data)"),
     ("line 3: forbidden file I/O call .write_bytes",)),
    ("write_text", ("def write(path, text):", "    path.write_text(text)"),
     ("line 3: forbidden file I/O call .write_text",)),
    ("stat", ("def size(path):", "    return path.stat().st_size"), ("line 3: forbidden file I/O call .stat",)),
    ("console output", ("def log(record):", "    print(record)"), ("line 3: forbidden clock/I/O call print",)),
    ("deleting the registry", ("def drop(path):", "    path.unlink()"), ("line 3: forbidden file change .unlink",)),
    ("truncating the registry", ("def cut(handle):", "    handle.truncate(0)"),
     ("line 3: forbidden file change .truncate",)),
    ("os", ("import os",), ("line 2: forbidden stdlib import os",)),
)
# The research grants are for research only: (package, checker, imports it must still report).
_RESEARCH_GRANTS_ELSEWHERE = (
    ("sochron.timebase", lambda source: _inspect_source(source, "sochron.timebase", "sochron.timebase"),
     ("sochron.backtest", "sochron.research")),
    ("sochron.core", lambda source: _inspect_core_source(source, "sochron.core"), ("sochron.backtest",)),
    ("sochron.costs", lambda source: _inspect_costs_source(source, "sochron.costs"), ("sochron.backtest",)),
    ("sochron.risk", lambda source: _inspect_risk_source(source, "sochron.risk"), ("sochron.backtest",)),
    ("sochron.data.snapshot", _inspect_as_snapshot, ("sochron.backtest", "sochron.research")),
    ("sochron.strategy", _inspect_as_listed_strategy, ("sochron.backtest", "sochron.costs", "sochron.research")),
    ("sochron.backtest", _inspect_as_backtest_zoneinfo, ("sochron.research",)),
)


def test_ac06_core008_research_imports_only_its_grants_and_listed_stdlib_and_does_io_only_in_registry():
    wrong = []
    # The checker first: exact findings for forbidden sources, none for the granted ones.
    for label, lines, expected in _RESEARCH_FORBIDDEN:
        findings = _inspect_as_research(_synthetic(lines))
        if findings != list(expected):
            wrong.append(f"{label}: expected {list(expected)}, got {findings}")
    for label, lines in _RESEARCH_ALLOWED:
        for inspect in (_inspect_as_research, _inspect_as_registry):
            findings = inspect(_synthetic(lines))
            if findings:
                wrong.append(f"{label}: legitimate source reported: {findings}")
    for label, lines, expected in _RESEARCH_REGISTRY_CASES:
        findings = _inspect_as_registry(_synthetic(lines))
        if findings != list(expected):
            wrong.append(f"registry.py, {label}: expected {list(expected)}, got {findings}")
        if len(lines) > 1 and not _inspect_as_research(_synthetic(lines)):
            wrong.append(f"outside registry.py, {label}: no finding")
    for package, inspect, modules in _RESEARCH_GRANTS_ELSEWHERE:
        for module in modules:
            findings = inspect(_synthetic((f"import {module}",)))
            if f"line 2: forbidden import {module}" not in findings:
                wrong.append(f"{package} importing {module}: got {findings}")
    # Every FIX-001 and CORE-001 rule holds for research too: the findings of _inspect_source (less the
    # four grants) all stay, anything added is one of the research kinds, and registry.py only loses
    # the I/O findings of its allowed calls.
    sources = [(label, source) for label, source, _ in _forbidden_cases()]
    for table in (_SCOPED_CASES, _LEGITIMATE_SOURCES, _BINDING_CASES, _ORIGINAL_CASES, _SNAPSHOT_FORBIDDEN_IMPORTS,
                  _SNAPSHOT_ALLOWED_IMPORTS, _STRATEGY_FORBIDDEN, _STRATEGY_ALLOWED, _STRATEGY_UNLISTED,
                  _STRATEGY_LISTED, _BACKTEST_FORBIDDEN, _BACKTEST_ALLOWED, _BACKTEST_ZONEINFO_FORBIDDEN,
                  _BACKTEST_ZONEINFO_ALLOWED, _RESEARCH_FORBIDDEN, _RESEARCH_ALLOWED, _RESEARCH_REGISTRY_CASES):
        sources += [(row[0], _synthetic(row[1])) for row in table]
    for label, source in sources:
        base = [item for item in _inspect_source(source, "sochron.research", "sochron.research")
                if not _granted_to_research(item)]
        findings = _inspect_as_research(source)
        added = set(findings) - set(base)
        if not set(base) <= set(findings) or not all(any(kind in item for kind in _RESEARCH_ADDED) for item in added):
            wrong.append(f"{label}: the CORE-001 checker {base}; the research checker {findings}")
        in_registry = _inspect_as_registry(source)
        dropped = set(findings) - set(in_registry)
        if not set(in_registry) <= set(findings) or not all(item.endswith(_RESEARCH_IO) for item in dropped):
            wrong.append(f"{label}: outside registry.py {findings}; in registry.py {in_registry}")
    for label, source, expected in _forbidden_cases():
        findings = _inspect_as_research(source)
        wrong += [f"{label}: line {line} lacks {name}; got {findings}"
                  for line, name in expected if not _reported(findings, line, name)]
    for label, lines, expected in _SCOPED_CASES:
        findings = _inspect_as_research(_synthetic(lines))
        wrong += [f"{label}: line {line} lacks {name}; got {findings}"
                  for line, name in expected if not _reported(findings, line, name)]
    for label, lines, expected, absent in _BINDING_CASES:
        findings = _inspect_as_research(_synthetic(lines))
        wrong += [f"{label}: line {line} lacks {name}; got {findings}"
                  for line, name in expected if not _reported(findings, line, name)]
        wrong += [f"{label}: line {line} reports {name}; got {findings}"
                  for line, name in absent if _reported(findings, line, name)]
    for label, lines, common, money in _ORIGINAL_CASES:
        # research may import random (for random.Random), so only the float part of the costs/risk row
        # applies; its "from random import choice" is covered by _RESEARCH_FORBIDDEN.
        findings = _inspect_as_research(_synthetic(lines))
        wrong += [f"{label}: lacks {finding!r}; got {findings}"
                  for finding in common + tuple(item for item in money if ": forbidden float " in item)
                  if finding not in findings]
    assert not wrong, "AC-06: the research checker:\n" + "\n".join(wrong)

    # Then the package itself, which must exist with its registry module.
    source_root = Path.cwd() / "src"
    directory = source_root / "sochron" / "research"
    assert directory.is_dir(), f"AC-06: {directory} does not exist; implementation missing"
    files = sorted(directory.rglob("*.py"))
    assert files, f"AC-06: {directory} contains no Python source; implementation missing"
    registry_file = directory / "registry.py"
    assert registry_file.is_file(), f"AC-06: {registry_file} does not exist; implementation missing"
    findings = []
    for path in files:
        relative = path.relative_to(source_root)
        current_package = ".".join(relative.parent.parts)
        try:
            violations = _inspect_research_source(path.read_text(encoding="utf-8-sig"), current_package,
                                                  registry=path == registry_file)
        except SyntaxError as error:
            findings.append(f"{relative}:{error.lineno}: invalid Python syntax: {error.msg}")
            continue
        findings.extend(f"{relative}: {violation}" for violation in violations)
    assert not findings, "AC-06: forbidden dependencies or side effects in sochron.research:\n" + "\n".join(findings)


# ENV-002 AC-06 (docs/contracts/ENV-002-research-host-separation.md v1.6): sochron.research,
# sochron.backtest and sochron.strategy may not import sochron.data.acquire, sochron.broker or
# sochron.app (ENV-002 adds the research-host check in sochron.app.envcheck). Their checkers above
# already report every package they are not granted; the first test pins each import form of the
# three packages for every checker of the three packages, the second runs those checkers over the
# real sources and src/sochron/__init__.py (which runs on every import of them), and the third imports
# the three packages in a fresh interpreter and reads sys.modules. Every function, table and test
# above stays as it was.
_ENV002_BLOCKED = ("sochron.app", "sochron.broker", "sochron.data.acquire")
_ENV002_DYNAMIC = "dynamic import prevents static boundary verification"
# (label, source lines, the finding every checker must report); line 1 is _HEADER.
_ENV002_BLOCKED_IMPORTS = (
    ("import sochron.app", ("import sochron.app",), "line 2: forbidden import sochron.app"),
    ("import sochron.app.envcheck", ("import sochron.app.envcheck",), "line 2: forbidden import sochron.app.envcheck"),
    ("import sochron.app.envcheck as host", ("import sochron.app.envcheck as host",),
     "line 2: forbidden import sochron.app.envcheck"),
    ("from sochron import app", ("from sochron import app",), "line 2: forbidden import sochron.app"),
    ("from sochron.app import envcheck", ("from sochron.app import envcheck",), "line 2: forbidden import sochron.app"),
    ("from sochron.app.envcheck import require_research_host",
     ("from sochron.app.envcheck import require_research_host",), "line 2: forbidden import sochron.app.envcheck"),
    ("the gate imported in a function body",
     ("def gate():", "    from sochron.app.envcheck import require_research_host", "    return require_research_host()"),
     "line 3: forbidden import sochron.app.envcheck"),
    ("from ..app import envcheck", ("from ..app import envcheck",), "line 2: forbidden import sochron.app"),
    ("from .. import app", ("from .. import app",), "line 2: forbidden import sochron.app"),
    ("import sochron.broker", ("import sochron.broker",), "line 2: forbidden import sochron.broker"),
    ("from sochron import broker", ("from sochron import broker",), "line 2: forbidden import sochron.broker"),
    ("from sochron.broker.mt5 import connect", ("from sochron.broker.mt5 import connect",),
     "line 2: forbidden import sochron.broker.mt5"),
    ("from ..broker import mt5", ("from ..broker import mt5",), "line 2: forbidden import sochron.broker"),
    ("import sochron.data.acquire", ("import sochron.data.acquire",), "line 2: forbidden import sochron.data.acquire"),
    ("from sochron.data.acquire import fetch_m1", ("from sochron.data.acquire import fetch_m1",),
     "line 2: forbidden import sochron.data.acquire"),
    ("from sochron.data import acquire", ("from sochron.data import acquire",), "line 2: forbidden import sochron.data"),
    ("from ..data.acquire import fetch_m1", ("from ..data.acquire import fetch_m1",),
     "line 2: forbidden import sochron.data.acquire"),
    ("the gate by importlib", ("import importlib", 'GATE = importlib.import_module("sochron.app.envcheck")'),
     f"line 3: {_ENV002_DYNAMIC}"),
    ("the gate by __import__", ('GATE = __import__("sochron.app.envcheck")',), f"line 2: {_ENV002_DYNAMIC}"),
)
# (package, checker) for every checker the three packages run under.
_ENV002_CHECKERS = (
    ("sochron.strategy", _inspect_as_strategy),
    ("sochron.strategy (listed stdlib)", _inspect_as_listed_strategy),
    ("sochron.backtest", _inspect_as_backtest),
    ("sochron.backtest (no ZoneInfo)", _inspect_as_backtest_zoneinfo),
    ("sochron.research", _inspect_as_research),
    ("sochron.research registry.py", _inspect_as_registry),
)


def _env002_boundary_findings(findings):
    """The findings that name an import of app, broker, data.acquire or the data package, or a dynamic import."""
    kept = []
    for finding in findings:
        match = _IMPORT_FINDING.fullmatch(finding)
        named = match["module"] if match else ""
        if (any(_within(named, blocked) for blocked in _ENV002_BLOCKED) or named == "sochron.data"
                or finding.endswith(_ENV002_DYNAMIC)):
            kept.append(finding)
    return kept


def test_ac06_env002_checkers_report_app_broker_and_data_acquire_imports():
    wrong = []
    for label, lines, expected in _ENV002_BLOCKED_IMPORTS:
        for package, inspect in _ENV002_CHECKERS:
            findings = inspect(_synthetic(lines))
            if expected not in findings:
                wrong.append(f"{package} | {label}: {expected!r} missing; got {findings}")
    assert not wrong, "AC-06: a checker misses an import of app, broker or data.acquire:\n" + "\n".join(wrong)


def test_ac06_env002_research_backtest_strategy_sources_do_not_import_app_broker_or_data_acquire():
    source_root = Path.cwd() / "src"
    checks = []
    for package, inspect in (("strategy", _inspect_strategy_listed_source), ("backtest", _inspect_backtest_zoneinfo_source),
                             ("research", None)):
        directory = source_root / "sochron" / package
        assert directory.is_dir(), f"AC-06: {directory} does not exist; implementation missing"
        checks += [(path, inspect) for path in sorted(directory.rglob("*.py"))]
    findings = []
    for path, inspect in checks:
        relative = path.relative_to(source_root)
        current_package = ".".join(relative.parent.parts)
        source = path.read_text(encoding="utf-8-sig")
        if inspect is None:
            found = _inspect_research_source(source, current_package, registry=path.name == "registry.py")
        else:
            found = inspect(source, current_package)
        findings += [f"{relative}: {item}" for item in _env002_boundary_findings(found)]
    # src/sochron/__init__.py runs on every import of the three packages: no blocked import there either.
    top = source_root / "sochron" / "__init__.py"
    if top.is_file():
        found = _inspect_source(top.read_text(encoding="utf-8-sig"), "sochron.core", "sochron")
        findings += [f"sochron/__init__.py: {item}" for item in _env002_boundary_findings(found)
                     if not item.endswith("forbidden import sochron.data")]
    assert not findings, "AC-06: research, backtest or strategy imports app, broker or data.acquire:\n" + "\n".join(findings)


def test_ac06_env002_importing_research_backtest_strategy_loads_no_app_broker_or_data_acquire():
    import json
    import subprocess

    source_root = Path.cwd() / "src"
    assert (source_root / "sochron").is_dir(), f"AC-06: {source_root / 'sochron'} does not exist"
    code = "\n".join((
        "import json, sys",
        f"sys.path.insert(0, {str(source_root)!r})",
        "import sochron.research, sochron.backtest, sochron.strategy",
        f"blocked = {_ENV002_BLOCKED!r}",
        "print(json.dumps(sorted(name for name in sys.modules",
        "                        if any(name == item or name.startswith(item + '.') for item in blocked))))",
    ))
    done = subprocess.run([sys.executable, "-I", "-B", "-c", code], capture_output=True, text=True, timeout=120,
                          check=False)
    assert done.returncode == 0, f"AC-06: importing the three packages failed: {done.stderr}"
    loaded = json.loads(done.stdout)
    assert loaded == [], f"AC-06: importing research, backtest and strategy loaded {loaded}"


# ENV-002 AC-06: sochron.app.envcheck uses no subprocess, socket or http, writes and deletes no files,
# and uses ctypes and winreg only for the functions the contract lists. It is not a pure package (it
# reads the OS, os.environ and files), so it gets its own checker. The checker resolves names through
# every import in the module (any scope, conservatively) and through plain aliases (name = value, a
# walrus), then reports, each with its line:
#   - an import of a process, network or file-writing stdlib module (_ENVCHECK_DENIED_MODULES), of any
#     other stdlib module outside the allow list of contract v1.7 (tests-r1 F5, _ENVCHECK_STDLIB, a
#     module's submodules included), of a third-party module, or of a sochron package other than the
#     pure ones, sochron.app and the module itself; a wildcard import;
#   - (tests r2, F3) a name bound to a second checked object that differs from its first (two
#     handles, or a module and a handle, under one name): the flat alias table could not tell them
#     apart, so the form is refused on purpose and the name is not resolved further;
#   - os functions that change files or start processes (_ENVCHECK_OS_DENIED, os.exec*, os.spawn*,
#     os.posix_spawn*); os.open whose flags are not built from read-only O_ names; open, io.open,
#     codecs.open, os.fdopen, io.FileIO and Path.open with a write mode or a mode that is no literal;
#     the Path methods that write, delete, rename or create (_ENVCHECK_FILE_CHANGES, and .replace with
#     one argument);
#   - ctypes: a library loaded other than kernel32, mpr, shell32 or ole32 by name (ctypes.windll.X,
#     ctypes.oledll.X, ctypes.WinDLL("X"), ctypes.OleDLL("X")), any other loader or function-pointer
#     factory (_ENVCHECK_CTYPES_DENIED), a library function other than the contract's
#     (_ENVCHECK_WIN32), and a library, loader, ctypes, winreg, os or open that escapes the check
#     (anything but attribute access, a call where that is the use, getattr/hasattr with a literal
#     name, or a plain alias);
#   - winreg members other than the read-only ones (_ENVCHECK_WINREG), an OpenKey access mask with an
#     int literal other than 0, a registry path literal ("SOFTWARE\..." or "SYSTEM\...") other than
#     the two Uninstall keys, and (v1.7, tests-r1 F5) any str literal passed as the sub-key of
#     OpenKey/OpenKeyEx (second argument or sub_key=) that is not one of the two Uninstall keys;
#   - Windows-only access at import time (winreg, ctypes.windll/oledll/WinDLL/OleDLL or a library
#     outside a function body), which would break the import on Linux;
#   - dynamic code: __import__, importlib.import_module or reload, module_from_spec, exec_module,
#     load_module, eval, exec, compile, and getattr of a checked module with a name that is no literal.
# Like the checkers above it is an AST check, not a proof about arbitrary execution. Contract v1.6 Q12
# accepts its limits: it admits only the forms it can follow (a library opened by its literal name and
# called as <handle>.<Function>, errors read with ctypes.get_last_error()) and refuses the rest on purpose.
_ENVCHECK_DENIED_MODULES = frozenset({
    "subprocess", "socket", "http", "urllib", "ssl", "ftplib", "smtplib", "poplib", "imaplib", "nntplib", "telnetlib",
    "xmlrpc", "socketserver", "asyncio", "selectors", "select", "multiprocessing", "concurrent", "pty", "webbrowser",
    "wsgiref", "shutil", "tempfile", "zipfile", "tarfile", "gzip", "bz2", "lzma", "sqlite3", "dbm", "shelve",
    "logging", "fileinput", "mmap", "runpy", "code", "_winapi", "nt", "posix", "_posixsubprocess", "_socket", "_ssl",
    "_ctypes", "_io", "_overlapped", "_multiprocessing", "_asyncio",
})
# Contract v1.7 (tests-r1 F5): the stdlib modules envcheck may import, with their submodules (winreg only
# inside a function, by the import-time rule). Every other stdlib module is a finding.
_ENVCHECK_STDLIB = frozenset({"argparse", "collections", "ctypes", "dataclasses", "datetime", "hashlib", "importlib",
                              "json", "os", "pathlib", "re", "sys", "typing", "winreg"})
_ENVCHECK_SOCHRON = ("sochron.core", "sochron.timebase", "sochron.costs", "sochron.risk", "sochron.strategy",
                     "sochron.backtest", "sochron.research", "sochron.data.snapshot")
_ENVCHECK_WIN32 = {
    "kernel32": frozenset({"GetDriveTypeW", "CreateToolhelp32Snapshot", "Process32FirstW", "Process32NextW",
                           "CloseHandle"}),
    "mpr": frozenset({"WNetOpenEnumW", "WNetEnumResourceW", "WNetCloseEnum"}),
    "shell32": frozenset({"SHGetKnownFolderPath"}),
    "ole32": frozenset({"CoTaskMemFree"}),
}
_ENVCHECK_CTYPES_DENIED = frozenset({"CDLL", "cdll", "PyDLL", "pydll", "pythonapi", "LibraryLoader", "CFUNCTYPE",
                                     "WINFUNCTYPE", "PYFUNCTYPE", "util", "macholib", "_dlopen"})
_ENVCHECK_WINREG = frozenset({
    "HKEY_LOCAL_MACHINE", "HKEY_CURRENT_USER", "KEY_READ", "KEY_QUERY_VALUE", "KEY_ENUMERATE_SUB_KEYS",
    "KEY_WOW64_32KEY", "KEY_WOW64_64KEY", "OpenKey", "OpenKeyEx", "EnumKey", "EnumValue", "QueryValue",
    "QueryValueEx", "QueryInfoKey", "CloseKey", "HKEYType", "error", "REG_SZ", "REG_EXPAND_SZ",
})
_ENVCHECK_UNINSTALL = ("software\\microsoft\\windows\\currentversion\\uninstall",
                       "software\\wow6432node\\microsoft\\windows\\currentversion\\uninstall")
_ENVCHECK_OS_DENIED = frozenset({
    "system", "popen", "startfile", "fork", "forkpty", "kill", "killpg", "remove", "unlink", "rmdir", "removedirs",
    "rename", "renames", "replace", "mkdir", "makedirs", "truncate", "ftruncate", "chmod", "lchmod", "fchmod",
    "chown", "lchown", "fchown", "link", "symlink", "utime", "mkfifo", "mknod", "write", "writev", "pwrite",
    "pwritev", "sendfile",
})
_ENVCHECK_OS_FAMILIES = ("exec", "spawn", "posix_spawn")
_ENVCHECK_READ_FLAGS = frozenset({"O_RDONLY", "O_BINARY", "O_NOINHERIT", "O_CLOEXEC", "O_SEQUENTIAL", "O_RANDOM",
                                  "O_NOFOLLOW", "O_NONBLOCK", "O_NOATIME", "O_DIRECTORY", "O_NOCTTY"})
_ENVCHECK_FILE_CHANGES = frozenset({"write_text", "write_bytes", "unlink", "rmdir", "rename", "touch", "mkdir",
                                    "chmod", "lchmod", "symlink_to", "hardlink_to", "link_to", "truncate"})
_ENVCHECK_OPEN_MODE_SECOND = frozenset({"builtins.open", "io.open", "codecs.open", "os.fdopen", "io.FileIO",
                                        "pathlib.Path.open"})
_ENVCHECK_DYNAMIC = frozenset({"builtins.__import__", "importlib.import_module", "importlib.reload",
                               "importlib.__import__", "importlib.util.module_from_spec", "builtins.eval",
                               "builtins.exec", "builtins.compile"})
_ENVCHECK_BUILTINS = frozenset({"open", "__import__", "eval", "exec", "compile", "getattr", "hasattr"})
# Resolved names that may only be reached as an attribute receiver, a plain alias or getattr/hasattr
# with a literal name (modules, loaders, libraries), or only be called (the rest).
_ENVCHECK_HELD = frozenset({"ctypes", "winreg", "os", "ctypes.windll", "ctypes.oledll"})
_ENVCHECK_CALLED = frozenset({"ctypes.WinDLL", "ctypes.OleDLL"}) | _ENVCHECK_OPEN_MODE_SECOND | _ENVCHECK_DYNAMIC
_ENVCHECK_TRACKED = ("ctypes", "winreg", "os", "io", "codecs", "builtins", "importlib", "pathlib", "dll:")
_ENVCHECK_IMPORT_TIME = "Windows-only access at import time"


def _envcheck_library(name):
    """'dll:<name>' for a library the contract lists (any case, an optional .dll and directory), else None."""
    base = name.replace("/", "\\").rsplit("\\", 1)[-1].lower()
    base = base[:-4] if base.endswith(".dll") else base
    return f"dll:{base}" if base in _ENVCHECK_WIN32 else None


def _envcheck_literal(node):
    return isinstance(node, ast.Constant) and type(node.value) is str


def _envcheck_member(parent, attribute):
    """The resolved name of parent.attribute, a library for ctypes.windll.X and ctypes.oledll.X."""
    if parent in ("ctypes.windll", "ctypes.oledll"):
        return _envcheck_library(attribute) or f"{parent}.{attribute}"
    return f"{parent}.{attribute}"


def _envcheck_resolve(node, bindings):
    """The resolved name of a Name, Attribute or Call node, or None."""
    if isinstance(node, ast.Name):
        if node.id in bindings:
            return bindings[node.id]
        return f"builtins.{node.id}" if node.id in _ENVCHECK_BUILTINS else None
    if isinstance(node, ast.Attribute):
        parent = _envcheck_resolve(node.value, bindings)
        return None if parent is None else _envcheck_member(parent, node.attr)
    if isinstance(node, ast.Call):
        called = _envcheck_resolve(node.func, bindings)
        if called in ("ctypes.WinDLL", "ctypes.OleDLL") and node.args and _envcheck_literal(node.args[0]):
            return _envcheck_library(node.args[0].value)
        if called in ("builtins.getattr", "builtins.hasattr") and len(node.args) >= 2 and _envcheck_literal(node.args[1]):
            target = _envcheck_resolve(node.args[0], bindings)
            if called == "builtins.getattr" and target is not None:
                return _envcheck_member(target, node.args[1].value)
    return None


def _envcheck_bindings(tree, current_package):
    """(bindings, conflicts): every name bound by an import (any scope) or by a plain alias of a tracked
    name, to a fixed point, and (line, name) for each name that a second binding gives another checked
    object (tests r2, F3). A name in conflict resolves to nothing afterwards."""
    bindings, conflicts, conflicted = {}, [], set()

    def bind(name, value, line):
        old = bindings.get(name, value)
        if name in conflicted or old == value:
            bindings.setdefault(name, value)
            return False
        if value.startswith(_ENVCHECK_TRACKED) or (old or "").startswith(_ENVCHECK_TRACKED):
            conflicted.add(name)
            conflicts.append((line, name))
        return False

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.asname:
                    bind(alias.asname, alias.name, node.lineno)
                else:
                    bind(alias.name.split(".")[0], alias.name.split(".")[0], node.lineno)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if node.level:
                try:
                    module = resolve_name("." * node.level + module, current_package)
                except ImportError:
                    continue
            for alias in node.names:
                if alias.name != "*":
                    bind(alias.asname or alias.name, f"{module}.{alias.name}", node.lineno)
    for _ in range(20):
        changed = False
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and all(isinstance(target, ast.Name) for target in node.targets):
                targets, value = [target.id for target in node.targets], node.value
            elif isinstance(node, (ast.AnnAssign, ast.NamedExpr)) and isinstance(node.target, ast.Name) and node.value:
                targets, value = [node.target.id], node.value
            else:
                continue
            resolved = _envcheck_resolve(value, bindings)
            if resolved and resolved.startswith(_ENVCHECK_TRACKED):
                for name in targets:
                    if name not in bindings and name not in conflicted:
                        bindings[name] = resolved
                        changed = True
                    else:
                        bind(name, resolved, node.lineno)
        if not changed:
            break
    for name in conflicted:
        bindings[name] = None
    return bindings, sorted(set(conflicts))


def _envcheck_runtime(tree):
    """The nodes inside a function or lambda body: they run when called, not when the module is imported."""
    runtime = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for statement in node.body:
                runtime.update(ast.walk(statement))
        elif isinstance(node, ast.Lambda):
            runtime.update(ast.walk(node.body))
    return runtime


def _envcheck_windows_only(resolved):
    return (resolved.startswith(("winreg", "dll:", "ctypes.windll", "ctypes.oledll"))
            or resolved in ("ctypes.WinDLL", "ctypes.OleDLL"))


def _envcheck_member_findings(resolved):
    """The rule a resolved name breaks by itself, or None."""
    if resolved.startswith("dll:"):
        library, _, rest = resolved[4:].partition(".")
        function = rest.split(".")[0]
        if function and function not in _ENVCHECK_WIN32[library]:
            return f"forbidden Win32 function {library}.{function}"
        return None
    parts = resolved.split(".")
    if parts[0] == "ctypes" and len(parts) > 2 and parts[1] in ("windll", "oledll"):
        return f"forbidden Win32 library {'.'.join(parts[:3])}"
    if parts[0] == "ctypes" and len(parts) > 1 and parts[1] in _ENVCHECK_CTYPES_DENIED:
        return f"forbidden ctypes use ctypes.{parts[1]}"
    if parts[0] == "winreg" and len(parts) > 1 and parts[1] not in _ENVCHECK_WINREG:
        return f"forbidden winreg use winreg.{parts[1]}"
    if parts[0] == "os" and len(parts) > 1 and (parts[1] in _ENVCHECK_OS_DENIED
                                                or parts[1].startswith(_ENVCHECK_OS_FAMILIES)):
        return f"forbidden file change or process os.{parts[1]}"
    return None


def _envcheck_escapes(node, resolved, parents):
    """Whether a held or call-only name is used in any way other than the ones the checker can follow."""
    held = resolved in _ENVCHECK_HELD or (resolved.startswith("dll:") and "." not in resolved)
    if not held and resolved not in _ENVCHECK_CALLED:
        return False
    parent = parents.get(node)
    if isinstance(parent, ast.Call) and parent.func is node:
        return held
    if not held:
        return True
    if isinstance(parent, ast.Attribute) and parent.value is node:
        return False
    if isinstance(parent, (ast.Assign, ast.AnnAssign, ast.NamedExpr)) and parent.value is node:
        targets = parent.targets if isinstance(parent, ast.Assign) else [parent.target]
        return not all(isinstance(target, ast.Name) for target in targets)
    if (isinstance(parent, ast.Call) and isinstance(parent.func, ast.Name) and parent.func.id in ("getattr", "hasattr")
            and parent.args and parent.args[0] is node):
        return False
    return True


def _envcheck_mode(node, position):
    """The mode argument of an open call: None when absent, else the node."""
    if len(node.args) > position:
        return node.args[position]
    return next((keyword.value for keyword in node.keywords if keyword.arg == "mode"), None)


def _envcheck_read_flags(node, bindings):
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
        return _envcheck_read_flags(node.left, bindings) and _envcheck_read_flags(node.right, bindings)
    if isinstance(node, ast.Constant) and type(node.value) is int:
        return node.value == 0
    if (isinstance(node, ast.Call) and _envcheck_resolve(node.func, bindings) == "builtins.getattr" and len(node.args) == 3
            and _envcheck_resolve(node.args[0], bindings) == "os" and _envcheck_literal(node.args[1])
            and isinstance(node.args[2], ast.Constant) and node.args[2].value == 0):
        return node.args[1].value in _ENVCHECK_READ_FLAGS
    resolved = _envcheck_resolve(node, bindings) or ""
    return resolved.startswith("os.") and resolved[3:] in _ENVCHECK_READ_FLAGS


def _envcheck_import_findings(node, current_package, runtime):
    findings = []
    if isinstance(node, ast.Import):
        modules = [alias.name for alias in node.names]
        members = []
    else:
        module = node.module or ""
        if node.level:
            try:
                module = resolve_name("." * node.level + module, current_package)
            except ImportError:
                return ["relative import escapes its package"]
        if any(alias.name == "*" for alias in node.names):
            findings.append("wildcard import prevents static verification")
        members = [f"{module}.{alias.name}" for alias in node.names if alias.name != "*"]
        modules = members if module in ("sochron", "sochron.app") else [module]
    for name in modules:
        top = name.split(".")[0]
        if top in sys.stdlib_module_names:
            if top in _ENVCHECK_DENIED_MODULES:
                findings.append(f"forbidden import {name}")
            elif top not in _ENVCHECK_STDLIB:
                findings.append(f"forbidden stdlib import {name}")
            elif top == "winreg" and node not in runtime:
                findings.append(_ENVCHECK_IMPORT_TIME)
        elif top == "sochron":
            allowed = name in ("sochron", "sochron.app", "sochron.app.envcheck") or any(
                _within(name, package) for package in _ENVCHECK_SOCHRON)
            if not allowed:
                findings.append(f"forbidden import {name}")
        else:
            findings.append(f"forbidden import {name}")
    for member in members:
        broken = _envcheck_member_findings(member)
        if broken:
            findings.append(broken)
        if _envcheck_windows_only(_envcheck_member(*member.rsplit(".", 1))) and node not in runtime:
            findings.append(_ENVCHECK_IMPORT_TIME)
    return findings


def _inspect_envcheck_source(source, current_package="sochron.app"):
    """ENV-002 AC-06: the findings of the envcheck checker described above, sorted and unique."""
    tree = ast.parse(source)
    bindings, conflicts = _envcheck_bindings(tree, current_package)
    parents = {child: node for node in ast.walk(tree) for child in ast.iter_child_nodes(node)}
    runtime = _envcheck_runtime(tree)
    findings = {f"line {line}: {name} is bound to more than one checked object" for line, name in conflicts}

    def report(node, message):
        findings.add(f"line {node.lineno}: {message}")

    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            for message in _envcheck_import_findings(node, current_package, runtime):
                report(node, message)
            continue
        if isinstance(node, ast.Constant) and type(node.value) is str:
            key = node.value.replace("/", "\\").lower()
            if key.startswith(("software\\", "system\\")) and key.rstrip("\\") not in _ENVCHECK_UNINSTALL:
                report(node, f"forbidden registry key {node.value}")
            continue
        if isinstance(node, ast.Name) and not isinstance(node.ctx, ast.Load):
            continue
        if not isinstance(node, (ast.Name, ast.Attribute, ast.Call)):
            continue
        resolved = _envcheck_resolve(node, bindings)
        if isinstance(node, ast.Call):
            _envcheck_call(node, resolved, bindings, report)
        if not resolved:
            continue
        broken = _envcheck_member_findings(resolved)
        if broken:
            report(node, broken)
        if _envcheck_escapes(node, resolved, parents):
            report(node, f"{resolved} escapes the static check")
        if _envcheck_windows_only(resolved) and node not in runtime:
            report(node, _ENVCHECK_IMPORT_TIME)
    return sorted(findings)


def _envcheck_call(node, resolved, bindings, report):
    """The rules on a call: open modes, os.open flags, library names, file-changing methods, dynamic code."""
    called = _envcheck_resolve(node.func, bindings)
    func = node.func
    if called in ("ctypes.WinDLL", "ctypes.OleDLL") and resolved is None:
        name = node.args[0].value if node.args and _envcheck_literal(node.args[0]) else "that is no literal"
        report(node, f"forbidden Win32 library {called}({name!r})")
    mode = None
    if called in _ENVCHECK_OPEN_MODE_SECOND:
        mode = _envcheck_mode(node, 1)
    elif isinstance(func, ast.Attribute) and func.attr == "open" and called != "os.open":
        mode = _envcheck_mode(node, 0)  # path.open(mode) on any receiver the checker does not resolve as above
    if mode is not None:
        if not _envcheck_literal(mode):
            report(node, "forbidden open with a mode that is no literal")
        elif set(mode.value) & set("wax+"):
            report(node, f"forbidden write open mode {mode.value!r}")
    if called == "os.open":
        flags = node.args[1] if len(node.args) > 1 else next(
            (keyword.value for keyword in node.keywords if keyword.arg == "flags"), None)
        if flags is None or not _envcheck_read_flags(flags, bindings):
            report(node, "forbidden os.open flags")
    if called in ("winreg.OpenKey", "winreg.OpenKeyEx"):
        access = node.args[3] if len(node.args) > 3 else next(
            (keyword.value for keyword in node.keywords if keyword.arg == "access"), None)
        if access is not None and any(isinstance(item, ast.Constant) and type(item.value) is int and item.value != 0
                                      for item in ast.walk(access)):
            report(node, "forbidden winreg access mask")
        # v1.7 (tests-r1 F5): a literal sub-key must be one of the two Uninstall keys.
        sub_key = node.args[1] if len(node.args) > 1 else next(
            (keyword.value for keyword in node.keywords if keyword.arg == "sub_key"), None)
        if (_envcheck_literal(sub_key)
                and sub_key.value.replace("/", "\\").lower().rstrip("\\") not in _ENVCHECK_UNINSTALL):
            report(node, f"forbidden registry key {sub_key.value}")
    if isinstance(func, ast.Attribute):
        if func.attr in _ENVCHECK_FILE_CHANGES or (func.attr == "replace" and len(node.args) == 1 and not node.keywords):
            report(node, f"forbidden file change .{func.attr}")
        if func.attr in ("exec_module", "load_module"):
            report(node, "dynamic code prevents static verification")
    if called in _ENVCHECK_DYNAMIC:
        report(node, "dynamic code prevents static verification")
    if called in ("builtins.getattr", "builtins.hasattr") and node.args:
        target = _envcheck_resolve(node.args[0], bindings)
        if target and target.startswith(_ENVCHECK_TRACKED) and (len(node.args) < 2 or not _envcheck_literal(node.args[1])):
            report(node, f"dynamic attribute of {target} prevents static verification")
        elif target and target.startswith(_ENVCHECK_TRACKED):
            broken = _envcheck_member_findings(_envcheck_member(target, node.args[1].value))
            if broken:
                report(node, broken)


# (label, source lines) that the envcheck checker must accept; line 1 is _HEADER.
_ENVCHECK_ALLOWED = (
    ("an envcheck as the contract describes it", (
        "import argparse",
        "import ctypes",
        "import hashlib",
        "import importlib.util",
        "import json",
        "import os",
        "import sys",
        "from ctypes import wintypes",
        "from dataclasses import dataclass",
        "from datetime import UTC, datetime",
        "from pathlib import Path",
        "from sochron.research import HOLDOUT_CUTOFF_UTC",
        r"UNINSTALL = r'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall'",
        r"WOW_UNINSTALL = 'SOFTWARE\\WOW6432Node\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\'",
        "RECALL = 0x00400000 | 0x00040000",
        "class PROCESSENTRY32W(ctypes.Structure):",
        "    _fields_ = [('dwSize', wintypes.DWORD), ('szExeFile', ctypes.c_wchar * 260)]",
        "@dataclass(frozen=True)",
        "class Item:",
        "    name: str",
        "    status: str",
        "    detail: str",
        "def is_cloud_only(path):",
        "    return bool(getattr(os.stat(path), 'st_file_attributes', 0) & RECALL)",
        "def _drives():",
        "    kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)",
        "    kernel32.GetDriveTypeW.argtypes = (wintypes.LPCWSTR,)",
        "    kernel32.GetDriveTypeW.restype = wintypes.UINT",
        "    drives = getattr(os, 'listdrives', None)",
        "    if not hasattr(os, 'listdrives'):",
        "        raise ctypes.WinError(ctypes.get_last_error())",
        "    return [d for d in drives() if kernel32.GetDriveTypeW(d) == 4]",
        "def _resources():",
        "    mpr = ctypes.WinDLL('mpr.dll', use_last_error=True)",
        "    handle = wintypes.HANDLE()",
        "    if mpr.WNetOpenEnumW(1, 0, 0, None, ctypes.byref(handle)):",
        "        return None",
        "    buffer = ctypes.create_string_buffer(16384)",
        "    try:",
        "        return mpr.WNetEnumResourceW(handle, ctypes.byref(wintypes.DWORD(-1)), buffer, None)",
        "    finally:",
        "        mpr.WNetCloseEnum(handle)",
        "def _processes():",
        "    k = ctypes.windll.kernel32",
        "    snapshot = k.CreateToolhelp32Snapshot(2, 0)",
        "    entry = PROCESSENTRY32W()",
        "    entry.dwSize = ctypes.sizeof(entry)",
        "    names = []",
        "    ok = k.Process32FirstW(snapshot, ctypes.byref(entry))",
        "    while ok:",
        "        names.append(entry.szExeFile)",
        "        ok = k.Process32NextW(snapshot, ctypes.byref(entry))",
        "    k.CloseHandle(snapshot)",
        "    return names",
        "def _known_folder(guid):",
        "    shell32 = ctypes.oledll.shell32",
        "    path = ctypes.c_wchar_p()",
        "    shell32.SHGetKnownFolderPath(ctypes.byref(guid), 0, None, ctypes.byref(path))",
        "    try:",
        "        return path.value",
        "    finally:",
        "        ctypes.windll.ole32.CoTaskMemFree(path)",
        "def _uninstall_names():",
        "    import winreg",
        "    names = []",
        "    for root in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):",
        "        for sub, flag in ((UNINSTALL, winreg.KEY_WOW64_64KEY), (WOW_UNINSTALL, 0)):",
        "            with winreg.OpenKey(root, sub, 0, winreg.KEY_READ | flag) as key:",
        "                for index in range(winreg.QueryInfoKey(key)[0]):",
        "                    with winreg.OpenKeyEx(key, winreg.EnumKey(key, index)) as child:",
        "                        names.append(winreg.QueryValueEx(child, 'DisplayName')[0])",
        "    return names",
        "def collect(roots):",
        "    spec = importlib.util.find_spec('MetaTrader5')",
        "    appdata = os.environ.get('APPDATA')",
        "    return (spec is not None, appdata, _drives(), _resources(), _processes(), _uninstall_names())",
        "def _manifest(path):",
        "    with open(path, 'rb') as handle:",
        "        return json.loads(handle.read())",
        "def _digest(path):",
        "    with path.open('rb') as handle:",
        "        return hashlib.file_digest(handle, 'sha256').hexdigest()",
        "def _text(path):",
        "    return Path(path).read_bytes(), Path(path).read_text(encoding='utf-8'), open(path, encoding='utf-8')",
        "def _raw(path):",
        "    fd = os.open(path, os.O_RDONLY | getattr(os, 'O_BINARY', 0))",
        "    return os.read(fd, 10), os.close(fd)",
        "def _walk(root):",
        "    for folder, dirs, files in os.walk(root):",
        "        dirs[:] = [d for d in dirs if d.lower() != 'metaquotes']",
        r"        yield folder, [name.replace('/', '\\') for name in files], os.path.join(folder, 'x')",
        "    for entry in os.scandir(root):",
        "        yield entry.stat().st_size, entry.name",
        "def main(argv=None):",
        "    parser = argparse.ArgumentParser(prog='envcheck')",
        "    parser.add_argument('--role', required=True)",
        "    args = parser.parse_args(argv)",
        "    print('RESEARCH HOST: PASS', datetime.now(UTC).isoformat(), HOLDOUT_CUTOFF_UTC, args.role)",
        r"    sys.stdout.write('done\n')",
        "    return 0",
        "if __name__ == '__main__':",
        "    raise SystemExit(main())",
    )),
    ("the package __init__ re-exports the gate", ("from .envcheck import require_research_host",
                                                  "from . import envcheck")),
    ("a walrus and an annotated alias of a library", (
        "import ctypes",
        "def drive_type(letter):",
        "    if (k := ctypes.WinDLL('KERNEL32.DLL')) is None:",
        "        return None",
        "    fn: object = k.GetDriveTypeW",
        "    return fn(letter)",
    )),
    # Tests r2 (F3, F5): the allow list with submodules, one library bound twice under the same name, and
    # literal Uninstall sub-keys.
    ("allowed stdlib modules and their submodules", (
        "import collections",
        "import ctypes.wintypes",
        "import os.path",
        "import re",
        "import typing",
        "from collections.abc import Mapping",
        "from importlib import util",
        "from json import JSONDecodeError",
        "from typing import Literal",
        "PATTERN = re.compile(r'[0-9a-f]{32}')",
    )),
    ("the same library under the same name in two functions", (
        "import ctypes",
        "def drive_type(letter):",
        "    kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)",
        "    return kernel32.GetDriveTypeW(letter)",
        "def close(handle):",
        "    kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)",
        "    return kernel32.CloseHandle(handle)",
    )),
    ("literal Uninstall sub-keys", (
        "def names():",
        "    import winreg",
        r"    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall') as key:",
        "        return winreg.QueryInfoKey(key)",
        "def wow_names():",
        "    import winreg",
        r"    return winreg.OpenKeyEx(winreg.HKEY_LOCAL_MACHINE, sub_key='Software\\WOW6432Node\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\')",
    )),
)
_ENVCHECK_OS = "forbidden file change or process os."
# (label, source lines, exact findings); line 1 is _HEADER, so the first source line is 2.
_ENVCHECK_FORBIDDEN = (
    ("subprocess", ("import subprocess",), ("line 2: forbidden import subprocess",)),
    ("socket", ("import socket",), ("line 2: forbidden import socket",)),
    ("http.client", ("import http.client",), ("line 2: forbidden import http.client",)),
    ("urllib.request", ("from urllib.request import urlopen",), ("line 2: forbidden import urllib.request",)),
    ("shutil", ("import shutil",), ("line 2: forbidden import shutil",)),
    ("tempfile", ("import tempfile",), ("line 2: forbidden import tempfile",)),
    ("asyncio", ("import asyncio",), ("line 2: forbidden import asyncio",)),
    ("_winapi", ("import _winapi",), ("line 2: forbidden import _winapi",)),
    ("nt", ("import nt",), ("line 2: forbidden import nt",)),
    ("MetaTrader5", ("import MetaTrader5",), ("line 2: forbidden import MetaTrader5",)),
    ("a third-party package", ("import psutil",), ("line 2: forbidden import psutil",)),
    ("broker", ("from sochron.broker import mt5",), ("line 2: forbidden import sochron.broker",)),
    ("data.acquire", ("import sochron.data.acquire",), ("line 2: forbidden import sochron.data.acquire",)),
    ("a sibling module of app", ("from . import loader",), ("line 2: forbidden import sochron.app.loader",)),
    ("wildcard", ("from os import *",), ("line 2: wildcard import prevents static verification",)),
    ("os.system", ("import os", "def run():", "    os.system('net use')"), (f"line 4: {_ENVCHECK_OS}system",)),
    ("os.remove", ("import os", "def drop(path):", "    os.remove(path)"), (f"line 4: {_ENVCHECK_OS}remove",)),
    ("os.unlink", ("import os", "def drop(path):", "    os.unlink(path)"),
     ("line 4: forbidden file change .unlink", f"line 4: {_ENVCHECK_OS}unlink")),
    ("os.rename", ("import os", "def move(a, b):", "    os.rename(a, b)"),
     ("line 4: forbidden file change .rename", f"line 4: {_ENVCHECK_OS}rename")),
    ("os.replace", ("import os", "def move(a, b):", "    os.replace(a, b)"), (f"line 4: {_ENVCHECK_OS}replace",)),
    ("os.makedirs", ("import os", "def make(path):", "    os.makedirs(path)"), (f"line 4: {_ENVCHECK_OS}makedirs",)),
    ("os.startfile", ("import os", "def launch(path):", "    os.startfile(path)"), (f"line 4: {_ENVCHECK_OS}startfile",)),
    ("os.execv", ("import os", "def launch(path):", "    os.execv(path, [path])"), (f"line 4: {_ENVCHECK_OS}execv",)),
    ("os.spawnl", ("import os", "def launch(path):", "    os.spawnl(os.P_WAIT, path)"), (f"line 4: {_ENVCHECK_OS}spawnl",)),
    ("os.posix_spawn", ("import os", "def launch(path):", "    os.posix_spawn(path, [path], {})"),
     (f"line 4: {_ENVCHECK_OS}posix_spawn",)),
    ("os.write", ("import os", "def put(fd):", "    os.write(fd, b'x')"), (f"line 4: {_ENVCHECK_OS}write",)),
    ("from os import remove", ("from os import remove",), (f"line 2: {_ENVCHECK_OS}remove",)),
    ("os.open for writing", ("import os", "def put(path):", "    return os.open(path, os.O_WRONLY | os.O_CREAT)"),
     ("line 4: forbidden os.open flags",)),
    ("os.open with a variable", ("import os", "def put(path, flags):", "    return os.open(path, flags)"),
     ("line 4: forbidden os.open flags",)),
    ("open for writing", ("def put(path):", "    return open(path, 'w')"), ("line 3: forbidden write open mode 'w'",)),
    ("open for appending", ("def put(path):", "    return open(path, mode='ab')"),
     ("line 3: forbidden write open mode 'ab'",)),
    ("open read-write", ("def put(path):", "    return open(path, 'r+b')"), ("line 3: forbidden write open mode 'r+b'",)),
    ("open exclusive", ("def put(path):", "    return open(path, 'x')"), ("line 3: forbidden write open mode 'x'",)),
    ("open with a variable mode", ("def put(path, mode):", "    return open(path, mode)"),
     ("line 3: forbidden open with a mode that is no literal",)),
    # Tests r2 (F5, v1.7): io and codecs are outside the stdlib allow list, so their import is a finding too.
    ("io.open for writing", ("import io", "def put(path):", "    return io.open(path, 'w')"),
     ("line 2: forbidden stdlib import io", "line 4: forbidden write open mode 'w'")),
    ("codecs.open for writing", ("import codecs", "def put(path):", "    return codecs.open(path, 'w', 'utf-8')"),
     ("line 2: forbidden stdlib import codecs", "line 4: forbidden write open mode 'w'")),
    ("Path.open for writing", ("from pathlib import Path", "def put(path):", "    return Path(path).open('w')"),
     ("line 4: forbidden write open mode 'w'",)),
    ("Path.open through the class", ("from pathlib import Path", "def put(path):", "    return Path.open(path, 'a')"),
     ("line 4: forbidden write open mode 'a'",)),
    ("open through another name", ("OPEN = open", "def put(path):", "    return OPEN(path, 'w')"),
     ("line 2: builtins.open escapes the static check", "line 4: forbidden write open mode 'w'")),
    ("write_text", ("def put(path):", "    path.write_text('x')"), ("line 3: forbidden file change .write_text",)),
    ("write_bytes", ("def put(path):", "    path.write_bytes(b'x')"), ("line 3: forbidden file change .write_bytes",)),
    ("unlink", ("def drop(path):", "    path.unlink(missing_ok=True)"), ("line 3: forbidden file change .unlink",)),
    ("rmdir", ("def drop(path):", "    path.rmdir()"), ("line 3: forbidden file change .rmdir",)),
    ("rename", ("def move(path, other):", "    path.rename(other)"), ("line 3: forbidden file change .rename",)),
    ("Path.replace", ("def move(path, other):", "    path.replace(other)"), ("line 3: forbidden file change .replace",)),
    ("touch", ("def make(path):", "    path.touch()"), ("line 3: forbidden file change .touch",)),
    ("mkdir", ("def make(path):", "    path.mkdir(parents=True)"), ("line 3: forbidden file change .mkdir",)),
    ("chmod", ("def lock(path):", "    path.chmod(0o444)"), ("line 3: forbidden file change .chmod",)),
    ("truncate", ("def cut(handle):", "    handle.truncate(0)"), ("line 3: forbidden file change .truncate",)),
    ("advapi32 through WinDLL", ("import ctypes", "def creds():", "    return ctypes.WinDLL('advapi32').CredEnumerateW"),
     ("line 4: forbidden Win32 library ctypes.WinDLL('advapi32')",)),
    ("advapi32 through windll", ("import ctypes", "def creds():", "    return ctypes.windll.advapi32.CredReadW"),
     ("line 4: forbidden Win32 library ctypes.windll.advapi32",)),
    ("a library name that is no literal", ("import ctypes", "def load(name):", "    return ctypes.WinDLL(name)"),
     ("line 4: forbidden Win32 library ctypes.WinDLL('that is no literal')",)),
    ("kernel32 DeleteFileW", ("import ctypes", "def drop(path):", "    ctypes.windll.kernel32.DeleteFileW(path)"),
     ("line 4: forbidden Win32 function kernel32.DeleteFileW",)),
    ("kernel32 CreateFileW through an alias", ("import ctypes", "def make(path):", "    k = ctypes.WinDLL('kernel32')",
                                               "    return k.CreateFileW(path, 0x40000000, 0, None, 2, 0, None)"),
     ("line 5: forbidden Win32 function kernel32.CreateFileW",)),
    ("kernel32 GetLastError (ctypes.get_last_error is the listed way)",
     ("import ctypes", "def last():", "    return ctypes.windll.kernel32.GetLastError()"),
     ("line 4: forbidden Win32 function kernel32.GetLastError",)),
    ("shell32 ShellExecuteW", ("import ctypes", "def launch(path):",
                               "    ctypes.windll.shell32.ShellExecuteW(None, 'open', path, None, None, 1)"),
     ("line 4: forbidden Win32 function shell32.ShellExecuteW",)),
    ("LoadLibrary", ("import ctypes", "def load():", "    return ctypes.windll.LoadLibrary('ws2_32')"),
     ("line 4: forbidden Win32 library ctypes.windll.LoadLibrary",)),
    ("CDLL", ("import ctypes", "def load():", "    return ctypes.CDLL('libc.so.6')"),
     ("line 4: forbidden ctypes use ctypes.CDLL",)),
    ("cdll", ("import ctypes", "def load():", "    return ctypes.cdll.msvcrt"), ("line 4: forbidden ctypes use ctypes.cdll",)),
    ("WINFUNCTYPE", ("import ctypes", "PROTOTYPE = ctypes.WINFUNCTYPE(ctypes.c_int)"),
     ("line 3: forbidden ctypes use ctypes.WINFUNCTYPE",)),
    ("ctypes.util", ("import ctypes.util", "def find():", "    return ctypes.util.find_library('c')"),
     ("line 4: forbidden ctypes use ctypes.util",)),
    ("from ctypes import CDLL", ("from ctypes import CDLL",), ("line 2: forbidden ctypes use ctypes.CDLL",)),
    ("a library passed as an argument", ("import ctypes", "def load(call):", "    return call(ctypes.WinDLL('kernel32'))"),
     ("line 4: dll:kernel32 escapes the static check",)),
    ("a library returned", ("import ctypes", "def kernel():", "    return ctypes.windll.kernel32"),
     ("line 4: dll:kernel32 escapes the static check",)),
    ("ctypes passed on", ("import ctypes", "def load(make):", "    return make(ctypes)"),
     ("line 4: ctypes escapes the static check",)),
    ("getattr of a library with a variable name", ("import ctypes", "def call(name):", "    k = ctypes.windll.kernel32",
                                                   "    return getattr(k, name)()"),
     ("line 5: dynamic attribute of dll:kernel32 prevents static verification",)),
    ("getattr of a library with a literal name", ("import ctypes", "def drop(path):", "    k = ctypes.windll.kernel32",
                                                  "    return getattr(k, 'DeleteFileW')(path)"),
     ("line 5: forbidden Win32 function kernel32.DeleteFileW",)),
    ("windll at import time", ("import ctypes", "KERNEL32 = ctypes.windll.kernel32"),
     (f"line 3: {_ENVCHECK_IMPORT_TIME}",)),
    ("from ctypes import windll at import time", ("from ctypes import windll",), (f"line 2: {_ENVCHECK_IMPORT_TIME}",)),
    ("winreg at import time", ("import winreg",), (f"line 2: {_ENVCHECK_IMPORT_TIME}",)),
    ("winreg SetValueEx", ("def put():", "    import winreg", "    winreg.SetValueEx(None, 'x', 0, 1, 'y')"),
     ("line 4: forbidden winreg use winreg.SetValueEx",)),
    ("winreg CreateKey", ("def put():", "    import winreg", "    return winreg.CreateKey(winreg.HKEY_CURRENT_USER, 'x')"),
     ("line 4: forbidden winreg use winreg.CreateKey",)),
    ("winreg DeleteKey", ("def drop():", "    import winreg", "    winreg.DeleteKey(winreg.HKEY_CURRENT_USER, 'x')"),
     ("line 4: forbidden winreg use winreg.DeleteKey",)),
    ("winreg ConnectRegistry", ("def remote():", "    import winreg",
                                r"    return winreg.ConnectRegistry(r'\\vps', winreg.HKEY_LOCAL_MACHINE)"),
     ("line 4: forbidden winreg use winreg.ConnectRegistry",)),
    ("winreg HKEY_USERS", ("def read():", "    import winreg", "    return winreg.HKEY_USERS"),
     ("line 4: forbidden winreg use winreg.HKEY_USERS",)),
    ("winreg KEY_WRITE", ("def read(root, sub):", "    import winreg",
                          "    return winreg.OpenKey(root, sub, 0, winreg.KEY_WRITE)"),
     ("line 4: forbidden winreg use winreg.KEY_WRITE",)),
    ("winreg a numeric access mask", ("def read(root, sub):", "    import winreg",
                                      "    return winreg.OpenKey(root, sub, 0, 0x20006)"),
     ("line 4: forbidden winreg access mask",)),
    ("from winreg import SetValue", ("def put():", "    from winreg import SetValue", "    return SetValue"),
     ("line 3: forbidden winreg use winreg.SetValue", "line 4: forbidden winreg use winreg.SetValue")),
    ("winreg passed on", ("def read(call):", "    import winreg", "    return call(winreg)"),
     ("line 4: winreg escapes the static check",)),
    ("a registry path other than Uninstall",
     (r"SHELL = r'Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders'",),
     (r"line 2: forbidden registry key Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders",)),
    ("a SYSTEM registry path", (r"PORTS = r'SYSTEM\CurrentControlSet\Services\Tcpip'",),
     (r"line 2: forbidden registry key SYSTEM\CurrentControlSet\Services\Tcpip",)),
    ("__import__", ("def load():", "    return __import__('subprocess')"),
     ("line 3: dynamic code prevents static verification",)),
    ("importlib.import_module", ("import importlib", "def load():", "    return importlib.import_module('socket')"),
     ("line 4: dynamic code prevents static verification",)),
    ("exec_module", ("import importlib.util", "def load(spec):",
                     "    spec.loader.exec_module(importlib.util.module_from_spec(spec))"),
     ("line 4: dynamic code prevents static verification",)),
    ("eval", ("def run(text):", "    return eval(text)"), ("line 3: dynamic code prevents static verification",)),
    ("exec", ("def run(text):", "    exec(text)"), ("line 3: dynamic code prevents static verification",)),
    ("getattr of os with a variable name", ("import os", "def call(name, path):", "    return getattr(os, name)(path)"),
     ("line 4: dynamic attribute of os prevents static verification",)),
    ("getattr of os with a literal name", ("import os", "def drop(path):", "    return getattr(os, 'remove')(path)"),
     (f"line 4: {_ENVCHECK_OS}remove",)),
    ("os passed on", ("import os", "def call(make):", "    return make(os)"), ("line 4: os escapes the static check",)),
    # Tests r2, F3 (review tests-r1): one name for two checked objects. (a) two libraries under one handle
    # name, which once named the wrong library; (b) a module, then a library, which once hid DeleteFileW.
    ("one handle name for two libraries", ("import ctypes", "def drives(letter):", "    lib = ctypes.WinDLL('kernel32')",
                                           "    return lib.GetDriveTypeW(letter)", "def close(handle):",
                                           "    lib = ctypes.WinDLL('mpr')", "    return lib.WNetCloseEnum(handle)"),
     ("line 7: lib is bound to more than one checked object",)),
    ("one name for a module and a library", ("import ctypes", "import os", "def sep():", "    k = os", "    return k.sep",
                                             "def drop(path):", "    k = ctypes.WinDLL('kernel32')",
                                             "    return k.DeleteFileW(path)"),
     ("line 8: k is bound to more than one checked object",)),
    ("an imported name rebound to a library", ("from json import loads as k", "import ctypes", "def drop(path):",
                                               "    k = ctypes.windll.kernel32", "    return k.DeleteFileW(path)"),
     ("line 5: k is bound to more than one checked object",)),
    # Tests r2, F5 (v1.7): stdlib modules outside the allow list, and registry sub-keys outside Uninstall.
    ("platform", ("import platform",), ("line 2: forbidden stdlib import platform",)),
    ("venv", ("import venv",), ("line 2: forbidden stdlib import venv",)),
    ("ensurepip", ("import ensurepip",), ("line 2: forbidden stdlib import ensurepip",)),
    ("py_compile", ("import py_compile",), ("line 2: forbidden stdlib import py_compile",)),
    ("compileall", ("import compileall",), ("line 2: forbidden stdlib import compileall",)),
    ("zipapp", ("import zipapp",), ("line 2: forbidden stdlib import zipapp",)),
    ("mailbox", ("import mailbox",), ("line 2: forbidden stdlib import mailbox",)),
    ("pydoc", ("import pydoc",), ("line 2: forbidden stdlib import pydoc",)),
    ("stat", ("import stat",), ("line 2: forbidden stdlib import stat",)),
    ("glob, from-imported", ("from glob import glob",), ("line 2: forbidden stdlib import glob",)),
    ("__future__", ("from __future__ import annotations",), ("line 2: forbidden stdlib import __future__",)),
    ("platform inside a function", ("def system():", "    import platform", "    return platform.system()"),
     ("line 3: forbidden stdlib import platform",)),
    ("an OpenKey sub-key outside Uninstall", ("def read():", "    import winreg",
                                              "    return winreg.OpenKey(winreg.HKEY_CURRENT_USER, 'Network')"),
     ("line 4: forbidden registry key Network",)),
    ("an OpenKeyEx sub_key= outside Uninstall", ("def read():", "    import winreg",
                                                 "    return winreg.OpenKeyEx(winreg.HKEY_CURRENT_USER, sub_key='Environment')"),
     ("line 4: forbidden registry key Environment",)),
    ("an OpenKey sub-key under SYSTEM", ("def read():", "    import winreg",
                                         r"    return winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r'SYSTEM\CurrentControlSet')"),
     (r"line 4: forbidden registry key SYSTEM\CurrentControlSet",)),
)


def test_ac06_env002_envcheck_uses_no_process_network_or_file_change_and_only_the_listed_win32_calls():
    wrong = []
    # The checker first: exact findings for forbidden sources, none for the sources the contract allows.
    for label, lines, expected in _ENVCHECK_FORBIDDEN:
        findings = _inspect_envcheck_source(_synthetic(lines))
        if findings != list(expected):
            wrong.append(f"{label}: expected {list(expected)}, got {findings}")
    for label, lines in _ENVCHECK_ALLOWED:
        findings = _inspect_envcheck_source(_synthetic(lines))
        if findings:
            wrong.append(f"{label}: legitimate source reported: {findings}")
    assert not wrong, "AC-06: the envcheck checker:\n" + "\n".join(wrong)

    # Then the module itself, which must exist, and the package __init__ that runs before it.
    source_root = Path.cwd() / "src"
    module = source_root / "sochron" / "app" / "envcheck.py"
    assert module.is_file(), f"AC-06: {module} does not exist; sochron.app.envcheck not implemented"
    files = [module] + [path for path in (source_root / "sochron" / "app" / "__init__.py",) if path.is_file()]
    findings = []
    for path in files:
        relative = path.relative_to(source_root)
        try:
            violations = _inspect_envcheck_source(path.read_text(encoding="utf-8-sig"), "sochron.app")
        except SyntaxError as error:
            findings.append(f"{relative}:{error.lineno}: invalid Python syntax: {error.msg}")
            continue
        findings.extend(f"{relative}: {violation}" for violation in violations)
    assert not findings, "AC-06: forbidden use in sochron.app.envcheck:\n" + "\n".join(findings)
