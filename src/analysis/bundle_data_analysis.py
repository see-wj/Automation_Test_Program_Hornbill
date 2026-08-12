"""Analyze completed Bundle Test realtime measurement files."""

import json
import math
import re
from dataclasses import dataclass
from itertools import combinations
from pathlib import Path

import pandas as pd


METRICS = (
    (
        "Programming Error",
        "Programming_Voltage_Error",
        "Programming_Upper_Limit_Boundary",
        "Programming_Lower_Limit_Boundary",
    ),
    (
        "Readback Error",
        "Readback_Voltage_Error",
        "Readback_Upper_Limit_Boundary",
        "Readback_lower_Limit_Boundary",
    ),
)
CONDITION_COLUMNS = ("Set Voltage (V)", "Set Current (A)")
MIN_INFERENCE_SAMPLES = 5
PRACTICAL_DIFFERENCE_THRESHOLD_PERCENT = 10.0
MIN_STABILITY_CONFIRMATION_LOOPS = 2
STABILITY_SPAN_THRESHOLD_PERCENT = 10.0
STABILITY_STD_THRESHOLD_PERCENT = 5.0
STABILITY_DRIFT_THRESHOLD_PERCENT_PER_LOOP = 1.0
TREND_FLAT_THRESHOLD_PERCENT_PER_LOOP = 0.25
TREND_MEANINGFUL_SHIFT_PERCENT = 1.0
TREND_JUMP_THRESHOLD_PERCENT = 5.0
TREND_NEAR_BOUNDARY_PERCENT = 80.0
TREND_OUTLIER_ROBUST_Z = 3.5
REPORT_COLUMNS = (
    "Set_Voltage",
    "Set_Current",
    "Readback_Voltage",
    "Readback_Current",
    "Programming_Voltage",
    "Programming_Voltage_Error",
    "Programming_Voltage_Percentage_Error",
    "Readback_Voltage_Error",
    "Readback_Voltage_Percentage_Error",
    "Local_Voltage",
    "Local_Voltage_Error",
    "Programming_Upper_Limit_Boundary",
    "Programming_Lower_Limit_Boundary",
    "Programming_Condition",
    "Readback_Upper_Limit_Boundary",
    "Readback_lower_Limit_Boundary",
    "Readback_Condition",
)
T_CRITICAL_95 = (
    None,
    12.706,
    4.303,
    3.182,
    2.776,
    2.571,
    2.447,
    2.365,
    2.306,
    2.262,
    2.228,
    2.201,
    2.179,
    2.160,
    2.145,
    2.131,
    2.120,
    2.110,
    2.101,
    2.093,
    2.086,
    2.080,
    2.074,
    2.069,
    2.064,
    2.060,
    2.056,
    2.052,
    2.048,
    2.045,
    2.042,
)
T_CRITICAL_90 = (
    None,
    6.314,
    2.920,
    2.353,
    2.132,
    2.015,
    1.943,
    1.895,
    1.860,
    1.833,
    1.812,
    1.796,
    1.782,
    1.771,
    1.761,
    1.753,
    1.746,
    1.740,
    1.734,
    1.729,
    1.725,
    1.721,
    1.717,
    1.714,
    1.711,
    1.708,
    1.706,
    1.703,
    1.701,
    1.699,
    1.697,
)


@dataclass(frozen=True)
class BundleAnalysisResult:
    observations: pd.DataFrame
    errors: pd.DataFrame
    summary: pd.DataFrame
    loop_performance: pd.DataFrame
    stability_summary: pd.DataFrame
    trend_summary: pd.DataFrame
    channel_comparison: pd.DataFrame
    hypothesis_tests: pd.DataFrame
    extremes: pd.DataFrame
    insights: tuple
    trend_report: tuple
    comparison_report: tuple
    methodology: tuple
    practical_difference_threshold_percent: float

    @property
    def empty(self):
        return self.observations.empty

    def export_csv(self, directory):
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)
        self.summary.to_csv(directory / "analysis_summary.csv", index=False)
        self.loop_performance.to_csv(
            directory / "analysis_loop_performance.csv", index=False
        )
        self.stability_summary.to_csv(
            directory / "analysis_stability_summary.csv", index=False
        )
        self.trend_summary.to_csv(
            directory / "analysis_trend_summary.csv", index=False
        )
        self.channel_comparison.to_csv(
            directory / "analysis_channel_comparison.csv", index=False
        )
        self.hypothesis_tests.to_csv(
            directory / "analysis_hypothesis_tests.csv", index=False
        )
        self.extremes.to_csv(directory / "analysis_extremes.csv", index=False)
        (directory / "analysis_trend_report.txt").write_text(
            "\n".join(self.trend_report) + "\n",
            encoding="utf-8",
        )
        (directory / "analysis_comparison_report.txt").write_text(
            "\n".join(self.comparison_report) + "\n",
            encoding="utf-8",
        )


def _empty_result(
    message="No completed realtime measurement data found.",
    practical_difference_threshold_percent=(
        PRACTICAL_DIFFERENCE_THRESHOLD_PERCENT
    ),
):
    empty = pd.DataFrame()
    return BundleAnalysisResult(
        empty,
        empty,
        empty,
        empty,
        empty,
        empty,
        empty,
        empty,
        empty,
        (message,),
        (message,),
        (message,),
        _methodology(practical_difference_threshold_percent),
        practical_difference_threshold_percent,
    )


def _load_metadata(raw_directory):
    path = raw_directory / "parameters.json"
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return {}


def _positive_integer(value, default=1):
    try:
        return max(1, int(float(value)))
    except (TypeError, ValueError):
        return default


def _channel_label(value):
    if isinstance(value, (list, tuple, set)):
        values = list(value)
        if len(values) == 1:
            return values[0]
        return ", ".join(str(item) for item in values)
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "Unknown"
    text = str(value).strip()
    if text.startswith("[") and text.endswith("]"):
        try:
            return _channel_label(json.loads(text))
        except (ValueError, TypeError):
            pass
    return value if not isinstance(value, str) else text


def _infer_loops(row_count, loop_count):
    if row_count <= 0:
        return []
    points_per_loop = max(1, math.ceil(row_count / loop_count))
    return [
        min(index // points_per_loop + 1, loop_count)
        for index in range(row_count)
    ]


def _discover_realtime_files(output_root):
    output_root = Path(output_root)
    if not output_root.exists():
        return []
    return sorted(output_root.rglob("raw/realtime_voltage_data_*.csv"))


def _discover_voltage_reports(output_root):
    output_root = Path(output_root)
    if not output_root.exists():
        return []
    return sorted(output_root.rglob("reports/VOLTAGE_*.xlsx"))


def _analysis_roots(output_root):
    if isinstance(output_root, (str, Path)):
        candidates = (output_root,)
    else:
        candidates = tuple(output_root or ())
    roots = []
    seen = set()
    for candidate in candidates:
        path = Path(candidate)
        identity = path.resolve()
        if identity in seen:
            continue
        seen.add(identity)
        roots.append(path)
    return tuple(roots)


def _discover_across_roots(roots, discover):
    discovered = {}
    for root in roots:
        for path in discover(root):
            discovered[path.resolve()] = path
    return sorted(discovered.values())


def _path_integer(path, pattern, default):
    for part in reversed(Path(path).parts):
        match = re.search(pattern, part, re.IGNORECASE)
        if match:
            return _positive_integer(match.group(1), default)
    return default


def _report_observations(report_path):
    try:
        frame = pd.read_excel(
            report_path,
            sheet_name="Data",
            header=7,
            usecols="D:T",
        )
    except (OSError, ValueError, ImportError):
        return pd.DataFrame()
    if frame.empty or len(frame.columns) < len(REPORT_COLUMNS):
        return pd.DataFrame()
    frame = frame.iloc[:, : len(REPORT_COLUMNS)].copy()
    frame.columns = REPORT_COLUMNS
    numeric_columns = (
        "Set_Voltage",
        "Set_Current",
        "Readback_Voltage",
        "Readback_Current",
        "Programming_Voltage",
        "Programming_Voltage_Error",
        "Readback_Voltage_Error",
        "Programming_Upper_Limit_Boundary",
        "Programming_Lower_Limit_Boundary",
        "Readback_Upper_Limit_Boundary",
        "Readback_lower_Limit_Boundary",
    )
    for column in numeric_columns:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    frame = frame.dropna(
        subset=(
            "Set_Voltage",
            "Set_Current",
            "Programming_Voltage_Error",
            "Readback_Voltage_Error",
        )
    ).reset_index(drop=True)
    if frame.empty:
        return frame

    report_path = Path(report_path)
    run_directory = report_path.parent.parent
    channel = _path_integer(run_directory, r"channel[_ -]?(\d+)", 1)
    loop_count = _path_integer(run_directory, r"(\d+)[_ -]?loop", 1)
    frame.insert(0, "Index", range(1, len(frame) + 1))
    frame.insert(1, "Loop", _infer_loops(len(frame), loop_count))
    frame.insert(2, "Channel", channel)
    frame["Percentage_Upper_Limit_Boundary"] = 100.0
    frame["Percentage_Lower_Limit_Boundary"] = -100.0
    frame["Run"] = run_directory.name
    frame["DUT"] = "Hornbill"
    frame["Test"] = "VOLTAGE"
    frame["Source"] = "Excel report fallback"
    return frame


def _load_observations(output_root):
    frames = []
    roots = _analysis_roots(output_root)
    realtime_files = _discover_across_roots(
        roots,
        _discover_realtime_files,
    )
    covered_run_directories = {
        csv_path.parent.parent.resolve() for csv_path in realtime_files
    }
    for csv_path in realtime_files:
        try:
            frame = pd.read_csv(csv_path)
        except (OSError, ValueError, pd.errors.EmptyDataError):
            continue
        if frame.empty:
            continue

        raw_directory = csv_path.parent
        run_directory = raw_directory.parent
        metadata = _load_metadata(raw_directory)
        channel = _channel_label(metadata.get("PSU_Channel"))
        loop_count = _positive_integer(metadata.get("noofloop"), 1)
        if "Loop" not in frame.columns:
            frame["Loop"] = _infer_loops(len(frame), loop_count)
        else:
            frame["Loop"] = pd.to_numeric(
                frame["Loop"], errors="coerce"
            ).fillna(1)
        if "Channel" not in frame.columns:
            frame["Channel"] = channel
        else:
            frame["Channel"] = frame["Channel"].map(
                lambda value: (
                    channel
                    if _channel_label(value) == "Unknown"
                    else _channel_label(value)
                )
            )

        frame["Run"] = run_directory.name
        frame["DUT"] = (
            metadata.get("DUT") or metadata.get("selected_DUT") or "Unknown"
        )
        frame["Test"] = metadata.get("unit") or "Unknown"
        frame["Source"] = "Realtime CSV"
        frames.append(frame)

    report_files = _discover_across_roots(
        roots,
        _discover_voltage_reports,
    )
    for report_path in report_files:
        if report_path.parent.parent.resolve() in covered_run_directories:
            continue
        report_frame = _report_observations(report_path)
        if not report_frame.empty:
            frames.append(report_frame)

    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True, sort=False)


