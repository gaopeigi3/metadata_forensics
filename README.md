# Metadata Forensics: B01–B05 Python Project

This project refactors the five supplied notebooks into importable Python modules and command-line workflows. It runs without Jupyter, IPython, or the original notebooks. The original files are preserved. Instructions in the source documents are retained as experimental reference material.

## Installation and Usage

Run these commands from the project directory (Python 3.10+):

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .

# B01: 40 patients, without activity-range blocking
metadata-forensics b01

# B02: 4,000 patients, four methods; add --methods nearest for the frozen baseline only
metadata-forensics b02

# B03: 10 main experimental conditions + 3 separate fragmentation diagnostics
metadata-forensics b03

# B04: three conditions by default; add --full to run all ten
metadata-forensics b04

# B05: prepare evidence and prompts offline; no model report is generated
metadata-forensics b05 --case outputs/b04/example_investigation.json

# Call the model explicitly; first set DEEPSEEK_API_KEY in your environment
metadata-forensics b05 --case outputs/b04/example_investigation.json --live --provider deepseek
```

`python -m metadata_forensics` is equivalent to `metadata-forensics`. Before installing the package, you can also run `PYTHONPATH=src python -m metadata_forensics ...` from the project root.

For a quick smoke test, add `--n-patients 40` to B02–B04. These small runs verify execution and do not represent the N=4,000 benchmark. The default seed is 42; use `--seed` to change it. Use `--output` to choose an output directory. Reusing a directory overwrites files with the same names, so use separate directories for different configurations.

B05 supports `--provider deepseek|openai|ollama` and `--model`, along with the environment variables `B05_PROVIDER`, `B05_MODEL`, and `B05_BASE_URL`. OpenAI uses `OPENAI_API_KEY`; Ollama requires no API key. Default models and endpoints are inherited from the source notebook, and their current service availability has not been verified. A missing `--case` file raises an error rather than falling back to a demonstration case.

## Project Structure

```text
src/metadata_forensics/
  synthetic.py       Synthetic data; preserves the original random draw order
  matching.py        Activity-range blocking, four scoring methods, and ranking
  corruption.py      Date shifts, missing events, wrong assignments, ID fragmentation
  evaluation.py      All-ground-truth denominators, observability, alias-aware metrics
  investigation.py   Top-two counterfactuals, event localization, evidence reports
  reporting.py       Evidence allowlist, model calls, output validation, and auditing
  pipeline.py        B01–B04 orchestration and CSV/JSON/PNG output
  cli.py             Command-line interface
  __main__.py        Entry point for python -m
tests/               Regression and edge-case checks
docs/                Original experiment notes, source hashes, migration and validation records
validation/          Metrics and offline evidence examples from the validation runs
```

Main outputs:

- **B01/B02:** `metrics.csv` and method-specific `*_top10.csv` files.
- **B03:** `b03_results.csv`, `fragmentation_diagnostic.csv`, and performance degradation plots.
- **B04:** decision tables, event suspicion scores, diagnostics grouped by review status, localization plots, and `*_investigation.json` files.
- **B05:** `prepared_evidence.json` in offline mode, or an audit JSON bundle and a Markdown report in live mode.

Completed conditions are saved incrementally to `*_results_partial.csv`. Automatic resumption is not currently supported.

Ground-truth crosswalks, corruption manifests, and per-identity evaluations are stored in `evaluation_only/`. The matcher receives observed data only; the LLM receives only allowlisted evidence fields. `MATCH` preserves the upstream heuristic decision: it does not certify identity or automatically modify source records.

## Preserved Experimental Definitions and Limitations

- B02–B04 use a 30-day activity-range buffer and a ±2-day hit tolerance. PB/BM samples collected on the same date are collapsed into one temporal event.
- B02c retains `alignment_cost` as a ranking criterion. B02d estimates the global background hit probability from sequence-alignment results.
- Ranking ties are resolved by ascending `lab_id`, consistent with B03/B04. At N=4,000 and seed=42, B02a reproduces all principal metrics reported in the original baseline document.
- B03 has 10 main conditions and 3 separate fragmentation diagnostics. The original notebook heading described the main loop as having 13 conditions; this distinction is clarified here.
- B04 measures sensitivity to deleting dates within the original top-two candidate set; it does not rerank the full candidate set. When there is no second candidate, instability is undefined and the case is assigned to REVIEW.
- Event localization covers only observed samples in current top-1 pairings. Deleted rows cannot be localized. Stability, margin, and `MATCH` are not calibrated probabilities.
- Model output checks cover structure, candidate order, sample membership, and evidence roles. They cannot establish the factual accuracy of every natural-language statement.
- The pipeline retains the full candidate table. N=4,000 runs, particularly across multiple methods or conditions, require substantially more time and memory than 40-patient smoke tests.

## Tests

```bash
python -m unittest discover -s tests -v
```

See the [validation record](docs/VALIDATION.md) for the actual validation scope and dependency versions, and the [migration record](docs/MIGRATION.md) for implementation changes. These supporting records remain in Chinese.
