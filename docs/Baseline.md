B02 — Clean Temporal-Only Entity Alignment Baseline

1. Research Question

B01 showed that temporal linkage was almost trivial when the synthetic population contained only 40 patients. Longitudinal visit and sample dates behaved almost like unique identifiers.

B02 asks:

When population density increases substantially, how well can cross-system identities be recovered using temporal evidence alone, without introducing any artificial data corruption?

The purpose of B02 is to establish a clean reference baseline before introducing missingness, transcription errors, schema inconsistencies, incorrect assignments, or other forms of data disorder.

⸻

2. Controlled Change from B01

The primary change from B01 is population size:

[
N=40 \rightarrow N=4000
]

The underlying data-generating process remains unchanged.

No artificial corruption is introduced.

Specifically, B02 contains:

* no ID typos;
* no incorrect dates;
* no missing fields;
* no duplicate records introduced as errors;
* no incorrect patient assignments;
* no schema drift;
* no formatting corruption;
* no fuzzy string variation.

The difficulty therefore arises naturally from population density, partial observation, different identifier namespaces, and accidental temporal collisions.

⸻

3. Data Structure

A hidden canonical patient identifier defines the synthetic ground truth.

For example:

PT00001
├── clinical identifier: UPIN00101
└── laboratory identifier: P00011

The canonical identifier is not exposed to the matching algorithm.

Observable clinical data

Clinical_Visits.csv

Each clinical patient has a longitudinal sequence of visits:

Patient_ID → Visit_Date[]

Observable laboratory data

Sample_Tracking.csv

Each laboratory patient has a longitudinal sequence of sample collection events:

Patient_No → Collection_Date[]

PB and BM samples collected on the same date are collapsed into a single temporal event when constructing the timeline.

Evaluation-only ground truth

Patient_Identifiers.csv

This file contains the hidden mapping:

patient_uid ↔ clinical identifier
patient_uid ↔ laboratory identifier

It is used only after candidate generation and ranking have completed.

The matching algorithm never receives patient_uid or the clinical-to-laboratory crosswalk.

⸻

4. Candidate Generation

Brute-force comparison of all pairs would require:

[
4000\times4000=16,000,000
]

clinical–laboratory comparisons.

A simple temporal blocking rule is therefore applied before detailed scoring.

For every clinical and laboratory identity, its activity range is defined as:

[
[\min(date),\max(date)]
]

A pair is retained when the two activity ranges overlap or fall within a 30-day buffer.

Thus the pipeline is:

All clinical × lab pairs
        ↓
30-day activity-range blocking
        ↓
Candidate pairs
        ↓
Temporal scoring
        ↓
Ranking

Blocking is fixed across all B02 experiments.

⸻

5. Evaluation

Candidate laboratory identities are ranked independently for each clinical identity.

Evaluation uses the hidden canonical mapping only after ranking.

Metrics are calculated over all ground-truth clinical identities, including cases where blocking fails to retrieve the correct laboratory identity.

The reported metrics are:

* Retrieval rate — proportion of true matches surviving candidate generation;
* Top-1 accuracy — proportion of all clinical identities whose true match ranks first;
* Top-3 recall — proportion whose true match appears within the first three candidates;
* Top-10 recall — proportion whose true match appears within the first ten candidates;
* MRR — mean reciprocal rank of the true match, with unretrieved matches contributing zero.

This distinction is important because an earlier evaluation calculated ranking performance only among successfully retrieved true matches, producing conditionally inflated values.

⸻

6. B02a — Nearest-Event Heuristic

For each laboratory sample event (s_j), the nearest clinical visit is identified:

[
d_j=\min_i |s_j-v_i|
]

An event is considered a temporal hit when:

[
d_j\le2\text{ days}
]

Candidate pairs are ranked lexicographically by:

1. hit rate, descending;
2. number of hits, descending;
3. mean temporal distance, ascending.

Results

Metric	Result
Retrieval rate	0.97800
Top-1	0.84825
Top-3	0.93950
Top-10	0.97750
MRR	0.89698

The earlier conditional evaluation, restricted to true matches surviving blocking, produced Top-1 = 0.86733. The end-to-end value of 0.84825 is used as the official baseline.

⸻

7. B02b — One-to-One Event Assignment

The nearest-event heuristic allows individual sample events to select their nearest clinical visit independently.

B02b tests whether enforcing global one-to-one event correspondence improves identity discrimination.

