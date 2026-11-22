import csv
import hashlib
import json
import re
from collections import Counter
from datetime import date
from pathlib import Path

from calculator import AfaNotDeclared, UnsupportedPeriod, compute_bill


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PIPELINE = ROOT / "data" / "pipeline_v2"
OUTPUT = ROOT / "docs" / "week4_evidence" / "rereview"
EXPECTED_MONTHS = {
    **{f"2025-{month:02d}": (12, 21) for month in range(7, 13)},
    **{f"2026-{month:02d}": (12, 21) for month in range(1, 9)},
    "2026-09": (22, 33),
    **{f"2026-{month:02d}": (20, 31) for month in range(10, 13)},
    "2027-01": (10, 19),
}
PERSONAL_DATA = {
    "mobile": re.compile(r"\b01\d-?\d{7,8}\b"),
    "IC": re.compile(r"\b\d{6}-\d{2}-\d{4}\b"),
    "10-14 digit numbers": re.compile(r"\b\d{10,14}\b"),
}
MONEY_FIELDS = (
    "energy",
    "capacity",
    "network",
    "afa",
    "retail",
    "eei",
    "service_tax",
    "kwtbb",
    "total",
)
REFERENCE_FIELDS = {
    "energy": "energy_rm",
    "capacity": "capacity_rm",
    "network": "network_rm",
    "afa": "afa_rm",
    "retail": "retail_rm",
    "eei": "eei_rm",
    "service_tax": "service_tax_rm",
    "kwtbb": "kwtbb_rm",
    "total": "total_rm",
}


