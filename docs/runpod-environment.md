# Runpod template environment

Synced to account template **Z-Image Turbo ComfyUI One-Click** (`flzb1wunuh`) on 2026-10-30.

[Open template](https://console.runpod.io/deploy?template=flzb1wunuh)

Image: `ghcr.io/acdevmedia/zimage-comfyui:1`. Container disk: **200 GB**. Workspace: `/workspace`. Template service: `8188/http` (ComfyUI). The gateway port 8000 is used by the Hub/Serverless listing only and is not exposed by the Pod template. No persistent volume is requested; `volumeInGb` is 0 and storage is temporary.

`config/runpod-template.json` holds the Pod defaults. `.runpod/template-source.json` records the account source. `.runpod/hub.json` exposes the same values through Hub inputs or fixed values. `.runpod/tests.json` uses the same defaults for readiness tests. `.runpod/test_template_sync.py` fails if any of those files, this document or the README drift apart.

## Credentials

**None required.** Z-Image's weights are published ungated, so first boot downloads them anonymously. Supplying `HF_TOKEN` is optional and is honoured if present, which helps only with Hugging Face rate limits.

## Template variables

### `HF_HOME`

Default: `/workspace/.cache/huggingface`.

Hugging Face cache and metadata directory on container storage.

### `MODEL_MODE`

Default: `turbo`.

Which variant to download: `turbo` (the eight-step distilled model), `base` (the 25-step model) or `both`. Each variant is about 20.7 GB including the shared text encoder and VAE; `both` is about 33 GB.

### `STUDIO_VERSION`

Default: `1`.

Which model generation this image serves, matching `versions/1/`. It is baked at build time and selects the weights downloaded on first boot and the workflows installed.

### `PORT`

Default: `8000`.

Gateway HTTP and WebSocket port served by `.runpod/handler.py`. ComfyUI itself stays on 8188.

### `PORT_HEALTH`

Default: `8001`.

Readiness port. `/ping` returns 503 until ComfyUI reports device information, then 200.

## Hub additions and differences

The Pod template and the Hub listing build from the same Dockerfile and defaults. The Hub listing runs the readiness test in `.runpod/tests.json`; that establishes the service starts and answers, not that output quality is acceptable.

## Account template metadata

Visibility: public. No custom entrypoint or start command is set. SSH starts inside the container only when `PUBLIC_KEY` is supplied, and the template does not expose port 2222.
