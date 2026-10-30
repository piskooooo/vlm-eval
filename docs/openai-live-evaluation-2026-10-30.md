# OpenAI live smoke evaluation — 2026-10-30

One owner-authorized run completed from 22:45:54 to 22:45:57 UTC against the
original MIT `basic-shapes` dataset, version `1`, using tested commit
`e7420f44eb3afd8ebc614d58fe58cc6c5fb08709`. No application code or services changed.
The owner authorized committing and publishing this record and its sanitized report
after reviewing the live result.

## Execution and limits

The owner launched the local, ignored one-shot helper from an SSH shell containing
`OPENAI_API_KEY`. The actual invocation used absolute checkout paths; expressed
relative to the checkout root, that exact helper invocation is:

```sh
.venv/bin/python runs/launch_openai_smoke.py
```

Helper SHA-256: `3eb623980f0c11de64c698b2d7f1f42853e1698540d960f9c6544d05ec253c37`.
It verified the clean tested commit, installed/source module equality, pinned
manifest and image bindings, and model access with an authenticated GET to the
fixed OpenAI model endpoint before inference. It used an exclusive one-run marker
and invoked the existing `OpenAI` adapter and `runner.run(..., max_requests=3)`
directly on the validated in-memory dataset. It did not invoke the CLI. The helper
is a local operational artifact, not part of the installed tool or a prerequisite
for another developer. Equivalent CLI settings for a separately authorized run:

```sh
.venv/bin/vlm-eval run examples/shapes/dataset.json --provider openai --model gpt-5.4-mini-2026-03-17 --max-requests 3 --max-tokens 512 --timeout 60 --out runs/shapes-openai-new-run.json
```

Requested and returned model on all three responses:
`gpt-5.4-mini-2026-03-17`. Settings: output cap 512 per request, image detail `auto`,
sampling/reasoning model defaults, network-operation timeout 60 seconds,
non-streaming, strict string-or-null JSON Schema, `store: false`, zero retries.
Three inference requests were made, with no failures or additional evaluations.
Only the images, prompt, field-name/type schema and model settings were sent;
truth values/states stayed local. Model availability was verified for this account
at run time; future availability is not guaranteed.

## Results

All three API responses were `completed`, with row status `ok` and no error code.
This establishes successful execution separately from the following exact-match
scores: color **3/3**, shape **3/3**, zero failed or skipped fields.

| Item | Returned color / shape | Input tokens | Output tokens | Client seconds |
|---|---|---:|---:|---:|
| 001 | red / circle | 161 | 18 | 1.799 |
| 002 | green / square | 161 | 18 | 0.744 |
| 003 | blue / triangle | 161 | 18 | 0.891 |

Provider-reported totals: **483 input + 54 output = 537 tokens**. Cached input
and reasoning tokens were both zero. Summed client duration: **3.434 seconds**;
this is not a server-only latency measurement. Scoring was
`normalized-exact-truth-states-v1`, case-folded and whitespace-normalized exact
string comparison, not semantic or partial-credit scoring.

Official [model pricing](https://developers.openai.com/api/docs/models/gpt-5.4-mini)
was checked before inference: $0.75/million input and $4.50/million output tokens.
The conservative preflight estimate used 10,000 total input tokens and all 1,536
allowed output tokens, giving **$0.014412**, below the authorized $1 threshold.
Applying those rates to reported usage gives **$0.00060525 estimated usage cost**.
This is an estimate, not an independently verified bill. Request/output limits
are not a guaranteed dollar cap. No additional paid run is authorized by this record.

## Dataset and report provenance

Canonical manifest SHA-256:
`c03ece3074c6b1499c210000365491e738b1f684f85cef8ef32f069993e24450`.
Each item used one unchanged 256×256 PNG:

| Image | SHA-256 |
|---|---|
| 001.png | `c161584c4b7db1b44465bc86efb9a7958ea0731a8bd53cae287108610e641e0c` |
| 002.png | `6d9521b7ff9c206ec6d758b968f4c995420cb99139c29d67fce672e0e9e67f3c` |
| 003.png | `ce692670e8176bb480e1f706ac502ceb624be49cf9ae8a2ce2766488c77280ca` |

The [sanitized report](reports/shapes-openai-2026-10-30.json) retains the exact
prompt, predictions, raw inference text, scores, models, settings, timing and usage.
Only the three provider response IDs were removed from the original report for
publication hygiene. The original remains preserved under ignored `runs/` as
`shapes-openai-live-20261030T224554Z-01701f96.json`, alongside preflight evidence.
The report was reviewed for credentials, authorization headers, private endpoints,
local home paths and unrelated personal/application data; none were included.

## Validation and limitations

Before inference, all 28 project tests and five mocked launcher checks passed,
and the three-image dataset validated. An independent launcher review passed
before the owner ran it. No live failure cases were deliberately induced.

This tiny procedural dataset checks transport, structured output, parsing and
scoring integration. It is not a benchmark, evidence of general vision accuracy,
or validation of other models, real-world images, refusals, truncation or rate
limits. Those error paths remain mock-tested. Ollama remains mock-tested only;
llama.cpp has its separate pinned local-model smoke record. No code fix was needed.
