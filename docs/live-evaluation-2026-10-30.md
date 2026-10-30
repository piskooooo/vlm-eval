# First live evaluation — 2026-10-30

One owner-authorized local run of `basic-shapes` version 1 completed successfully
on 2026-10-30 at 14:48 EDT (18:48 UTC). This is an actual vision-model run, not
fixture output. It is only a three-image workflow smoke test, not a benchmark or
proof of general accuracy.

## Configuration and identity

- Interface: llama.cpp `/v1/chat/completions`; model alias: `gemma4`.
- Resident model: Gemma 4 12B Q4, identified by the verified existing model pin.
- llama.cpp: `0.6.0`, build `11429`, commit `d81235049`.
- Model SHA-256: `0a270ec9fe6b34f4a0d33992b6135117b484ebc4766ab76b51d4ae8c457e4c42`.
- Projector SHA-256: `2e269f906eb15169ee9ce880ea649bd6d42d4964c21f8ede10d0d0efc738bcbb`.
- Server binary SHA-256: `cbd72c3d3579820bf117263fa565bf482f08a4edd803c491a8eff734aa7401be`.
- Manifest SHA-256: `c03ece3074c6b1499c210000365491e738b1f684f85cef8ef32f069993e24450`.
- Temperature 0; seed 0; maximum output tokens 512; timeout 120 seconds;
  non-streaming `json_object`; no retries.
- Existing server settings: context 16,384; image minimum/maximum tokens 280;
  parallelism 1; reasoning off. Service settings were not changed.
- Scorer: `normalized-exact-truth-states-v1`.

## Observed results

| Image | Model response | Color | Shape | Client wall seconds |
|---|---|---|---|---:|
| 001 | red / circle | pass | pass | 2.033 |
| 002 | green / square | pass | pass | 2.267 |
| 003 | blue / triangle | pass | pass | 1.888 |

Color: 3 pass, 0 fail, 0 skip (100%). Shape: 3 pass, 0 fail, 0 skip (100%).
All three native responses finished with `stop`. Total measured request/scoring
wall time was approximately 6.188 seconds. Provider-reported tokens: 1,041 prompt,
61 completion, 1,102 total. These are reported counts, not billing estimates.
There were three local requests, no paid API calls, and no model downloads.

## Evidence and preservation

Local raw report: `runs/shapes-gemma4-live-2026-10-30.json`, run ID
`556a430d-a7e9-4a74-9760-5689716232dc`.
Report SHA-256: `85c7cf165a27aed69fabf9b71d5af0d72c8d0e5b1edc07f8ab866f2082bec073`.
It contains the exact prompt, image hashes, predictions, unmodified responses,
settings and scores. `runs/local-service-verification.json` retains local
before/after checks and model identity. Both remain in ignored local storage;
private endpoints, credentials and service configuration are not distributed.

The existing worker was healthy and idle before and after. Worker PID/start
identity, protected configuration hashes and model-file size/mtime were unchanged.
Before/after memory and swap guards passed; the existing supervisor remained in
control throughout. No model/service restart, app edit, app deployment, maintenance
switch or publication occurred. This does not claim continuous resource sampling
by the evaluator or validate the listing application's workflow.

## Reproduce on a separately configured server

Export `VLM_EVAL_BASE_URL`, `VLM_EVAL_MODEL` and any required `VLM_EVAL_API_KEY`
for your authorized local server, then:

```sh
.venv/bin/vlm-eval run examples/shapes/dataset.json --provider llama-cpp --model "$VLM_EVAL_MODEL" --temperature 0 --seed 0 --max-tokens 512 --timeout 120 --out runs/shapes-reproduction.json
```

Only the pinned model/server combination above has live evidence here. Ollama
remains mock-tested, and other models/interfaces are not qualified by this run.
