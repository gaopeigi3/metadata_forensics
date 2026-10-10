# B05 — LLM Forensic Investigation Report (MVP)

**Goal:** Turn B04's deterministic, auditable investigation JSON into a readable **Chinese** forensic report using an LLM. **The LLM does not perform matching, invent evidence, or see ground truth/corruption manifests.**

**Fast path:** Run B04 first so `b04_outputs/example_investigation.json` exists. This notebook also contains a small explicitly synthetic smoke-test case, so you can test the LLM connection without rerunning the 4000-patient benchmark.

**Backends:** DeepSeek API (OpenAI-compatible), OpenAI API, or local Ollama. Credentials are read from environment variables, never saved in the notebook. Network and API credentials are needed for live inference. No external Python package is required beyond `requests` (and `IPython` for notebook display).


## 1. Setup and choose model

## 2. Load evidence (B04 report or smoke-test example)

## 3. Evidence boundary and strict output contract

The supplied JSON is the **only** source of case facts. Do not pass B03 manifests, ground-truth mappings, `correct` labels, or private crosswalks into the LLM. `nearest_visit_distance_days` and `role` are computed upstream, not inferred by the LLM. The LLM may explain, compare, and recommend verification, but cannot certify an identity or assert that corruption occurred.

The report's `decision` is inherited from B04, not overwritten by the LLM. Candidate IDs and sample IDs are validated against the input to catch hallucinations.

## 4. Call the live LLM (DeepSeek / OpenAI / Ollama)

## 5. Verify LLM output against original evidence

## 6. Save audit bundle and render the report

## 7. Acceptance checklist and next step

- **Connectivity:** a live LLM response was received (not a hard-coded fake).
- **Provenance:** the saved audit JSON contains the exact upstream evidence payload, provider/model, and model output.
- **No label leakage:** B03 corruption manifest and true crosswalk are excluded from prompts.
- **Identity safety:** output candidate/sample IDs must be drawn from the provided case; upstream MATCH/REVIEW is immutable.
- **Limitations:** schema validation does **not** establish that every natural-language statement is true; manually inspect 3–5 cases before scaling.

**Next:** Use B04's `investigate(...)` to generate several real cases, then point `B05_CASE_PATH` to each JSON. Do not report smoke-test cases as benchmark results. Do not use real patient-identifiable records with a cloud API without appropriate authorization and de-identification.
