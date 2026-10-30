# Extraction scope

The source application contains a legacy directory/CSV evaluation runner,
field scorers, schema-v2 manifests with content hashes and explicit truth states,
validated reports/comparisons, and specialized prompt and label experiments.

Reusable code extracted verbatim: `score_truth_field` and `_norm_exact` from the
original `vision/eval/scorers.py`. TruthState/TruthField retain the original
semantics. The new string scorer removes legacy CSV sentinels; explicit truth
states carry absence and unknown instead. Generic report aggregation retains the
original pass/fail/skip denominator design. SHA-256 dataset/image identity follows
the existing manifest approach.

Most original code is not generic: the legacy runner imports VisionResult,
size standardization and fixed clothing/sports fields; manifests enforce that
ontology; reports depend on those types; image conversion uses application
helpers; experiment drivers pin private runtimes, datasets and control protocols.
Those modules were inspected but not copied. Their original benchmark results do
not transfer to this release. No private datasets, photos, logs, endpoint names,
model assets, account identifiers, or Git history were copied.

The dataset loader, CLI, generic evaluation loop and isolated Ollama adapter are
new integration code. The native JSON/base64 transport follows the same protocol
used by the original Ollama backend but removes listing prompts, parsing,
retries, image conversion, cache directories, and service unloading.

Out of scope: application changes, production services, eBay integration,
size/fiber/condition scoring, crop pipelines, statistical comparisons, hosted
provider adapters, model downloads, benchmark claims and publication. This is a focused extraction of the reusable scoring core with the
minimum independent plumbing; it is not a wholesale port of the evaluation suite.

Follow-up on 2026-10-30: the owner authorized MIT adoption and an original
procedural example dataset. Both are now included; publication and live-model
qualification remain outside this local follow-up.

A subsequent owner-authorized follow-up added a generic llama.cpp adapter and
completed one three-image live smoke evaluation using an already resident model.
Only vlm-eval source and local results changed; no original app or service changes
were made. The live run record supersedes the earlier qualification-pending status.
