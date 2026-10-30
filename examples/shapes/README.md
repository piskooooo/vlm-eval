# Basic shapes, version 1

Three original 256×256 RGB PNGs: a red circle, green square and blue triangle,
each on white. Labels come from the geometry and color constants in `generate.py`,
not from a model. Numeric filenames do not disclose the target answers.

## Redistribution rights and provenance

Copyright (c) 2026 vlm-eval contributors. **SPDX-License-Identifier: MIT**.
The PNGs, dataset labels, prompt, provenance record, generator and this README
are provided under the accompanying [MIT license](LICENSE). You may use, copy,
modify and redistribute them, including commercially, subject to retaining the
license and copyright notice. This explicit grant covers the image assets as
well as the code and text, to the extent any rights apply.

Created locally for vlm-eval on 2026-10-30 using only procedural geometry and
Python's standard library. No third-party images, fonts, personal information,
private listing photos or generated model output were used. PNGs contain only
IHDR, IDAT and IEND chunks, with no textual or identifying metadata.
`provenance.json` records SHA-256 hashes of the shipped files.

Rebuild with `python3 examples/shapes/generate.py` from the repository root.
The pixel geometry is deterministic; PNG compression bytes can vary by zlib
version, so the generator refreshes the hashes together with the files.

This is a tiny workflow smoke dataset, not a representative benchmark. It cannot
establish photographic understanding, OCR ability, general accuracy or ranking.
Live smoke records for llama.cpp and OpenAI are linked from the main README.
These three simple images do not constitute a representative benchmark.
