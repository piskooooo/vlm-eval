# vlm-eval

A small evaluator for structured vision-model answers: load local images and
human-labeled truth, call a vision model once per item, and save field-level
scores together with the evidence needed to interpret them.

**MIT licensed.** One three-image live evaluation passed using
Gemma 4 on llama.cpp; see the [run record](docs/live-evaluation-2026-10-30.md).
Ollama and OpenAI remain mock-tested only. The smoke result is not
a general accuracy claim.

## Scope and supported interface

- Python 3.11 or newer; currently validated on Python 3.11, macOS arm64.
- Three interfaces: Ollama `POST /api/chat` (default), llama.cpp
  `POST /v1/chat/completions` via `--provider llama-cpp`, and hosted OpenAI
  `POST /v1/responses` via `--provider openai`; non-streaming JSON answers.
- PNG/JPEG inputs, sent unchanged as base64. Signature checks are not full image
  decoding. No resizing, cropping, EXIF stripping, HEIC/MPO conversion or OCR stage.
- Arbitrary named string/null output fields and explicit truth states.
- No built-in benchmark, leaderboard, training, semantic similarity scoring,
  listing integrations, model installation, or service management.
- The pinned Gemma 4 / llama.cpp combination in the run record has passed the
  example smoke test. Other combinations remain unverified. Use a vision
  model already installed on your own server for the local adapters. The hosted
  OpenAI adapter is documented below and has no live verification. Model aliases can change;
  retain model digest, quantization and server version separately when comparing
  runs. Server defaults such as context size and thinking are not pinned here.

## Install

From this repository, using Python 3.11+:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install .
.venv/bin/vlm-eval --help
```

There are no third-party runtime dependencies. The isolated build downloads
`setuptools==80.9.0`; installation needs package-index access unless it is cached.
Tests use Python's standard library:

```sh
.venv/bin/python -m unittest discover -s tests -v
```

## Configure

Ollama defaults to `http://127.0.0.1:11434`; llama.cpp defaults to
`http://127.0.0.1:8080`. Local-provider environment variables:

- `VLM_EVAL_BASE_URL`: bare provider origin, without a path, query, or credentials.
- `VLM_EVAL_API_KEY`: optional bearer credential. HTTPS is required, except that the
  llama.cpp adapter permits authenticated HTTP on literal `127.0.0.1` or `::1`.

`.env.example` documents placeholders. Export variables in your shell; the CLI
**does not load `.env` files**. Non-loopback endpoints require HTTPS. Redirects
and environment proxies are disabled. No endpoint or key is written to reports.
Remote endpoints receive the full images and prompt; only configure one you intend
to use. Private image metadata is not removed. The tool does not send truth labels. OpenAI uses only `OPENAI_API_KEY` and a
fixed HTTPS destination; the local-provider variables above do not affect it.

## Included example: basic shapes

The [basic-shapes dataset](examples/shapes/README.md) contains three original PNGs
and independently specified color/shape labels. Images, labels and generator are
MIT licensed with an explicit image redistribution grant, provenance and hashes.
No private or third-party images are included. This is a smoke dataset, not a
representative benchmark. The recorded llama.cpp smoke result was 3/3 on each
field.

From the repository root, validate it without any model calls:

```sh
.venv/bin/vlm-eval validate examples/shapes/dataset.json
```

When you choose to run inference, with your own Ollama server already running:

```sh
export VLM_EVAL_MODEL='your-installed-vision-model'
.venv/bin/vlm-eval run examples/shapes/dataset.json --model "$VLM_EVAL_MODEL" --temperature 0 --seed 0 --max-tokens 512 --timeout 120 --out runs/shapes-001.json
```

Replace the placeholder with the exact installed vision-model identifier. The
run command makes three requests; it has not been executed against a real model.
Source distributions include this dataset; wheels install the CLI only. Keep the
source checkout or source archive for the examples.

## One real evaluation with your own image

No existing private photos are distributed. Take a photo you own of a red object,
save it as a real PNG named `object.png`, then prepare the dataset:

```sh
mkdir -p data/my-objects
cp examples/dataset.template.json data/my-objects/dataset.json
```

Place your image at `data/my-objects/object.png`. Inspect it yourself and edit the
truth color if necessary; never use a model's answer as ground truth. With your own
Ollama server already running, export the **exact installed vision-model name**:

```sh
export VLM_EVAL_MODEL='your-installed-vision-model'
.venv/bin/vlm-eval validate data/my-objects/dataset.json
.venv/bin/vlm-eval run data/my-objects/dataset.json --model "$VLM_EVAL_MODEL" --temperature 0 --seed 0 --max-tokens 512 --timeout 120 --out runs/my-objects-001.json
```

