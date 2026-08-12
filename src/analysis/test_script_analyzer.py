"""Static analysis for importing external instrument test scripts safely."""

import ast
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path


VISA_ADDRESS_PATTERN = re.compile(
    r"\b(?:USB\d*|GPIB\d*|TCPIP\d*|ASRL\d*)::[^\s\"']+",
    re.IGNORECASE,
)
INSTRUMENT_OPERATIONS = {
    "write",
    "query",
    "query_ascii_values",
    "query_binary_values",
    "write_ascii_values",
    "write_binary_values",
    "scpi",
}
QUERY_OPERATIONS = {
    "query",
    "query_ascii_values",
    "query_binary_values",
    "socket_query",
}
SAFETY_NAME_TOKENS = (
    "limit",
    "lim",
    "rating",
    "rated",
    "maximum",
    "minimum",
)
DEFAULT_SCPI_LIBRARY_FILENAMES = (
    "Keysight.py",
    "IEEEStandard.py",
    "Chroma.py",
    "Keithley.py",
)


@dataclass(frozen=True)
class CommandFinding:
    line: int
    operation: str
    command: str
    receiver: str
    mappings: tuple[str, ...] = ()


@dataclass(frozen=True)
class DelayFinding:
    line: int
    expression: str


@dataclass(frozen=True)
class LoopFinding:
    line: int
    kind: str
    expression: str


@dataclass(frozen=True)
class ParameterFinding:
    line: int
    name: str
    prompt: str
    conversion: str


@dataclass(frozen=True)
class SafetyFinding:
    line: int
    name: str
    expression: str


@dataclass(frozen=True)
class SweepFinding:
    line: int
    name: str
    start: str
    stop: str
    step: str


@dataclass(frozen=True)
class OutputFinding:
    line: int
    operation: str
    path: str


@dataclass(frozen=True)
class ControlFinding:
    line: int
    kind: str
    expression: str


@dataclass(frozen=True)
class InstrumentRoleFinding:
    variable: str
    role: str
    address: str
    evidence: str


@dataclass
class ScriptAnalysis:
    source_path: str
    imports: list[str] = field(default_factory=list)
    classes: list[str] = field(default_factory=list)
    functions: list[str] = field(default_factory=list)
    visa_addresses: list[str] = field(default_factory=list)
    instrument_classes: list[str] = field(default_factory=list)
    instrument_roles: list[InstrumentRoleFinding] = field(default_factory=list)
    parameters: list[ParameterFinding] = field(default_factory=list)
    safety_limits: list[SafetyFinding] = field(default_factory=list)
    sweeps: list[SweepFinding] = field(default_factory=list)
    outputs: list[OutputFinding] = field(default_factory=list)
    controls: list[ControlFinding] = field(default_factory=list)
    data_fields: list[str] = field(default_factory=list)
    commands: list[CommandFinding] = field(default_factory=list)
    delays: list[DelayFinding] = field(default_factory=list)
    loops: list[LoopFinding] = field(default_factory=list)
    execution_flow: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    integration_steps: list[str] = field(default_factory=list)

    def to_dict(self):
        return asdict(self)


@dataclass(frozen=True)
class _CommandWrapper:
    command_index: int
    receiver_index: int | None
    operation: str


