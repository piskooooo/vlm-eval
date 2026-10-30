# OpenAI Responses provider — 2026-10-30

Published in commit `3a8ad31` after owner-authorized review, commit and push.
Status: one authorized live three-image run passed on 2026-10-30 using
`gpt-5.4-mini-2026-03-17`; see the [live record](openai-live-evaluation-2026-10-30.md).
Error paths remain mock-tested; this result does not qualify other models or datasets.

## Contract and sources

Official documentation was checked before implementation:

- [Image inputs](https://developers.openai.com/api/docs/guides/images-vision):
  inline base64 PNG/JPEG data URLs in `input_image` content.
- [Structured outputs](https://developers.openai.com/api/docs/guides/structured-outputs):
  Responses `text.format` strict JSON Schema and explicit refusal/incomplete handling.
- [Responses reference](https://developers.openai.com/api/reference/python/resources/responses/methods/create):
  output-token limit, response lifecycle, usage and storage control.
- [GPT-5.4 mini](https://developers.openai.com/api/docs/models/gpt-5.4-mini):
  current documented vision example, snapshot `gpt-5.4-mini-2026-03-17`.

The new `OpenAI` provider follows the existing `metadata`/`generate` interface,
with field-name-only schema input and a provider-specific response parser. It
uses Python's standard library and adds no runtime dependency. Existing Ollama
and llama.cpp provider implementations are unchanged. The common runner retains
truth-state semantics and failure denominators; the CLI resolves omitted local
seed/temperature to their original zero defaults.

Per-item output schema: a root object with one required string-or-null property
for each truth field **name**, and `additionalProperties: false`. No truth values,
truth states, enums inferred from answers, filenames or IDs enter the request.
The exact schema can be reconstructed from the report's row field names and the
recorded `strict-json-schema-string-or-null-v1` format. Different items may have
different field sets. Schema bounds are preflighted across all items before calls.

`--max-requests` is required for the hosted CLI and runner. It bounds the entire
dataset rather than selecting a prefix. There is one HTTP attempt per item, zero
retries and no SDK background retry behavior. The output cap maps to
`max_output_tokens`; model-default sampling/reasoning are recorded. This version
rejects seed and temperature options for OpenAI. Unsupported models/settings
rejected by the API produce a failed request; no fallback model is substituted.

## Parsing, evidence and failures

Response parsing searches the output array for one completed assistant message,
allowing preceding reasoning items. It does not assume the first output item is
text. Exactly one output-text block must parse as an object with the expected
keys and string/null values. Refusal blocks, incomplete/failed responses, missing
messages, duplicate JSON keys, extra keys and wrong value types fail closed.

OpenAI rows retain an allowlisted raw inference record: response ID, returned
model, status, safe incomplete reason, output/refusal text and valid token usage.
Error objects, HTTP bodies/headers, input echoes, annotations and unrelated
metadata are not stored. A credential echoed in retained text is redacted. This
is intentionally not a byte-for-byte copy of the entire HTTP response. Model
output can still include sensitive image/prompt content, so review reports before
sharing. API credentials never belong in prompts, images or field names.

| Event | Row status | Safe reason |
|---|---|---|
| HTTP 401/403 | request_error | authentication_error |
| HTTP 429 | request_error | rate_limited |
| Other non-success HTTP status | request_error | http_error |
| Timeout/network/protocol/redirect failure | request_error | transport_error |
| Invalid/oversized envelope | request_error | invalid_response_json / response_too_large |
| Oversized request or invalid image | request_error | request_too_large / invalid_image |
| Model refusal | invalid_response | refusal |
| Incomplete response | invalid_response | incomplete |
| Provider-declared failure | invalid_response | upstream_error |
| Malformed/schema-invalid answer | invalid_response | malformed_output |

All these failures retain the existing scoring rule: applicable fields fail,
unknown fields skip. Raw is null when no safe inference envelope was obtained.
Only nonnegative integer token counts are recorded. Output limits include
reasoning; missing usage is not estimated. There is no dollar spending cap.

## Validation and optional repeat command

New mocked tests demonstrated failures before implementation. The full 28-test
suite passes, including all 14 original tests. Coverage includes the three-image
CLI workflow, truth isolation, PNG transport, fixed HTTPS destination, credential
separation, redirect/proxy policy, schema parsing, refusal/incomplete output,
authentication/rate-limit/transport errors, output bounds, usage and no retries.
OpenAI tests explicitly block socket connections and use a placeholder credential.

Run from the repository root only after separate paid-call authorization and
securely exporting `OPENAI_API_KEY`:

```sh
.venv/bin/vlm-eval run examples/shapes/dataset.json --provider openai --model gpt-5.4-mini-2026-03-17 --max-requests 3 --max-tokens 512 --timeout 60 --out runs/shapes-openai-001.json
```

A 512-token cap may yield incomplete output, particularly with model-default
reasoning. Record that result rather than treating a larger cap or retry as
implicitly approved. Up to three attempts and 1,536 output tokens are requested;
input/image token charges and service behavior mean this is not a guaranteed
monetary limit. The live record covers only the tested account, snapshot and dataset.

Out of scope for the adapter: automatic retries, model discovery/downloads, pricing
estimates, Azure/custom endpoints, streaming, tools, SDK adoption, existing app
or service changes. Commit/push were separately authorized after local
implementation and completed. One subsequent paid smoke run was authorized and
completed; additional paid evaluations require new authorization in this workflow.