def _normalized_error(error, upper, lower):
    allowed = upper if error >= 0 else abs(lower)
    if allowed <= 0:
        return math.nan
    return error / allowed * 100.0


def _long_errors(observations):
    records = []
    identity_columns = (
        "Run",
        "DUT",
        "Test",
        "Channel",
        "Loop",
        "Index",
        "Set_Voltage",
        "Set_Current",
    )
    for metric, error_column, upper_column, lower_column in METRICS:
        required = {error_column, upper_column, lower_column}
        if not required.issubset(observations.columns):
            continue
        for _, row in observations.iterrows():
            try:
                error = float(row[error_column])
                upper = float(row[upper_column])
                lower = float(row[lower_column])
            except (TypeError, ValueError):
                continue
            if not all(math.isfinite(value) for value in (error, upper, lower)):
                continue
            normalized = _normalized_error(error, upper, lower)
            record = {column: row.get(column) for column in identity_columns}
            record.update(
                Metric=metric,
                **{
                    "Set Voltage (V)": row.get("Set_Voltage"),
                    "Set Current (A)": row.get("Set_Current"),
                },
                Error=error,
                Absolute_Error=abs(error),
                Upper_Limit=upper,
                Lower_Limit=lower,
                Normalized_Error_Percent=normalized,
                Margin_Remaining_Percent=(
                    100.0 - abs(normalized)
                    if math.isfinite(normalized)
                    else math.nan
                ),
                Passed=lower <= error <= upper,
            )
            records.append(record)
    return pd.DataFrame(records)


def _sample_std(series):
    return float(series.std(ddof=1)) if len(series) > 1 else 0.0


def _median_absolute_deviation(series):
    median = float(series.median())
    return float((series - median).abs().median())


def _t_critical(sample_count, confidence):
    if sample_count < 2:
        return math.nan
    table = T_CRITICAL_95 if confidence == 0.95 else T_CRITICAL_90
    degrees_freedom = sample_count - 1
    if degrees_freedom < len(table):
        return table[degrees_freedom]
    return 1.960 if confidence == 0.95 else 1.645


def _confidence_interval(errors, confidence):
    sample_count = len(errors)
    mean = float(errors.mean())
    if sample_count < 2:
        return math.nan, math.nan
    standard_error = _sample_std(errors) / math.sqrt(sample_count)
    half_width = _t_critical(sample_count, confidence) * standard_error
    return mean - half_width, mean + half_width


def _strict_limits(group):
    return (
        float(group["Lower_Limit"].max()),
        float(group["Upper_Limit"].min()),
    )


def _compliance_conclusion(
    sample_count,
    pass_rate,
    equivalent,
    estimated_lower,
    estimated_upper,
    lower_limit,
    upper_limit,
):
    if pass_rate < 100.0:
        return "FAIL - observed point exceeded limit"
    if sample_count < 2:
        return "PASS - repeatability not established"
    if sample_count < MIN_INFERENCE_SAMPLES:
        return "PASS - compliant; statistics preliminary (n<5)"
    if not equivalent:
        return "MARGINAL - mean equivalence not demonstrated"
    if estimated_lower < lower_limit or estimated_upper > upper_limit:
        return "MARGINAL - estimated spread approaches limit"
    return "PASS - compliant and statistically stable"


def _statistics(group):
    errors = group["Error"].astype(float)
    absolute_errors = errors.abs()
    normalized = group["Normalized_Error_Percent"].astype(float).abs()
    lower_limit, upper_limit = _strict_limits(group)
    ci95_lower, ci95_upper = _confidence_interval(errors, 0.95)
    ci90_lower, ci90_upper = _confidence_interval(errors, 0.90)
    sample_count = len(group)
    standard_deviation = _sample_std(errors)
    mean_error = float(errors.mean())
    pass_rate = float(group["Passed"].mean() * 100.0)
    equivalent = (
        sample_count > 1
        and ci90_lower >= lower_limit
        and ci90_upper <= upper_limit
    )
    bias_detected = (
        sample_count > 1
        and (ci95_lower > 0.0 or ci95_upper < 0.0)
    )
    estimated_lower = mean_error - 2.0 * standard_deviation
    estimated_upper = mean_error + 2.0 * standard_deviation
    return {
        "Samples": int(sample_count),
        "Loops": int(group["Loop"].nunique()),
        "Lower Limit": lower_limit,
        "Upper Limit": upper_limit,
        "Mean Error": mean_error,
        "Std Dev": standard_deviation,
        "Standard Error": (
            standard_deviation / math.sqrt(sample_count)
            if sample_count
            else math.nan
        ),
        "95% CI Lower": ci95_lower,
        "95% CI Upper": ci95_upper,
        "Median Error": float(errors.median()),
        "MAD": _median_absolute_deviation(errors),
        "Minimum Error": float(errors.min()),
        "Maximum Error": float(errors.max()),
        "MAE": float(absolute_errors.mean()),
        "RMSE": float((errors.pow(2).mean()) ** 0.5),
        "P95 Absolute Error": float(absolute_errors.quantile(0.95)),
        "Maximum Absolute Error": float(absolute_errors.max()),
        "Maximum Limit Usage (%)": float(normalized.max()),
        "Minimum Margin Remaining (%)": float(
            group["Margin_Remaining_Percent"].min()
        ),
        "Pass Rate (%)": pass_rate,
        "Bias Detected (95% CI)": (
            "Yes" if bias_detected else "No" if sample_count > 1 else "N/A"
        ),
        "Mean Equivalent to Limits": (
            "Yes" if equivalent else "No" if sample_count > 1 else "N/A"
        ),
        "Estimated Spread Lower (Mean-2σ)": estimated_lower,
        "Estimated Spread Upper (Mean+2σ)": estimated_upper,
        "Compliance Conclusion": _compliance_conclusion(
            sample_count,
            pass_rate,
            equivalent,
            estimated_lower,
            estimated_upper,
            lower_limit,
            upper_limit,
        ),
    }


def _group_statistics(errors, group_columns):
    rows = []
    for keys, group in errors.groupby(
        group_columns, dropna=False, sort=False
    ):
        if not isinstance(keys, tuple):
            keys = (keys,)
        row = dict(zip(group_columns, keys))
        row.update(_statistics(group))
        rows.append(row)
    return pd.DataFrame(rows)


def _linear_slope(x_values, y_values):
    x_values = pd.Series(x_values, dtype="float64")
    y_values = pd.Series(y_values, dtype="float64")
    if len(x_values) < 2:
        return 0.0
    centered_x = x_values - x_values.mean()
    denominator = float(centered_x.pow(2).sum())
    if denominator <= 0:
        return 0.0
    return float(
        (centered_x * (y_values - y_values.mean())).sum() / denominator
    )