def analyze_test_script(script_path, keysight_path=None, scpi_library_paths=None):
    script_path = Path(script_path)
    source = script_path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(source, filename=str(script_path))
    except SyntaxError as exception:
        raise ValueError(
            f"Python syntax error at line {exception.lineno}: {exception.msg}"
        ) from exception

    if scpi_library_paths is None:
        if keysight_path is not None:
            scpi_library_paths = (keysight_path,)
        else:
            library_directory = Path(__file__).resolve().parents[2] / "SCPI_Library"
            scpi_library_paths = tuple(
                library_directory / filename
                for filename in DEFAULT_SCPI_LIBRARY_FILENAMES
            )
    command_catalog, known_classes = build_scpi_command_catalog(
        scpi_library_paths
    )
    constants = _collect_module_constants(tree)
    wrappers = _find_command_wrappers(tree)
    protected_ranges = _cleanup_protected_ranges(tree)
    visitor = _ScriptVisitor(
        command_catalog,
        known_classes,
        constants,
        wrappers,
        protected_ranges,
    )
    visitor.visit(tree)

    analysis = ScriptAnalysis(
        source_path=str(script_path.resolve()),
        imports=sorted(visitor.imports),
        classes=visitor.classes,
        functions=visitor.functions,
        visa_addresses=sorted(set(VISA_ADDRESS_PATTERN.findall(source))),
        instrument_classes=sorted(visitor.instrument_classes),
        instrument_roles=_infer_instrument_roles(visitor),
        parameters=visitor.parameters,
        safety_limits=visitor.safety_limits,
        sweeps=visitor.sweeps,
        outputs=visitor.outputs,
        controls=visitor.controls,
        data_fields=sorted(visitor.data_fields),
        commands=visitor.commands,
        delays=visitor.delays,
        loops=visitor.loops,
        execution_flow=visitor.execution_flow,
    )
    analysis.warnings = _build_warnings(analysis, visitor)
    analysis.integration_steps = _build_integration_steps(analysis)
    return analysis


def build_keysight_command_catalog(keysight_path):
    return build_scpi_command_catalog((keysight_path,))


def build_scpi_command_catalog(library_paths):
    catalog = []
    class_names = set()
    for library_path in library_paths:
        path = Path(library_path)
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        module_name = path.stem
        for class_node in (
            node for node in tree.body if isinstance(node, ast.ClassDef)
        ):
            class_names.add(class_node.name)
            for method in (
                node
                for node in class_node.body
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            ):
                for call in sorted(
                    (node for node in ast.walk(method) if isinstance(node, ast.Call)),
                    key=lambda node: (node.lineno, node.col_offset),
                ):
                    operation = _call_name(call.func).rsplit(".", 1)[-1]
                    if operation not in INSTRUMENT_OPERATIONS or not call.args:
                        continue
                    command = _string_expression(call.args[0])
                    if not command or not _looks_like_scpi(command):
                        continue
                    signature = _scpi_signature(command)
                    if not signature:
                        continue
                    if signature in {("SYST", "ERR"), ("ERR",)} and (
                        "error" not in method.name.lower()
                        and "err" not in method.name.lower()
                    ):
                        continue
                    catalog.append(
                        (
                            signature,
                            _mapping_name(module_name, class_node.name, method.name),
                            _operation_family(operation),
                        )
                    )
    return tuple(catalog), frozenset(class_names)


def _mapping_name(module_name, class_name, method_name):
    if module_name == "Keysight":
        return f"{class_name}.{method_name}"
    if method_name == "__init__":
        return f"{module_name}.{class_name}"
    return f"{module_name}.{class_name}.{method_name}"