The placeholder model name must be replaced. This is the command for later live
verification; no real model call was performed during extraction. Use a fresh
output name for every run. There is no automatic retry. Each item makes one request.
Exit codes: 0 means responses were usable (scores may still fail), 1 means at least
one request/response failed, 2 means input/configuration/output setup failed.
An interrupted run can leave an empty/incomplete output file; there is no resume.

Local inference has hardware/electricity costs. An authenticated hosted endpoint
may charge for requests, including failures. This tool neither estimates nor
limits monetary cost, downloads models, nor manages provider billing.

## Dataset format

See `examples/dataset.template.json`. Schema 1 requires exactly:

- `schema_version`: integer 1; `dataset_id` and `version`: nonempty strings.
- `prompt`: full user prompt, including requested JSON fields.
- `items`: nonempty list of unique `id`, explicit relative `images` paths, and
  `truth` mapping field names to a state.

Each image must be a PNG/JPEG of at most 20 MiB; absolute paths, `..`, duplicate
paths within an item, and image symlinks are rejected. Paths are relative to the
manifest. All selected image bytes are held in memory, so keep datasets small.

Truth examples:

```json
{
  "color": {"state": "value", "value": "red"},
  "visible_text": {"state": "absent"},
  "material": {"state": "unknown"},
  "brand": {"state": "not_applicable"}
}
```

`value` requires a nonempty string. `unknown` skips that field. `absent` and
`not_applicable` require an explicit JSON null prediction; a missing key fails.
Ask the model for every field you intend to score. Booleans/numbers/arrays in model
answers are currently unsupported and invalidate the response. Extra string/null
fields are retained but unscored for local providers. OpenAI uses a strict schema
and rejects missing or additional keys. Dataset and response JSON with duplicate keys is invalid.

To add data, copy the template into an ignored `data/` directory, add owned images,
label them independently, and increment the dataset version when content changes.
To compare model configurations, rerun the same manifest with another installed
model name or CLI settings. An API other than Ollama, llama.cpp or OpenAI Responses requires a new adapter
and transport tests. Select OpenAI explicitly with `--provider openai`; changing
a local-provider URL does not select the hosted adapter.

## Scoring and results

`normalized-exact-truth-states-v1` compares strings after case folding and collapsing
whitespace. It gives no substring, synonym, fuzzy or partial credit. `red` and
`RED` match; `red` and `dark red` do not. Request failures, malformed/truncated JSON,
and missing fields fail all applicable scoreable fields. Unknown truth stays
skipped even on an error.

Each field reports `pass`, `fail`, `skip`, and `rate = pass / (pass + fail)`.
An entirely unknown field has a null rate. There is no combined accuracy number;
compare field counts and denominators as well as rates. One example is a smoke
test, not evidence of broad model quality. Null-heavy datasets can reward
abstention; include representative positive labels and retain held-out data.

The CLI prints the summary JSON and saves:

```text
report.json
  schema_version, tool_version, run_id, started_at, finished_at
  dataset: id, version, canonical manifest SHA-256
  provider: requested model, interface, generation settings, timeout, retry policy
  prompt, scoring
  rows[]: id, image paths/hashes, truth, raw response, parsed prediction,
          status, field scores, measured wall_seconds, provider_metrics
  summary: per-field pass/fail/skip/rate
```

Image hashes bind the exact bytes sent. Raw responses include the provider-returned
model identifier when present. llama.cpp prompt/completion/total token counts and Ollama token counts and nanosecond durations are
copied only when supplied as nonnegative integers; they are provider-reported, not
independently measured. Client wall time includes request and scoring overhead.
OpenAI usage includes reported input/output/total tokens and cached/reasoning
tokens when supplied; invalid usage types are omitted. No cost is inferred.
OpenAI `raw` is an allowlisted inference record: output/refusal text, response ID,
returned model, status and usage. It excludes error bodies, input echoes,
annotations and unrelated API metadata. Other providers retain their native raw
responses. Failed transport responses have null raw output; server error
bodies and exception details are not retained. Review raw outputs for sensitive
content before sharing reports. Reports are created with owner-only permissions;
`data/`, `runs/`, `.env`, and local environments are ignored by Git.

## Repository

```text
src/vlm_eval/   dataset.py, scoring.py, runner.py, providers.py, openai_provider.py, __main__.py
examples/      shapes/ (3 MIT PNGs, labels, provenance, generator); dataset.template.json
tests/         dataset, scoring, and mocked HTTP/CLI checks
docs/          extraction, validation, licensing, public-release checklist
.env.example   optional provider configuration
pyproject.toml package/build metadata; no runtime dependencies
```

