# Indicator reference sheets

> **Draft, for co-design with ARDE/KUBAHO staff.** Nothing here has been agreed with ARDE/KUBAHO. Use `docs/indicator_reference_sheets.xlsx` (with a Staff comments column) in the co-design session.

*Generated from `config/indicator_catalogue.yaml` by `src/indicators.py` on 15 October 2026. Do not edit by hand: change the YAML file instead.*

Traffic-light status (% of target achieved, from `config/settings.yaml`): on track 90% or more; at risk 70% to 89%; off track below 70%. A missing target shows "no target set".

| Code | Indicator | Level | Unit | Frequency | Availability |
|---|---|---|---|---|---|
| WASH-01 | Number of people with access to improved water sources | output | number | monthly | available |
| WASH-02 | Number of household latrines constructed or rehabilitated | output | number | monthly | available |
| WASH-03 | Percentage of trained households practising handwashing with soap | outcome | percent | quarterly | data source not yet available |
| WASH-04 | Number of water user committees established and functional | output | number | quarterly | available |
| AGR-01 | Number of farmers trained in climate-smart agriculture | output | number | monthly | available |
| AGR-02 | Hectares under solar-powered or improved irrigation | output | hectares | monthly | available |
| AGR-03 | Percentage of supported farmers reporting a yield increase | outcome | percent | semi-annual | data source not yet available |
| AGR-04 | Number of cooperatives formed or strengthened | output | number | quarterly | available |
| CC-01 | Percentage of participants who are women | output | percent | monthly | available |
| CC-02 | Percentage of planned activities completed on time | output | percent | monthly | available |
| CC-03 | Cost per person reached (RWF), as reported | output | RWF | quarterly | available |
| CC-05 | Cost per registered farmer trained, farmer field schools (RWF) | output | RWF | quarterly | available |
| CC-04 | Reporting completeness: percentage of expected monthly reports submitted | output | percent | monthly | available |

## WASH-01: Number of people with access to improved water sources

| Field | Value |
|---|---|
| Status | Draft, for co-design with ARDE/KUBAHO staff |
| Theme | WASH |
| Level | output |
| Unit | number |
| Definition | People who gained access to an improved water source (a borehole or water point built or rehabilitated by the project) during the period. |
| Numerator | People gaining access to an improved water source during the period. |
| Denominator | None (a count). |
| Calculation rule | Reported: the sum of the monthly values in the indicator reports. Derived: the people served recorded in the activity records, i.e. the participants of water-point activities (activity ACT01) that took place during the month (completed or delayed), in the district where the activity took place. |
| Counting rule | Both sources count people served by water-point activities as recorded by officers (not registered beneficiaries), so they are comparable. A person served by two water-point activities may be counted twice in both sources. |
| Coverage | Reported values cover the monthly reports received out of those expected. |
| Disaggregation | none |
| Target-setting rule | An annual target per project and district from the work plan, split into equal monthly targets. |
| Frequency | monthly |
| Data source | Monthly indicator report (field officers); beneficiary registers and service records (derived). |
| Availability | available |
| Owner | To be confirmed with partner (suggested - MEAL officer) |
| Higher is better | Yes |
| Notes | Reported and derived values are compared month by month in the reconciliation table; a gap above the tolerance points to a reporting or recording problem to follow up. |

## WASH-02: Number of household latrines constructed or rehabilitated

| Field | Value |
|---|---|
| Status | Draft, for co-design with ARDE/KUBAHO staff |
| Theme | WASH |
| Level | output |
| Unit | number |
| Definition | Household latrines completed (new or rehabilitated) to the project standard during the period. |
| Numerator | Latrines completed during the period. |
| Denominator | None (a count). |
| Calculation rule | The sum of the monthly values in the indicator reports. |
| Counting rule | Each latrine is counted once, in the month it is completed. |
| Coverage | The monthly reports received out of those expected. |
| Disaggregation | none |
| Target-setting rule | An annual target per project and district from the work plan, split into equal monthly targets. |
| Frequency | monthly |
| Data source | Monthly indicator report (field officers). |
| Availability | available |
| Owner | To be confirmed with partner (suggested - WASH project manager) |
| Higher is better | Yes |
| Notes | Activity records count construction events, not latrines, so this cannot be derived from them. |

## WASH-03: Percentage of trained households practising handwashing with soap

