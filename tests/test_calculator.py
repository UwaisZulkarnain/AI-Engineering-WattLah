import csv
import shutil
from datetime import date
from pathlib import Path

import pytest

from src.calculator import AfaNotDeclared, UnsupportedPeriod, compute_bill


ROOT = Path(__file__).resolve().parents[1]
TABLES = ROOT / "data" / "pipeline_v2" / "tables"
REFERENCE_BILLS = ROOT / "evaluation" / "reference_bills.csv"
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


def _reference_bills():
    with REFERENCE_BILLS.open(encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


@pytest.mark.parametrize("bill", _reference_bills(), ids=lambda bill: bill["case_id"])
def test_reference_bills_match(bill):
    results = compute_bill(
        int(bill["kwh"]),
        date.fromisoformat(bill["billing_start"]),
        date.fromisoformat(bill["billing_end"]),
    )
    assert len(results) == 1
    result = results[0]
    assert result.scenario == bill["scenario"]
    for field in MONEY_FIELDS:
        assert abs(getattr(result, field) - float(bill[REFERENCE_FIELDS[field]])) < 0.005


def _copy_tables(destination):
    destination.mkdir(parents=True, exist_ok=True)
    for source in TABLES.glob("*.csv"):
        shutil.copyfile(source, destination / source.name)
    return destination


def _add_afa_row(data_dir, month, value):
    path = data_dir / "prepared_afa_monthly.csv"
    with path.open(encoding="utf-8-sig", newline="") as file:
        rows = list(csv.DictReader(file))
        fieldnames = rows[0].keys()
    rows.append({
        "month": month,
        "afa_sen_per_kwh": value,
        "status": "declared",
        "computed_afa_sen_per_kwh": "",
        "kwie_offset_sen_per_kwh": "",
        "source_id": "S09",
        "also_in": "",
        "locator": "FUEL_BY_MONTH",
        "note": "Test-only declared AFA value",
    })
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def test_undeclared_afa_only_blocks_chargeable_bill():
    with pytest.raises(AfaNotDeclared):
        compute_bill(900, date(2026, 12, 1), date(2026, 12, 31))
    result = compute_bill(500, date(2026, 12, 1), date(2026, 12, 31))[0]
    assert result.afa == 0


def test_short_billing_period_is_unsupported():
    with pytest.raises(UnsupportedPeriod):
        compute_bill(900, date(2026, 11, 1), date(2026, 11, 20))


def test_2027_returns_both_relief_scenarios(tmp_path):
    data_dir = _copy_tables(tmp_path)
    _add_afa_row(data_dir, "2027-01", "1.00")
    results = compute_bill(700, date(2027, 1, 1), date(2027, 1, 31), data_dir=data_dir)
    assert [result.scenario for result in results] == ["relief_continues", "relief_ends"]
    continues, ends = results
    assert continues.assumed
    assert continues.afa == 0
    assert not ends.assumed
    assert ends.afa == 7.00
    assert ends.retail == 10.00


def test_new_declared_afa_row_is_used_without_code_change(tmp_path):
    data_dir = _copy_tables(tmp_path)
    _add_afa_row(data_dir, "2026-12", "3.50")
    result = compute_bill(900, date(2026, 12, 1), date(2026, 12, 31), data_dir=data_dir)[0]
    assert result.afa == 31.50