def _stability_window_metrics(window):
    means = window["Mean Error"].astype(float)
    lower_limit = float(window["Lower Limit"].max())
    upper_limit = float(window["Upper Limit"].min())
    practical_limit = min(abs(lower_limit), abs(upper_limit))
    span = float(means.max() - means.min())
    standard_deviation = _sample_std(means)
    slope = _linear_slope(window["Loop"], means)
    if practical_limit > 0:
        span_usage = span / practical_limit * 100.0
        standard_deviation_usage = (
            standard_deviation / practical_limit * 100.0
        )
        drift_usage = abs(slope) / practical_limit * 100.0
    else:
        span_usage = math.nan
        standard_deviation_usage = math.nan
        drift_usage = math.nan
    loop_numbers = window["Loop"].astype(int).tolist()
    consecutive = all(
        current == previous + 1
        for previous, current in zip(loop_numbers, loop_numbers[1:])
    )
    all_points_pass = bool((window["Pass Rate (%)"] >= 100.0).all())
    stable = (
        len(window) >= MIN_STABILITY_CONFIRMATION_LOOPS
        and consecutive
        and all_points_pass
        and math.isfinite(span_usage)
        and span_usage <= STABILITY_SPAN_THRESHOLD_PERCENT
        and standard_deviation_usage <= STABILITY_STD_THRESHOLD_PERCENT
        and drift_usage <= STABILITY_DRIFT_THRESHOLD_PERCENT_PER_LOOP
    )
    return {
        "stable": stable,
        "consecutive": consecutive,
        "all_points_pass": all_points_pass,
        "practical_limit": practical_limit,
        "mean_error": float(means.mean()),
        "span": span,
        "span_usage": span_usage,
        "standard_deviation": standard_deviation,
        "standard_deviation_usage": standard_deviation_usage,
        "slope": slope,
        "drift_usage": drift_usage,
    }


def _stability_failure_reason(metrics, loop_count):
    reasons = []
    if loop_count < MIN_STABILITY_CONFIRMATION_LOOPS:
        return (
            f"Need at least {MIN_STABILITY_CONFIRMATION_LOOPS} loops; "
            f"only {loop_count} available"
        )
    if not metrics["consecutive"]:
        reasons.append("loop numbers are not consecutive")
    if not metrics["all_points_pass"]:
        reasons.append("one or more points failed")
    if not math.isfinite(metrics["span_usage"]):
        reasons.append("engineering limit is unavailable")
    elif metrics["span_usage"] > STABILITY_SPAN_THRESHOLD_PERCENT:
        reasons.append("loop-mean span exceeds threshold")
    if (
        math.isfinite(metrics["standard_deviation_usage"])
        and metrics["standard_deviation_usage"]
        > STABILITY_STD_THRESHOLD_PERCENT
    ):
        reasons.append("loop-mean standard deviation exceeds threshold")
    if (
        math.isfinite(metrics["drift_usage"])
        and metrics["drift_usage"]
        > STABILITY_DRIFT_THRESHOLD_PERCENT_PER_LOOP
    ):
        reasons.append("linear drift exceeds threshold")
    return "; ".join(reasons) or "stability criteria were not satisfied"


def _stability_summary(loop_performance):
    if loop_performance.empty:
        return pd.DataFrame()
    rows = []
    group_columns = [
        "Run",
        "DUT",
        "Test",
        "Channel",
        *CONDITION_COLUMNS,
        "Metric",
    ]
    for keys, source in loop_performance.groupby(
        group_columns,
        dropna=False,
        sort=False,
    ):
        ordered = (
            source.sort_values("Loop")
            .drop_duplicates(subset=["Loop"], keep="last")
            .reset_index(drop=True)
        )
        selected_window = None
        selected_metrics = None
        for start_index in range(
            0,
            max(
                0,
                len(ordered) - MIN_STABILITY_CONFIRMATION_LOOPS + 1,
            ),
        ):
            candidate = ordered.iloc[start_index:].copy()
            metrics = _stability_window_metrics(candidate)
            if metrics["stable"]:
                selected_window = candidate
                selected_metrics = metrics
                break
        stable = selected_window is not None
        if not stable:
            selected_window = ordered.tail(
                min(len(ordered), MIN_STABILITY_CONFIRMATION_LOOPS)
            ).copy()
            selected_metrics = _stability_window_metrics(selected_window)
        stable_from_loop = (
            int(selected_window.iloc[0]["Loop"]) if stable else None
        )
        confirmed_at_loop = (
            int(
                selected_window.iloc[
                    MIN_STABILITY_CONFIRMATION_LOOPS - 1
                ]["Loop"]
            )
            if stable
            else None
        )
        rows.append(
            {
                **dict(zip(group_columns, keys)),
                "Total Loops": int(ordered["Loop"].nunique()),
                "Stability Reached": "Yes" if stable else "No",
                "Stable From Loop": stable_from_loop,
                "Confirmed At Loop": confirmed_at_loop,
                "Stable / Evaluated Loops": int(len(selected_window)),
                "Mean Error": selected_metrics["mean_error"],
                "Loop Mean Span": selected_metrics["span"],
                "Span Limit Usage (%)": selected_metrics["span_usage"],
                "Loop Mean Std Dev": selected_metrics[
                    "standard_deviation"
                ],
                "Std Dev Limit Usage (%)": selected_metrics[
                    "standard_deviation_usage"
                ],
                "Linear Drift per Loop": selected_metrics["slope"],
                "Drift Limit Usage (%/loop)": selected_metrics[
                    "drift_usage"
                ],
                "All Points Pass": (
                    "Yes" if selected_metrics["all_points_pass"] else "No"
                ),
                "Required Confirmation Loops": (
                    MIN_STABILITY_CONFIRMATION_LOOPS
                ),
                "Span Threshold (%)": STABILITY_SPAN_THRESHOLD_PERCENT,
                "Std Dev Threshold (%)": STABILITY_STD_THRESHOLD_PERCENT,
                "Drift Threshold (%/loop)": (
                    STABILITY_DRIFT_THRESHOLD_PERCENT_PER_LOOP
                ),
                "Conclusion": (
                    f"Stable from loop {stable_from_loop}; confirmed after "
                    f"loop {confirmed_at_loop}"
                    if stable
                    else "Not stable: "
                    + _stability_failure_reason(
                        selected_metrics,
                        len(ordered),
                    )
                ),
            }
        )
    return pd.DataFrame(rows)


def _robust_outlier_loops(loop_numbers, values):
    values = pd.Series(values, dtype="float64").reset_index(drop=True)
    loop_numbers = pd.Series(loop_numbers).reset_index(drop=True)
    if len(values) < 3:
        return []
    median = float(values.median())
    mad = float((values - median).abs().median())
    if mad <= 0:
        return []
    robust_z = 0.6745 * (values - median).abs() / mad
    return [
        int(loop_numbers.iloc[index])
        for index in robust_z.index[robust_z > TREND_OUTLIER_ROBUST_Z]
    ]


def _oscillation_classification(values):
    differences = pd.Series(values, dtype="float64").diff().dropna()
    signs = [
        1 if value > 0 else -1
        for value in differences
        if abs(value) > 1e-15
    ]
    if len(signs) < 2:
        return "Insufficient changes", 0.0
    reversals = sum(
        current != previous
        for previous, current in zip(signs, signs[1:])
    )
    reversal_rate = reversals / (len(signs) - 1) * 100.0
    if reversal_rate >= 60.0:
        classification = "Oscillating"
    elif reversal_rate <= 20.0:
        classification = "Mostly monotonic"
    else:
        classification = "Mixed movement"
    return classification, reversal_rate


def _confidence_label(sample_count):
    if sample_count < 2:
        return "Insufficient"
    if sample_count < 3:
        return "Low"
    if sample_count < MIN_INFERENCE_SAMPLES:
        return "Medium"
    return "High"


def _individual_engineering_conclusion(row):
    loops = int(row["Total Loops"])
    late_usage = float(row["Late Mean Limit Usage (%)"])
    drift_usage = float(row["Drift Limit Usage (%/loop)"])
    movement = row["Movement Relative to Zero"]
    unstable = row["Stability Reached"] != "Yes"
    jumps = int(row["Sudden Jump Count"])
    outliers = int(row["Robust Outlier Count"])

    if loops < 2:
        status = "Insufficient Data"
        finding = "Only one loop is available, so repeatability is unknown."
        action = "Collect at least two loops before evaluating the trend."
    elif math.isfinite(late_usage) and late_usage >= 100.0:
        status = "Fail"
        finding = "The latest mean error reached or exceeded its limit."
        action = (
            "Inspect the DUT, wiring, range, and instruments before repeating "
            "this condition."
        )
    elif (
        (math.isfinite(late_usage) and late_usage >= TREND_NEAR_BOUNDARY_PERCENT)
        or movement == "Moving away from zero"
        or jumps
        or outliers
        or unstable
    ):
        status = "Warning"
        reasons = []
        if late_usage >= TREND_NEAR_BOUNDARY_PERCENT:
            reasons.append("latest error is near the limit")
        if movement == "Moving away from zero":
            reasons.append("error magnitude is worsening")
        if jumps:
            reasons.append(f"{jumps} sudden jump(s) occurred")
        if outliers:
            reasons.append(f"{outliers} outlier loop(s) occurred")
        if unstable:
            reasons.append("stability was not demonstrated")
        finding = "; ".join(reasons).capitalize() + "."
        action = (
            "Review the highlighted loops and repeat the condition after "
            "checking connections, settling time, and instrument range."
        )
    else:
        status = "Pass"
        finding = "The loop trend is within limits without a major warning."
        action = "No immediate action; retain the result for traceability."

    confidence = _confidence_label(loops)
    magnitude = (
        f"Latest mean uses {late_usage:.2f}% of the strict limit; drift uses "
        f"{drift_usage:.2f}% of the limit per loop."
    )
    return status, finding, magnitude, confidence, action


