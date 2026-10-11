"""Convert chart-engine results to R-compatible records."""

from typing import Any

from ._data import Record, Settings


def spc_rows(rows: list[Record], settings: Settings) -> list[Record]:
    rows = [row.get("table_row", row) for row in rows]
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
    result = []
    for row in rows:
        record: Record = {name: row.get(name) for name in columns}
        record["date"] = record["date"].strip()
        result.append(record)
    return result


def spc_limits(raw: Record, settings: Settings) -> list[Record] | dict[str, Any]:
    if not raw["indicatorVarNames"]:
        return spc_rows(raw["plotPoints"], settings)
    result: dict[str, Any] = {}
    for groups, rows in zip(raw["groupNames"], raw["spcLimitRows"]):
        names = []
        for name in groups:
            if name is None or name == "":
                name = "<blank>"
            names.append(str(name))
        branch = result
        for name in names[:-1]:
            branch = branch.setdefault(name, {})
        branch[names[-1]] = spc_rows(rows, settings)
    return result


def funnel_lines(raw: Record, settings: Settings) -> list[Record]:
    result = []
    for row in raw["calculatedLimits"]:
        record = {"denominator": row["denominators"]}
        for name, value in row.items():
            if name == "denominators":
                continue
            if name == "alt_target" and settings.get("alt_target") is None:
                continue
            record[name] = value
        result.append(record)
    return result


def funnel_limits(raw: Record, lines: list[Record], settings: Settings) -> list[Record]:
    by_denominator: dict[Any, list[Record]] = {}
    for row in lines:
        by_denominator.setdefault(row["denominator"], []).append(row)
    result = []
    for point in raw["plotPoints"]:
        for line in by_denominator.get(point["x"], []):
            record = {
                "denominator": point["x"],
                "group": point["group_text"],
                "numerator": point["numerator"],
                "value": point["value"],
                "z": point["z"],
            }
            for flag in ("two_sigma", "three_sigma"):
                if settings.get(flag, False):
                    record[flag] = point[flag]
            record.update(line)
            result.append(record)
    return sorted(result, key=lambda row: row["denominator"])


def misc_limits(raw: Record) -> list[Record]:
    columns = (
        "indicator", "grouping", "group", "z", "score", "outlier",
        "numerator", "denominator", "value", "ll99", "target", "ul99",
    )
    return [{name: point[name] for name in columns} for point in raw["plotPoints"]]
