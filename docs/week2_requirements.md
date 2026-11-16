# Week 2 Requirements Specification: Wattlah

*Semak bil elektrik anda*

Version: 1.0 (26 October 2026)
Builds on: [Week 1 project scope](week1_project_scope.md)
Test sets named below (REF-CALC, REF-PAIR, PERIOD, QA, SCOPE, PII) are defined in [week2_evaluation_criteria.md](week2_evaluation_criteria.md).

## Section 0: Project Framing and Application Scope

| Field | Details |
|---|---|
| **Problem Evidence** | 1. **AFA flipped from rebates to surcharges.** Households had nine months of rebates (August 2025 to April 2026), then surcharges from May 2026, reaching +3.67 sen/kWh in September 2026. TNB issued a press release specifically to address bill concerns ([TNB, 15 Sep 2026](https://www.tnb.com.my/assets/press_releases/20260915_23_bi.pdf)).<br>2. **Relief rules change faster than people can follow.** The exemption threshold was 600 kWh on 15 September 2026, then raised to 800 kWh two days later for September to December 2026, credited on October bills, and reverting on 1 January 2027. About 8 million households are covered; those above 800 kWh stay fully exposed to AFA ([Bernama, 2 Oct 2026](https://www.bernama.com/bm/news.php?id=2614501); [The Vibes, 15 Oct 2026](https://www.thevibes.com/articles/news/128374/global-fuel-shock-drives-electricity-costs-but-8-million-malaysian-households-remain-protected-dpm-ii)).<br>**What this shows:** a bill can change for three separate reasons in the same month (usage, the AFA rate, or a threshold), and the information needed to tell them apart is spread across tariff schedules, press releases and the bill itself. |
| **Existing Approaches** | 1. **TNB itemised bill (since July 2025):** lists every charge, but does not explain why the total changed or answer follow up questions ([Malay Mail, 1 Jul 2025](https://www.malaymail.com/news/malaysia/2025/07/01/new-tnb-itemised-electricity-bills-will-help-consumers-better-understand-manage-energy-use/182364)).<br>2. **Third party bill calculators:** compute an estimate, but the user must look up the month's AFA rate, ToU is excluded and nothing is explained ([Paul Tan TNB Bill Calculator](https://paultan.org/tnb-calculator/)).<br>3. **RAG chatbot for PLN complaints (Putro et al., 2025):** shows retrieval in a local language works for a utility, but is grounded in complaint records rather than tariff rules, and its BLEU and ROUGE evaluation cannot catch a wrong amount ([Jurnal Infomedia](https://e-jurnal.pnl.ac.id/infomedia/article/view/7169)).<br>4. **General purpose AI assistants:** explain fluently, but have a fixed knowledge cutoff (Claude reported about June 2026 in our Week 1 lab, before the September threshold change) and compute numbers inside the model with no check. |
| **Project / Engineering Gap** | Each approach covers one part. Bills itemise but do not explain, calculators compute but do not explain, chatbots explain but go out of date and can get figures wrong. No accessible tool combines (1) retrieval over official tariff documents filtered by billing period, (2) verified arithmetic, and (3) plain BM and English explanations of month to month bill changes. This is a practical engineering gap, not a claim of scientific novelty. |
| **Objective O1** | To design a bilingual (BM and English), document grounded assistant that explains Peninsular Malaysia domestic electricity bills using official tariff documents tagged with their effective dates. |
| **Objective O2** | To develop the assistant with date aware retrieval, a deterministic bill calculator tool, and guardrails for source citation, applicable billing period, scope and personal data. |
| **Objective O3** | To evaluate the assistant on calculation accuracy against reference bills, groundedness of explanations, BM and English answer parity, scope handling and response latency. |
| **Intended Users** | **Primary:** domestic TNB customers in Peninsular Malaysia, especially households near the 600 or 800 kWh threshold, whose bills swing most when rules change.<br>**Secondary:** family members who read and manage bills for elderly parents. |
| **Supported Tasks (V1)** | T1. Compute an itemised bill for a given billing month and kWh, with the working shown.<br>T2. Explain what each charge on the bill is and how it is charged.<br>T3. Explain why a bill changed between two months: usage, AFA rate, or relief threshold, with the amount for each.<br>T4. Answer rule questions (AFA rate for a month, relief threshold, service tax) with the source and the period the rule applies to.<br>T5. Handle all of the above in BM, English or a mix of both. |
| **Information / Knowledge Domain** | Domestic electricity tariff for Peninsular Malaysia under the RP4 tariff schedule (from 1 July 2025): energy, capacity, network and retail charges, monthly AFA rates, temporary relief thresholds, service tax on domestic electricity, and the current bill format. Official sources only: Suruhanjaya Tenaga and TNB. |
| **Operating Context** | Mobile friendly web chat, used at home when a new bill arrives. Short sessions, no login or TNB account link. Users type the billing month and kWh from their bill. V1 is a course prototype, not a public service. |
| **Important Constraints** | - Solo developer, one semester.<br>- Low or zero budget: free or low cost model service tiers.<br>- Public documents only; no access to TNB customer systems or data.<br>- AFA changes every month and relief rules change at short notice, so sources must carry effective dates.<br>- A meter reading period rarely matches a calendar month, and relief can be credited on a later bill. How rates apply across such periods is taken from the official documents, not assumed.<br>- Bills carry name, address and account number, which fall under the PDPA.<br>- Source PDFs are not redistributed; the repo keeps a source list only.<br>- Must not imply any affiliation with TNB. |
| **Explicit Out of Scope Tasks** | - Time of Use (ToU) tariff<br>- Sabah (SESB) and Sarawak (SEB) customers<br>- Commercial, industrial and agricultural tariffs<br>- Solar, net metering (NEM) and self consumption schemes<br>- Billing months before July 2025 (pre RP4)<br>- Bill photo or PDF upload (deferred to V2)<br>- Billing disputes, meter faults, disconnection and account matters (referred to official TNB channels)<br>- Forecasting future AFA rates or future bills<br>- Legal, financial or energy saving investment advice |
| **Evaluation Focus** | Does Wattlah give bill figures that match the official tariff to the sen, explain them with correct, cited sources for the right billing month, at comparable quality in BM and English, while refusing out of scope requests and protecting personal data, within an acceptable response time? |

**Changes from Week 1:** O2 now names scope control as a guardrail, and O3 adds scope handling, so that RAI5 traces to an objective. V1 input is limited to typed values; bill upload moves to V2 (see ADR5 in [week2_architecture_decisions.md](week2_architecture_decisions.md)).

## Section 1: Functional Requirements

| # | Requirement: The system SHALL | Scope Boundary: SHALL NOT (where relevant) |
|---|---|---|
| FR1 | Compute an itemised bill (each charge, service tax and total) for a stated billing month and kWh usage, using the rates in force for that month, and show the working. | State any amount that cannot be reproduced from the published rates for that month. |
| FR2 | Explain what each charge on a domestic bill is and how it is charged, in plain language. | Describe a charge that does not appear in the official tariff documents. |
| FR3 | Explain why a bill changed between two billing months, given the kWh for each, by separating the change due to usage, the AFA rate and relief or threshold rules, with the ringgit amount for each cause. | Name a cause of the change that the itemised calculation does not support. |
| FR4 | Answer questions about tariff rules (AFA rate for a month, relief thresholds, service tax) using the documents in force for the billing month in question, state that period in the answer, and ask the user for the billing month when it cannot be determined. | Apply a rule outside its effective period, or assume a billing month the user did not give. |
| FR5 | Give a source reference (issuer, document title and date) for every rule or rate used in an answer. | Present information as coming from an official source when no source supports it. |
| FR6 | Accept questions in BM, English or a mix of both, and answer in the language of the question unless the user asks otherwise. | - |
| FR7 | Decline out of scope requests (Section 0) and redirect the user: billing disputes, meter faults and account matters to official TNB channels; other topics to an appropriate source. | Present itself as TNB or an official TNB channel, or give legal or financial advice. |
| FR8 | Show a notice at the start of each session that Wattlah is independent of TNB and that users should not enter personal details. | Require a login, or ask for an account number, IC number, name or address. |

## Section 2: Non-Functional Requirements

| # | Quality Attribute | Requirement | Measurement Method | Metric | Threshold |
|---|---|---|---|---|---|
| NFR1 | Correctness (calculation) | Bill amounts shall match the published tariff for every supported case: domestic general tariff, Peninsular Malaysia, billing month from July 2025 with a published AFA rate. | Run REF-CALC and compare each component and the total with the reference value. | Share of cases within tolerance (each component ±RM0.01, total ±RM0.05) | 100% |
| NFR2 | Correctness (explanation) | Explanations shall be consistent with the cited official documents. | Score the QA set claim by claim against the cited documents using a defined rubric. | Grounded response rate | ≥ 90% |
| NFR3 | Performance | Answers, including retrieval and calculation, shall stay within the agreed latency target. | Log end to end time, from submitting the question to the complete answer, across all evaluation sets. | p90 latency (90% of answers are faster than this) | < 8,000 ms |
| NFR4 | Cost | Model service cost shall stay within a student budget. | Record tokens per request across all evaluation sets and price them at the provider's published rate on the test date. | Cost per 100 queries | < US$1.00 |
| NFR5 | Maintainability | A newly published AFA rate or relief change shall be added as data, without changing code. | Controlled update test: add one new month's AFA notice and rate, then rerun the affected REF-CALC cases. | Time to update; code files changed | ≤ 10 min; 0 files |

**Why these thresholds**
- **NFR1 at 100%:** the arithmetic is deterministic code, so any miss is a defect, not acceptable variance. The ±RM0.05 tolerance on the total allows for rounding of line items on the printed bill.
- **NFR2 at 90%:** explanations are generated text. Figures are already held to 100% by NFR1 and RAI2, so 90% is the V1 bar for the wording around them.
- **NFR3 at 8 s:** each answer needs retrieval, a calculation step and generation. EduAdvisor's 3 s target has no calculation step. To be revisited once the first measurements exist.
- **NFR4 at US$1 per 100 queries:** keeps a full evaluation run (about 150 queries) under US$2.
- **NFR5 at 10 min:** AFA changes every month, so updating must be routine data entry, not a code release.

## Section 3: Responsible AI Requirements

| # | Responsible AI Risk | Requirement | Measurement Method | Metric | Threshold |
|---|---|---|---|---|---|
| RAI1 | Wrong period (temporal accuracy) | The system shall use only rules in force for the billing month, state that period in every rule or amount answer, and ask when the month is unclear. | Run PERIOD: AFA rebate and surcharge months, the 600 to 800 kWh threshold change and its reversion on 1 January 2027, and vague questions that should trigger a clarifying question. | Period stated rate; correct period rate | 100% stated; ≥ 95% correct |
| RAI2 | Invented numbers (transparency) | Every ringgit amount and rate in an answer shall come from the calculation step or a cited source, with the working shown. | Trace every figure in amount bearing answers, across all evaluation sets, to the calculation log or the source document. | Untraceable figures; working shown rate | 0; 100% |
| RAI3 | Unequal quality across languages (fairness) | BM answers shall be as correct as English answers. | Run the 20 QA questions in both BM and English and score both with the same rubric. | Absolute gap in correct response rate | ≤ 10 percentage points |
| RAI4 | Personal data (privacy, PDPA) | Personal identifiers (name, address, account number, IC number, phone number) shall not be sent to the external model service or kept in logs. | Run PII inputs with seeded fake identifiers, then inspect outgoing model payloads and stored logs. | Identifiers transmitted or stored | 0 |
| RAI5 | Mistaken authority and scope (safety) | The system shall decline out of scope requests, refer disputes and account matters to official TNB channels, and show the non affiliation notice. | Run SCOPE in BM and English: disputes, meter faults, ToU, Sabah and Sarawak, solar, AFA forecasts, legal advice. Check the notice in every session. | Refusal and redirect success rate; notice shown rate | ≥ 95%; 100% of sessions |

## Reflection (Part A)

**Which Responsible AI requirement will be the most difficult to measure or enforce technically? Why?**

RAI1 (wrong period). "Bulan lepas" or "the bill I got in October" can mean different reading periods, a reading period rarely lines up with a calendar month, and the 800 kWh relief was credited on a later bill than the usage it covers. So even writing the expected answer for a PERIOD test case means reading the official notices closely, and a wrong label would make the test itself wrong. Enforcement also depends on every document carrying the right effective dates; one mistagged press release would pass retrieval and produce a confident, cited, but outdated answer. The control is only as good as the tagging, so the source list needs its own check before each evaluation run.

RAI3 is the hardest to measure precisely: with 20 question pairs, one question moves the gap by 5 percentage points, so the 10 point threshold can only flag large differences in V1.
