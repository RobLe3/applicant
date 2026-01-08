# Phase 10 Verification

## Commands Executed
- python scripts/run_pipeline.py --config config/applicant.yaml
- python scripts/diagnose_rankings.py --config config/applicant.yaml --output data/output/ranking_diagnostics_intent_on.json
- python scripts/diagnose_rankings.py --config config/applicant.yaml --override matching.role_intent.alignment_bonus=0 
  --override matching.role_intent.mismatch_penalty=0 --override matching.role_intent.execution_bonus=0 
  --output data/output/ranking_diagnostics_intent_off.json
- python scripts/verify_intent_shift.py --intent-on data/output/ranking_diagnostics_intent_on.json 
  --intent-off data/output/ranking_diagnostics_intent_off.json

Profile role_intent: executive_strategy

## Top 25 Distribution (Intent ON)
- leadership: 4 (16.0%)
- architecture: 10 (40.0%)
- strategy: 2 (8.0%)
- engineering: 2 (8.0%)
- data_science: 0 (0.0%)
- other: 7 (28.0%)

## Top 25 Distribution (Intent OFF)
- leadership: 1 (4.0%)
- architecture: 5 (20.0%)
- strategy: 1 (4.0%)
- engineering: 11 (44.0%)
- data_science: 0 (0.0%)
- other: 7 (28.0%)

## Top 25 Delta (ON - OFF)
- leadership: 3 (12.0%)
- architecture: 5 (20.0%)
- strategy: 1 (4.0%)
- engineering: -9 (-36.0%)
- data_science: 0 (0.0%)
- other: 0 (0.0%)

## Top 50 Distribution (Intent ON)
- leadership: 6 (12.0%)
- architecture: 10 (20.0%)
- strategy: 5 (10.0%)
- engineering: 4 (8.0%)
- data_science: 0 (0.0%)
- other: 25 (50.0%)

## Top 50 Distribution (Intent OFF)
- leadership: 3 (6.0%)
- architecture: 10 (20.0%)
- strategy: 1 (2.0%)
- engineering: 22 (44.0%)
- data_science: 0 (0.0%)
- other: 14 (28.0%)

## Top 50 Delta (ON - OFF)
- leadership: 3 (6.0%)
- architecture: 0 (0.0%)
- strategy: 4 (8.0%)
- engineering: -18 (-36.0%)
- data_science: 0 (0.0%)
- other: 11 (22.0%)

