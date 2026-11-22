# WattLah: Your TNB Power Bill Guide and Decoder

**Semak bil elektrik anda.**

> WattLah explains Malaysian household electricity bills in BM and English. It grounds every answer in official tariff documents and computes every figure with a verified calculator.

*Independent student project for SAIA3113 AI Engineering, UTM. Not affiliated with or endorsed by Tenaga Nasional Berhad (TNB).*

## Problem Statement

Since July 2025, a domestic TNB bill combines energy, capacity, network and retail charges, an Energy Efficiency Incentive, a 1.6% Renewable Energy Fund levy (KWTBB), service tax, and an Automatic Fuel Adjustment (AFA) that changes every month. On top of that, relief thresholds change at short notice. When a bill rises, households cannot easily tell whether the cause is usage, the AFA, or crossing a threshold.

General chatbots go out of date and can get the arithmetic wrong, while calculators give a number without explaining it. WattLah combines retrieval over dated official documents with a deterministic calculator, so it can explain the change correctly and show its working. The AI handles what rules cannot: free form questions in BM, English or a mix of both, matched to the right rule for the right billing month.

## Evidence of the Problem

- **AFA flipped from rebates to surcharges in 2026.** Customers had nine months of rebates, then surcharges from May 2026 after the West Asia crisis pushed up fuel costs, reaching +3.67 sen/kWh in September 2026. TNB issued a press release to address bill concerns ([TNB, 15 Sep 2026](https://www.tnb.com.my/assets/press_releases/20260915_23_bi.pdf)).
- **The relief rules move faster than people can follow.** The exemption threshold was 600 kWh on 15 September 2026, then raised to 800 kWh two days later for September to December 2026 ([Bernama, 2 Oct 2026](https://www.bernama.com/bm/news.php?id=2614501)). About 8 million households are now covered, while those above the threshold stay exposed ([The Vibes, 15 Oct 2026](https://www.thevibes.com/articles/news/128374/global-fuel-shock-drives-electricity-costs-but-8-million-malaysian-households-remain-protected-dpm-ii)).

## Initial Related Work / Existing Approaches

- **TNB itemised bill (since July 2025):** lists each charge but does not explain why the total changed or answer questions ([Malay Mail, 1 Jul 2025](https://www.malaymail.com/news/malaysia/2025/07/01/new-tnb-itemised-electricity-bills-will-help-consumers-better-understand-manage-energy-use/182364)).
- **Third party bill calculators:** compute an estimate, but the user must look up the month's AFA rate. ToU is excluded and nothing is explained ([Paul Tan TNB Bill Calculator](https://paultan.org/tnb-calculator/)).
- **TNB's own bill calculator (myTNB tariff page):** estimates a bill from kWh and billing dates with TNB's published method, including the monthly AFA. It states the result is an estimate, and it does not explain each charge, answer questions or cite sources ([myTNB tariff page](https://www.mytnb.com.my/tariff/index.html)). WattLah uses this method as its calculation reference (64 of 64 reference bills match).
- **RAG chatbot for PLN complaints (Putro et al., 2025):** shows retrieval in a local language works for a utility. However, it is grounded in complaint records rather than tariff rules, and BLEU and ROUGE scores cannot catch a wrong amount ([Jurnal Infomedia](https://e-jurnal.pnl.ac.id/infomedia/article/view/7169)).
- **General purpose AI assistants:** have a fixed knowledge cutoff and compute numbers inside the model. In our Week 1 lab, Claude reported a cutoff of about June 2026, before the September threshold change.

## Engineering Gap / Limitation

No accessible tool combines three things:
- retrieval over official tariff documents filtered by billing period
- verified arithmetic
- plain BM and English explanations of month to month bill changes

## Project Objectives

- **O1:** To design a bilingual, document grounded assistant that explains Peninsular Malaysia domestic electricity bills using official tariff documents tagged with their effective dates.
- **O2:** To develop the assistant with date aware retrieval, a deterministic bill calculator tool, and guardrails for source citation, applicable billing period, scope and personal data.
- **O3:** To evaluate the assistant on calculation accuracy against reference bills, groundedness, BM and English answer parity, scope handling and latency.

Full requirements, evaluation criteria and architecture (V1 in Week 2, [V2](docs/architecture_v2.png) after the Week 4 audit): [docs/week2_requirements.md](docs/week2_requirements.md), [docs/week2_evaluation_criteria.md](docs/week2_evaluation_criteria.md), [docs/week2_architecture_decisions.md](docs/week2_architecture_decisions.md).

## Target Users

- **Primary:** Domestic TNB customers in Peninsular Malaysia, especially households near the 600 or 800 kWh threshold.
- **Secondary:** Family members who manage bills for elderly parents.

## Data Sources

Ten official sources, listed with URL, issuer, effective period and SHA-256 in [`data/raw/source_registry.csv`](data/raw/source_registry.csv):

| ID | Document | Issuer, date | Used for |
|---|---|---|---|
| S01 | [Jadual Tarif Elektrik, 1 Jul 2025 to 31 Dec 2027](https://www.mytnb.com.my/tariff/PDF/jadual-tarif-elektrik-terkini-2-julai-2025.pdf) | TNB (RP4 schedule), 2 Jul 2025 | Tariff rates |
| S02 | [Kenyataan Media: Jadual Elektrik Baharu](https://www.mytnb.com.my/tariff/PDF/kenyataan-media-suruhanjaya-tenaga-jadual-elektrik-baharu-20-jun-2025.pdf) | Suruhanjaya Tenaga, 20 Jun 2025 | Knowledge Source, worked example |
| S03 / S04 | AFA mechanism and September 2026 rate ([EN](https://www.tnb.com.my/assets/press_releases/20260915_23_bi.pdf), [BM](https://www.tnb.com.my/assets/press_releases/20260915_23_bm.pdf)) | TNB, 15 Sep 2026 | Knowledge Source |
| S05 | [Aras perlindungan dinaikkan ke 800kWj](https://www.tnb.com.my/assets/press_releases/20260918_24_bm.pdf) | TNB, 18 Sep 2026 | Knowledge Source |
| S06 | [Protection threshold raised to 800 kWh](https://www.tnb.com.my/assets/press_releases/20261002_25_bi.pdf) | TNB, 2 Oct 2026 | Knowledge Source, rules |
| S07 / S08 | myTNB tariff page text ([EN](https://www.mytnb.com.my/tariff/EN.json), [BM](https://www.mytnb.com.my/tariff/BM.json)) | TNB, retrieved Nov 2026 | Monthly AFA, charge rules, Knowledge Source in both languages |
| S09 | [myTNB calculator rates](https://www.mytnb.com.my/tariff/js/rates.js) | TNB, retrieved Nov 2026 | EEI bands, thresholds, calendar month split, rounding |
| S10 | [myTNB domestic bill calculator](https://www.mytnb.com.my/tariff/js/calculator-newDomestic.js) | TNB, retrieved Nov 2026 | Service tax base, KWTBB base, reference bills |

Source files are not committed. Download them from the URLs above into `data/raw/`; the pipeline checks each file against its registered SHA-256. The myTNB files (S07 to S10) change when TNB declares a new AFA rate, so a hash mismatch means the sources must be re-verified before release. Extracted text from these official publications is kept for this coursework with attribution; the right to republish it publicly has not been confirmed.

## Data Quality Gate

**Week 4 audit** ([report](docs/week4_data_quality_report.md)): text chunks GO WITH CONDITIONS; tables HOLD (7 of 14 rule groups, 0 of 50 TNB reference bills reproducible).

**Re-review, 22 November 2026** (`python src/quality_gate.py`, results in [`docs/week4_evidence/rereview/`](docs/week4_evidence/rereview/)):
- **Tables: GO.** 14 of 14 rule groups present; all 64 reference bills in [`evaluation/reference_bills.csv`](evaluation/reference_bills.csv) reproduce to the sen, including 13 bills that span the 1 September 2026 threshold change.
- **Text: GO WITH CONDITIONS.** The four 600 kWh chunks are dated to the period they are true for; English text now exists for every month. Condition: RAI3 parity is still to be measured once retrieval is built.
- **Still open:** 2027 protection threshold (shown as two labelled scenarios); public republication rights; S06 eligibility table kept as `needs_review`.

## Repository Structure

```
docs/                       lab reports, scope, architecture (V1 and V2) and pipeline diagrams
docs/week4_evidence/        Week 4 audit evidence; rereview/ holds the 22 Nov 2026 re-review
data/raw/                   source registry and curated tables (source files downloaded locally, not committed)
data/processed/             Week 3 prepared chunks and tables (kept as the Week 3 record)
data/pipeline_v1/           Week 3 pipeline runs with their manifests
data/pipeline_v2/           current prepared data: chunks, tables and manifest
data/week3_manifest.json    Week 3 lineage
src/pipeline_v2.py          builds data/pipeline_v2 from data/raw
src/calculator.py           deterministic bill calculator (TNB's published method, values from data tables)
src/quality_gate.py         provenance, rule completeness, reference bills and coverage checks
src/week4_audit.py          reproduces the Week 4 audit counts on the Week 3 data
tests/                      calculator tests
notebooks/                  Colab notebooks (week3_pipeline.ipynb)
evaluation/                 test sets and results (reference_bills.csv)
prompts/                    system and task prompts
```

Run order: `python src/pipeline_v2.py`, then `python src/quality_gate.py`, then `python -m pytest tests`.

## Weekly Progress

| Week | Focus | Deliverable | Status |
|------|-------|-------------|--------|
| W1 | System map + project scope | README + docs | ✅ |
| W2 | Requirements, evaluation criteria, V1 architecture | `docs/week2_*` | ✅ |
| W3 | V1 data pipeline: ingestion, cleaning, chunking, verified rate table, lineage | `notebooks/week3_pipeline.ipynb`, `docs/week3_*`, `data/` | ✅ |
| W4 | Data quality and bias audit | [`docs/week4_data_quality_report.md`](docs/week4_data_quality_report.md) | ✅ |
| W4 follow-up | Data fixes from the audit, V2 pipeline, calculator, reference bills, Week 2 v1.1, V2 architecture | `data/pipeline_v2/`, `src/`, `evaluation/`, [`docs/architecture_v2.png`](docs/architecture_v2.png) | ✅ |
