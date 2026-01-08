# Source Intent Diagnostic

## Source Intent Classification
| Source | Company | Jobs | Intent Label | Notes |
| --- | --- | --- | --- | --- |
| greenhouse | Cloudflare | 142 | engineering_first | eng 51.4% / strat 4.2% / arch 2.8% / lead 5.6% |
| greenhouse | Databricks | 41 | consulting / advisory | eng 48.8% / strat 0.0% / arch 26.8% / lead 4.9% |
| greenhouse | Elastic | 4 | engineering_first | eng 50.0% / strat 0.0% / arch 25.0% / lead 0.0% |
| greenhouse | GitLab | 41 | engineering_first | eng 61.0% / strat 2.4% / arch 2.4% / lead 0.0% |
| sample | TechCorp | 1 | executive_search | eng 0.0% / strat 100.0% / arch 0.0% / lead 0.0% |

## Conditional Probabilities P(role_family | source)
### greenhouse | Cloudflare
- leadership: 5.6%
- architecture: 2.8%
- strategy: 4.2%
- engineering: 51.4%
- data_science: 0.0%
- other: 35.9%
### greenhouse | Databricks
- leadership: 4.9%
- architecture: 26.8%
- strategy: 0.0%
- engineering: 48.8%
- data_science: 0.0%
- other: 19.5%
### greenhouse | Elastic
- leadership: 0.0%
- architecture: 25.0%
- strategy: 0.0%
- engineering: 50.0%
- data_science: 0.0%
- other: 25.0%
### greenhouse | GitLab
- leadership: 0.0%
- architecture: 2.4%
- strategy: 2.4%
- engineering: 61.0%
- data_science: 0.0%
- other: 34.1%
### sample | TechCorp
- leadership: 0.0%
- architecture: 0.0%
- strategy: 100.0%
- engineering: 0.0%
- data_science: 0.0%
- other: 0.0%

## Structurally Unlikely Families (Corpus)
- leadership: 4.4% of corpus
- strategy: 3.5% of corpus
- data_science: 0.0% of corpus

## Source Reweighting Simulation
- cap per source: 30%
- source weights:
  - greenhouse: 0.30
  - sample: 1.00
### Top 25 (Original)
- leadership: 4 (16.0%)
- architecture: 10 (40.0%)
- strategy: 2 (8.0%)
- engineering: 2 (8.0%)
- data_science: 0 (0.0%)
- other: 7 (28.0%)
### Top 25 (Reweighted)
- leadership: 4 (16.0%)
- architecture: 10 (40.0%)
- strategy: 2 (8.0%)
- engineering: 2 (8.0%)
- data_science: 0 (0.0%)
- other: 7 (28.0%)
### Top 50 (Original)
- leadership: 6 (12.0%)
- architecture: 10 (20.0%)
- strategy: 5 (10.0%)
- engineering: 4 (8.0%)
- data_science: 0 (0.0%)
- other: 25 (50.0%)
### Top 50 (Reweighted)
- leadership: 6 (12.0%)
- architecture: 10 (20.0%)
- strategy: 5 (10.0%)
- engineering: 4 (8.0%)
- data_science: 0 (0.0%)
- other: 25 (50.0%)

## Impact Assessment
- Source reweighting does not materially change Top 25 composition.

## Recommendation
- A) Source intent layer REQUIRED
- Rationale:
  - Underrepresented role families suggest source bias in discovery.
  - Reweighting does not change top ranks, suggesting intent logic already dominates.