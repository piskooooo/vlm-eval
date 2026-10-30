# Local validation — 2026-10-30

Scope: standalone candidate, Python 3.11.16 on macOS arm64. No application
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
- No paid or live model calls were made. The README supplies the live command.

## Privacy review scope

Gitleaks directory scans found zero matches in the standalone candidate and the
seven inspected original evaluation/backend modules. Publication candidate files
and built distributions were also inspected for private application identifiers,
local home paths, private network addresses and credential patterns. No original
private photos, model assets, environment files, runtime logs or historical
results were copied. There is no new Git commit history or remote to scan.

These are bounded checks, not proof that the entire original repository/history
is secret-free. No exposed credential was discovered in the inspected source.
No credential was modified or rotated. Raw future reports can contain private
model output and must be reviewed separately before sharing.

The source application's pre-existing backlog edit is preserved. The standalone
repository intentionally has no initial commit pending final review. An independent Codex review was used; no Hermes release-gate verdict,
public release, live model qualification, or owner acceptance is claimed.

## MIT and example dataset follow-up — 2026-10-30

The owner authorized MIT and an example image dataset, with publication and paid
model calls still excluded. Added three original procedural PNGs, their generator,
explicit MIT asset terms, independently specified labels, and SHA-256 provenance.
Two new checks failed before the assets existed, then passed after generation.
The complete suite now has 11 passing tests. New checks validate PNG chunks/CRCs,
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
