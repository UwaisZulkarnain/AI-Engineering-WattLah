# Week 4 Data Quality and Bias Report: Wattlah

**Project:** Wattlah, "Semak bil elektrik anda" | **Author:** Muhammad Uwais Bin Zulkarnain (A24AI0114) | **Course:** SAIA3113 AI Engineering
**Audit date:** 20 November 2026 | **Repository state audited:** commit `35b9a07` (Week 3 data, unchanged since `e880a18`)
**Version 1.1 (22 November 2026):** aligned with the Topic 4 lecture terms (rule anatomy, defect types, bias types and propagation, data leaving the system) and re-review added as Appendix C. Findings and numbers are unchanged.

Labels used: **[Observed]** checked directly in the data or source, **[Inferred risk]** a likely effect not yet tested, **[N.V.]** not verified.

## 1. Project and Data Overview

| Field | Record |
|---|---|
| Purpose and users | Bilingual (BM and English) explainer for Peninsular Malaysia households on the TNB domestic general tariff. Users type their kWh and billing dates; Wattlah computes the bill with a deterministic calculator and explains each charge from official documents (retrieval over dated sources). |
| Requirements audited | **NFR1** Correctness (calculation): bill amounts must match the published tariff for every supported case. Needs every charge rule, rate and monthly AFA value. **RAI1** Wrong period: only rules in force for the billing month may be used. Needs a correct effective period on every chunk and rule. |
| Pathways | **A, text:** `data/processed/prepared_text.jsonl` (Topic 3 Part B), lineage L01 to L05 in `data/week3_manifest.json`. Byte-identical to `data/pipeline_v1/documents/prepared_text.jsonl` (Part C). **B, tables:** `data/processed/prepared_tariff_rates.csv` and `prepared_relief_rules.csv`, lineage L06 and L07. |
| Sources | S01 to S06 in `data/raw/source_registry.csv`: TNB tariff schedule, ST media statement, four TNB press releases, published 20 Jun 2025 to 2 Oct 2026, retrieved 16 Nov 2026. Public official publications. All six SHA-256 hashes match the registry [Observed]. |
| Population and sample | Units: one text chunk, one table row. Population: 33 chunks and 11 rows, so automated checks ran on **all 44 items**. Manual review: **15 chunks** (all 6 `needs_review`, all 4 chunks with a period conflict, the 2 lowest word-coverage chunks, one near-duplicate pair, one control) and **all 11 rows**. Reference for the tables: the myTNB tariff page and TNB bill calculator code, retrieved 17 Nov 2026. |
| Limits | Accuracy check is word and number matching against the cited page, not a full semantic review. The TNB calculator is TNB's own estimator, not a billing system record. |

## 2. Five-Dimension Quality Scorecard

| Dimension | Finding | Evidence | Impact on task | Decision |
|---|---|---|---|---|
| Completeness | Tables hold 7 of the 14 rule groups TNB's calculator uses. Missing: Energy Efficiency Incentive (EEI), KWTBB levy, AFA for 16 of 17 months, the service tax base, AFA on all kWh above the threshold, rounding, billing-period split [Observed]. | `v2_rule_completeness.csv` | Calculator cannot produce a correct bill for any month (NFR1, FR1, FR3). | **Fail** |
| Consistency | Retail exemption row P03 (600 kWh, to 31 Dec 2027) overlaps P02 (800 kWh, Sep to Dec 2026) with a different value. 4 chunks dated Sep 2026 state 600 kWh protection, superseded by the 800 kWh decision for that month [Observed]. | `manual_review_tables.csv`, `manual_review_text.csv` | Retrieval for Sep 2026 can return a wrong threshold (RAI1). | **Review** |
| Accuracy | All 217 numbers in the 33 chunks appear on the cited source page. Lowest word coverage 0.897, caused only by section headings carried over from the previous page by design. 5 of 5 tariff rates and 5 of 6 rules match S01 and myTNB [Observed]. One extraction artifact ("ko s bahan") [Observed]. | `text_accuracy.csv` | Low. Artifact does not change meaning. | **Pass** |
| Timeliness | Latest AFA in data: Sep 2026. Latest declared: Nov 2026 (+3.60), so the tables are two months behind on the audit date. No source covers 2027 protection; the government has not decided [Observed]. | `audit_summary.json`, myTNB page | Bills for Oct and Nov 2026 cannot be computed; 2027 bills rest on an assumption. | **Warning** |
| Uniqueness | No duplicate chunk IDs, no exact duplicate texts, no duplicate row IDs [Observed]. One near-duplicate pair: energy saving tips repeated across two press releases (Jaccard 0.83). S03 and S04 are the same release in English and BM, kept on purpose for parity testing. | `audit_summary.json` | Repeats may crowd retrieval results [Inferred risk]. | **Pass** (exceptions kept) |

