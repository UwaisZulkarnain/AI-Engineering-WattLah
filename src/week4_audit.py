"""Reproduces the Week 4 audit (commit 83d4629) on the Week 3 data; S07 to S10 were added later."""

import csv
import hashlib
import json
import re
from collections import Counter
from datetime import date
from itertools import combinations
from pathlib import Path

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"
EXPECTED_NEAR_DUPLICATES = {("S04-p2-c06", "S05-p2-c04")}


def read_csv(path):
    with path.open(encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def normalized(text):
    return " ".join(text.split())


def month_range(start, end):
    year, month = start
    while (year, month) <= end:
        yield year, month
        month += 1
        if month == 13:
            year, month = year + 1, 1


def main():
    failures = []

    def check(label, actual, expected):
        result = "PASS" if actual == expected else "MISMATCH"
        print(f"{label}: {result}; actual={actual!r}; expected={expected!r}")
        if actual != expected:
            failures.append(label)

    registry = read_csv(RAW / "source_registry.csv")
    week4_registry = [
        row
        for row in registry
        if row["source_id"] in {"S01", "S02", "S03", "S04", "S05", "S06"}
    ]
    sources = {row["source_id"]: row for row in week4_registry}
    pdfs = sorted(RAW.glob("*.pdf"))
    pdf_matches = sum(
        1
        for source in week4_registry
        if (RAW / source["filename"]).is_file()
        and sha256((RAW / source["filename"]).read_bytes()) == source["sha256"]
    )
    check("Source PDF hashes", (pdf_matches, len(week4_registry), len(pdfs)), (6, 6, 6))

    chunks = [
        json.loads(line)
        for line in (PROCESSED / "prepared_text.jsonl").read_text(
            encoding="utf-8"
        ).splitlines()
        if line.strip()
    ]
    tables = read_csv(PROCESSED / "prepared_tariff_rates.csv") + read_csv(
        PROCESSED / "prepared_relief_rules.csv"
    )

    chunk_fields = (
        "chunk_id",
        "text",
        "source_id",
        "source_url",
        "issuer",
        "title",
        "language",
        "published_date",
        "effective_from",
        "page",
        "source_sha256",
    )
    v1_pass = 0
    for chunk in chunks:
        source = sources.get(chunk.get("source_id"))
        try:
            page = int(chunk.get("page", ""))
        except (TypeError, ValueError):
            page = 0
        v1_pass += bool(
            all(str(chunk.get(field, "")).strip() for field in chunk_fields)
            and source
            and chunk["source_sha256"] == source["sha256"]
            and 1 <= page <= int(source["pages"])
        )
    for row in tables:
        source = sources.get(row.get("source_id"))
        try:
            page = int(row.get("page", ""))
        except (TypeError, ValueError):
            page = 0
        v1_pass += bool(
            all(row.get(field, "").strip() for field in ("source_id", "page", "effective_from"))
            and source
            and 1 <= page <= int(source["pages"])
            and row.get("verified_in_source") == "True"
        )
    check("V1 provenance (chunks + rows)", (v1_pass, len(chunks) + len(tables) - v1_pass), (44, 0))

    chunk_ids = [chunk["chunk_id"] for chunk in chunks]
    duplicate_chunk_ids = sum(count > 1 for count in Counter(chunk_ids).values())
    exact_texts = [normalized(chunk["text"]).lower() for chunk in chunks]
    duplicate_texts = sum(count > 1 for count in Counter(exact_texts).values())
    table_ids = [row.get("rate_id") or row.get("rule_id") for row in tables]
    duplicate_table_ids = sum(count > 1 for count in Counter(table_ids).values())
    check(
        "Duplicate chunk IDs / exact texts / table IDs",
        (duplicate_chunk_ids, duplicate_texts, duplicate_table_ids),
        (0, 0, 0),
    )

    near_duplicates = []
    for left, right in combinations(chunks, 2):
        left_words = set(re.findall(r"\b\w+\b", left["text"].lower()))
        right_words = set(re.findall(r"\b\w+\b", right["text"].lower()))
        score = len(left_words & right_words) / len(left_words | right_words)
        if score >= 0.5:
            near_duplicates.append(
                (tuple(sorted((left["chunk_id"], right["chunk_id"]))), score)
            )
    near_ids = {pair for pair, _ in near_duplicates}
    print(
        "Near duplicates (Jaccard >= 0.5): "
        + repr([(pair, round(score, 2)) for pair, score in near_duplicates])
    )
    check("Near-duplicate pair IDs", near_ids, EXPECTED_NEAR_DUPLICATES)

    pdf_pages = {}
    for source in week4_registry:
        reader = PdfReader(str(RAW / source["filename"]))
        pdf_pages[source["source_id"]] = [
            (
                page.extract_text(extraction_mode="layout") or "",
                page.extract_text() or "",
            )
            for page in reader.pages
        ]
    number_total = 0
    number_missing = 0
    for chunk in chunks:
        source_id = chunk["source_id"]
        page_number = int(chunk["page"])
        layout, plain = pdf_pages[source_id][page_number - 1]
        candidates = [normalized(layout), normalized(plain)]
        compact_candidates = [re.sub(r"\s+", "", text) for text in candidates]
        for number in re.findall(r"\d+(?:[.,]\d+)?", chunk["text"]):
            number_total += 1
            if not any(number in text for text in candidates + compact_candidates):
                number_missing += 1
    check("Chunk numbers found on cited pages", (number_total, number_missing), (217, 0))

    covered_pages = {
        (chunk["source_id"], int(chunk["page"]))
        for chunk in chunks
        if chunk["source_id"] in {"S02", "S03", "S04", "S05", "S06"}
    }
    uncovered = [
        (source["source_id"], page)
        for source in week4_registry
        if source["source_id"] in {"S02", "S03", "S04", "S05", "S06"}
        for page in range(1, int(source["pages"]) + 1)
        if (source["source_id"], page) not in covered_pages
    ]
    expected_uncovered = [
        ("S02", 5),
        ("S03", 3),
        ("S04", 3),
        ("S05", 3),
        ("S05", 4),
        ("S06", 3),
    ]
    check("Pages without chunks (S02-S06)", (len(uncovered), len(uncovered) + len(covered_pages)), (6, 18))
    check("Uncovered source pages", uncovered, expected_uncovered)

    pii_patterns = {
        "mobile": re.compile(r"\b01\d-?\d{7,8}\b"),
        "IC": re.compile(r"\b\d{6}-\d{2}-\d{4}\b"),
        "10-14 digit numbers": re.compile(r"\b\d{10,14}\b"),
    }
    pii_counts = {
        label: sum(len(pattern.findall(chunk["text"])) for chunk in chunks)
        for label, pattern in pii_patterns.items()
    }
    check("Personal-data matches (mobile / IC / 10-14 digits)", tuple(pii_counts.values()), (0, 0, 0))

    month_counts = {}
    for year, month in month_range((2025, 7), (2027, 1)):
        mid_month = date(year, month, 15)
        counts = Counter()
        for chunk in chunks:
            start = date.fromisoformat(chunk["effective_from"])
            end = date.fromisoformat(chunk["effective_to"]) if chunk.get("effective_to") else date.max
            if start <= mid_month <= end:
                counts[chunk["language"]] += 1
        month_counts[f"{year:04d}-{month:02d}"] = counts
    for month, counts in month_counts.items():
        print(f"Eligible chunks {month}: en={counts['en']}, ms={counts['ms']}")
    zero_english_months = sum(counts["en"] == 0 for counts in month_counts.values())
    check("Months with zero eligible English chunks", zero_english_months, 15)

    rates = read_csv(PROCESSED / "prepared_tariff_rates.csv")
    rules = read_csv(PROCESSED / "prepared_relief_rules.csv")
    rate_by_component = {}
    for row in rates:
        rate_by_component.setdefault(row["component"].lower(), []).append(row)
    rule_by_name = {}
    for row in rules:
        rule_by_name.setdefault(row["rule"].lower(), []).append(row)

    def value_set(rows):
        result = set()
        for row in rows:
            try:
                result.add(float(row["value"]))
            except (KeyError, ValueError):
                pass
        return result

    energy_conditions = " ".join(row["condition"].lower() for row in rate_by_component.get("energy", []))
    boundary_rows = rule_by_name.get("energy tier boundary", [])
    threshold_rows = rule_by_name.get("exemption threshold", [])
    afa_rows = rule_by_name.get("afa rate", [])
    service_rows = rule_by_name.get("service tax", [])
    rule_texts = [
        " ".join(str(value).lower() for value in row.values()) for row in rules
    ]
    afa_months = set()
    for year, month in month_range((2025, 7), (2026, 11)):
        mid_month = date(year, month, 15)
        if any(
            date.fromisoformat(row["effective_from"]) <= mid_month
            and (not row["effective_to"] or mid_month <= date.fromisoformat(row["effective_to"]))
            for row in afa_rows
        ):
            afa_months.add((year, month))
    expected_afa_months = set(month_range((2025, 7), (2026, 11)))
    service_rate_present = any(
        float(row["value"]) == 8 and row["unit"].lower() == "percent"
        for row in service_rows
    )
    v2 = {
        "G01": "energy both tiers",
        "G02": "capacity",
        "G03": "network",
        "G04": "retail",
        "G05": "1500 kWh tier boundary",
        "G06": "600 and 800 kWh thresholds",
        "G07": "AFA every month Jul 2025-Nov 2026",
        "G08": "AFA on all kWh above the threshold",
        "G09": "service tax rate",
        "G10": "service tax base",
        "G11": "16-band EEI",
        "G12": "KWTBB 1.6% above 300 kWh",
        "G13": "line rounding",
        "G14": "billing-period split by month",
    }
    v2_results = {
        "G01": "<= 1500" in energy_conditions and "> 1500" in energy_conditions,
        "G02": bool(rate_by_component.get("capacity")),
        "G03": bool(rate_by_component.get("network")),
        "G04": bool(rate_by_component.get("retail")),
        "G05": 1500.0 in value_set(boundary_rows),
        "G06": {600.0, 800.0}.issubset(value_set(threshold_rows)),
        "G07": afa_months == expected_afa_months,
        "G08": any(
            "afa" in text
            and bool(re.search(r"all\s+kwh.{0,80}above.{0,30}threshold", text))
            for text in rule_texts
        ),
        "G09": service_rate_present,
        "G10": any(
            "service tax" in text
            and "above" in text
            and "threshold" in text
            and "retail" in text
            and "28 days" in text
            for text in rule_texts
        ),
        "G11": any(
            "energy efficiency incentive" in text
            and bool(re.search(r"\b16\b.{0,30}band", text))
            for text in rule_texts
        ),
        "G12": any(
            "kwtbb" in text and "1.6%" in text and "300 kwh" in text
            for text in rule_texts
        ),
        "G13": any(
            "rounding" in text and ("line" in text or "nearest cent" in text)
            for text in rule_texts
        ),
        "G14": any(
            "billing period" in text
            and ("calendar month" in text or "split" in text)
            for text in rule_texts
        ),
    }
    for group_id, present in v2_results.items():
        print(f"V2 {group_id} ({v2[group_id]}): {'PASS' if present else 'FAIL'}")
    v2_pass_ids = {group_id for group_id, present in v2_results.items() if present}
    expected_v2_pass_ids = {"G01", "G02", "G03", "G04", "G05", "G06", "G09"}
    check("V2 rule groups passed", (len(v2_pass_ids), len(v2_results)), (7, 14))
    check("V2 passing group IDs", v2_pass_ids, expected_v2_pass_ids)

    manifest = json.loads((ROOT / "data" / "week3_manifest.json").read_text(encoding="utf-8"))
    for record in manifest["records"]:
        filename = record["source_filename"]
        if filename not in {"tariff_domestic_rp4.csv", "relief_rules.csv"}:
            continue
        data = (RAW / filename).read_bytes()
        lf = data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
        crlf = lf.replace(b"\n", b"\r\n")
        print(
            f"Manifest hash {filename}: raw={sha256(data) == record['source_sha256']}; "
            f"LF-normalized={sha256(lf) == record['source_sha256']}; "
            f"CRLF-normalized={sha256(crlf) == record['source_sha256']} "
            f"(informational, not asserted)"
        )

    if failures:
        raise SystemExit("Audit mismatches: " + ", ".join(failures))
    print("All expected Week 4 audit values match.")


if __name__ == "__main__":
    main()