class _ScriptVisitor(ast.NodeVisitor):
    def __init__(
        self,
        command_catalog,
        known_classes,
        constants,
        wrappers,
        protected_ranges,
    ):
        self.command_catalog = command_catalog
        self.known_classes = known_classes
        self.constants = dict(constants)
        self.wrappers = wrappers
        self.protected_ranges = protected_ranges
        self.imports = set()
        self.classes = []
        self.functions = []
        self.instrument_classes = set()
        self.resource_bindings = {}
        self.receiver_commands = {}
        self.parameters = []
        self.safety_limits = []
        self.sweeps = []
        self.outputs = []
        self.controls = []
        self.data_fields = set()
        self.commands = []
        self.delays = []
        self.loops = []
        self.execution_flow = []
        self.open_resource_lines = []
        self.has_close = False
        self.has_finally = False
        self.has_socket_operations = False
        self.has_socket_timeout = False
        self.dynamic_command_lines = []
        self.bare_except_lines = []
        self.unbounded_while_lines = []
        self.function_stack = []

    def visit_Import(self, node):
        self.imports.update(alias.name for alias in node.names)
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        self.imports.add(node.module or "")
        self.generic_visit(node)

    def visit_ClassDef(self, node):
        self.classes.append(node.name)
        self.execution_flow.append(f"Line {node.lineno}: define class {node.name}")
        self.generic_visit(node)

    def visit_FunctionDef(self, node):
        self.functions.append(node.name)
        self.execution_flow.append(f"Line {node.lineno}: define function {node.name}()")
        self.function_stack.append(node.name)
        for statement in node.body:
            self.visit(statement)
        self.function_stack.pop()

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_Assign(self, node):
        target_names = [
            target.id for target in node.targets if isinstance(target, ast.Name)
        ]
        value = _expression_value(node.value, self.constants)
        for name in target_names:
            if value is None:
                self.constants.pop(name, None)
            else:
                self.constants[name] = value
            self._record_parameter(node, name)
            self._record_safety_limit(node, name, value)
            self._record_sweep(node, name)
            self._record_resource_binding(node, name)
        self._record_dataframe_fields(node)
        self.generic_visit(node)

    def visit_AnnAssign(self, node):
        if isinstance(node.target, ast.Name) and node.value is not None:
            value = _expression_value(node.value, self.constants)
            if value is not None:
                self.constants[node.target.id] = value
            self._record_parameter(node, node.target.id)
            self._record_safety_limit(node, node.target.id, value)
        self.generic_visit(node)

    def visit_For(self, node):
        expression = f"{_safe_unparse(node.target)} in {_safe_unparse(node.iter)}"
        self.loops.append(LoopFinding(node.lineno, "for", expression))
        self.execution_flow.append(f"Line {node.lineno}: for {expression}")
        for name in _assigned_names(node.target):
            self.constants.pop(name, None)
        self.generic_visit(node)

    def visit_While(self, node):
        expression = _safe_unparse(node.test)
        self.loops.append(LoopFinding(node.lineno, "while", expression))
        self.execution_flow.append(f"Line {node.lineno}: while {expression}")
        if _is_always_true(node.test):
            self.unbounded_while_lines.append(node.lineno)
            self.controls.append(
                ControlFinding(node.lineno, "unbounded_poll", expression)
            )
        self.generic_visit(node)

    def visit_If(self, node):
        expression = _safe_unparse(node.test)
        self.execution_flow.append(f"Line {node.lineno}: if {expression}")
        self.generic_visit(node)

    def visit_Break(self, node):
        self.controls.append(ControlFinding(node.lineno, "break", "break"))

    def visit_Try(self, node):
        if node.finalbody:
            self.has_finally = True
        for handler in node.handlers:
            if handler.type is None:
                self.bare_except_lines.append(handler.lineno)
        self.generic_visit(node)

    def visit_Call(self, node):
        call_name = _call_name(node.func)
        method_name = call_name.rsplit(".", 1)[-1]
        receiver = call_name.rsplit(".", 1)[0] if "." in call_name else ""

        if method_name == "open_resource":
            self.open_resource_lines.append(node.lineno)
        if method_name == "close":
            self.has_close = True
        if method_name == "settimeout":
            self.has_socket_timeout = True
        if call_name in {"time.sleep", "sleep", "QThread.msleep"}:
            expression = _safe_unparse(node.args[0]) if node.args else "unknown"
            self.delays.append(DelayFinding(node.lineno, expression))
            self.execution_flow.append(f"Line {node.lineno}: wait {expression}")
        if call_name == "keyboard.is_pressed":
            key = _string_expression(node.args[0], self.constants) if node.args else ""
            self.controls.append(ControlFinding(node.lineno, "keyboard_abort", key or ""))
        if call_name == "signal.signal":
            self.controls.append(
                ControlFinding(node.lineno, "signal_handler", _safe_unparse(node))
            )
        if call_name == "sys.exit":
            self.controls.append(
                ControlFinding(node.lineno, "process_exit", _safe_unparse(node))
            )

        constructor = method_name
        if constructor in self.known_classes:
            self.instrument_classes.add(constructor)

        if method_name in {"to_excel", "to_csv"} and node.args:
            path = _string_expression(node.args[0], self.constants) or _safe_unparse(
                node.args[0]
            )
            self.outputs.append(OutputFinding(node.lineno, method_name, path))

        if call_name in self.wrappers:
            self._record_wrapper_command(node, call_name)
        elif method_name in INSTRUMENT_OPERATIONS and node.args:
            self._record_command(node, method_name, receiver, node.args[0])
        elif method_name == "send" and node.args:
            self.has_socket_operations = True
            if not self._inside_command_wrapper():
                self._record_command(node, "send", receiver, node.args[0])
        elif method_name in {"recv", "recv_into"}:
            self.has_socket_operations = True
        elif method_name == "connect":
            self.has_socket_operations = True
            self._record_socket_binding(node, receiver)
        self.generic_visit(node)

    def _record_command(self, node, operation, receiver, expression):
        command = _string_expression(expression, self.constants)
        if command and _looks_like_scpi(command):
            mappings = map_scpi_command(
                command,
                self.command_catalog,
                operation=operation,
                preferred_prefixes=_preferred_mapping_prefixes(
                    receiver,
                    command,
                ),
            )
            finding = CommandFinding(
                node.lineno,
                operation,
                command,
                receiver,
                mappings,
            )
            self.commands.append(finding)
            self.receiver_commands.setdefault(receiver, []).append(command)
            self.execution_flow.append(
                f"Line {node.lineno}: {receiver}.{operation}({command})"
            )
        elif operation in INSTRUMENT_OPERATIONS or operation == "send":
            self.dynamic_command_lines.append(node.lineno)

    def _record_wrapper_command(self, node, wrapper_name):
        wrapper = self.wrappers[wrapper_name]
        if len(node.args) <= wrapper.command_index:
            self.dynamic_command_lines.append(node.lineno)
            return
        receiver = wrapper_name
        if wrapper.receiver_index is not None and len(node.args) > wrapper.receiver_index:
            receiver = _safe_unparse(node.args[wrapper.receiver_index])
        self._record_command(
            node,
            wrapper.operation,
            receiver,
            node.args[wrapper.command_index],
        )

    def _inside_command_wrapper(self):
        return bool(
            self.function_stack and self.function_stack[-1] in self.wrappers
        )

    def _record_parameter(self, node, name):
        input_call, conversion = _input_call(node.value)
        if input_call is None:
            return
        prompt = (
            _string_expression(input_call.args[0], self.constants)
            if input_call.args
            else ""
        )
        self.parameters.append(
            ParameterFinding(node.lineno, name, prompt or "", conversion)
        )
        self.execution_flow.append(
            f"Line {node.lineno}: request parameter {name} ({conversion})"
        )

    def _record_safety_limit(self, node, name, value):
        normalized = name.lower()
        if not any(token in normalized for token in SAFETY_NAME_TOKENS):
            return
        expression = repr(value) if value is not None else _safe_unparse(node.value)
        self.safety_limits.append(
            SafetyFinding(node.lineno, name, expression)
        )

    def _record_sweep(self, node, name):
        if not isinstance(node.value, ast.Call):
            return
        if _call_name(node.value.func) not in {"np.arange", "numpy.arange", "range"}:
            return
        arguments = [_safe_unparse(argument) for argument in node.value.args]
        if len(arguments) == 1:
            start, stop, step = "0", arguments[0], "1"
        elif len(arguments) == 2:
            start, stop, step = arguments[0], arguments[1], "1"
        elif len(arguments) >= 3:
            start, stop, step = arguments[:3]
        else:
            return
        self.sweeps.append(SweepFinding(node.lineno, name, start, stop, step))

    def _record_resource_binding(self, node, name):
        if not isinstance(node.value, ast.Call):
            return
        call_name = _call_name(node.value.func)
        if call_name.rsplit(".", 1)[-1] != "open_resource":
            return
        address = ""
        if node.value.args:
            address = _string_expression(node.value.args[0], self.constants) or _safe_unparse(
                node.value.args[0]
            )
        self.resource_bindings[name] = (address, f"VISA resource assigned at line {node.lineno}")

    def _record_socket_binding(self, node, receiver):
        address = _safe_unparse(node.args[0]) if node.args else ""
        if node.args and isinstance(node.args[0], (ast.Tuple, ast.List)):
            values = [
                _expression_value(item, self.constants) for item in node.args[0].elts
            ]
            if all(value is not None for value in values):
                address = ":".join(str(value) for value in values)
        self.resource_bindings.setdefault(
            receiver,
            (address, f"TCP socket connected at line {node.lineno}"),
        )

    def _record_dataframe_fields(self, node):
        if not isinstance(node.value, ast.Call):
            return
        if _call_name(node.value.func) not in {"pd.DataFrame", "pandas.DataFrame"}:
            return
        if not node.value.args or not isinstance(node.value.args[0], ast.Dict):
            return
        for key in node.value.args[0].keys:
            value = _expression_value(key, self.constants)
            if isinstance(value, str):
                self.data_fields.add(value)


