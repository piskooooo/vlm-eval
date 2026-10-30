# Local validation — 2026-10-30

Current status: the initial release and OpenAI provider update are published.
The latest implementation suite passed 28 tests, including a clean Python 3.11
wheel installation. Both Gemma 4 / llama.cpp and OpenAI GPT-5.4 mini have
three-image live smoke evidence. Ollama remains mock-tested only. The OpenAI run
used three authorized paid requests; see the [live record](openai-live-evaluation-2026-10-30.md).
See the [release record](release-checklist.md) for commit identities.

## Initial extraction evidence (historical)

Scope at extraction: standalone candidate, Python 3.11.16 on macOS arm64. No application
configuration, original source files, model services or private photos changed.

- Initial behavioral tests failed on unimplemented dataset/scoring/runner functions;
  implementation then passed five tests.
- Provider/CLI tests first failed; implementation then passed seven tests.
- Independent review identified unhandled HTTP response errors and nonfinite JSON
  numeric overflow. Both were reproduced with failing tests before correction.
- Initial extraction suite: nine tests, all passing. It covers exact/truth-state scoring,
  dataset/image hashes, duplicate IDs, invalid truth, path rejection, malformed
  predictions, HTTP errors, numeric overflow, endpoint rules, the complete
  installed CLI against a loopback HTTP fixture, template usage and no-overwrite.
- A clean venv installed the package using the README's pip workflow. The installed
  CLI and tests passed. Source archive and pure-Python wheel build successfully.
- The HTTP fixture uses synthetic bytes with an image signature, not a real
  decoded image. It verifies base64 transport and workflow only. No real image
  decode or model-accuracy result is claimed.
- No paid or live model calls were made during initial extraction. The later
  authorized local-model run is recorded below.

## Initial privacy review scope (historical)

Gitleaks directory scans found zero matches in the standalone candidate and the
seven inspected original evaluation/backend modules. Publication candidate files
and built distributions were also inspected for private application identifiers,
local home paths, private network addresses and credential patterns. No original
private photos, model assets, environment files, runtime logs or historical
results were copied. At that initial checkpoint there was no Git commit history
or remote to scan. Later pre-publication scans covered the new commit history.

These are bounded checks, not proof that the entire original repository/history
is secret-free. No exposed credential was discovered in the inspected source.
No credential was modified or rotated. Raw future reports can contain private
model output and must be reviewed separately before sharing.

The source application's pre-existing backlog edit was preserved. At this initial
checkpoint, the standalone repository was uncommitted pending review. Independent
Codex review was used; it was not a Hermes release-gate verdict. Subsequent
publication and the bounded live evaluation are recorded separately.

## MIT and example dataset follow-up — 2026-10-30

The owner authorized MIT and an example image dataset, with publication and paid
model calls excluded at that stage. Added three original procedural PNGs, their generator,
explicit MIT asset terms, independently specified labels, and SHA-256 provenance.
Two new checks failed before the assets existed, then passed after generation.
The suite at that stage had 11 passing tests. New checks validate PNG chunks/CRCs,
dimensions, decompressed pixels, provenance hashes and the three-item mocked
scoring workflow. All three images were visually inspected. Fixture scores are
plumbing evidence only, not real model results. No model calls were made.

## llama.cpp and live follow-up — 2026-10-30

The owner authorized using the existing idle local model service. Three new
adapter tests failed before implementation; all 14 tests then passed, including
installed-package HTTP/CLI checks. Independent review passed before inference.
The real three-request run then passed both fields 3/3 with no retries, paid calls,
service changes or publication. See `live-evaluation-2026-10-30.md` for exact
identities, settings, results and bounded service-preservation evidence. Earlier
"no model calls" statements describe the preceding preparation only.

## Hosted OpenAI follow-up — 2026-10-30

Added a separate Responses API adapter using current official documentation.
The 28-test source suite passes, including all 14 prior local-provider checks.
New cases cover structured image requests, credential isolation, explicit limits,
refusals/incompleteness, sanitized HTTP failures and the mocked three-image CLI
workflow. OpenAI test sockets are blocked; no real credentials or paid requests
were used. See `openai-provider.md` for the exact optional live command and limits.


## Publication verification — 2026-10-30

The owner authorized both releases. Initial commit `7b8e529` and OpenAI update
`3a8ad31` were pushed to the public repository's `main` branch; remote commit
identities were verified. Exact-tree independent reviews passed, and Gitleaks
scans of publication files, expanded packages and new Git history found no matches.
Git uses the public GitHub username and GitHub noreply commit address. Local raw
runs and private service details remain ignored and were not published.
The OpenAI update passed 28 tests before push; this is mocked evidence, not live
OpenAI verification. No listing application or service changes were made.

## Authorized OpenAI live smoke — 2026-10-30

At tested commit `e7420f44eb3afd8ebc614d58fe58cc6c5fb08709`, the owner launched the
reviewed one-shot helper from the credential-bearing SSH shell. Preflight passed
28 project tests, five mocked launcher checks, dataset/hash validation and account
model availability. Three requests completed successfully: color 3/3, shape 3/3,
483 input and 54 output tokens, 3.434 seconds summed client time. No retries,
additional evaluations, application changes or service changes occurred.
See the [live record and sanitized report](openai-live-evaluation-2026-10-30.md).
The earlier mock-only statements above describe the implementation/publication
checkpoints, not the current OpenAI evidence. Live failure cases and Ollama remain
unverified; this smoke run is not a general accuracy benchmark.
