# Week 2 Evaluation Criteria: Wattlah

Version: 1.1 (22 November 2026). Changes are listed at the end.
Requirement IDs refer to [week2_requirements.md](week2_requirements.md).

## Evaluation Criteria Table

| Objective / Requirement ID | Evaluation Criterion | Capability Bucket | Measurement Method | Metric | Threshold | User / Business Outcome |
|---|---|---|---|---|---|---|
| O2, O3 / FR1, NFR1 | Calculation accuracy | Domain-specific capability | Run REF-CALC; compare each component and the total with the reference value. | Share of cases within tolerance | 100% (components ±RM0.01, total ±RM0.05) | Households see the same figures as on their bill, so they can trust the rest of the answer. |
| O1, O3 / FR3 | Bill change attribution | Domain-specific capability | Run REF-PAIR; compare the causes named and the amount for each with the reference split. | Share of pairs fully correct (every cause named, every amount matching) | ≥ 90% | Users learn whether a higher bill came from their own usage or from rules they cannot control, and what they can act on. |
| O1, O3 / FR4, RAI1 | Applicable billing period | Domain-specific capability | Run PERIOD; check the period stated and the rule applied in each answer, and that vague questions get a clarifying question. | Period stated rate; correct period rate | 100%; ≥ 95% | Users do not budget for, or dispute, a bill based on an expired or future rule. |
| O1, O3 / FR2, FR5, NFR2 | Grounded and cited explanations | Generation capability | Score QA claim by claim against the cited documents; check that each citation exists and supports the claim it is attached to. | Grounded response rate; citation presence rate; citation source match rate | ≥ 90%; 100%; ≥ 95% | Users can check any explanation against the official document themselves. |
| O2, O3 / RAI2 | Figure traceability | Instruction-following capability | Trace every figure in amount bearing answers, across all sets, to the calculation log or a cited source. | Untraceable figures; working shown rate | 0; 100% | No confident but made up ringgit amount reaches a user. |
| O1, O3 / FR6, RAI3 | BM and English parity | Generation capability | Score the 20 QA question pairs in both languages with the same rubric. | Absolute gap in correct response rate | ≤ 10 percentage points | Households who prefer BM get equally reliable help. |
| O2, O3 / FR7, FR8, RAI5 | Out of scope refusal and redirect | Instruction-following capability | Run SCOPE; check that each answer declines and points to the right channel; check the notice in every session. | Refusal and redirect success rate; notice shown rate | ≥ 95%; 100% | Disputes go to TNB, and users do not mistake Wattlah for an official channel. |
| O2, O3 / RAI4 | Personal data protection | Instruction-following capability | Run PII; inspect outgoing model payloads and stored logs. | Identifiers transmitted or stored | 0 | Users can ask about their bill without exposing personal data. |
| O3 / NFR3 | Response latency | Cost and latency | Log end to end time across all sets. | p90 latency | < 8 s | Answers arrive fast enough for a quick check when a bill arrives. |
| O3 / NFR4 | Cost per query | Cost and latency | Record tokens per request across all sets; price at the provider's published rate on the test date. | Cost per 100 queries | < US$1.00 | The tool runs on a student budget, and a free public version stays realistic. |

Personal data protection is a system control rather than a model capability. It is grouped under instruction-following because the test checks whether the system obeys a defined rule.

NFR5 (monthly update without code change) is evaluated by the controlled update test in [week2_requirements.md](week2_requirements.md), not by a query set, so it is not listed here.

## Test Sets

| Set | Contents | Size | Used by |
|---|---|---|---|
| REF-CALC | `evaluation/reference_bills.csv`: 63 bills with expected values from TNB's own calculation method (myTNB, retrieved 17 November 2026) and the ST worked example (S02 page 5). Covers 150 to 2000 kWh on both sides of every threshold (300, 600, 800, 1000, 1500 kWh), rebate and surcharge AFA months, months inside and outside the 800 kWh relief period, and 13 bills spanning the 1 September 2026 threshold change. Real bills, with identifiers removed, are added where available as a cross check. | ≥ 30 cases (64 built) | NFR1, RAI2, NFR3, NFR4 |
| REF-PAIR | Month pairs drawn from REF-CALC, each with the change split by cause (usage, AFA rate, relief) in the spreadsheet. | ≥ 15 pairs | FR3 |
| PERIOD | Rule questions where the right answer depends on the month: AFA rebate against surcharge months, 600 against 800 kWh threshold, bills spanning the change, 2027 bills that must show both labelled scenarios, and vague questions that should get a clarifying question. | ≥ 20 (BM and English) | FR4, RAI1 |
| QA | 20 in scope questions on charges, AFA, thresholds and service tax, each written in BM and in English, with expected answers and sources. | 40 (20 pairs) | FR2, FR5, NFR2, RAI3 |
| SCOPE | Out of scope requests: disputes, meter faults, ToU, Sabah and Sarawak, solar, AFA forecasts, legal or financial advice. | ≥ 20 (half BM, half English) | FR7, FR8, RAI5 |
| PII | Questions containing seeded fake names, addresses, account, IC and phone numbers, including numbers that look like kWh readings. | ≥ 15 | RAI4 |

- Expected values in REF-CALC and REF-PAIR are produced outside Wattlah, so the calculator is never graded against itself.
- All sets and results are kept in `evaluation/`. Real bills are stored only after identifiers are removed.

## Reflection (Part B)

**Which evaluation criterion is most important for determining whether Wattlah will be useful to its intended users? Why?**

Calculation accuracy. The first thing a user does is hold Wattlah's answer next to their actual bill. If one ringgit figure does not match, the explanation around it loses all credibility, and if the user does not notice the mismatch, they act on a wrong number, which is worse. It is also the main thing that separates Wattlah from a general chatbot. Applicable billing period is a close second, because a correct calculation done with the wrong month's AFA rate is still a wrong bill.

## Changes in Version 1.1 (22 November 2026)

- **REF-CALC built:** 64 reference bills. Expected values come from TNB's published calculator method rather than a hand checked spreadsheet, so they are still produced outside Wattlah and are closer to what TNB actually bills.
- **PERIOD:** the 1 January 2027 reversion was not an official rule; tests now check that both 2027 scenarios are shown and labelled.