def map_scpi_command(
    command,
    command_catalog,
    operation=None,
    limit=5,
    preferred_prefixes=(),
):
    signature = _scpi_signature(command)
    if not signature:
        return ()
    operation_family = _operation_family(operation)
    matches = []
    for candidate in command_catalog:
        if len(candidate) == 2:
            candidate_signature, method_name = candidate
            candidate_operation = None
        else:
            candidate_signature, method_name, candidate_operation = candidate
        if (
            operation_family
            and candidate_operation
            and operation_family != candidate_operation
        ):
            continue
        score = _signature_match_score(signature, candidate_signature)
        if score is not None:
            score += _method_relevance_score(command, method_name)
            matches.append((score, method_name))
    preferred_matches = [
        item
        for item in matches
        if any(
            prefix in item[1].split(".")[:-1]
            for prefix in preferred_prefixes
        )
    ]
    if preferred_matches:
        matches = preferred_matches
    matches.sort(
        key=lambda item: (
            _preferred_mapping_rank(item[1], preferred_prefixes),
            -item[0],
            item[1],
        )
    )
    result = []
    for _score, method_name in matches:
        if method_name not in result:
            result.append(method_name)
        if len(result) >= limit:
            break
    return tuple(result)


def _preferred_mapping_rank(mapping_name, preferred_prefixes):
    mapping_parts = mapping_name.split(".")[:-1]
    for index, prefix in enumerate(preferred_prefixes):
        if prefix in mapping_parts:
            return index
    return len(preferred_prefixes)