def _trend_narrative(row):
    condition = (
        f"{row['Set Voltage (V)']:.6g} V / "
        f"{row['Set Current (A)']:.6g} A"
    )
    movement_text = {
        "Moving away from zero": "is moving away from zero",
        "Moving toward zero": "is moving toward zero",
        "No meaningful magnitude change": "shows no meaningful change",
        "Unavailable": "could not be evaluated",
    }.get(
        row["Movement Relative to Zero"],
        str(row["Movement Relative to Zero"]).lower(),
    )
    narrative = (
        f"[{row['Status']}] {row['Metric']} on Channel {row['Channel']} at "
        f"{condition}. Finding: {row['Finding']} "
        f"Magnitude: {row['Magnitude']} Confidence: {row['Confidence']}. "
        f"Action: {row['Recommended Action']} Technical detail: "
        f"signed error trend is {row['Trend Direction'].lower()} "
        f"({row['Linear Slope per Loop']:+.6g} per loop, "
        f"{row['Drift Limit Usage (%/loop)']:.3f}% of limit per loop). "
        f"The final-window mean is {row['Late Mean Error']:+.6g}, compared "
        f"with {row['Early Mean Error']:+.6g} initially; error magnitude "
        f"{movement_text}. "
        f"Boundary behavior is {row['Boundary Direction'].lower()}."
    )
    if row["Sudden Jump Count"]:
        narrative += (
            f" {int(row['Sudden Jump Count'])} sudden jump(s) were detected; "
            f"the largest was {row['Maximum Jump']:.6g} entering loop "
            f"{int(row['Maximum Jump At Loop'])}."
        )
    if row["Robust Outlier Count"]:
        narrative += (
            f" Robust outlier loop(s): {row['Robust Outlier Loops']}."
        )
    narrative += (
        f" Pattern: {row['Movement Pattern'].lower()}. "
        f"Stability: {row['Stability Conclusion']}."
    )
    return narrative