## Biggest Upward Movers (Top 100)
- Sales Operations and Strategy, Mid-Market | Cloudflare | Hybrid | 101 -> 27 | score_raw 0.1552 | score_on 0.2152 | intent bonus adj 0.06 out_of_scope False | adjusted_by preset:balanced + intent:bonus:executive_strategy
- Strategy and M&A Lead | Cloudflare | Hybrid | 101 -> 28 | score_raw 0.1516 | score_on 0.2116 | intent bonus adj 0.06 out_of_scope False | adjusted_by preset:balanced + intent:bonus:executive_strategy
- GTM Strategy Manager, Cloudflare One | Cloudflare | Hybrid | 101 -> 29 | score_raw 0.148 | score_on 0.208 | intent bonus adj 0.06 out_of_scope False | adjusted_by preset:balanced + intent:bonus:executive_strategy
- Senior Territory Account Executive, Ukraine | Cloudflare | Hybrid | 101 -> 30 | score_raw 0.1363 | score_on 0.1963 | intent bonus adj 0.06 out_of_scope False | adjusted_by preset:balanced + intent:bonus:executive_strategy
- Vice President, Strategy and Planning | Cloudflare | Hybrid | 101 -> 31 | score_raw 0.1354 | score_on 0.1954 | intent bonus adj 0.06 out_of_scope False | adjusted_by preset:balanced + intent:bonus:executive_strategy
- Senior Named Account Executive, Spain | Cloudflare | Hybrid | 101 -> 39 | score_raw 0.1218 | score_on 0.1818 | intent bonus adj 0.06 out_of_scope False | adjusted_by preset:balanced + intent:bonus:executive_strategy
- Application Security and Performance Consultant | Cloudflare | Distributed; Hybrid | 101 -> 42 | score_raw 0.1203 | score_on 0.1803 | intent bonus adj 0.06 out_of_scope False | adjusted_by preset:balanced + intent:bonus:executive_strategy
- Director of Product, Media Platform | Cloudflare | Hybrid | 84 -> 26 | score_raw 0.1678 | score_on 0.2278 | intent bonus adj 0.06 out_of_scope False | adjusted_by preset:balanced + intent:bonus:executive_strategy
- Director, Product Marketing - Application Security and Performance | Cloudflare | Hybrid | 81 -> 25 | score_raw 0.1682 | score_on 0.2282 | intent bonus adj 0.06 out_of_scope False | adjusted_by preset:balanced + intent:bonus:executive_strategy
- Strategic Account Executive - India ( Mumbai BFSI ) | GitLab | Remote, India | 101 -> 47 | score_raw 0.1199 | score_on 0.1799 | intent bonus adj 0.06 out_of_scope False | adjusted_by preset:balanced + intent:bonus:executive_strategy
- Strategic Account Executive - Energy, Utilities, Manufacturing, Spain | GitLab | Remote, Spain | 101 -> 51 | score_raw 0.1184 | score_on 0.1784 | intent bonus adj 0.06 out_of_scope False | adjusted_by preset:balanced + intent:bonus:executive_strategy
- Strategic Account Executive - Financial Services Industry, Spain | GitLab | Remote, Spain | 101 -> 52 | score_raw 0.1184 | score_on 0.1784 | intent bonus adj 0.06 out_of_scope False | adjusted_by preset:balanced + intent:bonus:executive_strategy
- Senior Named Account Executive, Mumbai | Cloudflare | Hybrid | 101 -> 53 | score_raw 0.1181 | score_on 0.1781 | intent bonus adj 0.06 out_of_scope False | adjusted_by preset:balanced + intent:bonus:executive_strategy
- Senior Renewals & BDR Operations & Strategy Manager (11-month contract) | Cloudflare | Hybrid | 67 -> 23 | score_raw 0.1759 | score_on 0.2359 | intent bonus adj 0.06 out_of_scope False | adjusted_by preset:balanced + intent:bonus:executive_strategy
- Director of Network Deployment Engineering & Infrastructure Operations | Cloudflare | Hybrid | 101 -> 58 | score_raw 0.1166 | score_on 0.1766 | intent bonus adj 0.06 out_of_scope False | adjusted_by preset:balanced + intent:bonus:executive_strategy
- Senior Majors Account Executive, Mumbai | Cloudflare | Hybrid | 101 -> 64 | score_raw 0.1145 | score_on 0.1745 | intent bonus adj 0.06 out_of_scope False | adjusted_by preset:balanced + intent:bonus:executive_strategy
- Big Data Solutions Architect (Professional Services) | Databricks | Remote - France | 101 -> 67 | score_raw 0.1132 | score_on 0.1732 | intent bonus adj 0.06 out_of_scope False | adjusted_by preset:balanced + intent:bonus:executive_strategy
- Enterprise Hunter Account Executive, Air Force | Databricks | Remote - Virginia | 101 -> 68 | score_raw 0.1132 | score_on 0.1732 | intent bonus adj 0.06 out_of_scope False | adjusted_by preset:balanced + intent:bonus:executive_strategy
- Senior Director of Product Management, Data Security | Cloudflare | Hybrid | 43 -> 20 | score_raw 0.1847 | score_on 0.2447 | intent bonus adj 0.06 out_of_scope False | adjusted_by preset:balanced + intent:bonus:executive_strategy
- Senior Director of Product - App Performance | Cloudflare | Hybrid | 44 -> 21 | score_raw 0.1843 | score_on 0.2443 | intent bonus adj 0.06 out_of_scope False | adjusted_by preset:balanced + intent:bonus:executive_strategy