def _build_warnings(analysis, visitor):
    warnings = []
    if visitor.open_resource_lines:
        warnings.append(
            "The script opens VISA resources directly; integration should use "
            "project session and cleanup helpers."
        )
    unprotected = [
        line
        for line in visitor.open_resource_lines
        if not any(start <= line <= end for start, end in visitor.protected_ranges)
    ]
    if unprotected:
        warnings.append(
            "VISA resources are opened outside a cleanup-protected try/finally at "
            f"line(s): {', '.join(map(str, unprotected))}."
        )
    if visitor.open_resource_lines and not visitor.has_close:
        warnings.append("A VISA resource is opened but no close() call was detected.")
    if visitor.has_socket_operations and not visitor.has_socket_timeout:
        warnings.append(
            "Socket communication has no detected timeout and may block indefinitely."
        )
    if visitor.unbounded_while_lines:
        warnings.append(
            "Unbounded while-loop polling requires timeout, delay, and abort checks at "
            f"line(s): {', '.join(map(str, visitor.unbounded_while_lines))}."
        )
    if analysis.visa_addresses:
        warnings.append(
            "Hardcoded VISA addresses should become GUI/configuration parameters."
        )
    if analysis.instrument_roles and any(
        ":" in role.address and "::" not in role.address
        for role in analysis.instrument_roles
    ):
        warnings.append(
            "Hardcoded socket host/port values should become configuration parameters."
        )
    if analysis.parameters:
        warnings.append(
            "Interactive input() parameters should become validated GUI fields."
        )
    if visitor.dynamic_command_lines:
        lines = ", ".join(str(line) for line in sorted(set(visitor.dynamic_command_lines)))
        warnings.append(f"Dynamic commands could not be resolved at line(s): {lines}.")
    unmapped = [finding for finding in analysis.commands if not finding.mappings]
    if unmapped:
        warnings.append(
            f"{len(unmapped)} command(s) have no likely SCPI library mapping and "
            "require developer review."
        )
    if analysis.commands and not any(
        "ERR?" in finding.command.upper() for finding in analysis.commands
    ):
        warnings.append("No instrument error-query command was detected.")
    if visitor.bare_except_lines:
        warnings.append(
            "Bare except blocks hide cleanup or communication failures at line(s): "
            f"{', '.join(map(str, visitor.bare_except_lines))}."
        )
    if analysis.outputs and any(_looks_absolute_user_path(item.path) for item in analysis.outputs):
        warnings.append(
            "Hardcoded user-specific output paths should use RunContext storage."
        )
    if "keyboard" in analysis.imports:
        warnings.append(
            "Global keyboard polling should be replaced by TestWorker checkpoints."
        )
    if not analysis.delays and analysis.commands:
        warnings.append(
            "No explicit settling delay was detected between instrument commands."
        )
    return warnings