## 3. Validation Findings

| Rule | Quality expectation | Observable property and check | Result | Action | Evidence |
|---|---|---|---|---|---|
| **V1** Provenance | Every chunk and row can be traced to its official source and the period it applies to (RAI1, FR5). | Source ID in the registry; page within the source's page count; effective start date present; source hash equal to the registry hash; rows `verified_in_source = True`. | **44 of 44 pass** | Hard fail: any failing item is quarantined. None failed. | `v1_provenance.csv` |
| **V2** Rule completeness | The tables hold every rule needed to reproduce a TNB bill for every supported month (NFR1). | Each of the 14 rule groups TNB's calculator uses exists, for every month from Jul 2025 to Nov 2026. | **7 pass, 7 fail** (G07, G08, G10 to G14) | Hard fail: tables on HOLD until the groups are added and V2 is re-run. | `v2_rule_completeness.csv`, `tnb_reference_bills.csv` |

Supporting check for V2: all 50 TNB reference bills (`tnb_reference_bills.csv`, four billing months, 150 to 2000 kWh) contain an EEI or KWTBB line, which the current tables cannot produce, so **0 of 50** are reproducible [Observed].

A related lineage finding: the manifest hashes for the two raw CSVs (L06, L07) match the files only with Windows line endings. On a Linux or Colab clone, 2 of 7 lineage records fail the hash check [Observed].

## 4. Duplicate, Anomaly and Coverage Findings

| Defect type | Finding [Observed] | Decision |
|---|---|---|
| Missing | Tables lack EEI, KWTBB, 16 of 17 AFA months and four calculation rules (section 3). The ST worked example bill (S02 p5) is an image, so no text was extracted. | Hard fail (V2). Worked bill to be transcribed as a reference case. |
| Corrupted | Extraction artifact "ko s bahan" for "kos bahan" (S05-p1-c03). Eligibility table flattened with its header row split (S06-p1-c02). | Warning: correct the text; keep the table chunk with a warning. |
| Inconsistent | Row P03 (600 kWh to Dec 2027) overlaps P02 (800 kWh, Sep to Dec 2026). 4 chunks dated Sep 2026 state 600 kWh protection (S03-p1-c02, S03-p2-c07, S04-p1-c02, S04-p2-c07). | Manual review: re-date the chunks to the period they are true for. |
| Noisy | Energy saving tips repeated across two releases (S04-p2-c06, S05-p2-c04, Jaccard 0.83). 5 of the 6 pages with no chunks are intended exclusions: press contacts, "About TNB", a repeated infographic and a blank page. | Keep: exceptions, not defects. Handle repeats at retrieval. |
| Anomaly | 6 chunks flagged `needs_review`, but only 2 have a defect; the other 4 copied a page-level note. The two raw CSV manifest hashes match only with Windows line endings. | Review: set status per chunk; fix line endings with `.gitattributes`. |

- **Coverage, period (RAI1) [Observed].** Bills from Jul 2025 to Aug 2026 (14 months) have 9 eligible chunks each, all BM. Sep 2026 has 33, Oct to Dec 2026 have 19. Jan 2027 has 9. AFA explanations in S03 and S04 are dated to Sep 2026 only, so they are not eligible for any other month even though the explanation itself is general.
- **Coverage, language (RAI3) [Observed].** 22 BM and 11 English chunks. English chunks exist **only for Sep to Dec 2026**: 0 English chunks for 15 of the 19 months checked (`eligible_chunks_by_month.csv`). EEI is covered by 2 BM chunks and 0 English chunks; KWTBB by none.