| Field | Value |
|---|---|
| Status | Draft, for co-design with ARDE/KUBAHO staff |
| Theme | WASH |
| Level | outcome |
| Unit | percent |
| Definition | Of the households trained in hygiene, the percentage observed (or reporting) handwashing with soap at critical times. |
| Numerator | Trained households practising handwashing with soap. |
| Denominator | Trained households surveyed. |
| Calculation rule | Numerator divided by denominator, times 100, from a household survey. |
| Counting rule | One household counted once per survey round. |
| Coverage | Households surveyed out of households trained. |
| Disaggregation | none |
| Target-setting rule | To be agreed with ARDE/KUBAHO after a baseline survey. |
| Frequency | quarterly |
| Data source | Household survey (DATA SOURCE NOT YET AVAILABLE) |
| Availability | data source not yet available |
| Owner | To be confirmed with partner (suggested - MEAL officer) |
| Higher is better | Yes |
| Notes | Not calculated. It needs a household survey that does not exist yet. The synthetic monthly reports contain placeholder values for this indicator; they are deliberately ignored. Recommendation for ARDE/KUBAHO: run a baseline and follow-up handwashing survey. |

## WASH-04: Number of water user committees established and functional

| Field | Value |
|---|---|
| Status | Draft, for co-design with ARDE/KUBAHO staff |
| Theme | WASH |
| Level | output |
| Unit | number |
| Definition | Water user committees newly established during the period that meet the functionality criteria. |
| Numerator | Committees established and functional during the period. |
| Denominator | None (a count). |
| Calculation rule | The latest quarterly value in the indicator reports for the period. |
| Counting rule | Treated as a SNAPSHOT (aggregation: latest): a quarter or year shows the latest reported number of functional committees, not a sum. To be confirmed with partner whether the reports count new committees (which would add up, aggregation: sum) or all functional committees at the end of the quarter (as assumed here). |
| Coverage | The quarterly reports received out of those expected. |
| Disaggregation | none |
| Target-setting rule | An annual target per project and district from the work plan, split into quarters. |
| Frequency | quarterly |
| Data source | Quarterly figure in the monthly indicator report (field officers). |
| Availability | available |
| Owner | To be confirmed with partner (suggested - WASH project manager) |
| Higher is better | Yes |
| Notes | The functionality criteria need to be written down with ARDE/KUBAHO. |

## AGR-01: Number of farmers trained in climate-smart agriculture

| Field | Value |
|---|---|
| Status | Draft, for co-design with ARDE/KUBAHO staff |
| Theme | Agriculture |
| Level | output |
| Unit | number |
| Definition | Farmers who took part in climate-smart agriculture training (farmer field schools) during the period. |
| Numerator | Farmers trained during the period. |
| Denominator | None (a count). |
| Calculation rule | Reported: the sum of the monthly values in the indicator reports, by sex. Derived: the number of different registered people who received a "farmer training" service (activity ACT10) during the period, by sex. |
| Counting rule | Each month counts different registered people (not attendance): a farmer at four sessions in one month counts once. Reported values are counts typed by officers for the same thing. |
| Coverage | Reported values cover the monthly reports received out of those expected. |
| Disaggregation | sex |
| Target-setting rule | An annual target per project, district and sex from the work plan, split into equal monthly targets. |
| Frequency | monthly |
| Data source | Monthly indicator report (field officers); beneficiary registers and service records (derived). |
| Availability | available |
| Owner | To be confirmed with partner (suggested - agriculture project manager) |
| Higher is better | Yes |
| Notes | The definition of "trained" (one session, or the full course) needs to be agreed. Quarters and years add up the months, as the reports do, so a farmer trained in two different months counts in both. |

## AGR-02: Hectares under solar-powered or improved irrigation

| Field | Value |
|---|---|
| Status | Draft, for co-design with ARDE/KUBAHO staff |
| Theme | Agriculture |
| Level | output |
| Unit | hectares |
| Definition | Hectares newly brought under solar-powered or improved irrigation during the period. |
| Numerator | Hectares newly irrigated during the period. |
| Denominator | None (an area). |
| Calculation rule | The sum of the monthly values in the indicator reports. |
| Counting rule | Each hectare is counted once, in the month the irrigation starts working. |
| Coverage | The monthly reports received out of those expected. |
| Disaggregation | none |
| Target-setting rule | An annual target per project and district from the work plan, split into equal monthly targets. |
| Frequency | monthly |
| Data source | Monthly indicator report (field officers). |
| Availability | available |
| Owner | To be confirmed with partner (suggested - agriculture project manager) |
| Higher is better | Yes |
| Notes | How areas are measured (GPS or estimate) needs to be agreed. |

