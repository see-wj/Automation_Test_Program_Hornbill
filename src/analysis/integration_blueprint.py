"""Reviewed, non-executable integration blueprint for imported test scripts."""

from dataclasses import asdict, dataclass, field
from datetime import datetime

from analysis.blueprint_execution import build_command_bindings, build_execution_plan


BLUEPRINT_SCHEMA_VERSION = 2


@dataclass(frozen=True)
class BlueprintInstrument:
    variable: str
    role: str
    address: str
    evidence: str


@dataclass(frozen=True)
class BlueprintParameter:
    name: str
    value_type: str
    prompt: str
    default: str
    include_in_gui: bool


@dataclass(frozen=True)
class BlueprintCommand:
    line: int
    operation: str
    receiver: str
    command: str
    selected_mapping: str
    approved: bool


@dataclass(frozen=True)
class BlueprintSafety:
    maximum_voltage: str
    maximum_current: str
    maximum_power: str
    polling_timeout_seconds: float
    settling_delay_seconds: float
    checkpoint_each_point: bool
    guaranteed_shutdown: bool
    confirmed_by_developer: bool


@dataclass
class IntegrationBlueprint:
    source_path: str
    test_name: str
    instruments: list[BlueprintInstrument]
    parameters: list[BlueprintParameter]
    commands: list[BlueprintCommand]
    safety: BlueprintSafety
    sweeps: list[dict]
    outputs: list[dict]
    data_fields: list[str]
    warnings: list[str]
    integration_steps: list[str]
    command_bindings: list[dict] = field(default_factory=list)
    execution_plan: dict = field(default_factory=dict)
    schema_version: int = BLUEPRINT_SCHEMA_VERSION
    generated_at: str = field(
        default_factory=lambda: datetime.now().isoformat(timespec="seconds")
    )
    status: str = "review_required"
    review_issues: list[str] = field(default_factory=list)

    def finalize_status(self):
        self.review_issues = validate_blueprint(self)
        self.status = "approved" if not self.review_issues else "review_required"
        return self

    def to_dict(self):
        return asdict(self)


def create_integration_blueprint(
    analysis,
    *,
    test_name,
    instrument_roles=None,
    parameter_settings=None,
    command_settings=None,
    safety_settings=None,
):
    instrument_roles = instrument_roles or {}
    parameter_settings = parameter_settings or {}
    command_settings = command_settings or {}
    safety_settings = safety_settings or {}

    instruments = []
    for finding in analysis.instrument_roles:
        role = instrument_roles.get(finding.variable, finding.role)
        instruments.append(
            BlueprintInstrument(
                variable=finding.variable,
                role=str(role),
                address=finding.address,
                evidence=finding.evidence,
            )
        )

    parameters = []
    for finding in analysis.parameters:
        settings = parameter_settings.get(finding.name, {})
        parameters.append(
            BlueprintParameter(
                name=finding.name,
                value_type=finding.conversion,
                prompt=finding.prompt,
                default=str(settings.get("default", "")),
                include_in_gui=bool(settings.get("include_in_gui", True)),
            )
        )

    commands = []
    for index, finding in enumerate(analysis.commands):
        settings = command_settings.get(index, {})
        default_mapping = finding.mappings[0] if finding.mappings else ""
        commands.append(
            BlueprintCommand(
                line=finding.line,
                operation=finding.operation,
                receiver=finding.receiver,
                command=finding.command,
                selected_mapping=str(
                    settings.get("selected_mapping", default_mapping)
                ).strip(),
                approved=bool(settings.get("approved", False)),
            )
        )

    safety = BlueprintSafety(
        maximum_voltage=str(safety_settings.get("maximum_voltage", "")).strip(),
        maximum_current=str(safety_settings.get("maximum_current", "")).strip(),
        maximum_power=str(safety_settings.get("maximum_power", "")).strip(),
        polling_timeout_seconds=float(
            safety_settings.get("polling_timeout_seconds", 30.0)
        ),
        settling_delay_seconds=float(
            safety_settings.get("settling_delay_seconds", 0.0)
        ),
        checkpoint_each_point=bool(
            safety_settings.get("checkpoint_each_point", True)
        ),
        guaranteed_shutdown=bool(
            safety_settings.get("guaranteed_shutdown", True)
        ),
        confirmed_by_developer=bool(
            safety_settings.get("confirmed_by_developer", False)
        ),
    )

    blueprint = IntegrationBlueprint(
        source_path=analysis.source_path,
        test_name=str(test_name).strip(),
        instruments=instruments,
        parameters=parameters,
        commands=commands,
        safety=safety,
        sweeps=[asdict(item) for item in analysis.sweeps],
        outputs=[asdict(item) for item in analysis.outputs],
        data_fields=list(analysis.data_fields),
        warnings=list(analysis.warnings),
        integration_steps=list(analysis.integration_steps),
        command_bindings=build_command_bindings(commands),
        execution_plan=build_execution_plan(
            commands,
            [asdict(item) for item in analysis.sweeps],
        ),
    )
    return blueprint.finalize_status()