See [extraction](docs/extraction.md), [validation](docs/validation.md),
[licensing](docs/licensing.md), and [release checklist](docs/release-checklist.md).
Provider protocol reference: [Ollama Chat API](https://docs.ollama.com/api/chat).


### Using an existing llama.cpp vision server

Configure its origin and export any required `VLM_EVAL_API_KEY` securely, then use:

```sh
.venv/bin/vlm-eval run examples/shapes/dataset.json --provider llama-cpp --model "$VLM_EVAL_MODEL" --temperature 0 --seed 0 --max-tokens 512 --timeout 120 --out runs/shapes-llama-001.json
```

The server must already have a vision model and its matching projector loaded.
The adapter sends unchanged PNG/JPEG data URLs and requests `json_object` output.
It retains the native response, requires exactly one choice with finish reason
`stop`, and records provider-reported usage. It does not install, restart, unload,
or reconfigure the server. Obtain permission before sharing an application's
model service. [Protocol reference](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md).


## Hosted OpenAI vision (mock-validated, not live-verified)

Use `--provider openai` to opt into sending data to OpenAI. The adapter uses the
Responses API with inline images and strict JSON Schema output, not the llama.cpp
protocol. [GPT-5.4 mini](https://developers.openai.com/api/docs/models/gpt-5.4-mini)
is a currently documented image-input/Responses model. The example pins
`gpt-5.4-mini-2026-03-17`; this project has not run it live. `--model` is configurable,
but account access and image/structured-output support must be verified for any
model you choose. No untested model is claimed to work.

Set `OPENAI_API_KEY` in your shell using your secret manager or an interactive
hidden-input prompt; never place a real key in a command saved to history. The
CLI does not load `.env`. It reads no other credential for OpenAI. Requests go
only to `https://api.openai.com/v1/responses`, with normal TLS verification;
endpoint overrides, proxies and redirects are disabled. No Azure/custom gateway
support is included. The fixed destination is unaffected by `VLM_EVAL_BASE_URL`,
`VLM_EVAL_API_KEY` or `OPENAI_BASE_URL`.

After installing the current checkout and exporting your key, this is the exact
optional three-image live smoke command (do not run until you authorize charges):

```sh
.venv/bin/vlm-eval run examples/shapes/dataset.json --provider openai --model gpt-5.4-mini-2026-03-17 --max-requests 3 --max-tokens 512 --timeout 60 --out runs/shapes-openai-001.json
```

- `--max-requests` is required for OpenAI. A dataset larger than this limit is
  rejected before any requests; it is never silently truncated. The example has
  three items, hence at most three HTTP attempts. There are zero automatic retries.
- `--max-tokens` maps to `max_output_tokens` (minimum 16, default 512), including
  reasoning and visible output. `--timeout` sets the network-operation timeout
  (default 120 seconds), not a strict end-to-end run deadline. A timed-out request
  might still execute and be charged by the service.
- `--seed` and `--temperature` are explicitly unsupported in this hosted adapter,
  even if a selected model happens to accept temperature. Omit both. Sampling
  and reasoning use model defaults, recorded as such. Local providers retain
  their previous temperature/seed defaults of 0. Image detail is fixed to `auto`.
- Requests contain the original images (including any embedded metadata), the
  manifest prompt, model/settings, and the requested output field names and
  string-or-null types. Ground-truth values/states, item IDs, filenames and other
  dataset metadata are not sent. Do not embed private truth in your prompt or
  field names. No file uploads, tools or conversation history are used.
- Responses are requested with `store: false`; this does not promise zero provider
  retention. Review [OpenAI data controls](https://developers.openai.com/api/docs/guides/your-data)
  before sending sensitive material. Existing PNG/JPEG validation still applies;
  the hosted adapter additionally caps each serialized request at 32 MiB and each
  response at 4 MiB. Up to 100 output fields, each named with at most 128 characters.

**API usage can incur charges. Request and output-token limits are not a guaranteed
dollar spending cap.** Image/input tokens also cost money, model prices vary, and
reasoning may consume the output allowance. Incomplete responses are recorded as
failures, not silently retried. This tool does not estimate cost or manage billing.

Authentication/rate-limit/transport failures use `request_error`; refusals,
incomplete responses and malformed structured output use `invalid_response`.
A fixed `error_code` gives a safe reason without retaining sensitive error bodies.
Scoreable fields fail on either status, while unknown truth remains skipped.
The report preserves raw output/refusal text and measured client duration; no
credentials or authorization headers are recorded. See [provider implementation
and validation notes](docs/openai-provider.md) for the contract and limitations.