def _build_integration_steps(analysis):
    steps = [
        "Confirm each inferred instrument role using *IDN? before selecting a driver.",
        "Create a dedicated test class under DUT_Test_Scripts or src/instruments.",
        "Expose addresses, sweep values, limits, timing, and output options through configuration.",
        "Use TestWorker checkpoints for pause, resume, abort, and bounded polling.",
        "Define required instruments and safety limits in execution/preflight.py.",
        "Write results through RunContext and the project report exporters.",
        "Add deterministic simulation tests before real-hardware execution.",
    ]
    if any(not command.mappings for command in analysis.commands):
        steps.insert(
            2,
            "Review unmapped SCPI and add approved wrappers to the appropriate SCPI library.",
        )
    return steps


def _collect_module_constants(tree):
    constants = {}
    for node in tree.body:
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        value_node = node.value
        value = _expression_value(value_node, constants)
        if value is None:
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        for target in targets:
            if isinstance(target, ast.Name):
                constants[target.id] = value
    return constants


def _find_command_wrappers(tree):
    wrappers = {}
    for function in (
        node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    ):
        parameter_names = [argument.arg for argument in function.args.args]
        has_receive = any(
            isinstance(node, ast.Call)
            and _call_name(node.func).rsplit(".", 1)[-1] in {"recv", "read"}
            for node in ast.walk(function)
        )
        for call in (node for node in ast.walk(function) if isinstance(node, ast.Call)):
            method = _call_name(call.func).rsplit(".", 1)[-1]
            if method not in {"send", "write"} or not call.args:
                continue
            referenced = _referenced_names(call.args[0])
            command_indexes = [
                index
                for index, name in enumerate(parameter_names)
                if name in referenced and any(token in name.lower() for token in ("cmd", "command", "scpi"))
            ]
            if not command_indexes:
                continue
            receiver_name = _call_name(call.func).rsplit(".", 1)[0].split(".", 1)[0]
            receiver_index = (
                parameter_names.index(receiver_name)
                if receiver_name in parameter_names
                else None
            )
            wrappers[function.name] = _CommandWrapper(
                command_indexes[0],
                receiver_index,
                "socket_query" if has_receive else method,
            )
            break
    return wrappers


