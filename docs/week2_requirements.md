# Week 2 Requirements Specification: WattLah

*Semak bil elektrik anda*

Version: 1.2 (22 November 2026). Version 1.0 was submitted on 26 October 2026; changes are listed at the end.
Builds on: [Week 1 project scope](week1_project_scope.md)
Test sets named below (REF-CALC, REF-PAIR, PERIOD, QA, SCOPE, PII) are defined in [week2_evaluation_criteria.md](week2_evaluation_criteria.md).

## Section 0: Project Framing and Application Scope

| Field | Details |
|---|---|
| **Problem Evidence** | 1. **AFA flipped from rebates to surcharges.** Households had nine months of rebates (August 2025 to April 2026), then surcharges from May 2026, reaching +3.67 sen/kWh in September 2026. TNB issued a press release specifically to address bill concerns ([TNB, 15 Sep 2026](https://www.tnb.com.my/assets/press_releases/20260915_23_bi.pdf)).<br>2. **Relief rules change faster than people can follow.** The exemption threshold was 600 kWh on 15 September 2026, then raised to 800 kWh two days later for September to December 2026, credited on October bills. What applies from 1 January 2027 has not been decided ([The Edge, 12 Oct 2026](https://theedgemalaysia.com/node/821515)). About 8 million households are covered; those above 800 kWh stay fully exposed to AFA ([Bernama, 2 Oct 2026](https://www.bernama.com/bm/news.php?id=2614501); [The Vibes, 15 Oct 2026](https://www.thevibes.com/articles/news/128374/global-fuel-shock-drives-electricity-costs-but-8-million-malaysian-households-remain-protected-dpm-ii)).<br>**What this shows:** a bill can change for three separate reasons in the same month (usage, the AFA rate, or a threshold), and the information needed to tell them apart is spread across tariff schedules, press releases and the bill itself. |
| **Existing Approaches** | 1. **TNB itemised bill (since July 2025):** lists every charge, but does not explain why the total changed or answer follow up questions ([Malay Mail, 1 Jul 2025](https://www.malaymail.com/news/malaysia/2025/07/01/new-tnb-itemised-electricity-bills-will-help-consumers-better-understand-manage-energy-use/182364)).<br>2. **Third party bill calculators:** compute an estimate, but the user must look up the month's AFA rate, ToU is excluded and nothing is explained ([Paul Tan TNB Bill Calculator](https://paultan.org/tnb-calculator/)).<br>3. **RAG chatbot for PLN complaints (Putro et al., 2025):** shows retrieval in a local language works for a utility, but is grounded in complaint records rather than tariff rules, and its BLEU and ROUGE evaluation cannot catch a wrong amount ([Jurnal Infomedia](https://e-jurnal.pnl.ac.id/infomedia/article/view/7169)).<br>4. **General purpose AI assistants:** explain fluently, but have a fixed knowledge cutoff (Claude reported about June 2026 in our Week 1 lab, before the September threshold change) and compute numbers inside the model with no check. |
| **Project / Engineering Gap** | Each approach covers one part. Bills itemise but do not explain, calculators compute but do not explain, chatbots explain but go out of date and can get figures wrong. No accessible tool combines (1) retrieval over official tariff documents filtered by billing period, (2) verified arithmetic, and (3) plain BM and English explanations of month to month bill changes. This is a practical engineering gap, not a claim of scientific novelty. |
| **Objective O1** | To design a bilingual (BM and English), document grounded assistant that explains Peninsular Malaysia domestic electricity bills using official tariff documents tagged with their effective dates. |
| **Objective O2** | To develop the assistant with date aware retrieval, a deterministic bill calculator tool, and guardrails for source citation, applicable billing period, scope and personal data. |
| **Objective O3** | To evaluate the assistant on calculation accuracy against reference bills, groundedness of explanations, BM and English answer parity, scope handling and response latency. |
| **Intended Users** | **Primary:** domestic TNB customers in Peninsular Malaysia, especially households near the 600 or 800 kWh threshold, whose bills swing most when rules change.<br>**Secondary:** family members who read and manage bills for elderly parents. |
| **Supported Tasks (V1)** | T1. Compute an itemised bill for a given billing period (start and end dates on the bill) and kWh, with the working shown.<br>T2. Explain what each charge on the bill is and how it is charged.<br>T3. Explain why a bill changed between two months: usage, AFA rate, or relief threshold, with the amount for each.<br>T4. Answer rule questions (AFA rate for a month, relief threshold, service tax) with the source and the period the rule applies to.<br>T5. Handle all of the above in BM, English or a mix of both. |
| **Information / Knowledge Domain** | Domestic electricity tariff for Peninsular Malaysia under the RP4 tariff schedule (from 1 July 2025): energy, capacity, network and retail charges, monthly AFA rates, the Energy Efficiency Incentive (EEI), the Renewable Energy Fund levy (KWTBB), temporary relief thresholds, service tax on domestic electricity, and the current bill format. Official sources only: Suruhanjaya Tenaga and TNB, including the bill calculation method TNB publishes on myTNB. |
| **Operating Context** | Mobile friendly web chat, used at home when a new bill arrives. Short sessions, no login or TNB account link. Users type the billing period dates and kWh from their bill. V1 is a course prototype, not a public service. |
| **Important Constraints** | - Solo developer, one semester.<br>- Low or zero budget: free or low cost model service tiers.<br>- Public documents only; no access to TNB customer systems or data.<br>- AFA changes every month and relief rules change at short notice, so sources must carry effective dates.<br>- A meter reading period rarely matches a calendar month, and relief can be credited on a later bill. Usage, thresholds and AFA rates are split across calendar months by days, following the calculation method TNB publishes, not assumed.<br>- Bills carry name, address and account number, which fall under the PDPA.<br>- Source files (PDFs and myTNB data files) are not redistributed; the repo keeps a source list with hashes only.<br>- Must not imply any affiliation with TNB. |
| **Explicit Out of Scope Tasks** | - Time of Use (ToU) tariff<br>- Sabah (SESB) and Sarawak (SEB) customers<br>- Commercial, industrial and agricultural tariffs<br>- Solar, net metering (NEM) and self consumption schemes<br>- Billing months before July 2025 (pre RP4)<br>- Bill photo or PDF upload (deferred to V2)<br>- Billing disputes, meter faults, disconnection and account matters (referred to official TNB channels)<br>- Forecasting future AFA rates or future bills, including bills that need an AFA rate not yet declared (TNB's projection is shown only as a forecast)
- Billing periods shorter than 28 days, because the service tax rule for them is not fully specified in the sources<br>- Legal, financial or energy saving investment advice |
| **Evaluation Focus** | Does WattLah give bill figures that match the official tariff to the sen, explain them with correct, cited sources for the right billing month, at comparable quality in BM and English, while refusing out of scope requests and protecting personal data, within an acceptable response time? |

**Changes from Week 1:** O2 now names scope control as a guardrail, and O3 adds scope handling, so that RAI5 traces to an objective. V1 input is limited to typed values; bill upload moves to V2 (see ADR5 in [week2_architecture_decisions.md](week2_architecture_decisions.md)).

## Section 1: Functional Requirements

| # | Requirement: The system SHALL | Scope Boundary: SHALL NOT (where relevant) |
|---|---|---|
| FR1 | Compute an itemised bill (each charge, the Energy Efficiency Incentive, service tax, KWTBB and total) for a stated billing period and kWh usage, applying the rates, AFA rate and protection threshold in force on each day of the period, and show the working. For periods from 1 January 2027, show two labelled results until the threshold is announced: relief continues (800 kWh, assumed) and relief ends (600 kWh). | State any amount that cannot be reproduced from the published rates and calculation method, or compute a bill that needs an AFA rate that has not been declared yet. |
| FR2 | Explain what each charge on a domestic bill is and how it is charged, in plain language. | Describe a charge that does not appear in the official tariff documents. |
| FR3 | Explain why a bill changed between two billing months, given the kWh for each, by separating the change due to usage, the AFA rate and relief or threshold rules, with the ringgit amount for each cause. | Name a cause of the change that the itemised calculation does not support. |
| FR4 | Answer questions about tariff rules (AFA rate for a month, relief thresholds, service tax) using the documents in force for the billing month in question, state that period in the answer, and ask the user for the billing period when it cannot be determined. | Apply a rule outside its effective period, or assume a billing period the user did not give. |
| FR5 | Give a source reference (issuer, document title and date) for every rule or rate used in an answer. | Present information as coming from an official source when no source supports it. |
| FR6 | Accept questions in BM, English or a mix of both, and answer in the language of the question unless the user asks otherwise. | - |
| FR7 | Decline out of scope requests (Section 0) and redirect the user: billing disputes, meter faults and account matters to official TNB channels; other topics to an appropriate source. | Present itself as TNB or an official TNB channel, or give legal or financial advice. |
| FR8 | Show a notice at the start of each session that WattLah is independent of TNB and that users should not enter personal details. | Require a login, or ask for an account number, IC number, name or address. |

## Section 2: Non-Functional Requirements

| # | Quality Attribute | Requirement | Measurement Method | Metric | Threshold |
|---|---|---|---|---|---|
| NFR1 | Correctness (calculation) | Bill amounts shall match the published tariff for every supported case: domestic general tariff, Peninsular Malaysia, billing periods from July 2025 in which every month has a declared AFA rate. | Run REF-CALC (64 reference bills) and compare each component and the total with the reference value. | Share of cases within tolerance (each component ±RM0.01, total ±RM0.05) | 100% |
| NFR2 | Correctness (explanation) | Explanations shall be consistent with the cited official documents. | Score the QA set claim by claim against the cited documents using a defined rubric. | Grounded response rate | ≥ 90% |
| NFR3 | Performance | Answers, including retrieval and calculation, shall stay within the agreed latency target. | Log end to end time, from submitting the question to the complete answer, across all evaluation sets. | p90 latency (90% of answers are faster than this) | < 8,000 ms |
| NFR4 | Cost | Model service cost shall stay within a student budget. | Record tokens per request across all evaluation sets and price them at the provider's published rate on the test date. Local model calls count as zero. | Cost per 100 queries | < US$1.00 |
| NFR5 | Maintainability | A newly published AFA rate or relief change shall be added as data, without changing code. | Controlled update test: add one new month's AFA notice and rate, then rerun the affected REF-CALC cases. | Time to update; code files changed | ≤ 10 min; 0 files |

**Why these thresholds**
- **NFR1 at 100%:** the arithmetic is deterministic code, so any miss is a defect, not acceptable variance. The ±RM0.05 tolerance on the total allows for rounding of line items on the printed bill.
- **NFR2 at 90%:** explanations are generated text. Figures are already held to 100% by NFR1 and RAI2, so 90% is the V1 bar for the wording around them.
- **NFR3 at 8 s:** each answer needs retrieval, a calculation step and generation. EduAdvisor's 3 s target has no calculation step. Kept at 8 s for V1 and measured from Topic 5 on the local model; slow local answers can use the cloud fallback (ADR9).
- **NFR4 at US$1 per 100 queries:** keeps a full evaluation run (about 150 queries) under US$2. With a local open model and a free-tier cloud fallback (ADR9) the expected cost is near zero; it is still measured, because free-tier limits or a move to a paid tier would change it.
- **NFR5 at 10 min:** AFA changes every month, so updating must be routine data entry, not a code release.

## Section 3: Responsible AI Requirements

| # | Responsible AI Risk | Requirement | Measurement Method | Metric | Threshold |
|---|---|---|---|---|---|
| RAI1 | Wrong period (temporal accuracy) | The system shall use only rules in force for the billing month, state that period in every rule or amount answer, and ask when the month is unclear. | Run PERIOD: AFA rebate and surcharge months, the 600 to 800 kWh threshold change and bills that span it, 2027 bills that must show both labelled threshold scenarios, and vague questions that should trigger a clarifying question. | Period stated rate; correct period rate | 100% stated; ≥ 95% correct |
| RAI2 | Invented numbers (transparency) | Every ringgit amount and rate in an answer shall come from the calculation step or a cited source, with the working shown. | Trace every figure in amount bearing answers, across all evaluation sets, to the calculation log or the source document. | Untraceable figures; working shown rate | 0; 100% |
| RAI3 | Unequal quality across languages (fairness) | BM answers shall be as correct as English answers. | Run the 20 QA questions in both BM and English and score both with the same rubric. | Absolute gap in correct response rate | ≤ 10 percentage points |
| RAI4 | Personal data (privacy, PDPA) | Personal identifiers (name, address, account number, IC number, phone number) shall not be sent to the external model service or kept in logs. | Run PII inputs with seeded fake identifiers, then inspect outgoing model payloads and stored logs. | Identifiers transmitted or stored | 0 |
| RAI5 | Mistaken authority and scope (safety) | The system shall decline out of scope requests, refer disputes and account matters to official TNB channels, and show the non affiliation notice. | Run SCOPE in BM and English: disputes, meter faults, ToU, Sabah and Sarawak, solar, AFA forecasts, legal advice. Check the notice in every session. | Refusal and redirect success rate; notice shown rate | ≥ 95%; 100% of sessions |

## Reflection (Part A)

**Which Responsible AI requirement will be the most difficult to measure or enforce technically? Why?**

RAI1 (wrong period). "Bulan lepas" or "the bill I got in October" can mean different reading periods, a reading period rarely lines up with a calendar month, and the 800 kWh relief was credited on a later bill than the usage it covers. So even writing the expected answer for a PERIOD test case means reading the official notices closely, and a wrong label would make the test itself wrong. Enforcement also depends on every document carrying the right effective dates; one mistagged press release would pass retrieval and produce a confident, cited, but outdated answer. The control is only as good as the tagging, so the source list needs its own check before each evaluation run.

RAI3 is the hardest to measure precisely: with 20 question pairs, one question moves the gap by 5 percentage points, so the 10 point threshold can only flag large differences in V1.

## Changes in Version 1.1 (22 November 2026)

Driven by the Week 4 data quality audit ([week4_data_quality_report.md](week4_data_quality_report.md)) and TNB's published calculation method (sources S07 to S10).

- **Billing period input:** T1, FR1, FR4, operating context. TNB splits usage, thresholds and AFA by calendar month, so a bill that spans 1 September 2026 differs by up to RM26 from a single month estimate in the reference cases.
- **2027 threshold:** removed the claim that the 800 kWh relief reverts on 1 January 2027; no official source states it. FR1 now shows both labelled scenarios, and RAI1 tests them.
- **Charges added to the domain and FR1:** Energy Efficiency Incentive and KWTBB, which were missing from v1.0.
- **Undeclared AFA months and short periods:** a bill that needs an undeclared AFA rate, and billing periods under 28 days, are out of scope; a projection is shown only as a forecast.
- **NFR1:** REF-CALC now has 64 reference bills in `evaluation/reference_bills.csv`.

## Changes in Version 1.2 (22 November 2026)

- **NFR3, NFR4:** measurement and rationale updated for ADR9 (local open model with a free-tier cloud fallback). Thresholds unchanged.
