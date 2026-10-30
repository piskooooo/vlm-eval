# Licensing and redistribution review

The owner selected MIT on 2026-10-30. The root LICENSE and package SPDX metadata
apply MIT to the published project, including the extracted scoring functions.
The owner subsequently authorized public GitHub publication; the initial release
and OpenAI provider update are published. See the [release record](release-checklist.md).

The original procedural example dataset has its own copy of LICENSE and explicit
redistribution terms covering images, labels, prompt, provenance and generator.
No original application photographs or third-party assets are included.

## Inventory

- Runtime: Python standard library only; Python itself is not vendored.
- Build: setuptools 80.9.0, MIT; installed in an isolated build environment and
  not bundled into the vlm-eval wheel. [Upstream license](https://github.com/pypa/setuptools/blob/v80.9.0/LICENSE).
- Tests: unittest and a local HTTP server from the standard library. Synthetic
  byte fixtures test transport only; they are not a distributable image dataset.
- Ollama and llama.cpp: external user-provided servers, not redistributed. Review
  the selected server distribution and model license separately.
- OpenAI: external hosted API, not redistributed; no SDK dependency or model
  assets are bundled. Its adapter remains mock-tested only.
- Model weights, projectors and tokenizer assets: none included or downloaded.
- Images/datasets: three original procedural PNGs in `examples/shapes/`, licensed
  MIT with provenance and content hashes. No external source assets. The template
  also contains only generic authored text. Private source photos remain excluded.
- No third-party implementation source was vendored. The two extracted scorer
  functions originate in the private application; the owner has authorized MIT for this extraction.

No model compatibility or benchmark score is implied by the dependency inventory.