def _cleanup_protected_ranges(tree):
    ranges = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Try) or not node.finalbody or not node.body:
            continue
        ranges.append((node.body[0].lineno, node.body[-1].end_lineno))
    return tuple(ranges)


def _infer_instrument_roles(visitor):
    roles = []
    for variable, (address, evidence) in visitor.resource_bindings.items():
        commands = visitor.receiver_commands.get(variable, [])
        normalized_name = variable.upper()
        command_headers = " ".join(commands).upper()
        if any(token in normalized_name for token in ("DMM", "VOUT", "METER")) or any(
            token in command_headers for token in ("FETCH", "CONF:VOLT", "STAT:OPER")
        ):
            role = "DMM"
        elif any(token in normalized_name for token in ("LOAD", "ELOAD", "CURR")):
            role = "ELOAD"
        elif any(token in normalized_name for token in ("DUT", "PSU", "SOCK")) or "DIAG:" in command_headers:
            role = "DUT/Hornbill"
        elif "SCOPE" in normalized_name or "OSC" in normalized_name:
            role = "OSCILLOSCOPE"
        else:
            role = "UNKNOWN"
        roles.append(InstrumentRoleFinding(variable, role, address, evidence))
    return sorted(roles, key=lambda item: item.variable)


def _input_call(node):
    conversion = "str"
    current = node
    if isinstance(current, ast.Call):
        call_name = _call_name(current.func)
        if call_name in {"float", "int", "str"} and current.args:
            conversion = call_name
            current = current.args[0]
    if isinstance(current, ast.Call) and _call_name(current.func) == "input":
        return current, conversion
    return None, conversion


def _expression_value(node, constants=None):
    constants = constants or {}
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Name):
        return constants.get(node.id)
    if isinstance(node, (ast.Tuple, ast.List)):
        values = [_expression_value(item, constants) for item in node.elts]
        return tuple(values) if all(value is not None for value in values) else None
    if isinstance(node, ast.JoinedStr):
        parts = []
        for value in node.values:
            if isinstance(value, ast.Constant):
                parts.append(str(value.value))
            elif isinstance(value, ast.FormattedValue):
                resolved = _expression_value(value.value, constants)
                parts.append(
                    str(resolved)
                    if resolved is not None
                    else "{" + _safe_unparse(value.value) + "}"
                )
        return "".join(parts)
    if isinstance(node, ast.BinOp):
        left = _expression_value(node.left, constants)
        right = _expression_value(node.right, constants)
        if isinstance(node.op, ast.Add) and left is not None and right is not None:
            try:
                return left + right
            except TypeError:
                return None
        if isinstance(node.op, ast.Mod) and isinstance(left, str) and right is not None:
            try:
                return left % right
            except (TypeError, ValueError):
                return None
    if isinstance(node, ast.UnaryOp):
        value = _expression_value(node.operand, constants)
        if isinstance(value, (int, float)):
            if isinstance(node.op, ast.USub):
                return -value
            if isinstance(node.op, ast.UAdd):
                return value
    if isinstance(node, ast.Call):
        method = _call_name(node.func).rsplit(".", 1)[-1]
        if method in {"encode", "decode", "strip"} and isinstance(node.func, ast.Attribute):
            return _expression_value(node.func.value, constants)
    return None


def _string_expression(node, constants=None):
    value = _expression_value(node, constants)
    if not isinstance(value, str):
        return None
    return value.strip()


def _call_name(node):
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        prefix = _call_name(node.value)
        return f"{prefix}.{node.attr}" if prefix else node.attr
    return ""


def _safe_unparse(node):
    try:
        return ast.unparse(node)
    except Exception:
        return "<dynamic>"


def _assigned_names(node):
    if isinstance(node, ast.Name):
        return (node.id,)
    if isinstance(node, (ast.Tuple, ast.List)):
        return tuple(
            name
            for item in node.elts
            for name in _assigned_names(item)
        )
    return ()


