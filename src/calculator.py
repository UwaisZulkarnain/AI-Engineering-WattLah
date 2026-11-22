import csv
import math
import re
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_DIR = ROOT / "data" / "pipeline_v2" / "tables"
EPSILON = 2**-52


class UnsupportedPeriod(ValueError):
    pass


class AfaNotDeclared(ValueError):
    pass


@dataclass(frozen=True)
class MonthBreakdown:
    month: str
    days: int
    usage: int
    threshold: int
    afa_rate: float | None


@dataclass(frozen=True)
class BillResult:
    scenario: str
    assumed: bool
    energy: float
    capacity: float
    network: float
    afa: float
    retail: float
    eei: float
    service_tax: float
    kwtbb: float
    total: float
    per_month: list[MonthBreakdown]
    rule_ids: list[str]


def _read_csv(path):
    with path.open(encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def _load_tables(data_dir=None):
    folder = Path(data_dir) if data_dir is not None else DEFAULT_DATA_DIR
    if not (folder / "prepared_tariff_rates.csv").is_file() and (folder / "tables").is_dir():
        folder = folder / "tables"
    names = (
        "prepared_tariff_rates.csv",
        "prepared_charge_rules.csv",
        "prepared_afa_monthly.csv",
        "prepared_eei_tiers.csv",
    )
    return {
        name: _read_csv(folder / name)
        for name in names
    }


def _by_id(rows, field):
    return {row[field]: row for row in rows}


def _number(value):
    return float(value)


def _js_round(value):
    return math.floor(value + 0.5)


def _round_domestic_amount(value):
    magnitude = (abs(value) + EPSILON * max(1.0, abs(value))) * 100
    return math.copysign(_js_round(magnitude) / 100, value)


def _threshold_for(period_start, scenario, rules):
    p01, p02, p07 = rules["P01"], rules["P02"], rules["P07"]
    start = date.fromisoformat(period_start.isoformat())
    expanded_start = date.fromisoformat(p02["effective_from"])
    expanded_end = date.fromisoformat(p02["effective_to"])
    assumed_start = date.fromisoformat(p07["effective_from"])
    if expanded_start <= start <= expanded_end:
        return int(float(p02["value"])), "P02"
    if scenario == "relief_continues" and start >= assumed_start:
        return int(float(p07["value"])), "P07"
    return int(float(p01["value"])), "P01"


def _billing_periods(kwh, start, end, scenario, rules):
    total_days = (end - start).days + 1
    periods = []
    allocated_usage = 0
    cursor = start
    while cursor <= end:
        next_month = date(cursor.year + (cursor.month == 12), cursor.month % 12 + 1, 1)
        month_end = next_month - timedelta(days=1)
        last_day = min(end, month_end)
        days = (last_day - cursor).days + 1
        threshold, threshold_rule = _threshold_for(cursor, scenario, rules)
        elapsed = (last_day - start).days + 1
        before = (cursor - start).days
        cumulative_usage = (
            kwh if last_day == end else _js_round(kwh * elapsed / total_days)
        )
        usage = cumulative_usage - allocated_usage
        allowance = (
            _js_round(threshold * elapsed / total_days)
            - _js_round(threshold * before / total_days)
        )
        non_st = min(usage, allowance)
        periods.append({
            "month": cursor.strftime("%Y-%m"),
            "days": days,
            "total_days": total_days,
            "threshold": threshold,
            "threshold_rule": threshold_rule,
            "usage": usage,
            "non_st": non_st,
            "st": usage - non_st,
            "chargeable": kwh > threshold,
        })
        allocated_usage = cumulative_usage
        cursor = last_day + timedelta(days=1)
    return periods


def _charge_groups(periods):
    if all(period["threshold"] == periods[0]["threshold"] for period in periods):
        return [{
            "days": periods[0]["total_days"],
            "total_days": periods[0]["total_days"],
            "usage": sum(period["usage"] for period in periods),
            "non_st": sum(period["non_st"] for period in periods),
            "st": sum(period["st"] for period in periods),
        }]
    return periods


def _sum_period_charges(groups, usage_key, rate):
    return _round_domestic_amount(sum(
        _round_domestic_amount(group[usage_key] * rate) for group in groups
    ))


def _tiered_charge(kwh, component, groups, tariff_rows, boundary):
    rows = [row for row in tariff_rows if row["component"] == component]
    if component == "energy":
        wanted = "R02" if kwh > boundary else "R01"
        row = next(item for item in rows if item["rate_id"] == wanted)
    else:
        row = rows[0]
    rate = _number(row["rate"]) / 100 if row["unit"] == "sen/kWh" else _number(row["rate"])
    non_st = _sum_period_charges(groups, "non_st", rate)
    st = _sum_period_charges(groups, "st", rate)
    total = (
        _sum_period_charges(groups, "usage", rate)
        if len(groups) > 1
        else _round_domestic_amount(non_st + st)
    )
    return {"rate": rate, "non_st": non_st, "st": st, "total": total, "row": row}


def _afa_charges(periods, afa_by_month):
    charges = []
    for period in periods:
        if not period["chargeable"]:
            charges.append({"rate": 0.0, "non_st": 0.0, "st": 0.0, "total": 0.0})
            continue
        row = afa_by_month.get(period["month"])
        if row is None or row["status"] != "declared":
            raise AfaNotDeclared(f"AFA for {period['month']} is not declared.")
        rate = _number(row["afa_sen_per_kwh"]) / 100
        charges.append({
            "rate": rate,
            "non_st": _round_domestic_amount(period["non_st"] * rate),
            "st": _round_domestic_amount(period["st"] * rate),
            "total": _round_domestic_amount(period["usage"] * rate),
        })
    first_month = {"rate": charges[0]["rate"], "non_st": 0.0, "st": 0.0, "total": 0.0}
    for charge in charges[:-1]:
        for key in ("non_st", "st", "total"):
            first_month[key] = _round_domestic_amount(first_month[key] + charge[key])
    return first_month, charges[-1]


def _eei_rate(kwh, tiers, scope):
    if kwh > int(float(scope["value"])):
        return 0.0, None
    for row in tiers:
        if kwh <= int(row["kwh_to"]):
            return _number(row["rate_sen_per_kwh"]) / 100, row["band_id"]
    return 0.0, None


def _eei_amount(kwh, rate):
    if kwh < 0:
        return 0.0
    return -_js_round(abs(kwh * rate) * 100) / 100


def _result(kwh, start, end, scenario, tables):
    tariff_rows = tables["prepared_tariff_rates.csv"]
    rules = _by_id(tables["prepared_charge_rules.csv"], "rule_id")
    afa_by_month = _by_id(tables["prepared_afa_monthly.csv"], "month")
    tiers = tables["prepared_eei_tiers.csv"]
    boundary = int(float(rules["P06"]["value"]))
    periods = _billing_periods(kwh, start, end, scenario, rules)
    groups = _charge_groups(periods)

    energy = _tiered_charge(kwh, "energy", groups, tariff_rows, boundary)
    capacity = _tiered_charge(kwh, "capacity", groups, tariff_rows, boundary)
    network = _tiered_charge(kwh, "network", groups, tariff_rows, boundary)
    afa_first, afa_last = _afa_charges(periods, afa_by_month)
    retail_row = next(row for row in tariff_rows if row["component"] == "retail")
    retail_rate = _number(retail_row["rate"])
    chargeable_days = sum(period["days"] for period in periods if period["chargeable"])
    retail = _round_domestic_amount(retail_rate * chargeable_days / periods[0]["total_days"])

    eei_rate, eei_band = _eei_rate(kwh, tiers, rules["P09"])
    eei_total = _eei_amount(kwh, eei_rate)
    non_st_consumption = sum(period["non_st"] for period in periods)
    st_consumption = kwh - non_st_consumption
    if len(groups) > 1:
        eei_non_st = _round_domestic_amount(sum(
            -_js_round(abs(group["non_st"] * eei_rate) * 100) / 100 for group in groups
        ))
        eei_st = _round_domestic_amount(sum(
            -_js_round(abs(group["st"] * eei_rate) * 100) / 100 for group in groups
        ))
        eei_total = _round_domestic_amount(eei_non_st + eei_st)
    elif st_consumption > 0 and kwh:
        eei_non_st = eei_total * non_st_consumption / kwh
        eei_st = eei_total * st_consumption / kwh
    else:
        eei_non_st, eei_st = eei_total, 0.0

    current_non_st = _round_domestic_amount(
        energy["non_st"] + afa_first["non_st"] + afa_last["non_st"]
        + capacity["non_st"] + network["non_st"] + eei_non_st
    )
    current_st = _round_domestic_amount(
        energy["st"] + afa_first["st"] + afa_last["st"]
        + capacity["st"] + network["st"] + retail + eei_st
    )
    if len(groups) > 1:
        usage_charge = _round_domestic_amount(
            energy["total"] + capacity["total"] + network["total"]
            + afa_first["total"] + afa_last["total"] + retail + eei_total
        )
    else:
        usage_charge = _round_domestic_amount(current_non_st + current_st)

    service_rate = _number(rules["P05"]["value"]) / 100
    service_tax = (
        _round_domestic_amount(current_st * service_rate)
        if any(period["chargeable"] for period in periods)
        else 0.0
    )
    kwtbb_rate = _number(rules["P08"]["value"]) / 100
    match = re.search(r"(\d+)\s*kWh", rules["P08"]["description"], re.I)
    if not match:
        raise ValueError("P08 description has no KWTBB usage limit.")
    kwtbb = _round_domestic_amount(
        (energy["total"] + capacity["total"] + network["total"] + eei_total)
        * (kwtbb_rate if kwh > int(match.group(1)) else 0)
    )
    total = _round_domestic_amount(usage_charge + service_tax + kwtbb)

    month_breakdown = []
    for period in periods:
        afa = afa_by_month.get(period["month"])
        month_breakdown.append(MonthBreakdown(
            month=period["month"],
            days=period["days"],
            usage=period["usage"],
            threshold=period["threshold"],
            afa_rate=(
                _number(afa["afa_sen_per_kwh"])
                if afa is not None and afa["status"] == "declared"
                else None
            ),
        ))

    rule_ids = {
        energy["row"]["rate_id"],
        capacity["row"]["rate_id"],
        network["row"]["rate_id"],
        retail_row["rate_id"],
        "P05",
        "P06",
        "P08",
        "P09",
        "P10",
        "P12",
        *(period["threshold_rule"] for period in periods),
    }
    if len(periods) > 1:
        rule_ids.add("P11")
    if any(period["chargeable"] for period in periods):
        rule_ids.add("P04")
        rule_ids.update(
            f"AFA-{period['month']}" for period in periods if period["chargeable"]
        )
    if eei_band is not None:
        rule_ids.add(eei_band)
    assumed = scenario == "relief_continues"
    return BillResult(
        scenario=scenario,
        assumed=assumed,
        energy=energy["total"],
        capacity=capacity["total"],
        network=network["total"],
        afa=_round_domestic_amount(afa_first["total"] + afa_last["total"]),
        retail=retail,
        eei=eei_total,
        service_tax=service_tax,
        kwtbb=kwtbb,
        total=total,
        per_month=month_breakdown,
        rule_ids=sorted(rule_ids),
    )


def compute_bill(kwh: int, start: date, end: date, data_dir: str | Path | None = None) -> list[BillResult]:
    if not isinstance(kwh, int) or isinstance(kwh, bool) or kwh < 0:
        raise ValueError("kwh must be a non-negative integer.")
    if end < start:
        raise UnsupportedPeriod("Billing end date is before its start date.")
    days = (end - start).days + 1
    if days < 28 or days > 62:
        raise UnsupportedPeriod(f"Billing period has {days} days; supported range is 28 to 62.")
    tables = _load_tables(data_dir)
    earliest = date.fromisoformat(_by_id(tables["prepared_charge_rules.csv"], "rule_id")["P01"]["effective_from"])
    if start < earliest:
        raise UnsupportedPeriod(f"Billing periods before {earliest.isoformat()} are unsupported.")
    rules = _by_id(tables["prepared_charge_rules.csv"], "rule_id")
    assumed_start = date.fromisoformat(rules["P07"]["effective_from"])
    scenarios = ("relief_continues", "relief_ends") if end >= assumed_start else ("base",)
    return [_result(kwh, start, end, scenario, tables) for scenario in scenarios]