A distance matrix is constructed:

[
D_{ij}=|s_i-v_j|
]

and the minimum-cost one-to-one assignment is obtained using the Hungarian algorithm.

All other experimental conditions remain unchanged.

Result

B02b produced the same ranking metrics as B02a.

Therefore, enforcing one-to-one temporal assignment provided no measurable improvement under the current clean data-generating process.

A likely explanation is structural: clinical visits are generally separated by 20–120 days, while sample collection occurs only approximately −1 to +2 days around the originating visit. Event competition is consequently rare.

⸻

8. B02c — Sequence Alignment

B02c treats the two longitudinal timelines as ordered sequences rather than independent sets of dates.

Dynamic programming allows three operations:

clinical visit ↔ sample event
skip clinical visit
skip sample event

Skipping a clinical visit is permitted without penalty because not every visit generates a sample.

Unexplained laboratory events receive a penalty.

The alignment preserves chronological ordering and therefore uses more trajectory structure than the nearest-event heuristic.

Result

B02c again produced the same ranking metrics as B02a and B02b.

Thus, under the current clean synthetic process, additional temporal alignment complexity did not improve identity recovery.

Nearest-neighbor matching, one-to-one assignment, and order-preserving sequence alignment effectively converge to the same discrimination performance.

⸻

9. B02d — Empirical Probabilistic Ranking

B02d tests a different hypothesis.

Instead of asking only how closely two timelines align, it attempts to quantify whether the observed number of temporal hits would be surprising under accidental matching.

A global background temporal hit probability (p_0) is estimated from candidate pairs.

For a candidate with (k) hits among (n) sample events, chance agreement is approximated using:

[
K\sim\operatorname{Binomial}(n,p_0)
]

and:

[
P(K\ge k\mid n,p_0)
]

is converted into an evidence score:

[
-\log_{10}P(K\ge k)
]

Result

The probabilistic ranking performed worse than B02a–c.

This should not be interpreted as evidence that probabilistic reasoning is inherently unsuitable. The baseline uses a deliberately simple global background model.

In particular:

* all patients share the same estimated background hit probability;
* temporal event independence is assumed;
* clinical timeline density is ignored;
* the background probability is estimated after temporal blocking, meaning the reference population is already enriched for temporally plausible candidates.

B02d is therefore retained as an informative negative baseline rather than optimized further.

⸻

10. Main Findings

B02 establishes several useful observations.

First, increasing population size from 40 to 4000 is sufficient to create substantial ambiguity without introducing artificial corruption. Temporal coincidences emerge naturally as the entity population becomes denser.

Second, candidate retrieval is strong but imperfect:

[
Retrieval\ Rate=97.8%
]

Approximately 2.2% of true identities are removed by the fixed blocking stage and therefore cannot be recovered by downstream ranking.

Third, among the tested deterministic temporal methods, additional algorithmic complexity does not improve performance. Nearest-event matching, one-to-one assignment, and sequence alignment produce the same end-to-end results.

Fourth, naïvely correcting for population-level chance coincidence using a single global background probability reduces ranking quality.

⸻

11. Frozen Clean Baseline

B02a is selected as the frozen clean reference method because it achieves the best observed performance while remaining the simplest and most interpretable temporal matcher.

The frozen clean baseline is therefore:

Population:          N = 4000
Injected corruption: None
Evidence source:     Temporal only
Blocking:            30-day activity-range overlap
Matcher:             Nearest-event heuristic
Tolerance:           ±2 days
Retrieval rate:      0.97800
Top-1:               0.84825
Top-3:               0.93950
Top-10:              0.97750
MRR:                 0.89698

B02 should not be interpreted as estimating the theoretical upper bound of entity resolution on clean data.

It establishes a narrower reference point:

Under the current synthetic data-generating process, a clean temporal-only cross-system linkage pipeline recovers 84.825% of identities at rank 1, while retrieving 97.8% of true identities into the candidate set.

This frozen reference can now be used as the control condition for subsequent experiments introducing controlled forms of data disorder.

12. Decision

B02 is frozen.

Further optimization of clean temporal matching is not pursued at this stage.

Subsequent experiments should preserve the B02 data-generating assumptions, blocking strategy, matcher, and evaluation framework wherever possible, while introducing controlled changes to the observed evidence.

This allows performance degradation to be attributed to specific forms of data disorder rather than simultaneous changes in both the data and the matching algorithm.