def read_csv(path):
    with path.open(encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def write_csv(path, rows, fields):
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_jsonl(path):
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def month_range(start_year, start_month, end_year, end_month):
    year, month = start_year, start_month
    while (year, month) <= (end_year, end_month):
        yield f"{year:04d}-{month:02d}"
        month += 1
        if month == 13:
            year, month = year + 1, 1


def main():
    failures = []

    def check(label, actual, expected):
        ok = actual == expected
        print(f"{label}: {'PASS' if ok else 'FAIL'}; actual={actual!r}; expected={expected!r}")
        if not ok:
            failures.append(label)
        return ok

    registry = read_csv(RAW / "source_registry.csv")
    sources = {row["source_id"]: row for row in registry}
    source_hash_matches = sum(
        1
        for row in registry
        if (RAW / row["filename"]).is_file()
        and sha256(RAW / row["filename"]) == row["sha256"]
    )
    check("Source hashes", (source_hash_matches, len(registry)), (10, 10))

    web_json = {
        sid: json.loads((RAW / sources[sid]["filename"]).read_text(encoding="utf-8"))
        for sid in ("S07", "S08")
    }
    chunks = load_jsonl(PIPELINE / "documents" / "prepared_text.jsonl")
    tables = {
        name: read_csv(PIPELINE / "tables" / name)
        for name in (
            "prepared_tariff_rates.csv",
            "prepared_charge_rules.csv",
            "prepared_afa_monthly.csv",
            "prepared_eei_tiers.csv",
        )
    }
    v1_rows = []
    for chunk in chunks:
        source_id = chunk.get("source_id", "")
        source = sources.get(source_id)
        failed = []
        fields = (
            "chunk_id",
            "text",
            "source_id",
            "source_url",
            "issuer",
            "title",
            "language",
            "effective_from",
            "source_sha256",
        )
        if not all(str(chunk.get(field, "")).strip() for field in fields):
            failed.append("required fields")
        if not chunk.get("published_date") and source_id not in {"S07", "S08"}:
            failed.append("published_date")
        if source is None or chunk.get("source_sha256") != source["sha256"]:
            failed.append("source hash")
        if source_id in {"S07", "S08"}:
            if chunk.get("locator") not in web_json[source_id]:
                failed.append("JSON locator")
        else:
            try:
                page = int(chunk.get("page", ""))
                if source is None or not 1 <= page <= int(source["pages"]):
                    failed.append("PDF page")
            except (TypeError, ValueError):
                failed.append("PDF page")
        v1_rows.append({
            "pathway": "text",
            "item_id": chunk.get("chunk_id", ""),
            "result": "FAIL" if failed else "PASS",
            "failed_checks": "; ".join(failed),
        })

    table_specs = (
        ("prepared_tariff_rates.csv", "rate_id"),
        ("prepared_charge_rules.csv", "rule_id"),
        ("prepared_afa_monthly.csv", "month"),
        ("prepared_eei_tiers.csv", "band_id"),
    )
    for table_name, id_field in table_specs:
        for row in tables[table_name]:
            item_id = row.get(id_field, "")
            assumed = table_name == "prepared_charge_rules.csv" and item_id == "P07"
            source_ok = row.get("source_id") in sources
            verified = row.get("verified_in_source") == "True"
            if assumed:
                result = (
                    "ASSUMED"
                    if row.get("verified_in_source") == "assumed"
                    and row.get("note", "").strip()
                    else "FAIL"
                )
                failed = "" if result == "ASSUMED" else "assumption status or note"
            else:
                result = "PASS" if source_ok and verified else "FAIL"
                failed = "" if result == "PASS" else "source_id or verified_in_source"
            v1_rows.append({
                "pathway": "table",
                "item_id": item_id,
                "result": result,
                "failed_checks": failed,
            })

    v1_pass = sum(row["result"] == "PASS" for row in v1_rows)
    v1_assumed = sum(row["result"] == "ASSUMED" for row in v1_rows)
    v1_fail = sum(row["result"] == "FAIL" for row in v1_rows)
    check("V1 items (PASS, ASSUMED, FAIL)", (len(v1_rows), v1_pass, v1_assumed, v1_fail), (112, 111, 1, 0))

    rates = {row["rate_id"]: row for row in tables["prepared_tariff_rates.csv"]}
    rules = {row["rule_id"]: row for row in tables["prepared_charge_rules.csv"]}
    afa_months = {
        row["month"] for row in tables["prepared_afa_monthly.csv"]
        if row["status"] == "declared"
    }
    expected_afa = set(month_range(2025, 7, 2026, 11))
    eei_rows = sorted(
        tables["prepared_eei_tiers.csv"],
        key=lambda row: int(row["kwh_from"]),
    )
    contiguous_eei = (
        len(eei_rows) == 16
        and int(eei_rows[0]["kwh_from"]) == 1
        and int(eei_rows[-1]["kwh_to"]) == 1000
        and all(
            int(current["kwh_from"]) == int(previous["kwh_to"]) + 1
            for previous, current in zip(eei_rows, eei_rows[1:])
        )
    )
    v2_definitions = {
        "G01": "Energy charge, both tiers",
        "G02": "Capacity charge",
        "G03": "Network charge",
        "G04": "Retail charge amount",
        "G05": "1500 kWh tier boundary P06",
        "G06": "Protection thresholds P01 and P02",
        "G07": "Declared AFA every month Jul 2025 to Nov 2026",
        "G08": "P04 AFA applies to all kWh above threshold",
        "G09": "P05 service tax rate",
        "G10": "P05 service tax base wording",
        "G11": "16 contiguous EEI bands from 1 to 1000 kWh",
        "G12": "P08 KWTBB rate and 300 kWh limit",
        "G13": "P10 rounding rule",
        "G14": "P11 billing period split by calendar month",
    }

    def confirmed_rule(rule_id, rule_name, value=None, source_id=None):
        row = rules.get(rule_id)
        return bool(
            row
            and row["rule"] == rule_name
            and row["verified_in_source"] == "True"
            and (value is None or round(float(row["value"]), 2) == round(value, 2))
            and (source_id is None or row["source_id"] == source_id)
        )

    v2_checks = {
        "G01": {"R01", "R02"}.issubset(rates),
        "G02": "R03" in rates and rates["R03"]["component"] == "capacity",
        "G03": "R04" in rates and rates["R04"]["component"] == "network",
        "G04": "R05" in rates and rates["R05"]["component"] == "retail",
        "G05": confirmed_rule("P06", "energy_tier_boundary"),
        "G06": (
            confirmed_rule("P01", "protection_threshold")
            and confirmed_rule("P02", "protection_threshold")
        ),
        "G07": afa_months == expected_afa,
        "G08": confirmed_rule("P04", "afa_scope"),
        "G09": confirmed_rule("P05", "service_tax", value=8.0),
        "G10": confirmed_rule("P05", "service_tax", source_id="S07"),
        "G11": contiguous_eei,
        "G12": confirmed_rule("P08", "kwtbb", value=1.6),
        "G13": confirmed_rule("P10", "rounding"),
        "G14": confirmed_rule("P11", "billing_period_split"),
    }
    v2_rows = [
        {
            "group_id": group_id,
            "required_rule": label,
            "result": "PASS" if v2_checks[group_id] else "FAIL",
            "note": "",
        }
        for group_id, label in v2_definitions.items()
    ]
    v2_pass = sum(row["result"] == "PASS" for row in v2_rows)
    check("V2 rule groups", (v2_pass, len(v2_rows)), (14, 14))

    reference_rows = read_csv(ROOT / "evaluation" / "reference_bills.csv")
    reference_checks = []
    for bill in reference_rows:
        failed = []
        try:
            results = compute_bill(
                int(bill["kwh"]),
                date.fromisoformat(bill["billing_start"]),
                date.fromisoformat(bill["billing_end"]),
            )
            if len(results) != 1:
                failed.append(f"result count={len(results)}")
            else:
                result = results[0]
                if result.scenario != bill["scenario"]:
                    failed.append(f"scenario={result.scenario}")
                for field, column in REFERENCE_FIELDS.items():
                    if abs(getattr(result, field) - float(bill[column])) >= 0.005:
                        failed.append(field)
        except (AfaNotDeclared, UnsupportedPeriod, KeyError, ValueError) as error:
            failed.append(type(error).__name__)
        reference_checks.append({
            "case_id": bill["case_id"],
            "result": "PASS" if not failed else "FAIL",
            "failed_checks": "; ".join(failed),
        })
    reference_pass = sum(row["result"] == "PASS" for row in reference_checks)
    check("Reference bills", (reference_pass, len(reference_rows)), (64, 64))

    eligible = []
    for month in month_range(2025, 7, 2027, 1):
        mid_month = date.fromisoformat(month + "-15")
        counts = Counter()
        for chunk in chunks:
            start = date.fromisoformat(chunk["effective_from"])
            end = date.fromisoformat(chunk["effective_to"]) if chunk.get("effective_to") else date.max
            if start <= mid_month <= end:
                counts[chunk["language"]] += 1
        eligible.append({
            "bill_month": month,
            "eligible_en_chunks": counts["en"],
            "eligible_ms_chunks": counts["ms"],
        })
    actual_months = {
        row["bill_month"]: (row["eligible_en_chunks"], row["eligible_ms_chunks"])
        for row in eligible
    }
    check("Eligible chunks per month", actual_months, EXPECTED_MONTHS)
    check("Months with zero English chunks", sum(row["eligible_en_chunks"] == 0 for row in eligible), 0)

    conflict_ids = {
        "S03-p1-c02",
        "S03-p2-c07",
        "S04-p1-c02",
        "S04-p2-c07",
    }
    conflict_counts = {}
    for chunk in chunks:
        if chunk["chunk_id"] not in conflict_ids:
            continue
        start = date.fromisoformat(chunk["effective_from"])
        end = date.fromisoformat(chunk["effective_to"]) if chunk.get("effective_to") else date.max
        conflict_counts[chunk["chunk_id"]] = sum(
            start <= date.fromisoformat(month + "-15") <= end
            for month in ("2026-09", "2026-10", "2026-11", "2026-12")
        )
    check("Superseded chunks eligible in Sep-Dec 2026", conflict_counts, {chunk_id: 0 for chunk_id in sorted(conflict_ids)})

    pii_counts = {
        label: sum(len(pattern.findall(chunk["text"])) for chunk in chunks)
        for label, pattern in PERSONAL_DATA.items()
    }
    check("Personal-data matches (mobile, IC, long number)", tuple(pii_counts.values()), (0, 0, 0))
    review_ids = sorted(chunk["chunk_id"] for chunk in chunks if chunk["status"] == "needs_review")
    check("Needs-review chunk IDs", review_ids, ["S06-p1-c02"])

    OUTPUT.mkdir(parents=True, exist_ok=True)
    write_csv(
        OUTPUT / "v1_provenance.csv",
        v1_rows,
        ("pathway", "item_id", "result", "failed_checks"),
    )
    write_csv(
        OUTPUT / "v2_rule_completeness.csv",
        v2_rows,
        ("group_id", "required_rule", "result", "note"),
    )
    write_csv(
        OUTPUT / "reference_bills_check.csv",
        reference_checks,
        ("case_id", "result", "failed_checks"),
    )
    write_csv(
        OUTPUT / "eligible_chunks_by_month.csv",
        eligible,
        ("bill_month", "eligible_en_chunks", "eligible_ms_chunks"),
    )
    summary = {
        "source_hash_matches": {"actual": source_hash_matches, "expected": 10},
        "v1": {
            "items": len(v1_rows),
            "PASS": v1_pass,
            "ASSUMED": v1_assumed,
            "FAIL": v1_fail,
        },
        "v2": {"groups": len(v2_rows), "PASS": v2_pass, "FAIL": len(v2_rows) - v2_pass},
        "reference_bills": {"PASS": reference_pass, "total": len(reference_rows)},
        "eligible_chunks_by_month": eligible,
        "superseded_chunk_midmonth_counts": conflict_counts,
        "personal_data_matches": pii_counts,
        "needs_review_chunks": review_ids,
        "failures": failures,
    }
    with (OUTPUT / "summary.json").open("w", encoding="utf-8", newline="\n") as file:
        json.dump(summary, file, indent=2, ensure_ascii=False)
        file.write("\n")
    if failures:
        raise SystemExit("Quality gate failed: " + "; ".join(failures))
    print(f"Quality gate passed. Evidence written to {OUTPUT.relative_to(ROOT)}.")


if __name__ == "__main__":
    main()
