"""Convert chart-engine results to R-compatible records."""

from typing import cast

from ._data import Limits, Record, Scalar, Settings
from ._engine import FunnelResult, SPCResult


def spc_rows(rows: list[Record], settings: Settings) -> list[Record]:
    if not rows:
        return []
    flags = {
        "astronomical": "astpoint",
        "shift": "shift",
        "trend": "trend",
        "two_in_three": "two_in_three",
    }
    excluded = {
        column for flag, column in flags.items() if not settings.get(flag, False)
    }
    columns: list[str] = []
    for row in rows:
        for name, value in row.items():
            if value is not None and name not in excluded and name not in columns:
                columns.append(name)
    result: list[Record] = []
    for row in rows:
        record: Record = {name: row.get(name) for name in columns}
        record["date"] = cast(str, record["date"]).strip()
        result.append(record)
    return result


def spc_limits(raw: SPCResult, settings: Settings) -> Limits:
    if not raw["indicatorVarNames"]:
        return spc_rows([point["table_row"] for point in raw["plotPoints"]], settings)
    result: dict[str, Limits] = {}
    for groups, rows in zip(raw["groupNames"], raw["spcLimitRows"]):
        names: list[str] = []
        for name in groups:
            if name is None or name == "":
                name = "<blank>"
            names.append(str(name))
        branch = result
        for name in names[:-1]:
            branch = cast(dict[str, Limits], branch.setdefault(name, {}))
        branch[names[-1]] = spc_rows(rows, settings)
    return result


def funnel_lines(raw: FunnelResult, settings: Settings) -> list[Record]:
    result: list[Record] = []
    for row in raw["calculatedLimits"]:
        record: Record = {"denominator": row["denominators"]}
        for name, value in row.items():
            if name == "denominators":
                continue
            if name == "alt_target" and settings.get("alt_target") is None:
                continue
            record[name] = value
        result.append(record)
    return result


def funnel_limits(raw: FunnelResult, lines: list[Record], settings: Settings) -> list[Record]:
    by_denominator: dict[Scalar, list[Record]] = {}
    for row in lines:
        by_denominator.setdefault(row["denominator"], []).append(row)
    result: list[Record] = []
    for point in sorted(raw["plotPoints"], key=lambda point: point["x"]):
        for line in by_denominator.get(point["x"], []):
            record: Record = {
                "denominator": point["x"],
                "group": point["group_text"],
                "numerator": point["numerator"],
                "value": point["value"],
                "z": point["z"],
            }
            if settings.get("two_sigma", False):
                record["two_sigma"] = point["two_sigma"]
            if settings.get("three_sigma", False):
                record["three_sigma"] = point["three_sigma"]
            record.update(line)
            result.append(record)
    return result


def misc_limits(raw: FunnelResult) -> list[Record]:
    result: list[Record] = []
    for point in raw["miscPoints"]:
        record: Record = {
            "indicator": point["indicator"],
            "group": point["group_text"],
            "z": point["z"],
            "score": point["score"],
            "three_sigma": point["three_sigma"],
            "numerator": point["numerator"],
            "denominator": point["x"],
            "value": point["value"],
        }
        record.update(point["limits"])
        del record["denominators"]
        result.append(record)
    return result