## AGR-03: Percentage of supported farmers reporting a yield increase

| Field | Value |
|---|---|
| Status | Draft, for co-design with ARDE/KUBAHO staff |
| Theme | Agriculture |
| Level | outcome |
| Unit | percent |
| Definition | Of the farmers supported, the percentage reporting a higher yield than in the previous comparable season. |
| Numerator | Supported farmers reporting a yield increase. |
| Denominator | Supported farmers surveyed. |
| Calculation rule | Numerator divided by denominator, times 100, from a farmer survey. |
| Counting rule | One farmer counted once per survey round. |
| Coverage | Farmers surveyed out of farmers supported. |
| Disaggregation | none |
| Target-setting rule | To be agreed with ARDE/KUBAHO after a baseline survey. |
| Frequency | semi-annual |
| Data source | Farmer survey (DATA SOURCE NOT YET AVAILABLE) |
| Availability | data source not yet available |
| Owner | To be confirmed with partner (suggested - MEAL officer) |
| Higher is better | Yes |
| Notes | Not calculated. It needs a farmer yield survey that does not exist yet. The synthetic monthly reports contain placeholder values for this indicator; they are deliberately ignored. Recommendation for ARDE/KUBAHO: run a baseline and end-of-season yield survey, and record results by sex. |

## AGR-04: Number of cooperatives formed or strengthened

| Field | Value |
|---|---|
| Status | Draft, for co-design with ARDE/KUBAHO staff |
| Theme | Agriculture |
| Level | output |
| Unit | number |
| Definition | Cooperatives newly formed, or existing cooperatives meeting the strengthening criteria, during the period. |
| Numerator | Cooperatives formed or strengthened during the period. |
| Denominator | None (a count). |
| Calculation rule | The sum of the quarterly values in the indicator reports. |
| Counting rule | Each cooperative is counted once, in the quarter it is formed or first meets the criteria. |
| Coverage | The quarterly reports received out of those expected. |
| Disaggregation | none |
| Target-setting rule | An annual target per project and district from the work plan, split into quarters. |
| Frequency | quarterly |
| Data source | Quarterly figure in the monthly indicator report (field officers). |
| Availability | available |
| Owner | To be confirmed with partner (suggested - agriculture project manager) |
| Higher is better | Yes |
| Notes | The strengthening criteria need to be written down with ARDE/KUBAHO. |

## CC-01: Percentage of participants who are women

| Field | Value |
|---|---|
| Status | Draft, for co-design with ARDE/KUBAHO staff |
| Theme | Cross-cutting |
| Level | output |
| Unit | percent |
| Definition | Of the different registered people reached during the period, the percentage who are women or girls. |
| Numerator | Different registered women and girls reached during the period. |
| Denominator | Different registered people reached during the period whose sex is recorded. |
| Calculation rule | Numerator divided by denominator, times 100. |
| Counting rule | Unique people, not attendance: a woman who attended five sessions counts once. People are attributed to the district where they registered. |
| Coverage | People whose sex is recorded out of all people reached. |
| Disaggregation | none |
| Target-setting rule | To be agreed with ARDE/KUBAHO (for example at least 50%). |
| Frequency | monthly |
| Data source | Beneficiary registers and service records (derived). |
| Availability | available |
| Owner | To be confirmed with partner (suggested - MEAL officer) |
| Higher is better | Yes |
| Notes | Only registered beneficiaries are counted; people at open meetings who are not registered are not. Activity attendance figures (participants_female / participants_total) count people once per session and are not used. |

## CC-02: Percentage of planned activities completed on time

| Field | Value |
|---|---|
| Status | Draft, for co-design with ARDE/KUBAHO staff |
| Theme | Cross-cutting |
| Level | output |
| Unit | percent |
| Definition | Of the activities planned for the period, the percentage completed within the allowed number of days of the planned date (on_time_tolerance_days in settings, now 7). |
| Numerator | Activities completed on time. |
| Denominator | Activities planned for the period (completed, delayed or cancelled) whose timing can be checked. |
| Calculation rule | Numerator divided by denominator, times 100. The period is the month of the PLANNED date. |
| Counting rule | Each activity event counted once. Cancelled and delayed activities count as not on time. |
| Coverage | Activities whose timing can be checked out of all activities planned for the period, using the same definition as the data-quality measure "on_time_checkable" (config/dq_metrics.yaml), on the rows kept in the warehouse. Timing cannot be checked when only the month is known, or when the record has no planned date (e.g. paper records). An activity with neither a planned date nor an activity date cannot be placed in any period. |
| Disaggregation | none |
| Target-setting rule | To be agreed with ARDE/KUBAHO (for example 85%). |
| Frequency | monthly |
| Data source | Activity monitoring files and digitised paper records (derived). |
| Availability | available |
| Owner | To be confirmed with partner (suggested - programme managers) |
| Higher is better | Yes |
| Notes | Coverage matters here: on the synthetic data the timing of only about three quarters of activities can be checked. Adding a planned-date field to the paper form (decision log D56) would raise it. |

