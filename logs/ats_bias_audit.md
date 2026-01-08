# ATS Coverage Bias Audit

## Active ATS Inventory (Observed)
| ATS | Company | Jobs | % of Corpus |
| --- | --- | --- | --- |
| greenhouse | Cloudflare | 142 | 62.0% |
| greenhouse | Databricks | 41 | 17.9% |
| greenhouse | Elastic | 4 | 1.7% |
| greenhouse | GitLab | 41 | 17.9% |
| sample | TechCorp | 1 | 0.4% |

## Role-Family Distribution per ATS
| ATS | Company | Total | % Leadership | % Architecture | % Strategy | % Engineering | % Data Science | % Other |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| greenhouse | Cloudflare | 142 | 5.6% | 2.8% | 4.2% | 51.4% | 0.0% | 35.9% |
| greenhouse | Databricks | 41 | 4.9% | 26.8% | 0.0% | 48.8% | 0.0% | 19.5% |
| greenhouse | Elastic | 4 | 0.0% | 25.0% | 0.0% | 50.0% | 0.0% | 25.0% |
| greenhouse | GitLab | 41 | 0.0% | 2.4% | 2.4% | 61.0% | 0.0% | 34.1% |
| sample | TechCorp | 1 | 0.0% | 0.0% | 100.0% | 0.0% | 0.0% | 0.0% |

## Cross-ATS Aggregation vs Top 50 (Intent ON)
### Corpus Distribution
- leadership: 10 (4.4%)
- architecture: 17 (7.4%)
- strategy: 8 (3.5%)
- engineering: 120 (52.4%)
- data_science: 0 (0.0%)
- other: 74 (32.3%)
### Top 50 Distribution (Intent ON)
- leadership: 6 (12.0%)
- architecture: 10 (20.0%)
- strategy: 5 (10.0%)
- engineering: 4 (8.0%)
- data_science: 0 (0.0%)
- other: 25 (50.0%)

- Engineering roles are more prevalent in the crawl corpus than in Top 50 results.
- Intent calibration mitigates corpus bias by pulling non-engineering roles up in Top 50.

## Title-Level Skew (Top 15 Titles per ATS)
### greenhouse | Cloudflare
- consultant developer platform (2)
- data analyst (2)
- senior security engineer security technology delivery (2)
- technical support engineer zero trust (2)
- application security and performance consultant (1)
- application security engineer (1)
- application security fullstack engineer (1)
- cloud and ai strategic negotiator (1)
- cloudforce one malware reversing engineer (1)
- cloudforce one react principal consultant (1)
- corporate counsel governance and securities (1)
- crm data governance analyst 6 month contract (1)
- customer education instructional designer and trainer (1)
- data analyst finance transformation (1)
- data and analytics engineer (1)
### greenhouse | Databricks
- ai engineer fde forward deployed engineer (5)
- big data solutions architect professional services (4)
- staff product security engineer (3)
- senior sap product specialist (2)
- big data manager professional services (1)
- director enterprise retail cpg (1)
- director enterprise sales retail travel hospitality (1)
- enterprise hunter account executive air force (1)
- lead senior solutions architect retail cpg data ai (1)
- lead solutions architect cto level cpg retail ds de background (1)
- pre sales solutions architect ai ml genai llm digital native business (1)
- presales solutions architect ds ml ai (1)
- product management intern 2026 berlin (1)
- product manager new grad 2026 berlin (1)
- senior applied ai engineer (1)
### greenhouse | Elastic
- consulting architect public sector uk (1)
- elasticsearch principal engineer core infrastructure jvm internals (1)
- security enterprise account executive (1)
- senior offensive security engineer detection adversary research (1)
### greenhouse | GitLab
- associate paralegal privacy (1)
- data analyst customer intelligence (1)
- distinguished data systems architect data engineering (1)
- engineering manager database reliability scalability operations (1)
- engineering manager software supply chain security auth infrastructure (1)
- engineering manager software supply chain security pipeline security (1)
- intermediate backend engineer golang monitor platform insights (1)
- intermediate backend engineer go verify ci functions platform (1)
- intermediate backend engineer ror security risk management platform management (1)
- intermediate backend engineer ruby on rails analytics instrumentation (1)
- intermediate backend engineer ruby on rails plan knowledge (1)
- intermediate fullstack engineer ruby on rails vue js monetization engineering (1)
- intermediate fullstack engineer typescript ai engineering editor extensions multi platform (1)
- intermediate site reliability engineer database operations (1)
- intermediate site reliability engineer environment automation (1)
### sample | TechCorp
- ai strategy consultant (1)

## Bias Indicators
- greenhouse | Cloudflare: 58% titles include engineering tokens
- greenhouse | GitLab: 63% titles include engineering tokens

## Coverage Gap Hypothesis
- Underrepresented families in corpus: leadership (4.4%), architecture (7.4%), strategy (3.5%).
- These roles are often posted outside engineering-focused ATSs (executive search, LinkedIn-native, consulting firm boards).

## Verdict
- WARN
- PASS: ATS bias exists but intent calibration keeps Top 25/50 target-aligned.
- WARN: ATS bias limits discovery breadth despite correct top ranks.
- FAIL: ATS bias overwhelms intent logic.