def _referenced_names(node):
    return {
        child.id for child in ast.walk(node) if isinstance(child, ast.Name)
    }


def _is_always_true(node):
    return isinstance(node, ast.Constant) and bool(node.value) is True


def _operation_family(operation):
    if operation is None:
        return None
    return "query" if operation in QUERY_OPERATIONS else "write"


def _preferred_mapping_prefixes(receiver, command):
    normalized_receiver = str(receiver).upper()
    normalized_command = str(command).upper()
    if normalized_command.startswith("*"):
        return ("IEEEStandard",)
    if "SOCK" in normalized_receiver or "DUT" in normalized_receiver:
        if "DIAG:" in normalized_command:
            return ("Hornbill",)
        return ("Hornbill", "Voltage", "Current", "Output")
    if any(token in normalized_receiver for token in ("CURR", "LOAD", "ELOAD")):
        return (
            "ELOAD_E363XXA",
            "ELOAD_E367XXA",
            "ELOAD_E63200A",
            "Current",
            "Output",
        )
    if any(token in normalized_receiver for token in ("VOUT", "DMM", "METER")):
        return (
            "DMM_344XXA",
            "DMM_3458A",
            "Fetch",
            "Status",
            "Trigger",
            "Initiate",
        )
    return ()


def _method_relevance_score(command, method_name):
    normalized_command = str(command).upper()
    normalized_method = str(method_name).upper()
    score = 0
    if "VOLT" in normalized_command and "VOLT" in normalized_method:
        score += 5
    if "CURR" in normalized_command and "CURR" in normalized_method:
        score += 5
    if "OUTP" in normalized_command and "OUTPUT" in normalized_method:
        score += 5
    if "DIAG:PEEK" in normalized_command and "READBACKVOLTAGE" in normalized_method:
        score += 20
    if "FETCH" in normalized_command and "FETCH" in normalized_method:
        score += 5
    return score


def _looks_like_scpi(command):
    normalized = str(command).strip().upper()
    if not normalized:
        return False
    return bool(
        normalized.startswith("*")
        or ":" in normalized
        or "?" in normalized
        or normalized.startswith(
            (
                "VOLT",
                "CURR",
                "MEAS",
                "SENS",
                "SOUR",
                "CONF",
                "CAL",
                "DIAG",
                "TRIG",
                "INIT",
                "FETCH",
                "FETC",
                "OUTP",
                "TARM",
                "PRESET",
                "ID",
                "ERR",
                "STAT",
            )
        )
    )


def _scpi_signature(command):
    normalized = str(command).strip().upper().lstrip(":")
    if not _looks_like_scpi(normalized):
        return ()
    header = re.split(r"[\s,(]", normalized, maxsplit=1)[0]
    header = header.replace("?", "").lstrip("*")
    aliases = {"TRG": "TRIG", "FETC": "FETCH"}
    return tuple(
        aliases.get(segment, segment)
        for segment in header.split(":")
        if segment
    )


def _signature_match_score(left, right):
    common_length = min(len(left), len(right))
    if not common_length:
        return None
    for left_segment, right_segment in zip(left[:common_length], right[:common_length]):
        if not (
            left_segment.startswith(right_segment)
            or right_segment.startswith(left_segment)
        ):
            return None
    length_difference = abs(len(left) - len(right))
    if length_difference > 2:
        return None
    return common_length * 10 - length_difference


def _looks_absolute_user_path(path):
    normalized = str(path).replace("\\", "/")
    return bool(re.match(r"^[A-Z]:/Users/", normalized, re.IGNORECASE))


__all__ = [
    "CommandFinding",
    "ControlFinding",
    "DelayFinding",
    "InstrumentRoleFinding",
    "LoopFinding",
    "OutputFinding",
    "ParameterFinding",
    "SafetyFinding",
    "ScriptAnalysis",
    "SweepFinding",
    "analyze_test_script",
    "build_scpi_command_catalog",
    "build_keysight_command_catalog",
    "map_scpi_command",
]