## CC-03: Cost per person reached (RWF), as reported

| Field | Value |
|---|---|
| Status | Draft, for co-design with ARDE/KUBAHO staff |
| Theme | Cross-cutting |
| Level | output |
| Unit | RWF |
| Definition | Activity spending divided by the people reached as reported in the monthly indicator reports, by programme. |
| Numerator | Total cost (RWF) of the activities of projects that report people reached, during the period. |
| Denominator | People reached as reported by the same projects during the period: WASH programme - people with access to improved water (WASH-01); agriculture programme - farmers trained (AGR-01). |
| Calculation rule | Numerator divided by denominator. Not available for a project or programme that reports no reach. |
| Counting rule | Reported monthly figures are added up, as the reports do, so a person reached in two months counts twice. Projects without a people-reached indicator (sanitation, hygiene, irrigation) are left out of both sides. |
| Coverage | Activities whose cost is included (projects that report reach) out of all activities. |
| Disaggregation | none |
| Target-setting rule | To be agreed with ARDE/KUBAHO (a benchmark per type of project). |
| Frequency | quarterly |
| Data source | Activity monitoring files (costs) and monthly indicator reports (people reached) (derived). |
| Availability | available |
| Owner | To be confirmed with partner (suggested - finance officer with MEAL officer) |
| Higher is better | No |
| Notes | Replaces cost per REGISTERED person (D161, D163): the register holds far fewer people than the activities reach. Which indicators count "people reached" for each programme must be agreed with ARDE/KUBAHO; sanitation, hygiene and irrigation projects have none yet. Only activity costs are included (not staff or overheads). |

## CC-05: Cost per registered farmer trained, farmer field schools (RWF)

| Field | Value |
|---|---|
| Status | Draft, for co-design with ARDE/KUBAHO staff |
| Theme | Cross-cutting |
| Level | output |
| Unit | RWF |
| Definition | Cost of farmer field school sessions divided by the different registered people who attended them (training activities only). |
| Numerator | Total cost (RWF) of farmer field school sessions (ACT10) during the period. |
| Denominator | Different registered people who received farmer training (ACT10) during the period. |
| Calculation rule | Numerator divided by denominator. |
| Counting rule | Unique people, not attendance. Training is the one activity where every participant is registered. |
| Coverage | Sessions with a cost recorded out of all sessions that took place. |
| Disaggregation | none |
| Target-setting rule | To be agreed with ARDE/KUBAHO. |
| Frequency | quarterly |
| Data source | Activity monitoring files (costs) and beneficiary registers and service records (people) (derived). |
| Availability | available |
| Owner | To be confirmed with partner (suggested - finance officer with MEAL officer) |
| Higher is better | No |
| Notes | Kept for training activities only, where registration is complete; labelled as per REGISTERED farmer. |

## CC-04: Reporting completeness: percentage of expected monthly reports submitted

| Field | Value |
|---|---|
| Status | Draft, for co-design with ARDE/KUBAHO staff |
| Theme | Cross-cutting |
| Level | output |
| Unit | percent |
| Definition | Of the monthly indicator reports due, the percentage received. |
| Numerator | Reports received. |
| Denominator | Reports due: one per project, district and month in which at least one of the project's indicators is due. |
| Calculation rule | Numerator divided by denominator, times 100. |
| Counting rule | One report per project, district and month. |
| Coverage | Not applicable (all expected reports are counted). |
| Disaggregation | none |
| Target-setting rule | To be agreed with ARDE/KUBAHO (for example 100%). |
| Frequency | monthly |
| Data source | Monthly indicator reports compared with the reporting schedule (derived). |
| Availability | available |
| Owner | To be confirmed with partner (suggested - MEAL officer) |
| Higher is better | Yes |
| Notes | Uses the same definition as the "reporting completeness" data-quality measure (config/dq_metrics.yaml), so the two always agree. |