## Biggest Downward Movers (Top 100)
- Software Engineer - Distributed Data Systems | Databricks | Belgrade, Serbia | 26 -> 98 | score_raw 0.2145 | score_on 0.1345 | intent penalty adj -0.08 out_of_scope False | adjusted_by preset:balanced + intent:penalty:executive_strategy
- Senior Offensive Security Engineer – Detection & Adversary Research | Elastic | United Kingdom | 24 -> 96 | score_raw 0.2184 | score_on 0.1384 | intent penalty adj -0.08 out_of_scope False | adjusted_by preset:balanced + intent:penalty:executive_strategy
- Sr. Software Engineer - Data Engineering | Databricks | Aarhus, Denmark | 23 -> 94 | score_raw 0.2218 | score_on 0.1418 | intent penalty adj -0.08 out_of_scope False | adjusted_by preset:balanced + intent:penalty:executive_strategy
- Senior Software Engineer - Distributed Data Systems | Databricks | Belgrade, Serbia | 22 -> 93 | score_raw 0.2232 | score_on 0.1432 | intent penalty adj -0.08 out_of_scope False | adjusted_by preset:balanced + intent:penalty:executive_strategy
- Senior Fullstack Engineer (RoR/vue.js), Software Supply Chain Security: Authorization | GitLab | Remote, Canada; Remote, Netherlands; Remote, United Kingdom | 32 -> 101 | score_raw 0.2122 | score_on None | intent neutral adj 0.0 out_of_scope True | adjusted_by preset:balanced
- Staff Software Engineer - Distributed Data Systems | Databricks | Belgrade, Serbia | 31 -> 100 | score_raw 0.2132 | score_on 0.1332 | intent penalty adj -0.08 out_of_scope False | adjusted_by preset:balanced + intent:penalty:executive_strategy
- Senior Software Engineer - Database Engine Internals | Databricks | Belgrade, Serbia | 30 -> 99 | score_raw 0.2132 | score_on 0.1332 | intent penalty adj -0.08 out_of_scope False | adjusted_by preset:balanced + intent:penalty:executive_strategy
- Software Engineer - Database Engine Internals | Databricks | Belgrade, Serbia | 34 -> 101 | score_raw 0.2036 | score_on None | intent neutral adj 0.0 out_of_scope True | adjusted_by preset:balanced
- AI Engineer - FDE (Forward Deployed Engineer) | Databricks | Remote - Germany | 14 -> 80 | score_raw 0.2444 | score_on 0.1644 | intent penalty adj -0.08 out_of_scope True | adjusted_by preset:balanced + intent:penalty:executive_strategy
- AI Engineer - FDE (Forward Deployed Engineer) | Databricks | London, United Kingdom | 15 -> 81 | score_raw 0.2444 | score_on 0.1644 | intent penalty adj -0.08 out_of_scope True | adjusted_by preset:balanced + intent:penalty:executive_strategy
- Staff Software Engineer - Database Engine Internals | Databricks | Belgrade, Serbia | 35 -> 101 | score_raw 0.2033 | score_on None | intent neutral adj 0.0 out_of_scope True | adjusted_by preset:balanced
- Senior Backend Engineer (Ruby on Rails), Verify: Pipeline Execution | GitLab | Remote, APAC; Remote, Canada; Remote, Netherlands; Remote, United Kingdom | 37 -> 101 | score_raw 0.2029 | score_on None | intent neutral adj 0.0 out_of_scope True | adjusted_by preset:balanced
- Intermediate Backend Engineer (Go), Verify: CI Functions Platform | GitLab | Remote, Canada; Remote, Netherlands; Remote, United Kingdom | 38 -> 101 | score_raw 0.2 | score_on None | intent neutral adj 0.0 out_of_scope True | adjusted_by preset:balanced
- Intermediate Fullstack Engineer (Ruby on rails/Vue.js), Monetization Engineering | GitLab | Remote, APAC; Remote, Canada; Remote, Europe; Remote, Netherlands; Remote, United Kingdom | 39 -> 101 | score_raw 0.1973 | score_on None | intent neutral adj 0.0 out_of_scope True | adjusted_by preset:balanced
- Intermediate Backend Engineer (RoR), Security Risk Management: Platform Management | GitLab | Remote, India; Remote, Netherlands; Remote, United Kingdom | 41 -> 101 | score_raw 0.1943 | score_on None | intent neutral adj 0.0 out_of_scope True | adjusted_by preset:balanced
- Intermediate Fullstack Engineer (TypeScript), AI Engineering: Editor Extensions – Multi-Platform | GitLab | Remote, APAC; Remote, Canada; Remote, Netherlands; Remote, United Kingdom | 13 -> 72 | score_raw 0.2516 | score_on 0.1716 | intent penalty adj -0.08 out_of_scope True | adjusted_by preset:balanced + intent:penalty:executive_strategy
- Elasticsearch - Principal Engineer – Core Infrastructure, JVM Internals | Elastic | United Kingdom | 42 -> 101 | score_raw 0.1939 | score_on None | intent neutral adj 0.0 out_of_scope True | adjusted_by preset:balanced
- Senior Applied AI Engineer | Databricks | Belgrade, Serbia | 10 -> 61 | score_raw 0.2557 | score_on 0.1757 | intent penalty adj -0.08 out_of_scope True | adjusted_by preset:balanced + intent:penalty:executive_strategy
- Intermediate Backend Engineer (Ruby on Rails), Analytics Instrumentation | GitLab | Remote, APAC; Remote, Canada; Remote, EMEA; Remote, Netherlands; Remote, United Kingdom | 51 -> 101 | score_raw 0.1816 | score_on None | intent neutral adj 0.0 out_of_scope True | adjusted_by preset:balanced
- Senior Site Reliability Engineer, Environment Automation | GitLab | Remote, Americas; Remote, Canada | 53 -> 101 | score_raw 0.1814 | score_on None | intent neutral adj 0.0 out_of_scope True | adjusted_by preset:balanced

## Coverage Sanity Check (Top 50, Intent ON)
- coverage==0 count: 49
- Examples (leadership/architecture/strategy with coverage==0):
  - Lead/Senior Solutions Architect – Retail & CPG (Data & AI) | Databricks | London, United Kingdom | len 0 | seniority lead | work_mode  | contract 
  - Consulting Architect, Public Sector - UK | Elastic | United Kingdom | len 0 | seniority c_level | work_mode  | contract 
  - Senior Specialist Solutions Architect - DS/ML/AI/GenAI | Databricks | London, United Kingdom | len 0 | seniority senior | work_mode  | contract 
  - Presales Solutions Architect (DS/ML/AI) | Databricks | London, United Kingdom | len 0 | seniority  | work_mode  | contract 
  - Pre-sales Solutions Architect (AI/ML/GenAI/LLM - Digital Native Business) | Databricks | London, United Kingdom | len 0 | seniority  | work_mode  | contract 

## Conclusion
- target families (leadership+architecture+strategy) in Top25: 16/25 (64.00%)
- engineering in Top25: 2/25 (8.00%)
- intent adjustment evidence in Top25: 17 entries
- Result: PASS