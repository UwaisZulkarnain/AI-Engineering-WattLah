# Week 3 Data Inventory: WattLah

Version: 1.0 (16 November 2026)
Requirement IDs refer to [week2_requirements.md](week2_requirements.md). Notebook: [notebooks/week3_pipeline.ipynb](../notebooks/week3_pipeline.ipynb).

## A1: From Topic 2 Requirements to Data Needs

| Requirement ID | Needed information | Candidate source | Why usable / constraint |
|---|---|---|---|
| FR1, NFR1: itemised bill exact to the sen | Domestik Am energy, capacity, network and retail rates, with the period they apply | S01, the RP4 tariff schedule (1 Jul 2025 to 31 Dec 2027), page 1 | Official schedule for the whole RP4 period. It is a table, so rates are transcribed to CSV and every value is checked against the PDF text |
| FR4, RAI1: rules for the right billing month | Exemption thresholds, the monthly AFA rate and service tax, each with an effective period | S03 and S04 (15 Sep 2026), S05 (18 Sep 2026), S06 (2 Oct 2026) | Official TNB notices. They contradict each other on purpose: 600 kWh before the change, 800 kWh for Sep to Dec 2026. Only an effective date on every item tells them apart |
| FR2, FR5, NFR2: explanations with a source | Plain explanations of the tariff structure, AFA and the relief, with issuer, title, date and page | S02 (ST, 20 Jun 2025) and S03 to S06 | Regulator and utility statements written for the public. Page numbers are kept on every chunk for citations |
| FR6, RAI3: BM and English at equal quality | The same content in both languages | S03 (EN) and S04 (BM) are the same release | A matched pair, so later parity tests compare answers grounded in identical facts |
| NFR5: updates as data | One registry row per source and one CSV row per rate or rule | `source_registry.csv`, `tariff_domestic_rp4.csv`, `relief_rules.csv` | A new AFA month is one new row; no code change |
| RAI4: no personal data | Press releases with the contact block removed | S03 page 3 lists press officers' names and mobile numbers | Removed in cleaning; the output check fails the run if a mobile number appears in any chunk |

## A4: Source Inventory

All six sources were retrieved on 16 November 2026. Raw PDFs stay in `data/raw/` locally and are **not committed** (Week 2 constraint). [`data/raw/source_registry.csv`](../data/raw/source_registry.csv) holds each file's URL and SHA-256, so anyone can download the same file and prove it is identical.