## 5. Bias Assessment

**Main finding: representation bias by language and period, amplified by the pipeline.**
Source choice (BM-only tariff schedule and ST statement, English press releases only from Sep 2026) plus a pipeline decision (each chunk took its whole document's effective dates) → 0 English evidence for 15 of 19 billing months, and no English explanation of EEI or KWTBB [Observed] → English answers for most months would have no English source to retrieve [Inferred risk]. This hits RAI3 (equal BM and English quality) and FR5. It is a coverage skew, not proven unfairness; RAI3 parity tests measure the real gap.

| Stage | How the English gap travels | Where it is interrupted |
|---|---|---|
| Source data | English sources only from Sep 2026 | Add official English text (myTNB English tariff page and FAQ) |
| Data preparation | Whole-document dates hide general explanations from other months | Date each chunk by the rule it describes |
| Retrievable corpus | 0 English chunks for 15 months | Gate check: no month may have 0 English chunks |
| Retrieved context | An English question finds BM text or nothing | Retrieval says when it falls back to a BM source (Topic 7 build) |
| Generated response | Ungrounded or mistranslated answer | Answer only from retrieved text and calculator output (RAI2) |
| User experience | English speakers get weaker help | RAI3 parity measured per period, not only overall |

**Other bias types checked.** Historical: S03 and S04 state the AFA history and rebate totals as at 15 Sep 2026, which is accurate but goes stale, so those figures stay dated to that release. Measurement: chunk count is not a coverage measure (Sep 2026 has 33 chunks but none on KWTBB), so coverage was measured per month, language and topic. Viewpoint: all six sources come from TNB or ST, so explanations follow the utility's framing (for example "RM3.1 billion in rebates"); Wattlah states facts and amounts, not promotional claims.

## 6. Privacy, Rights and Governance

| Question | Finding |
|---|---|
| Provenance and version | Six sources with issuer, document reference, publish date, retrieval date and SHA-256 in the registry; all hashes verified [Observed]. Lineage L01 to L07 in `week3_manifest.json`; L06 and L07 raw CSV hashes are line-ending dependent (section 3). |
| Rights | Public official publications. Raw PDFs are not in the repository: `git ls-files` lists 0 PDFs [Observed]. Whether the extracted press release text may be republished in a public repository: **[N.V.]**. TNB pages state "Hak Cipta Terpelihara". |
| Privacy | Raw S03 page 3 lists named media contacts with personal mobile numbers. That page is excluded by the end-marker rule, and the prepared text has 0 mobile, IC or long account number matches [Observed]. 5 chunks keep TNB's organisational CareLine email, which is not personal data. |
| Will data leave the system? | Not in this audit: no model is integrated yet. From the V1 build, the user's question, kWh, billing dates and retrieved public chunks go to the external model service, after the Personal Data Filter removes identifiers (RAI4, ADR3). Raw sources and logs stay local. |
| User interaction / consent | No personal data is collected in the corpus, so consent does not apply. V1 stores only redacted evaluation logs; their purpose, access and retention must be written down before any public release **[N.V.]**. |
| Maintenance | Owner: project author. Re-validate on each monthly AFA declaration (around the 1st), any new TNB or ST notice, a government decision on 2027 protection, or a change in the myTNB page hash. |

**Safeguards and actions:** keep raw PDFs out of Git; keep the end-marker exclusion and the phone-number assertion as hard checks; ask the lecturer whether the extracted text may stay in a public repository, otherwise make the repository private or keep only chunk IDs and hashes.

## 7. Mitigation and Impact on Requirements

| # | Action | Owner and when | Requirements affected |
|---|---|---|---|
| 1 | Add the missing rule groups from official TNB sources (S07 myTNB tariff page, S08 AFA series, S09 calculator method): EEI table, KWTBB, AFA Jul 2025 to Nov 2026, service tax base, AFA on all kWh above the threshold, rounding, billing-period split. Resolve P03 against P02. Store 2027 as two labelled scenarios (800 kWh assumed, 600 kWh base). Re-run V2 (target 14 of 14) and reproduce the 50 TNB reference bills. | Author, by 21 Nov 2026 | NFR1, FR1, FR3, RAI2, NFR5 |
| 2 | Text: add chunk-level `superseded_for` metadata to the 4 conflicting chunks, set review status per chunk, date general AFA explanations by rule, add English official text for all months, correct the "ko s" artifact. Add `.gitattributes` for CSV line endings and regenerate the manifest. | Author, before the Topic 5 retrieval build | RAI1, RAI3, FR4, FR5 |

**Residual risks:** 2027 protection is unknown until the government decides; the TNB calculator is an estimator; the sources hold no worked example in machine-readable form until S02 p5 is transcribed.

## 8. Quality-Gate Decision

| Audited scope | Decision | Evidence |
|---|---|---|
| **A, text** (33 chunks) | **GO WITH CONDITIONS** | V1 44 of 44 pass; 217 of 217 numbers found on the cited page; no personal data. Conditions: priority 2 completed before retrieval is built; RAI3 parity tested per period. |
| **B, tables** (11 rows) | **HOLD** | V2 7 of 14 rule groups; 0 of 50 TNB reference bills reproducible; AFA two months out of date. |

**Re-review triggers:** V2 reaches 14 of 14 and the 50 reference bills match to the sen (lifts the HOLD); a new AFA declaration; a 2027 protection decision; any V1 failure.

---

## Appendix A: Evidence files (`docs/week4_evidence/`)

| File | Content |
|---|---|
| `v1_provenance.csv` | V1 result for all 44 items |
| `v2_rule_completeness.csv` | V2 result for the 14 rule groups |
| `text_accuracy.csv` | Word and number coverage of each chunk on its cited page |
| `page_coverage.csv` | Chunks per source page |
| `eligible_chunks_by_month.csv` | Eligible chunks per billing month and language |
| `manual_review_text.csv`, `manual_review_tables.csv` | Manual review of 15 chunks and 11 rows |
| `tnb_reference_bills.csv` | 50 reference bills from TNB's calculator method (retrieved 17 Nov 2026) |
| `audit_summary.json` | All counts quoted in this report |

## Appendix B: Manual review results

Text, 15 chunks: 7 Pass, 2 Pass (kept exceptions), 2 Warning (S05-p1-c03, S06-p1-c02), 4 Review (S03-p1-c02, S03-p2-c07, S04-p1-c02, S04-p2-c07).
Tables, 11 rows: 9 Pass, 1 Review (P03), 1 Warning (P05).

## Appendix C: Re-review after mitigation (22 November 2026)

Priority 1 and most of priority 2 from section 7 were completed. Sources added: S07 and S08 (myTNB tariff page text, English and BM), S09 (myTNB calculator rates) and S10 (myTNB domestic bill calculator). The section 7 plan named these S07 to S09; the English and BM text became two sources. Re-run with `python src/quality_gate.py` on `data/pipeline_v2/`; results in `docs/week4_evidence/rereview/`.

| Check | Week 4 | Re-review |
|---|---|---|
| V1 provenance | 44 of 44 | All chunks and rows pass; the one assumed rule (2027, 800 kWh) is labelled `assumed` with no source, as designed |
| V2 rule completeness | 7 of 14 | 14 of 14 |
| TNB reference bills reproduced to the sen | 0 of 50 | 64 of 64 (50 full month, 13 spanning 1 Sep 2026, 1 ST worked example) |
| Months with 0 English chunks (Jul 2025 to Jan 2027) | 15 of 19 | 0 of 19 |
| Chunks stating 600 kWh that are eligible for Sep to Dec 2026 | 4 | 0 |
| Personal data matches | 0 | 0 |

**Decision:** tables move from HOLD to **GO**. Text stays **GO WITH CONDITIONS** until RAI3 parity is measured on the built retrieval. Still open: the 2027 threshold (two labelled scenarios), public republication rights, and the S06 eligibility table (`needs_review`).
