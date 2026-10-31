# Validation status — Z-Image

## GPU generation — NVIDIA A40 48 GB

All four packaged graphs executed on a disposable A40 Pod (`$0.59/hr`) from image digest
`sha256:a051f6aae260fbaa3a53432bfab0c276fdd04fe6d8b46cab14e670454f74c754`, built from commit
`94a4fe4`. The Pod downloaded both variants (about 33 GB), rendered at 512 × 512 with seed 42, and was
deleted automatically.

| Workflow | Elapsed | Entropy |
| --- | --- | --- |
| 03 Base Text to Image | 24.03 s | 9.02 |
| 04 Base Image to Image | 13.34 s | 9.03 |
| 01 Turbo Text to Image | 14.41 s | 9.25 |
| 02 Turbo Image to Image | 13.64 s | 9.18 |

Elapsed times include model loading when a variant first runs, so they are not per-image times. Each
variant generated first and its image-to-image run started from that output.

The PNGs were inspected rather than trusted to the numeric checks. Both text-to-image renders follow
the prompt closely: a lit lighthouse on a rocky headland, long-exposure sea, low cloud catching
the last light, a muted teal and amber palette. Turbo is the sharper and more dramatic of the two; base
is moodier. Both image-to-image outputs keep the source's composition while re-rendering it, which is the
intended behaviour at `denoise` 0.6. Two blemishes are visible: Turbo's variation has a swirled texture on
the bottom-right rocks and an added pier with figures, and base's has a strong HDR look and a few stray
white posts at the bottom edge. Neither is a failure of the workflow; both are what a text-to-image model
does when asked to vary a picture, and lowering `denoise` keeps more of the source.

## Not validated

- **Other GPUs.** Only an A40 has been run. Z-Image's weights are bf16 and need no FP8 support, so an L40S
  or RTX A6000 should behave the same, but that has not been shown.
- **Content filtering.** One benign prompt was rendered per variant. This says nothing about how the model
  treats borderline or mature prompts, and no claim is made about that here.
- **Output size.** Everything above was rendered at 512 × 512 for cost. The packaged default is 1280 × 720.

## How a first attempt failed

The first run never produced an image. The container crash-looped for the full 30-minute deadline on
`Model checksum mismatch`, because the pinned SHA256 values were not the files' hashes: they had been read
from the `ETag` of a redirected request and so held the CDN's value. Sizes were right and only the hashes
were wrong, which is why every local check passed. `scripts/verify-pins.py` now asks Hugging Face for the
authoritative LFS hash and size and runs in CI before each build, and `check-source` requires real hex.

## What the automated checks do and do not cover

Generation checks assert dimensions, pixel variance, entropy and flatness, and reject passthrough output. They do
not judge composition, prompt adherence or artefacts: a corrupted render with heavy texture raises entropy and
passes. Inspect the uploaded PNGs.