| Source ID | Filename / URL | Type and purpose | Version / date / owner | Access / rights | Inspection evidence |
|---|---|---|---|---|---|
| S01 | `tnb_jadual_tarif_2025-07-02.pdf` <br>[mytnb.com.my](https://www.mytnb.com.my/tariff/PDF/jadual-tarif-elektrik-terkini-2-julai-2025.pdf) | Unstructured PDF holding a table, 7 pages, BM. Rates for the Tariff Rate Table (Pathway B) | Schedule for 1 Jul 2025 to 31 Dec 2027, file dated 2 Jul 2025. TNB, under the ST-approved RP4 tariff | Public. Not redistributed | 7 pages, 676 to 1,512 characters each. Plain extraction keeps Domestik Am rows on one line: `Caj Tenaga - Untuk penggunaan ≤1500 kW sen/kWj 27.03`. Automatic parsing of page 1 recovered 17 of 21 rows; 4 lost their values to broken reading order. Source typos: `≤1500 kW` (page 1), `sen/kWi` (page 7) |
| S02 | `st_kenyataan_media_2025-06-20.pdf` <br>[mytnb.com.my](https://www.mytnb.com.my/tariff/PDF/kenyataan-media-suruhanjaya-tenaga-jadual-elektrik-baharu-20-jun-2025.pdf) | Unstructured PDF, 5 pages, BM. Tariff structure, base rate, Energy Efficiency Incentive, ToU hours (Pathway A) | Media statement, 20 Jun 2025. Suruhanjaya Tenaga | Public. Not redistributed. **The original st.gov.my link returned HTTP 404 on 16 Nov 2026**; the copy TNB hosts was used | 5 pages: 1,758 / 1,976 / 1,977 / 1,687 / 484 characters. Page 5 is an image of a worked bill example: only its caption extracts (silent failure). Same footer paragraph on all 5 pages. The file was re-saved from a browser (Aug 2026) and raises PDF cross-reference warnings, but every page loads. Sample: `ditetapkan pada kadar 45.40 sen/kWj` |
| S03 | `tnb_20260915_23_bi.pdf` <br>[tnb.com.my](https://www.tnb.com.my/assets/press_releases/20260915_23_bi.pdf) | Unstructured PDF, 3 pages, English. AFA explanation, September AFA rate, 600 kWh protection (Pathway A) | Press release S.A. 2026/09/15_23, 15 Sep 2026. TNB | Public. Not redistributed | 2,216 / 2,443 / 827 characters. Page 3 is company profile and press contacts with personal mobile numbers. Plain extraction broke words (`c ustomers`); layout extraction does not. Sample: `The AFA rate for September 2026 is +3.67 sen/kWh.` |
| S04 | `tnb_20260915_23_bm.pdf` <br>[tnb.com.my](https://www.tnb.com.my/assets/press_releases/20260915_23_bm.pdf) | Unstructured PDF, 3 pages, BM. BM version of S03 (Pathway A) | Siaran akhbar S.A. 2026/09/15_23, 15 Sep 2026. TNB | Public. Not redistributed | 2,257 / 2,256 / 1,066 characters. Same structure as S03. Sample: `Kadar AFA bagi September 2026 ialah +3.67 sen/kWj.` |
| S05 | `tnb_20260918_24_bm.pdf` <br>[tnb.com.my](https://www.tnb.com.my/assets/press_releases/20260918_24_bm.pdf) | Unstructured PDF, 4 pages, BM. Threshold raised to 800 kWh for Sep to Dec 2026 (Pathway A) | Siaran akhbar S.A. 2026/09/18_24, 18 Sep 2026. TNB | Public. Not redistributed | 2,104 / 2,028 / 939 / 1,044 characters. Page 4 is an infographic repeating pages 1 to 2 with broken reading order (`8 JUTA 1 JUTA90%`). Extraction artifact in the text: `ko s bahan` for `kos bahan` |
| S06 | `tnb_20261002_25_bi.pdf` <br>[tnb.com.my](https://www.tnb.com.my/assets/press_releases/20261002_25_bi.pdf) | Unstructured PDF, 3 pages, English. 800 kWh relief, pro-rated September credit, eligibility table (Pathway A) | Press release S.A. 2026/10/02_25, 2 Oct 2026. TNB | Public. Not redistributed | 1,854 / 1,600 / 34 characters. Page 3 holds only the reference number and page number. Page 1's eligibility table extracts as lines: row order kept, columns lost |
| C01 | `data/raw/tariff_domestic_rp4.csv` | Structured CSV, 5 rows. Domestik Am rates from S01 page 1 (Pathway B) | v1, 16 Nov 2026. Own transcription | Own work. Committed | 5 rows x 12 columns, no empty cells, no duplicates. 5 of 5 rates found in the Domestik Am block of S01 page 1 |
| C02 | `data/raw/relief_rules.csv` | Structured CSV, 6 rows. Thresholds, AFA rate, service tax, tier boundary from S01, S03 and S06 (Pathway B) | v1, 16 Nov 2026. Own transcription | Own work. Committed | 6 rows x 11 columns; 2 rules open-ended by design (P01, P05). 6 of 6 evidence texts found on their cited pages |

Out of scope and not transcribed: ToU, non-domestic, agricultural and other tariffs on S01 pages 1 to 7 (Week 2, Section 0).

## Raw vs Prepared Storage

| Layer | Location | In the repo? |
|---|---|---|
| Raw official PDFs | `data/raw/*.pdf` | No. URL and SHA-256 in `source_registry.csv` |
| Curated raw tables | `data/raw/tariff_domestic_rp4.csv`, `relief_rules.csv`, `source_registry.csv` | Yes |
| Prepared (Part B) | `data/processed/prepared_text.jsonl` (33 chunks), `prepared_tariff_rates.csv`, `prepared_relief_rules.csv` | Yes |
| Lineage | `data/week3_manifest.json` (7 entries), `data/pipeline_v1/*/pipeline_manifest.json` | Yes |

## Checkpoint A

**Which Topic 2 requirement needs this data?** Every source maps to the A1 table: S01 to FR1 and NFR1, S03 to S06 to FR4 and RAI1, all five statements to FR2 and FR5, the S03 and S04 pair to FR6 and RAI3.

**What was actually loaded?** The page counts, characters per page and samples above, from notebook cell A3. Three pages load without usable text (S02 page 5, S06 page 3, and S05 page 4 in readable order). They are flagged, not trusted.