def validate_blueprint(blueprint):
    issues = []
    if not blueprint.test_name:
        issues.append("Test name is required.")
    unknown_roles = [
        item.variable
        for item in blueprint.instruments
        if item.role in {"", "UNKNOWN"}
    ]
    if unknown_roles:
        issues.append(
            "Instrument roles require confirmation: " + ", ".join(unknown_roles)
        )
    unresolved_commands = [
        str(item.line)
        for item in blueprint.commands
        if not item.selected_mapping
    ]
    if unresolved_commands:
        issues.append(
            "Commands require a mapping at source line(s): "
            + ", ".join(unresolved_commands)
        )
    unapproved_commands = [
        str(item.line)
        for item in blueprint.commands
        if not item.approved
    ]
    if unapproved_commands:
        issues.append(
            "Commands require developer approval at source line(s): "
            + ", ".join(unapproved_commands)
        )
    required_safety = {
        "maximum voltage": blueprint.safety.maximum_voltage,
        "maximum current": blueprint.safety.maximum_current,
        "maximum power": blueprint.safety.maximum_power,
    }
    missing_safety = [name for name, value in required_safety.items() if not value]
    if missing_safety:
        issues.append("Safety values are required: " + ", ".join(missing_safety))
    numeric_safety = {}
    for name, value in required_safety.items():
        if not value:
            continue
        try:
            numeric_value = float(value)
        except (TypeError, ValueError):
            issues.append(f"Safety value must be numeric: {name}.")
            continue
        if numeric_value <= 0:
            issues.append(f"Safety value must be greater than zero: {name}.")
            continue
        numeric_safety[name] = numeric_value
    issues.extend(_validate_sweep_safety(blueprint.sweeps, numeric_safety))
    if blueprint.safety.polling_timeout_seconds <= 0:
        issues.append("Polling timeout must be greater than zero.")
    if not blueprint.safety.checkpoint_each_point:
        issues.append("A pause/abort checkpoint is required at every test point.")
    if not blueprint.safety.guaranteed_shutdown:
        issues.append("Guaranteed instrument shutdown must remain enabled.")
    if not blueprint.safety.confirmed_by_developer:
        issues.append("Safety limits require explicit developer confirmation.")
    return issues


def _validate_sweep_safety(sweeps, numeric_safety):
    issues = []
    sweep_limits = {"voltage": [], "current": []}
    for sweep in sweeps:
        description = " ".join(
            str(sweep.get(field, ""))
            for field in ("name", "start", "stop", "step")
        ).lower()
        quantity = None
        if "curr" in description:
            quantity = "current"
        elif "volt" in description or "sweep_values" in description:
            quantity = "voltage"
        if quantity is None:
            continue
        try:
            stop = float(sweep.get("stop", ""))
        except (TypeError, ValueError):
            continue
        sweep_limits[quantity].append((stop, sweep.get("line", "unknown")))

    for quantity, limits in sweep_limits.items():
        safety_limit = numeric_safety.get(f"maximum {quantity}")
        if safety_limit is None or not limits:
            continue
        sweep_stop = max(stop for stop, _line in limits)
        if safety_limit < sweep_stop:
            lines = ", ".join(
                str(line) for stop, line in limits if stop == sweep_stop
            )
            issues.append(
                f"Maximum {quantity} {safety_limit:g} is below detected "
                f"{quantity} sweep stop {sweep_stop:g} at source line(s): {lines}."
            )
    return issues


__all__ = [
    "BLUEPRINT_SCHEMA_VERSION",
    "BlueprintCommand",
    "BlueprintInstrument",
    "BlueprintParameter",
    "BlueprintSafety",
    "IntegrationBlueprint",
    "create_integration_blueprint",
    "validate_blueprint",
]
