import csv
import hashlib
import html
import json
import logging
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
OUTPUT = ROOT / "data" / "pipeline_v2"
PDF_SOURCES = ("S02", "S03", "S04", "S05", "S06")
ALL_PDF_SOURCES = ("S01", *PDF_SOURCES)
REGISTRY = {
    row["source_id"]: row
    for row in pd.read_csv(RAW / "source_registry.csv", dtype=str, keep_default_na=False).to_dict("records")
}
logging.getLogger("pypdf").setLevel(logging.ERROR)


def sha256_file(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_csv(path):
    return pd.read_csv(path, dtype=str, keep_default_na=False)


def ensure_sources():
    missing, mismatched = [], []
    for source_id, row in REGISTRY.items():
        path = RAW / row["filename"]
        if not path.is_file():
            missing.append(source_id)
        elif sha256_file(path) != row["sha256"]:
            mismatched.append(source_id)
    if len(REGISTRY) != 10 or missing or mismatched:
        raise SystemExit(
            f"Source check failed: actual={len(REGISTRY)} expected=10; "
            f"missing={missing}; hash mismatches={mismatched}"
        )
    print("Source hashes: 10 of 10 match the registry.")


def source_path(source_id):
    return RAW / REGISTRY[source_id]["filename"]


def page_texts(path, mode="layout"):
    reader = PdfReader(str(path))
    out = []
    for page in reader.pages:
        raw = page.extract_text(extraction_mode=mode) or ""
        out.append([re.sub(r"[ \t]+", " ", line).strip() for line in raw.splitlines() if line.strip()])
    return out


def norm(text):
    return re.sub(r"\s+", "", text).lower()


def clean(value):
    value = "" if value is None else str(value)
    value = re.sub(r"<br\s*/?>|</p\s*>|</li\s*>", "\n", value, flags=re.I)
    value = re.sub(r"<[^>]*>", "", value)
    value = html.unescape(value)
    lines = [re.sub(r"\s+", " ", line).strip() for line in value.splitlines()]
    return "\n".join(line for line in lines if line)


def norm_web(source_id):
    text = source_path(source_id).read_text(encoding="utf-8")
    text = re.sub(r"<[^>]*>", "", text)
    return norm(html.unescape(text))


PDF_TEXT = {}


def norm_pdf(source_id, page):
    layout = " ".join(PDF_TEXT[source_id]["layout"][page - 1])
    plain = " ".join(PDF_TEXT[source_id]["plain"][page - 1])
    return norm(layout + " " + plain)


FURNITURE = [re.compile(pattern) for pattern in (
    r"^Page \d+ of \d+$", r"^\d+ of \d+$",
    r"^S\.A\. \d{4}/\d{2}/\d{2}_\d+ \(HQ\)$",
    r"^(PRESS RELEASE|SIARAN AKHBAR|KENYATAAN MEDIA)$")]
ST_LETTERHEAD = [re.compile(pattern) for pattern in (
    r"^www\.st\.gov\.my$", r"^Suruhanjaya Tenaga$", r"^12, Jalan Tun Hussein",
    r"^62100 Putrajaya", r"^T : \+603", r"^Toll Free", r"^\d{1,2} JUN 2025$")]
ST_FOOTER = re.compile(r"^MENGENAI SURUHANJAYA TENAGA$")
END_MARKER = re.compile(r"^(\*{5}|\*{3}TAMAT\*{3})$")
MIN_PAGE_CHARS = 80


def clean_pages(pages):
    log = {"furniture": 0, "st_letterhead": 0, "st_footer": 0, "after_end_marker": 0}
    cleaned, ended = [], False
    for page_no, lines in enumerate(pages, 1):
        kept, in_footer = [], False
        for line in lines:
            if ended:
                log["after_end_marker"] += 1
            elif END_MARKER.match(line):
                ended = True
                log["after_end_marker"] += 1
            elif in_footer or ST_FOOTER.match(line):
                in_footer = True
                log["st_footer"] += 1
            elif any(pattern.match(line) for pattern in FURNITURE):
                log["furniture"] += 1
            elif any(pattern.match(line) for pattern in ST_LETTERHEAD):
                log["st_letterhead"] += 1
            else:
                kept.append(line)
        cleaned.append((page_no, kept))
    return cleaned, log


PARA_END = re.compile(r"[.!?:;][\"”’)]*$")
LIST_START = re.compile(r"^(\d+\.\s|\([ivx]+\)\s|[-•]\s)")
SENTENCE_END = re.compile(r"(?<=[.!?])\s+(?=[A-Z(“\"])")


def is_heading(line, next_line=None):
    if len(line) > 80 or PARA_END.search(line) or LIST_START.match(line) or line.endswith(",") or not line[0].isupper():
        return False
    words = [word for word in re.findall(r"[A-Za-z][A-Za-z'’-]*", line) if len(word) > 3]
    if words and sum(word[0].isupper() for word in words) / len(words) >= 0.6:
        return True
    return len(line) <= 65 and bool(next_line) and len(next_line) >= 60 and next_line[0].isupper()


def to_blocks(lines):
    blocks, current = [], []
    prev_closed, last_heading = True, False
    for index, line in enumerate(lines):
        next_line = lines[index + 1] if index + 1 < len(lines) else None
        if current and (prev_closed or LIST_START.match(line)):
            blocks.append(("para", " ".join(current)))
            current = []
        if last_heading and (line.isupper() or len(line) <= 40) and is_heading(line, next_line):
            blocks[-1] = ("heading", blocks[-1][1] + " " + line)
            continue
        if not current and prev_closed and not last_heading and is_heading(line, next_line):
            blocks.append(("heading", line))
            last_heading = True
            continue
        last_heading = False
        current.append(line)
        prev_closed = bool(PARA_END.search(line))
    if current:
        blocks.append(("para", " ".join(current)))
    return blocks


def split_long(text, limit):
    parts, current = [], ""
    for sentence in SENTENCE_END.split(text):
        if current and len(current) + 1 + len(sentence) > limit:
            parts.append(current)
            current = sentence
        else:
            current = f"{current} {sentence}".strip()
    if current:
        parts.append(current)
    return [part[index:index + limit] for part in parts for index in range(0, len(part), limit)]


def structure_chunks(sid, size, overlap_paras=0, cleaned=None, page_status=None):
    chunks, heading = [], None
    for page_no, lines in cleaned[sid]:
        if page_status.get((sid, page_no)) != "content":
            continue
        body = []

        def flush(keep=0):
            if body:
                chunks.append({"page": page_no, "section": heading, "body": list(body)})
                carry = body[-keep:] if keep else []
                body.clear()
                body.extend(carry)

        for kind, text in to_blocks(lines):
            if kind == "heading":
                flush()
                heading = text
                continue
            room = size - (len(heading) + 1 if heading else 0)
            for piece in split_long(text, room) if len(text) > room else [text]:
                if body and len("\n".join(body)) + 1 + len(piece) > room:
                    flush(overlap_paras)
                    while body and len("\n".join(body)) + 1 + len(piece) > room:
                        body.pop(0)
                body.append(piece)
        flush()
    for chunk in chunks:
        text = "\n".join(chunk.pop("body"))
        chunk["text"] = f"{chunk['section']}\n{text}" if chunk["section"] else text
    return chunks


def apply_text_corrections(cleaned):
    corrections = read_csv(RAW / "text_corrections.csv")
    for row in corrections.to_dict("records"):
        sid, page_no = row["source_id"], int(row["page"])
        page = next(lines for number, lines in cleaned[sid] if number == page_no)
        matches = sum(line.count(row["find"]) for line in page)
        if matches != 1:
            raise AssertionError(
                f"Text correction {sid} page {page_no}: actual matches={matches}, expected=1"
            )
        for index, line in enumerate(page):
            page[index] = line.replace(row["find"], row["replace"], 1)


def build_pdf_records(sid, cleaned, page_status):
    meta = REGISTRY[sid]
    records = []
    for number, chunk in enumerate(structure_chunks(sid, 1000, 0, cleaned, page_status), 1):
        records.append({
            "chunk_id": f"{sid}-p{chunk['page']}-c{number:02d}",
            "text": chunk["text"],
            "source_id": sid,
            "source_file": f"data/raw/{meta['filename']}",
            "source_url": meta["url"],
            "issuer": meta["issuer"],
            "title": meta["title"],
            "doc_ref": meta["doc_ref"],
            "language": meta["language"],
            "published_date": meta["published_date"],
            "effective_from": meta["effective_from"],
            "effective_to": meta["effective_to"] or None,
            "page": chunk["page"],
            "section": chunk["section"],
            "processing": (
                "pypdf 5.9.0 layout extraction; cleaned: whitespace, page furniture, "
                "ST letterhead and footer, text after end marker; structure-aware chunks; "
                "max_chars=1000; overlap_paragraphs=0; page-bounded"
            ),
            "source_sha256": meta["sha256"],
            "status": "needs_review" if (sid, chunk["page"]) in {("S05", 1), ("S06", 1)} else "ready",
            "notes": "",
            "locator": "",
            "superseded_for_from": "",
            "superseded_for_to": "",
            "superseded_by": "",
            "override_reason": "",
        })
    return records


def assert_pdf_regression(records):
    old_path = ROOT / "data" / "processed" / "prepared_text.jsonl"
    previous = {
        row["chunk_id"]: row
        for row in (json.loads(line) for line in old_path.read_text(encoding="utf-8").splitlines() if line)
    }
    current = {row["chunk_id"]: row for row in records}
    if len(previous) != 33 or set(current) != set(previous):
        raise AssertionError(
            f"PDF chunk IDs: actual={len(current)}, expected=33 and identical Week 3 IDs"
        )
    for chunk_id, old in previous.items():
        expected = old["text"]
        if chunk_id == "S05-p1-c03":
            if expected.count("ko s bahan") != 1:
                raise AssertionError("Week 3 S05-p1-c03 does not contain one expected correction")
            expected = expected.replace("ko s bahan", "kos bahan", 1)
        if current[chunk_id]["text"] != expected:
            raise AssertionError(f"PDF text regression mismatch: {chunk_id}")
    print("PDF regression: 33 chunk IDs match; only S05-p1-c03 has the specified correction.")


def apply_chunk_overrides(records):
    by_id = {record["chunk_id"]: record for record in records}
    overrides = read_csv(RAW / "chunk_overrides.csv")
    seen = set()
    fields = (
        "effective_from",
        "effective_to",
        "status",
        "superseded_for_from",
        "superseded_for_to",
        "superseded_by",
    )
    for row in overrides.to_dict("records"):
        chunk_id = row["chunk_id"]
        if chunk_id not in by_id:
            raise AssertionError(f"Chunk override references unknown chunk_id: {chunk_id}")
        if chunk_id in seen:
            raise AssertionError(f"Duplicate chunk override: {chunk_id}")
        seen.add(chunk_id)
        record = by_id[chunk_id]
        for field in fields:
            value = row[field]
            if value:
                record[field] = None if field == "effective_to" and value.lower() == "open" else value
        if row["reason"]:
            record["override_reason"] = row["reason"]


def build_web_records():
    records = []
    source_json = {}
    for sid in ("S07", "S08"):
        source_json[sid] = json.loads(source_path(sid).read_text(encoding="utf-8"))
    keys = read_csv(RAW / "web_text_keys.csv")
    for row in keys.to_dict("records"):
        sid = row["source_id"]
        payload = source_json[sid]
        title = clean(payload[row["title_key"]]) if row["title_key"] else clean(row["title_text"])
        body = clean(payload[row["body_key"]])
        text = f"{title}\n{body}"
        if len(text) > 1200:
            raise AssertionError(
                f"Web chunk {sid}-{row['body_key']}-c01 length={len(text)}, expected <=1200"
            )
        meta = REGISTRY[sid]
        records.append({
            "chunk_id": f"{sid}-{row['body_key']}-c01",
            "text": text,
            "source_id": sid,
            "source_file": f"data/raw/{meta['filename']}",
            "source_url": meta["url"],
            "issuer": meta["issuer"],
            "title": meta["title"],
            "doc_ref": meta["doc_ref"],
            "language": row["language"],
            "published_date": meta["published_date"],
            "effective_from": row["effective_from"],
            "effective_to": None if row["effective_to"].lower() == "open" else row["effective_to"],
            "page": "",
            "section": title,
            "processing": "myTNB JSON key, HTML stripped",
            "source_sha256": meta["sha256"],
            "status": "ready",
            "notes": "",
            "locator": row["body_key"],
            "superseded_for_from": "",
            "superseded_for_to": "",
            "superseded_by": "",
            "override_reason": "",
        })
    if len(records) != 26 or Counter(record["language"] for record in records) != {"en": 13, "ms": 13}:
        raise AssertionError(
            f"Web chunks: actual={len(records)}; expected=26 (13 EN + 13 BM)"
        )
    return records, source_json


def js_fuel_by_month(text):
    match = re.search(r"const FUEL_BY_MONTH\s*=\s*\{(.*?)\};", text, re.S)
    if not match:
        raise AssertionError("FUEL_BY_MONTH not found in S09")
    return {
        month: float(value) * 100
        for month, value in re.findall(r'"(\d{4}-\d{2})"\s*:\s*([+-]?\d+(?:\.\d+)?)', match.group(1))
    }


def js_domestic_tiers(text):
    match = re.search(r"const DOMESTIC\s*=\s*\{.*?INCENTIVE_TIERS:\s*\[(.*?)\]", text, re.S)
    if not match:
        raise AssertionError("DOMESTIC.INCENTIVE_TIERS not found in S09")
    return [
        (int(maximum), float(rate) * 100)
        for maximum, rate in re.findall(
            r"\{\s*max:\s*(\d+),\s*rate:\s*([+-]?\d+(?:\.\d+)?)\s*\}", match.group(1)
        )
    ]


def source_page_count(source_id, page):
    return 1 <= int(page) <= int(REGISTRY[source_id]["pages"])


def verify_tariff_rates():
    rates = read_csv(RAW / "tariff_domestic_rp4.csv")
    verified = []
    page_text = norm_pdf("S01", 1)
    for row in rates.to_dict("records"):
        label_found = norm(row["label_in_source"]) in page_text
        target = f"{round(float(row['rate']), 2):.2f}"
        rate_found = target in page_text
        verified.append(label_found and rate_found)
    rates["verified_in_source"] = ["True" if value else "False" for value in verified]
    if not all(verified):
        raise AssertionError(f"Tariff verification failed: {verified}")
    return rates


def verify_charge_rules(source_json):
    rules = read_csv(RAW / "charge_rules.csv")
    pdf_sources = set(PDF_SOURCES) | {"S01"}
    web_norms = {sid: norm_web(sid) for sid in ("S07", "S08", "S09", "S10")}
    verified = []
    for row in rules.to_dict("records"):
        if row["rule_id"] == "P07" and row["status"] == "assumed":
            verified.append(bool(row["note"]))
            continue
        source_id = row["source_id"]
        evidence = norm(row["evidence_text"])
        if source_id in pdf_sources:
            found = source_page_count(source_id, row["page"]) and evidence in norm_pdf(
                source_id, int(row["page"])
            )
        elif source_id in web_norms:
            found = bool(evidence) and evidence in web_norms[source_id]
        else:
            found = False
        verified.append(found)
    rules["verified_in_source"] = [
        "assumed" if row["rule_id"] == "P07" and row["status"] == "assumed"
        else "True" if value else "False"
        for row, value in zip(rules.to_dict("records"), verified)
    ]
    failed = [
        row["rule_id"]
        for row, value in zip(rules.to_dict("records"), verified)
        if not value
    ]
    if failed:
        raise AssertionError(f"Charge-rule verification failed: {failed}")
    return rules


def verify_afa_monthly(source_json, rates_js):
    afa = read_csv(RAW / "afa_monthly.csv")
    json_rows = source_json["S07"]["afaGraph"]["data"]
    month_number = dict(zip(
        "JAN FEB MAR APR MAY JUN JUL AUG SEP OCT NOV DEC".split(),
        range(1, 13),
    ))
    web_afa = {
        f"{row['year']}-{month_number[row['month']]:02d}": float(row["value"])
        for row in json_rows
    }
    fuel = js_fuel_by_month(rates_js)
    verified = []
    for row in afa.to_dict("records"):
        month = row["month"]
        value = float(row["afa_sen_per_kwh"])
        web_match = row["status"] != "declared" or (
            month in web_afa and round(web_afa[month], 2) == round(value, 2)
        )
        fuel_match = month in fuel and round(fuel[month], 2) == round(value, 2)
        computed, offset = row["computed_afa_sen_per_kwh"], row["kwie_offset_sen_per_kwh"]
        if computed or offset:
            text = norm_web("S07")
            values_found = bool(computed and offset) and all(
                f"{round(float(number), 2):.2f}" in text for number in (computed, offset)
            )
        else:
            values_found = True
        verified.append(web_match and fuel_match and values_found)
    afa["verified_in_source"] = ["True" if value else "False" for value in verified]
    if len(web_afa) != 17 or len(fuel) != 20 or not all(verified):
        failed = [row["month"] for row, ok in zip(afa.to_dict("records"), verified) if not ok]
        raise AssertionError(
            f"AFA verification: JSON months={len(web_afa)} expected=17; "
            f"fuel entries={len(fuel)} expected=20; failed rows={failed}"
        )
    return afa


def verify_eei_tiers(rates_js):
    eei = read_csv(RAW / "eei_tiers.csv")
    actual = js_domestic_tiers(rates_js)
    rows = eei.to_dict("records")
    verified = []
    for row, expected in zip(rows, actual):
        verified.append(
            int(row["kwh_to"]) == expected[0]
            and round(float(row["rate_sen_per_kwh"]), 2) == round(expected[1], 2)
        )
    if len(rows) != 16 or len(actual) != 17 or actual[-1] != (1500, 0.0) or not all(verified):
        raise AssertionError(
            f"EEI verification: CSV bands={len(rows)} expected=16; "
            f"JS bands={len(actual)} expected=17 incl. (1500, 0); results={verified}"
        )
    eei["verified_in_source"] = ["True" if value else "False" for value in verified]
    return eei


def write_jsonl(path, records):
    with path.open("w", encoding="utf-8", newline="\n") as file:
        for record in records:
            file.write(json.dumps(record, ensure_ascii=False) + "\n")


def main():
    ensure_sources()
    pdf_text = {
        sid: {"layout": page_texts(source_path(sid), "layout"), "plain": page_texts(source_path(sid), "plain")}
        for sid in ALL_PDF_SOURCES
    }
    global PDF_TEXT
    PDF_TEXT = pdf_text
    for sid in ALL_PDF_SOURCES:
        if len(pdf_text[sid]["layout"]) != int(REGISTRY[sid]["pages"]):
            raise AssertionError(f"{sid} page count differs from the registry")

    doc_sources = [sid for sid, row in REGISTRY.items() if row["pipeline"] == "documents"]
    cleaned, clean_log, page_status = {}, {}, {}
    for sid in doc_sources:
        cleaned[sid], clean_log[sid] = clean_pages(pdf_text[sid]["layout"])
        for page_no, lines in cleaned[sid]:
            size = sum(len(line) for line in lines)
            page_status[(sid, page_no)] = "content" if size >= MIN_PAGE_CHARS else "no usable text"
    apply_text_corrections(cleaned)

    pdf_records = [
        record for sid in doc_sources
        for record in build_pdf_records(sid, cleaned, page_status)
    ]
    assert_pdf_regression(pdf_records)
    web_records, source_json = build_web_records()
    records = pdf_records + web_records
    apply_chunk_overrides(records)
    expected_counts = {"S02": 9, "S03": 7, "S04": 7, "S05": 6, "S06": 4, "S07": 13, "S08": 13}
    actual_counts = dict(Counter(record["source_id"] for record in records))
    if len(records) != 59 or actual_counts != expected_counts:
        raise AssertionError(
            f"Document chunks: actual={len(records)}, per source={actual_counts}; "
            f"expected=59, per source={expected_counts}"
        )
    print("Document chunks:", len(records), actual_counts)

    rates_js = source_path("S09").read_text(encoding="utf-8")
    tables = {
        "prepared_tariff_rates.csv": verify_tariff_rates(),
        "prepared_charge_rules.csv": verify_charge_rules(source_json),
        "prepared_afa_monthly.csv": verify_afa_monthly(source_json, rates_js),
        "prepared_eei_tiers.csv": verify_eei_tiers(rates_js),
    }
    expected_rows = {
        "prepared_tariff_rates.csv": 5,
        "prepared_charge_rules.csv": 12,
        "prepared_afa_monthly.csv": 20,
        "prepared_eei_tiers.csv": 16,
    }
    for name, table in tables.items():
        if len(table) != expected_rows[name]:
            raise AssertionError(
                f"{name} rows: actual={len(table)}, expected={expected_rows[name]}"
            )

    documents_path = OUTPUT / "documents" / "prepared_text.jsonl"
    tables_dir = OUTPUT / "tables"
    documents_path.parent.mkdir(parents=True, exist_ok=True)
    tables_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(documents_path, records)
    output_records = [{
        "path": documents_path.relative_to(ROOT).as_posix(),
        "sha256": sha256_file(documents_path),
        "rows": len(records),
    }]
    for name, table in tables.items():
        path = tables_dir / name
        table.to_csv(path, index=False, lineterminator="\n")
        output_records.append({
            "path": path.relative_to(ROOT).as_posix(),
            "sha256": sha256_file(path),
            "rows": len(table),
        })

    manifest = {
        "pipeline_version": "v2",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "configuration": {
            "pdf_sources": list(PDF_SOURCES),
            "chunk_size": 1000,
            "overlap_paragraphs": 0,
            "page_bounded": True,
            "text_corrections": "data/raw/text_corrections.csv",
            "chunk_overrides": "data/raw/chunk_overrides.csv",
        },
        "sources": [
            {
                "source_id": sid,
                "path": f"data/raw/{row['filename']}",
                "sha256": row["sha256"],
            }
            for sid, row in REGISTRY.items()
        ],
        "outputs": output_records,
        "note": "text files written with LF; Week 3 manifest raw CSV hashes were CRLF-based (Week 4 finding)",
    }
    manifest_path = OUTPUT / "pipeline_manifest.json"
    with manifest_path.open("w", encoding="utf-8", newline="\n") as file:
        json.dump(manifest, file, indent=2, ensure_ascii=False)
        file.write("\n")
    print("Wrote V2 outputs and manifest.")


if __name__ == "__main__":
    main()
