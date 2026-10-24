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
side-effect-free stdlib only, with no random module and no float names or literals.
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