def _trend_summary(loop_performance, stability_summary):
    if loop_performance.empty:
        return pd.DataFrame()
    group_columns = [
        "Run",
        "DUT",
        "Test",
        "Channel",
        *CONDITION_COLUMNS,
        "Metric",
    ]
    stability_lookup = {}
    if not stability_summary.empty:
        for _, row in stability_summary.iterrows():
            stability_lookup[
                tuple(row[column] for column in group_columns)
            ] = row
    rows = []
    for keys, source in loop_performance.groupby(
        group_columns,
        dropna=False,
        sort=False,
    ):
        if not isinstance(keys, tuple):
            keys = (keys,)
        ordered = (
            source.sort_values("Loop")
            .drop_duplicates(subset=["Loop"], keep="last")
            .reset_index(drop=True)
        )
        loops = ordered["Loop"].astype(float)
        means = ordered["Mean Error"].astype(float)
        lower_limit = float(ordered["Lower Limit"].max())
        upper_limit = float(ordered["Upper Limit"].min())
        practical_limit = min(abs(lower_limit), abs(upper_limit))
        slope = _linear_slope(loops, means)
        drift_usage = (
            abs(slope) / practical_limit * 100.0
            if practical_limit > 0
            else math.nan
        )
        if not math.isfinite(drift_usage):
            trend_direction = "Unavailable"
        elif drift_usage <= TREND_FLAT_THRESHOLD_PERCENT_PER_LOOP:
            trend_direction = "Flat"
        elif slope > 0:
            trend_direction = "Increasing"
        else:
            trend_direction = "Decreasing"

        window_size = max(1, min(3, len(ordered) // 2))
        early_mean = float(means.head(window_size).mean())
        late_mean = float(means.tail(window_size).mean())
        early_late_change = late_mean - early_mean
        change_usage = (
            early_late_change / practical_limit * 100.0
            if practical_limit > 0
            else math.nan
        )
        magnitude_change_usage = (
            (abs(late_mean) - abs(early_mean)) / practical_limit * 100.0
            if practical_limit > 0
            else math.nan
        )
        if not math.isfinite(magnitude_change_usage):
            movement_zero = "Unavailable"
        elif magnitude_change_usage > TREND_MEANINGFUL_SHIFT_PERCENT:
            movement_zero = "Moving away from zero"
        elif magnitude_change_usage < -TREND_MEANINGFUL_SHIFT_PERCENT:
            movement_zero = "Moving toward zero"
        else:
            movement_zero = "No meaningful magnitude change"

        late_limit_usage = (
            abs(late_mean) / practical_limit * 100.0
            if practical_limit > 0
            else math.nan
        )
        if not math.isfinite(late_limit_usage):
            boundary_direction = "Unavailable"
        elif late_limit_usage >= TREND_NEAR_BOUNDARY_PERCENT:
            boundary_direction = "Near or beyond boundary"
        elif magnitude_change_usage > TREND_MEANINGFUL_SHIFT_PERCENT:
            boundary_direction = "Approaching boundary"
        elif magnitude_change_usage < -TREND_MEANINGFUL_SHIFT_PERCENT:
            boundary_direction = "Moving away from boundary"
        else:
            boundary_direction = "No meaningful boundary movement"

        absolute_differences = means.diff().abs()
        jump_usage = (
            absolute_differences / practical_limit * 100.0
            if practical_limit > 0
            else pd.Series(math.nan, index=ordered.index)
        )
        jump_mask = jump_usage >= TREND_JUMP_THRESHOLD_PERCENT
        jump_count = int(jump_mask.fillna(False).sum())
        if absolute_differences.dropna().empty:
            maximum_jump = 0.0
            maximum_jump_loop = None
            maximum_jump_usage = 0.0
        else:
            maximum_jump_index = absolute_differences.idxmax()
            maximum_jump = float(absolute_differences.loc[maximum_jump_index])
            maximum_jump_loop = int(
                ordered.loc[maximum_jump_index, "Loop"]
            )
            maximum_jump_usage = float(
                jump_usage.loc[maximum_jump_index]
            )
        outlier_loops = _robust_outlier_loops(loops, means)
        movement_pattern, reversal_rate = _oscillation_classification(means)
        stability = stability_lookup.get(keys)
        stability_reached = (
            stability is not None
            and stability["Stability Reached"] == "Yes"
        )
        if stability_reached:
            stability_conclusion = (
                f"stable from loop {int(stability['Stable From Loop'])}, "
                f"confirmed at loop {int(stability['Confirmed At Loop'])}"
            )
        elif stability is not None:
            stability_conclusion = str(stability["Conclusion"])
        else:
            stability_conclusion = "not evaluated"
        priority_score = (
            (late_limit_usage if math.isfinite(late_limit_usage) else 0.0)
            + (drift_usage if math.isfinite(drift_usage) else 0.0) * 5.0
            + jump_count * 10.0
            + len(outlier_loops) * 10.0
            + (20.0 if not stability_reached else 0.0)
            + (
                10.0
                if movement_zero == "Moving away from zero"
                else 0.0
            )
        )
        row = {
            **dict(zip(group_columns, keys)),
            "Total Loops": int(ordered["Loop"].nunique()),
            "Early Window Loops": window_size,
            "Early Mean Error": early_mean,
            "Late Mean Error": late_mean,
            "Early-to-Late Change": early_late_change,
            "Early-to-Late Change Limit Usage (%)": change_usage,
            "Error Magnitude Change Limit Usage (%)": (
                magnitude_change_usage
            ),
            "Linear Slope per Loop": slope,
            "Drift Limit Usage (%/loop)": drift_usage,
            "Trend Direction": trend_direction,
            "Movement Relative to Zero": movement_zero,
            "Late Mean Limit Usage (%)": late_limit_usage,
            "Boundary Direction": boundary_direction,
            "Movement Pattern": movement_pattern,
            "Direction Reversal Rate (%)": reversal_rate,
            "Sudden Jump Count": jump_count,
            "Maximum Jump": maximum_jump,
            "Maximum Jump Limit Usage (%)": maximum_jump_usage,
            "Maximum Jump At Loop": maximum_jump_loop,
            "Robust Outlier Count": len(outlier_loops),
            "Robust Outlier Loops": (
                ", ".join(str(loop) for loop in outlier_loops)
                if outlier_loops
                else "None"
            ),
            "Stability Reached": "Yes" if stability_reached else "No",
            "Stable From Loop": (
                stability["Stable From Loop"]
                if stability is not None
                else None
            ),
            "Confirmed At Loop": (
                stability["Confirmed At Loop"]
                if stability is not None
                else None
            ),
            "Stability Conclusion": stability_conclusion,
            "Priority Score": priority_score,
        }
        (
            row["Status"],
            row["Finding"],
            row["Magnitude"],
            row["Confidence"],
            row["Recommended Action"],
        ) = _individual_engineering_conclusion(row)
        row["Narrative"] = _trend_narrative(row)
        rows.append(row)
    return pd.DataFrame(rows)


def _trend_report(trend_summary):
    if trend_summary.empty:
        return ("No loop trend data is available.",)
    total = len(trend_summary)
    direction_counts = trend_summary["Trend Direction"].value_counts()
    stable_count = int(
        (trend_summary["Stability Reached"] == "Yes").sum()
    )
    away_count = int(
        (
            trend_summary["Movement Relative to Zero"]
            == "Moving away from zero"
        ).sum()
    )
    approaching_count = int(
        trend_summary["Boundary Direction"].isin(
            ["Approaching boundary", "Near or beyond boundary"]
        ).sum()
    )
    jump_count = int((trend_summary["Sudden Jump Count"] > 0).sum())
    outlier_count = int((trend_summary["Robust Outlier Count"] > 0).sum())
    status_counts = trend_summary["Status"].value_counts()
    report = [
        "Executive summary: "
        f"{int(status_counts.get('Pass', 0))} pass, "
        f"{int(status_counts.get('Warning', 0))} warning, "
        f"{int(status_counts.get('Fail', 0))} fail, and "
        f"{int(status_counts.get('Insufficient Data', 0))} insufficient-data "
        "condition/metric series.",
        f"Analyzed {total} condition/metric loop series.",
        "Signed trend directions: "
        f"{int(direction_counts.get('Increasing', 0))} increasing, "
        f"{int(direction_counts.get('Decreasing', 0))} decreasing, "
        f"{int(direction_counts.get('Flat', 0))} flat.",
        f"Stability was reached by {stable_count} of {total} series.",
        f"{away_count} series moved meaningfully away from zero; "
        f"{approaching_count} approached or reached an engineering boundary.",
        f"{jump_count} series contained sudden jumps and {outlier_count} "
        "contained robust outlier loops.",
        "Increasing or decreasing describes signed error direction. Use "
        "'Movement Relative to Zero' to determine whether magnitude improved "
        "or worsened.",
    ]
    priority = trend_summary.sort_values(
        "Priority Score",
        ascending=False,
    ).head(min(10, total))
    report.append("Highest-priority findings:")
    report.extend(
        f"{index}. {row['Narrative']}"
        for index, (_, row) in enumerate(priority.iterrows(), start=1)
    )
    return tuple(report)


def _hypothesis_assessments(summary):
    rows = []
    identity_columns = (
        "DUT",
        "Test",
        "Channel",
        *CONDITION_COLUMNS,
        "Metric",
    )
    for _, source in summary.iterrows():
        identity = {column: source[column] for column in identity_columns}
        samples = int(source["Samples"])
        if samples < 2:
            bias_result = "Insufficient repeated samples"
            equivalence_result = "Insufficient repeated samples"
        else:
            bias_result = (
                "Bias detected"
                if source["Bias Detected (95% CI)"] == "Yes"
                else "No significant bias detected"
            )
            equivalence_result = (
                "Mean equivalent within limits"
                if source["Mean Equivalent to Limits"] == "Yes"
                else "Mean equivalence not demonstrated"
            )
            if samples < MIN_INFERENCE_SAMPLES:
                bias_result += " (preliminary; n<5)"
                equivalence_result += " (preliminary; n<5)"
        rows.append(
            {
                **identity,
                "Assessment": "Bias assessment",
                "Null Hypothesis": "Mean error = 0",
                "Interval": (
                    f"[{source['95% CI Lower']:.6g}, "
                    f"{source['95% CI Upper']:.6g}]"
                    if samples > 1
                    else "N/A"
                ),
                "Engineering Margin": "0",
                "Result": bias_result,
                "Interpretation": (
                    "Detects systematic offset; it does not determine "
                    "specification compliance."
                ),
            }
        )
        rows.append(
            {
                **identity,
                "Assessment": "Mean equivalence (TOST via 90% CI)",
                "Null Hypothesis": "Mean error is outside allowed limits",
                "Interval": (
                    f"[{_confidence_value(source, '90% CI Lower')}, "
                    f"{_confidence_value(source, '90% CI Upper')}]"
                ),
                "Engineering Margin": (
                    f"[{source['Lower Limit']:.6g}, "
                    f"{source['Upper Limit']:.6g}]"
                ),
                "Result": equivalence_result,
                "Interpretation": (
                    "Supports mean equivalence only; every measured point "
                    "must still pass its boundary."
                ),
            }
        )
    return pd.DataFrame(rows)


def _confidence_value(source, column):
    value = source.get(column)
    if value is None or pd.isna(value):
        return "N/A"
    return f"{float(value):.6g}"


def _add_90_percent_intervals(summary, errors):
    if summary.empty:
        return summary
    group_columns = [
        "DUT",
        "Test",
        "Channel",
        *CONDITION_COLUMNS,
        "Metric",
    ]
    intervals = []
    for keys, group in errors.groupby(
        group_columns, dropna=False, sort=False
    ):
        if not isinstance(keys, tuple):
            keys = (keys,)
        lower, upper = _confidence_interval(group["Error"].astype(float), 0.90)
        intervals.append(
            {
                **dict(zip(group_columns, keys)),
                "90% CI Lower": lower,
                "90% CI Upper": upper,
            }
        )
    return summary.merge(
        pd.DataFrame(intervals),
        on=group_columns,
        how="left",
    )


def _comparison_engineering_conclusion(
    channel_a,
    channel_b,
    matched_loops,
    mean_difference,
    practical_usage,
    difference_detected,
    practical_difference,
    evidence_strength,
    subject_label="Channel",
):
    confidence = {
        "Supported": "High",
        "Preliminary": "Low",
        "Insufficient": "Insufficient",
    }[evidence_strength]
    if evidence_strength == "Insufficient":
        status = "Insufficient Data"
        finding = "Only one matched loop is available."
        action = "Collect at least two matched loops before comparing runs."
    elif (
        evidence_strength == "Supported"
        and difference_detected
        and practical_difference
    ):
        status = "Fail"
        finding = (
            "A repeatable difference is both statistically and practically "
            "meaningful."
        )
        action = (
            f"Investigate why {subject_label} {channel_a} and "
            f"{subject_label} {channel_b} "
            "behave differently, then repeat the matched condition."
        )
    elif difference_detected or practical_difference:
        status = "Warning"
        if difference_detected and practical_difference:
            finding = (
                "The observed offset is statistically and practically "
                "meaningful, but evidence is preliminary."
            )
        elif practical_difference:
            finding = (
                "The engineering difference is meaningful, but statistical "
                "support is not established."
            )
        else:
            finding = (
                "A statistical offset exists, but its engineering magnitude "
                "is small."
            )
        action = (
            "Collect at least five matched loops and check setup differences "
            "before making a DUT decision."
        )
    else:
        status = "Pass"
        finding = "No meaningful difference was detected between the runs."
        action = (
            "No immediate action; collect more matched loops if higher "
            "confidence is required."
        )
    magnitude = (
        f"A-B mean difference is {mean_difference:+.6g}, using "
        f"{practical_usage:.2f}% of the strict limit across "
        f"{matched_loops} matched loop(s)."
    )
    return status, finding, magnitude, confidence, action


def _channel_comparison(
    errors,
    practical_difference_threshold_percent,
    comparison_column="Channel",
    subject_label="Channel",
):
    rows = []
    group_columns = ["DUT", "Test", *CONDITION_COLUMNS, "Metric"]
    for keys, condition in errors.groupby(
        group_columns, dropna=False, sort=False
    ):
        subjects = list(condition[comparison_column].drop_duplicates())
        for channel_a, channel_b in combinations(subjects, 2):
            left_rows = condition.loc[condition[comparison_column] == channel_a]
            right_rows = condition.loc[condition[comparison_column] == channel_b]
            left = (
                left_rows
                .groupby("Loop", as_index=False)["Error"]
                .mean()
            )
            right = (
                right_rows
                .groupby("Loop", as_index=False)["Error"]
                .mean()
            )
            paired = left.merge(
                right,
                on="Loop",
                suffixes=("_A", "_B"),
            )
            if paired.empty:
                continue
            differences = paired["Error_A"] - paired["Error_B"]
            ci_lower, ci_upper = _confidence_interval(differences, 0.95)
            difference_detected = (
                len(differences) > 1
                and (ci_lower > 0.0 or ci_upper < 0.0)
            )
            if len(differences) < 2:
                evidence_strength = "Insufficient"
            elif len(differences) < MIN_INFERENCE_SAMPLES:
                evidence_strength = "Preliminary"
            else:
                evidence_strength = "Supported"
            correlation = None
            if (
                len(paired) > 1
                and paired["Error_A"].std(ddof=1) > 0
                and paired["Error_B"].std(ddof=1) > 0
            ):
                value = paired["Error_A"].corr(paired["Error_B"])
                if not pd.isna(value):
                    correlation = float(value)
            lower_limit, upper_limit = _strict_limits(condition)
            practical_limit = min(abs(lower_limit), abs(upper_limit))
            mean_difference = float(differences.mean())
            practical_usage = (
                abs(mean_difference) / practical_limit * 100.0
                if practical_limit > 0
                else math.nan
            )
            practical_difference = (
                math.isfinite(practical_usage)
                and practical_usage
                >= practical_difference_threshold_percent
            )
            if difference_detected and practical_difference:
                if evidence_strength == "Preliminary":
                    conclusion = (
                        "Preliminary statistically and practically meaningful "
                        "channel offset; collect at least 5 matched loops"
                    )
                else:
                    conclusion = (
                        "Statistically and practically meaningful channel offset"
                    )
            elif difference_detected:
                conclusion = (
                    "Statistical offset detected, but engineering magnitude "
                    "is below the practical threshold"
                )
            elif practical_difference:
                conclusion = (
                    "Practical difference observed, but statistical evidence "
                    "is not established"
                )
            elif evidence_strength == "Preliminary":
                conclusion = (
                    "No meaningful offset detected; collect at least 5 "
                    "matched loops"
                )
            else:
                conclusion = "No meaningful channel offset detected"
            if mean_difference > 0:
                direction = (
                    f"{subject_label} {channel_a} error is higher than "
                    f"{subject_label} {channel_b}"
                )
            elif mean_difference < 0:
                direction = (
                    f"{subject_label} {channel_a} error is lower than "
                    f"{subject_label} {channel_b}"
                )
            else:
                direction = f"Mean {subject_label.lower()} errors are equal"
            comparison_priority = (
                (practical_usage if math.isfinite(practical_usage) else 0.0)
                + (25.0 if difference_detected else 0.0)
                + (25.0 if practical_difference else 0.0)
                + (5.0 if evidence_strength == "Preliminary" else 0.0)
            )
            (
                status,
                finding,
                magnitude,
                confidence,
                recommended_action,
            ) = _comparison_engineering_conclusion(
                channel_a,
                channel_b,
                len(paired),
                mean_difference,
                practical_usage,
                difference_detected,
                practical_difference,
                evidence_strength,
                subject_label,
            )
            comparison_narrative = (
                f"[{status}] {keys[4]} at {keys[2]:.6g} V / "
                f"{keys[3]:.6g} A. {subject_label} {channel_a} minus "
                f"{subject_label} {channel_b}. Finding: {finding} "
                f"Magnitude: {magnitude} Confidence: {confidence}. "
                f"Action: {recommended_action} Technical detail: "
                f"{direction}. Statistical difference: "
                f"{'yes' if difference_detected else 'no'}; practical "
                f"difference: {'yes' if practical_difference else 'no'}; "
                f"{conclusion}."
            )
            rows.append(
                {
                    **dict(zip(group_columns, keys)),
                    "Comparison Basis": subject_label,
                    "Channel A": channel_a,
                    "Channel B": channel_b,
                    "DUT Channel A": ", ".join(
                        str(value) for value in left_rows["Channel"].drop_duplicates()
                    ),
                    "DUT Channel B": ", ".join(
                        str(value) for value in right_rows["Channel"].drop_duplicates()
                    ),
                    "Matched Loops": int(len(paired)),
                    "Mean Error A": float(paired["Error_A"].mean()),
                    "Mean Error B": float(paired["Error_B"].mean()),
                    "Mean Difference (A-B)": mean_difference,
                    "Std Dev Difference": _sample_std(differences),
                    "95% CI Difference Lower": ci_lower,
                    "95% CI Difference Upper": ci_upper,
                    "Difference Detected": (
                        "Yes"
                        if difference_detected
                        else "No" if len(differences) > 1 else "N/A"
                    ),
                    "Evidence Strength": evidence_strength,
                    "Difference Limit Usage (%)": practical_usage,
                    "Practical Threshold (%)": (
                        practical_difference_threshold_percent
                    ),
                    "Practically Meaningful": (
                        "Yes" if practical_difference else "No"
                    ),
                    "Matched Correlation": correlation,
                    "Engineering Limits": (
                        f"[{lower_limit:.6g}, {upper_limit:.6g}]"
                    ),
                    "Conclusion": conclusion,
                    "Status": status,
                    "Finding": finding,
                    "Magnitude": magnitude,
                    "Confidence": confidence,
                    "Recommended Action": recommended_action,
                    "Comparison Priority Score": comparison_priority,
                    "Comparison Narrative": comparison_narrative,
                }
            )
    return pd.DataFrame(rows)


def _comparison_report(channel_comparison):
    if channel_comparison.empty:
        return (
            "No matched channel/run conditions were available for comparison.",
            "Run A and Run B must share DUT, test, voltage, current, metric "
            "and loop conditions.",
        )
    total = len(channel_comparison)
    statistical = int(
        (channel_comparison["Difference Detected"] == "Yes").sum()
    )
    practical = int(
        (channel_comparison["Practically Meaningful"] == "Yes").sum()
    )
    both = int(
        (
            (channel_comparison["Difference Detected"] == "Yes")
            & (channel_comparison["Practically Meaningful"] == "Yes")
        ).sum()
    )
    preliminary = int(
        (channel_comparison["Evidence Strength"] == "Preliminary").sum()
    )
    comparison_basis = str(
        channel_comparison.get("Comparison Basis", pd.Series(["Channel"])).iloc[0]
    ).lower()
    status_counts = channel_comparison["Status"].value_counts()
    report = [
        "Executive summary: "
        f"{int(status_counts.get('Pass', 0))} pass, "
        f"{int(status_counts.get('Warning', 0))} warning, "
        f"{int(status_counts.get('Fail', 0))} fail, and "
        f"{int(status_counts.get('Insufficient Data', 0))} insufficient-data "
        "matched conditions.",
        f"Compared {total} matched voltage/current/metric conditions.",
        f"{statistical} conditions showed a statistical {comparison_basis} offset; "
        f"{practical} reached the practical-difference threshold; "
        f"{both} satisfied both criteria.",
        f"{preliminary} comparison conclusions are preliminary because they "
        "contain fewer than five matched loops.",
        "A statistical difference can be very small, while a practical "
        "difference may lack enough repeated loops for statistical support.",
        "Highest-priority comparison findings:",
    ]
    priority = channel_comparison.sort_values(
        "Comparison Priority Score",
        ascending=False,
    ).head(min(10, total))
    report.extend(
        f"{index}. {row['Comparison Narrative']}"
        for index, (_, row) in enumerate(priority.iterrows(), start=1)
    )
    return tuple(report)


def _extremes(errors):
    rows = []
    for (dut, test, channel, metric), group in errors.groupby(
        ["DUT", "Test", "Channel", "Metric"],
        dropna=False,
        sort=False,
    ):
        for label, index in (
            ("Minimum", group["Error"].idxmin()),
            ("Maximum", group["Error"].idxmax()),
            ("Maximum Absolute", group["Absolute_Error"].idxmax()),
        ):
            source = errors.loc[index]
            rows.append(
                {
                    "DUT": dut,
                    "Test": test,
                    "Channel": channel,
                    "Metric": metric,
                    "Extreme": label,
                    "Error": source["Error"],
                    "Limit Usage (%)": abs(
                        source["Normalized_Error_Percent"]
                    ),
                    "Passed": source["Passed"],
                    "Run": source["Run"],
                    "Loop": source["Loop"],
                    "Set Voltage (V)": source["Set Voltage (V)"],
                    "Set Current (A)": source["Set Current (A)"],
                }
            )
    return pd.DataFrame(rows)


def _insights(
    errors,
    summary,
    stability_summary,
    channel_comparison,
    practical_difference_threshold_percent,
):
    run_count = errors["Run"].nunique()
    sample_count = len(errors) // max(1, errors["Metric"].nunique())
    channels = tuple(errors["Channel"].drop_duplicates())
    messages = [
        f"Analyzed {sample_count} measurement points from {run_count} run(s), "
        f"{len(channels)} channel(s), and "
        f"{summary[list(CONDITION_COLUMNS)].drop_duplicates().shape[0]} "
        "voltage/current condition(s)."
    ]
    if not summary.empty:
        worst = summary.loc[summary["Maximum Limit Usage (%)"].idxmax()]
        messages.append(
            f"Worst limit usage: {worst['Maximum Limit Usage (%)']:.2f}% "
            f"at {worst['Set Voltage (V)']:.6g} V / "
            f"{worst['Set Current (A)']:.6g} A "
            f"({worst['Metric']}, channel {worst['Channel']})."
        )
        failed = summary.loc[summary["Pass Rate (%)"] < 100.0]
        marginal = summary.loc[
            summary["Compliance Conclusion"].str.startswith("MARGINAL")
        ]
        messages.append(
            f"Condition conclusions: {len(failed)} failed, "
            f"{len(marginal)} marginal, "
            f"{len(summary) - len(failed) - len(marginal)} passed."
        )
    if not stability_summary.empty:
        stable_rows = stability_summary.loc[
            stability_summary["Stability Reached"] == "Yes"
        ]
        messages.append(
            f"Loop stability: {len(stable_rows)} of "
            f"{len(stability_summary)} condition/metric series met all "
            "stability criteria."
        )
        if len(stable_rows) == len(stability_summary):
            latest_confirmation = int(
                stable_rows["Confirmed At Loop"].max()
            )
            messages.append(
                "Overall DUT stability was reached because every series "
                f"qualified; confirmation required through loop "
                f"{latest_confirmation}."
            )
        else:
            messages.append(
                "Overall DUT stability was not reached because "
                f"{len(stability_summary) - len(stable_rows)} "
                "condition/metric series did not satisfy every criterion."
            )
    if len(channels) < 2:
        messages.append(
            "Run identical voltage/current points on multiple channels to "
            "enable matched channel comparison."
        )
    elif channel_comparison.empty:
        messages.append(
            "No channel pairs had matching loop numbers for comparison."
        )
    else:
        practical_count = int(
            (
                channel_comparison["Practically Meaningful"] == "Yes"
            ).sum()
        )
        statistical_count = int(
            (channel_comparison["Difference Detected"] == "Yes").sum()
        )
        messages.append(
            f"Matched channel comparison: {practical_count} of "
            f"{len(channel_comparison)} conditions reached the "
            f"{practical_difference_threshold_percent:.1f}% practical "
            f"threshold; {statistical_count} showed a statistical offset."
        )
        if (
            channel_comparison["Evidence Strength"] == "Preliminary"
        ).any():
            messages.append(
                "At least one channel comparison is preliminary because it "
                "contains fewer than five matched loops."
            )
    messages.append(
        "Specification compliance is decided by point boundaries first; "
        "confidence intervals describe bias, repeatability, and uncertainty."
    )
    return tuple(messages)


def _methodology(practical_difference_threshold_percent):
    return (
        "<h2>Statistical Mathematics and Decision Rules</h2>"
        "<h3>1. Notation and source measurements</h3>"
        "<p>For one fixed DUT, test, channel, set voltage and set current, let "
        "<code>n</code> be the number of valid error records and let "
        "<code>x_i</code> be error record <code>i</code>. "
        "<code>V_set</code> is the programmed PSU voltage, "
        "<code>V_ref</code> is the reference DMM measurement, and "
        "<code>V_rb</code> is the PSU voltage readback.</p>"
        "<ul>"
        "<li>Programming error: <code>e_prog = V_ref - V_set</code>.</li>"
        "<li>Readback error: <code>e_rb = V_rb - V_ref</code>.</li>"
        "<li>The analysis uses the lower and upper boundaries recorded with "
        "each point. The report normally creates a symmetric limit from "
        "<code>U = gain * V_set + offset</code> and <code>L = -U</code>, "
        "with independent gain/offset settings for programming and readback.</li>"
        "</ul>"
        "<p>Different DUTs, tests, channels, set voltages, set currents and "
        "error metrics are never pooled into one condition statistic.</p>",
        "<h3>2. Point compliance and boundary normalization</h3>"
        "<p>A point passes exactly when <code>L_i &lt;= x_i &lt;= U_i</code>. "
        "When repeated records contain different limits, the condition uses "
        "the strict intersection: <code>L_strict = max(L_i)</code> and "
        "<code>U_strict = min(U_i)</code>.</p>"
        "<p>Directional limit usage preserves asymmetric limits:</p>"
        "<ul>"
        "<li>If <code>x_i &gt;= 0</code>: "
        "<code>usage_i = 100 * x_i / U_i</code>.</li>"
        "<li>If <code>x_i &lt; 0</code>: "
        "<code>usage_i = 100 * x_i / abs(L_i)</code>.</li>"
        "<li>Maximum limit usage: <code>max(abs(usage_i))</code>.</li>"
        "<li>Margin remaining: <code>100 - abs(usage_i)</code>. Zero is on "
        "the boundary; a negative value is beyond the boundary.</li>"
        "<li>Pass rate: <code>100 * count(passed points) / n</code>.</li>"
        "</ul>",
        "<h3>3. Location, spread and error magnitude</h3>"
        "<ul>"
        "<li>Mean error (bias): <code>x_bar = sum(x_i) / n</code>.</li>"
        "<li>Median error: the middle ordered error, or the mean of the two "
        "middle errors when <code>n</code> is even.</li>"
        "<li>Sample standard deviation: "
        "<code>s = sqrt(sum((x_i - x_bar)^2) / (n - 1))</code>. "
        "The application reports zero for one sample.</li>"
        "<li>Standard error of the mean: <code>SE = s / sqrt(n)</code>.</li>"
        "<li>Unscaled median absolute deviation: "
        "<code>MAD = median(abs(x_i - median(x)))</code>. No 1.4826 normal "
        "consistency multiplier is applied.</li>"
        "<li>Mean absolute error: <code>MAE = sum(abs(x_i)) / n</code>.</li>"
        "<li>Root mean square error: "
        "<code>RMSE = sqrt(sum(x_i^2) / n)</code>.</li>"
        "<li>P95 absolute error: the 0.95 quantile of <code>abs(x_i)</code>, "
        "using pandas linear interpolation.</li>"
        "<li>Maximum absolute error: <code>max(abs(x_i))</code>.</li>"
        "<li>Estimated spread: <code>x_bar +/- 2s</code>. This is a descriptive "
        "screening band, not a formal confidence or prediction interval.</li>"
        "</ul>",
        "<h3>4. Student-t confidence intervals</h3>"
        "<p>For confidence level <code>C</code>, the mean interval is "
        "<code>x_bar +/- t(C, n-1) * s / sqrt(n)</code>. The 95% interval "
        "uses the two-sided Student-t critical value associated with 95% "
        "coverage; the 90% interval uses the corresponding 90% value. "
        "For sample counts through 31, the program uses its stored t table. "
        "For larger samples it uses 1.960 for 95% and 1.645 for 90%. "
        "No interval is calculated for <code>n &lt; 2</code>.</p>",
        "<h3>5. Bias assessment</h3>"
        "<p>Null hypothesis: <code>H0: mean error = 0</code>. "
        "A systematic offset is labelled detected when the two-sided 95% "
        "confidence interval excludes zero: either "
        "<code>CI95_lower &gt; 0</code> or <code>CI95_upper &lt; 0</code>. "
        "If zero remains inside the interval, the result means insufficient "
        "evidence of non-zero bias; it does not prove the true bias is zero. "
        "The application reports this interval rule rather than a p-value.</p>",
        "<h3>6. Mean equivalence using TOST logic</h3>"
        "<p>The equivalence margins are the strict engineering limits "
        "<code>[L_strict, U_strict]</code>. The null hypothesis is that the "
        "mean error lies outside the allowed interval. At alpha 0.05, the "
        "confidence-interval form of the Two One-Sided Tests rule accepts mean "
        "equivalence only when "
        "<code>CI90_lower &gt;= L_strict</code> and "
        "<code>CI90_upper &lt;= U_strict</code>. This assesses the mean only. "
        "It never changes a failed measured point into a pass.</p>",
        "<h3>7. Compliance conclusion priority</h3>"
        "<ol>"
        "<li>If pass rate is below 100%: "
        "<b>FAIL - observed point exceeded limit</b>.</li>"
        "<li>If <code>n = 1</code>: "
        "<b>PASS - repeatability not established</b>.</li>"
        "<li>If <code>2 &lt;= n &lt; 5</code>: "
        "<b>PASS - compliant; statistics preliminary</b>.</li>"
        "<li>For <code>n &gt;= 5</code>, if mean equivalence is not "
        "demonstrated: <b>MARGINAL</b>.</li>"
        "<li>If <code>x_bar - 2s &lt; L_strict</code> or "
        "<code>x_bar + 2s &gt; U_strict</code>: <b>MARGINAL</b>.</li>"
        "<li>Otherwise: <b>PASS - compliant and statistically stable</b>.</li>"
        "</ol>",
        "<h3>8. Matched channel comparison</h3>"
        "<p>Channels are compared only for the same DUT, test, set voltage, "
        "set current and metric. Measurements are first averaged within each "
        "channel and loop. Only loop identifiers present in both channels are "
        "kept. For matched loop <code>j</code>: "
        "<code>d_j = mean_error_A,j - mean_error_B,j</code>. The reported "
        "mean difference is <code>d_bar = sum(d_j) / m</code>, where "
        "<code>m</code> is the number of matched loops. Its 95% interval is "
        "<code>d_bar +/- t(0.95, m-1) * s_d / sqrt(m)</code>. A statistical "
        "difference is detected when this interval excludes zero.</p>"
        "<p>Matched Pearson correlation is "
        "<code>r = sum((A_j-A_bar)(B_j-B_bar)) / "
        "sqrt(sum((A_j-A_bar)^2) * sum((B_j-B_bar)^2))</code>. It is reported "
        "only for at least two matched loops when both channels have non-zero "
        "sample standard deviation. Correlation describes shared movement, "
        "not agreement: a high correlation can coexist with a large offset.</p>",
        "<h3>9. Practical difference threshold</h3>"
        "<p>The practical limit is the strictest magnitude available for the "
        "condition: <code>P = min(abs(L_strict), abs(U_strict))</code>. "
        "Difference limit usage is "
        "<code>100 * abs(d_bar) / P</code>. The selected practical threshold "
        f"is currently <b>{practical_difference_threshold_percent:.1f}% of "
        "the engineering limit</b>. A channel difference is practically "
        "meaningful when difference limit usage is greater than or equal to "
        "this threshold.</p>"
        "<p>Example: if the strict engineering limit is +/-0.010 V and the "
        "threshold is 10%, the practical difference level is "
        "<code>0.10 * 0.010 V = 0.001 V</code>. A mean A-B difference of "
        "0.0012 V uses 12% of the limit and is practically meaningful. "
        "This threshold is an operator-selected engineering screening rule, "
        "not a universal statistical significance level and not a new "
        "pass/fail specification.</p>",
        "<h3>10. Statistical versus practical evidence</h3>"
        "<ul>"
        "<li>Statistical yes, practical yes: detectable and large enough to "
        "matter under the selected engineering rule.</li>"
        "<li>Statistical yes, practical no: consistent offset, but small "
        "relative to the allowed error.</li>"
        "<li>Statistical no, practical yes: observed magnitude is important, "
        "but the available matched loops do not establish consistency.</li>"
        "<li>Both no: no meaningful channel offset is established.</li>"
        "</ul>"
        "<p>Evidence strength is <b>Insufficient</b> for fewer than two "
        "matched loops, <b>Preliminary</b> for two through four, and "
        "<b>Supported</b> for five or more.</p>",
        "<h3>11. Dashboard aggregation</h3>"
        "<p>Weighted pass rate is "
        "<code>sum(condition pass rate * condition samples) / "
        "sum(condition samples)</code>. Weighted mean bias uses the same "
        "sample weighting. Worst limit usage and maximum absolute error are "
        "the maxima among visible conditions. Heatmap cells use the worst "
        "limit usage and lowest pass rate among metrics/channels at the same "
        "voltage/current point. Green is below 80%, amber is 80% through "
        "100%, and red is above 100% limit usage.</p>",
        "<h3>12. Assumptions and limitations</h3>"
        "<ul>"
        "<li>Confidence intervals assume repeated errors are sufficiently "
        "independent and their mean is reasonably described by Student-t "
        "methods. Time drift or autocorrelation can overstate evidence.</li>"
        "<li>Outliers are retained. MAD helps expose robust spread but does "
        "not remove or replace observations.</li>"
        "<li>No multiple-comparison correction is applied when many "
        "conditions are assessed.</li>"
        "<li>Correlation does not prove causation or interchangeability.</li>"
        "<li>Instrument calibration uncertainty, reference uncertainty, "
        "guardbanding and uncertainty budgets are not included automatically.</li>"
        "<li>Results from two through four samples are marked preliminary; "
        "at least five repeated or matched loops are recommended, and more "
        "may be needed for stable conclusions.</li>"
        "</ul>",
        "<h3>13. Loop stability detection</h3>"
        "<p>Stability is evaluated separately for every run, DUT, test, "
        "channel, set voltage, set current and error metric. One mean error "
        "is calculated per loop. For each possible starting loop, the "
        "algorithm evaluates that loop and every later loop. The earliest "
        "suffix satisfying all rules is the stable period.</p>"
        "<ul>"
        f"<li>At least {MIN_STABILITY_CONFIRMATION_LOOPS} consecutive loops "
        "must remain.</li>"
        "<li>Every measured point in the evaluated period must pass.</li>"
        "<li>Practical limit: "
        "<code>P = min(abs(L_strict), abs(U_strict))</code>.</li>"
        "<li>Loop-mean span usage: "
        "<code>100 * (max(loop_mean)-min(loop_mean)) / P</code> must be "
        f"&lt;= {STABILITY_SPAN_THRESHOLD_PERCENT:.1f}%.</li>"
        "<li>Loop-mean standard-deviation usage: "
        "<code>100 * std(loop_mean) / P</code> must be "
        f"&lt;= {STABILITY_STD_THRESHOLD_PERCENT:.1f}%.</li>"
        "<li>An ordinary least-squares line is fitted against loop number. "
        "Drift usage is <code>100 * abs(slope) / P</code> per loop and must "
        f"be &lt;= {STABILITY_DRIFT_THRESHOLD_PERCENT_PER_LOOP:.1f}% "
        "per loop.</li>"
        "</ul>"
        "<p><b>Stable From Loop</b> is the first loop in the accepted period. "
        "<b>Confirmed At Loop</b> is the second loop in that period, because "
        "the conclusion cannot be made until two qualifying loops exist. "
        "Overall DUT stability is reported only when every analyzed "
        "condition/metric series reaches stability; its confirmation loop is "
        "the latest confirmation loop among those series. "
        "This is a transparent engineering screening algorithm, not a formal "
        "change-point test. Thresholds are intentionally tied to the recorded "
        "engineering error boundary.</p>",
        "<h3>14. Automated error trend text</h3>"
        "<p>Trend analysis uses one mean error per loop for each exact run, "
        "DUT, channel, voltage, current and metric series. Ordinary least "
        "squares gives signed slope per loop. A trend is flat when "
        "<code>100 * abs(slope) / P</code> is at most "
        f"{TREND_FLAT_THRESHOLD_PERCENT_PER_LOOP:.2f}% of the strict limit "
        "per loop; otherwise its sign labels it increasing or decreasing.</p>"
        "<p>The early and late means each use up to three loops, or half the "
        "available loops when fewer exist. Magnitude movement is "
        "<code>100 * (abs(late_mean)-abs(early_mean)) / P</code>. A change "
        f"greater than {TREND_MEANINGFUL_SHIFT_PERCENT:.1f}% moves away from "
        "zero; below the negative threshold moves toward zero. A late mean at "
        f"or above {TREND_NEAR_BOUNDARY_PERCENT:.0f}% of the limit is near "
        "or beyond the boundary.</p>"
        "<p>A sudden jump is a consecutive loop-mean change at or above "
        f"{TREND_JUMP_THRESHOLD_PERCENT:.1f}% of the limit. Robust outliers "
        "use <code>robust_z = 0.6745 * abs(x-median) / MAD</code> and are "
        f"flagged above {TREND_OUTLIER_ROBUST_Z:.1f}. Oscillation is based on "
        "the percentage of consecutive non-zero slope signs that reverse. "
        "At least 60% is oscillating, at most 20% is mostly monotonic, and "
        "the remainder is mixed movement.</p>"
        "<p>The priority score ranks review order; it combines late boundary "
        "usage, normalized drift, jumps, outliers, failure to reach stability "
        "and movement away from zero. It is not a specification or probability. "
        "All source rows remain available in "
        "<code>analysis_trend_summary.csv</code>.</p>",
    )


def analyze_bundle_runs(
    output_root,
    practical_difference_threshold_percent=(
        PRACTICAL_DIFFERENCE_THRESHOLD_PERCENT
    ),
):
    try:
        practical_difference_threshold_percent = min(
            100.0,
            max(
                0.1,
                float(practical_difference_threshold_percent),
            ),
        )
    except (TypeError, ValueError):
        practical_difference_threshold_percent = (
            PRACTICAL_DIFFERENCE_THRESHOLD_PERCENT
        )
    observations = _load_observations(output_root)
    if observations.empty:
        return _empty_result(
            practical_difference_threshold_percent=(
                practical_difference_threshold_percent
            )
        )
    errors = _long_errors(observations)
    if errors.empty:
        return _empty_result(
            "Realtime files do not contain supported error columns.",
            practical_difference_threshold_percent,
        )

    summary = _group_statistics(
        errors,
        ["DUT", "Test", "Channel", *CONDITION_COLUMNS, "Metric"],
    )
    summary = _add_90_percent_intervals(summary, errors)
    loop_performance = _group_statistics(
        errors,
        [
            "Run",
            "DUT",
            "Test",
            "Channel",
            "Loop",
            *CONDITION_COLUMNS,
            "Metric",
        ],
    )
    loop_performance = loop_performance.drop(
        columns=["Loops"],
        errors="ignore",
    )
    stability_summary = _stability_summary(loop_performance)
    trend_summary = _trend_summary(
        loop_performance,
        stability_summary,
    )
    roots = _analysis_roots(output_root)
    compare_separate_runs = len(roots) > 1 and errors["Run"].nunique() > 1
    channel_comparison = _channel_comparison(
        errors,
        practical_difference_threshold_percent,
        comparison_column="Run" if compare_separate_runs else "Channel",
        subject_label="Run" if compare_separate_runs else "Channel",
    )
    hypothesis_tests = _hypothesis_assessments(summary)
    extremes = _extremes(errors)
    return BundleAnalysisResult(
        observations,
        errors,
        summary,
        loop_performance,
        stability_summary,
        trend_summary,
        channel_comparison,
        hypothesis_tests,
        extremes,
        _insights(
            errors,
            summary,
            stability_summary,
            channel_comparison,
            practical_difference_threshold_percent,
        ),
        _trend_report(trend_summary),
        _comparison_report(channel_comparison),
        _methodology(practical_difference_threshold_percent),
        practical_difference_threshold_percent,
    )
