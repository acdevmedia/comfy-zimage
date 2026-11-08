# Z-Image Turbo ComfyUI One-Click

[![Runpod](https://api.runpod.io/badge/acdevmedia/comfy-zimage)](https://console.runpod.io/hub/listing/acdevmedia/comfy-zimage)

Z-Image running locally in ComfyUI: the eight-step **Turbo** model and the 25-step **base** model, with text-to-image and image-to-image for each. Weights are published ungated by Tongyi-MAI and packaged for ComfyUI by Comfy-Org, so there is no access agreement and no mandatory token.

Container: **`ghcr.io/acdevmedia/zimage-comfyui:1`**, with an immutable `1-sha-<commit>` tag per build. Model revisions, checksums and workflow defaults live under `versions/1/`.

Everything runs on ComfyUI's **native** Z-Image support — no custom nodes and no Diffusers pipeline, unlike the Ideogram package.

## Start on Runpod

1. Create or update the template with `python3 scripts/create-runpod-template.py`, or `--dry-run` to review the payload first. It only calls the Runpod API; it builds nothing and downloads no weights.
2. Launch on a **48 GB** GPU with a **200 GB container disk** and no persistent volume. L40S, A40 and RTX A6000 all suit it; each variant is about 20.7 GB resident, so there is ample headroom.
3. Open **Connect → HTTP 8188 / ComfyUI** once the service reports Ready. First boot downloads the pinned weights into `/workspace/ComfyUI/models`.
4. Pick a workflow in the sidebar, type a prompt, press Queue.

For authenticated downloads, create Runpod Secret `HUGGINGFACE_TOKEN` with your Hugging Face read token; the template maps it to `HF_TOKEN`. The weights are ungated, so you can remove the mapping to download anonymously. A token is optional and improves download rate limits.

Storage is temporary and no network volume is attached. First-boot downloads resume, your workflow edits persist across restarts, and no weights or credentials are baked into the image.

## Variants

| `MODEL_MODE` | Model | Steps | CFG | Download |
| --- | --- | --- | --- | --- |
| `turbo` (default) | `z_image_turbo_bf16` | 8 | 1.0 | 20.7 GB |
| `base` | `z_image_bf16` | 25 | 4.0 | 20.7 GB |
| `both` | both | — | — | 33.0 GB |

Both share the 8.04 GB Qwen3-4B text encoder and the 0.34 GB VAE, which is why `both` is far less than twice one variant. Turbo is the default: eight steps at CFG 1.0 makes it dramatically faster, and it is the model most people want for iteration.

## Workflows

- **01 / 02 Turbo** — text to image, and image to image.
- **03 / 04 Base** — the same pair on the 25-step model.
- **10 / 11 Advanced** — Comfy-Org's own upstream templates for turbo and base, kept verbatim as a reference.

Image-to-image loads your picture and uses it whole: **Render Width** and **Render Height** set the frame's area and the picture sets its shape, in multiples of 16, so a portrait stays a portrait and a very large upload cannot exhaust GPU memory. Turn on the **Exact Frame** node to use your typed size exactly, which centre-crops the image. It then VAE-encodes it and denoises toward the prompt at `denoise` 0.6. Lower values keep more of the source; raise it toward 1.0 for a freer reinterpretation. Raise `megapixels` on the scale node for a larger working size, at the cost of memory.

Z-Image is a text-to-image model, so this is **image-to-image variation**, not instruction-following editing: describe the picture you want rather than the change to make. For instruction-based edits, use the Qwen Image Edit package.

The sampler is `res_multistep` with the `simple` schedule and a `ModelSamplingAuraFlow` shift of 3, matching the upstream templates. Canvas defaults to **1280 × 720**.

The text encoder is loaded with `CLIPLoader` type **`lumina2`**. That looks wrong and is not: ComfyUI has no `z_image` option in that list, and a Qwen3-4B encoder is routed to the Z-Image text encoder for any type that is not FLUX. This is what the upstream templates do.

## Seeds

The seed widget carries ComfyUI's standard **control after generate**, set to `randomize` in every packaged workflow. Set `fixed` to reproduce an exact image, or `increment` to walk a series.

## Image preview ribbon

A strip of recent output images sits along the bottom of the window and refreshes as each queued graph finishes. Click a thumbnail to open the viewer: arrow keys move through the batch, **space** picks, **D** downloads, **Escape** closes. **Download picked** saves only the chosen files, so you can queue a batch, skim it and keep a few.

## Optional LoRAs

Turbo workflows use the [Flow-DPO](https://huggingface.co/F16/z-image-turbo-flow-dpo) photoreal lighting LoRA (Apache 2.0) at strength **0.7**, which works against the flat, plastic light of the 8-step model. Set its node's strength to 0 to turn it off, or try up to 1.0. It is trained for exactly 8 steps, so it is not on the base workflows.

The base workflows have a bypassed **Draft mode** node (EasyCache): select it and press Ctrl+B for quicker, softer drafts.

These are pinned and downloaded at first boot, never baked into the image. At strength 0 ComfyUI skips a LoRA entirely, so it costs nothing while it is off.

## Speed

ComfyUI starts with SageAttention and `--highvram`, so models stay on the 48 GB GPU between runs. Each boot tests Sage on the assigned GPU and falls back to PyTorch attention if the check fails; set `COMFYUI_ATTENTION=pytorch` to force that. Attention that needs a mask runs on PyTorch either way. First-boot downloads use Hugging Face's high-performance Xet mode.

## Browse and download outputs

**Connect → HTTP 3923 / Copyparty** opens a gallery of everything in `/workspace/ComfyUI/output`, newest first. Sign in with the values of Runpod Secrets `COPYPARTY_USERNAME` and `COPYPARTY_SECRET`. Select files to download them, or a whole folder as a ZIP. It is read-only: nothing can be uploaded, changed or deleted, and if either secret is missing it stays off without affecting ComfyUI. The log is `/workspace/logs/copyparty.log`.

`zip`, `unzip` and `aws` are on the path in the terminal for moving outputs off the Pod yourself.

## Environment variables

- `HF_TOKEN`: `{{ RUNPOD_SECRET_HUGGINGFACE_TOKEN }}`; optional read token for authenticated Hugging Face downloads.
- `COPYPARTY_USERNAME`: `{{ RUNPOD_SECRET_COPYPARTY_USERNAME }}`; login for the file browser on port 3923.
- `COPYPARTY_PASSWORD`: `{{ RUNPOD_SECRET_COPYPARTY_SECRET }}`; its password. The browser stays off without both.
- `HF_HOME=/workspace/.cache/huggingface`: Hugging Face cache and metadata location.
- `MODEL_MODE=turbo`: which variant to download — `turbo`, `base` or `both`.
- `STUDIO_VERSION=1`: which generation this image serves, baked at build time from `versions/1/profile.json`.
- `PORT=8000`: gateway port for the Runpod Hub/Serverless listing. The Pod template does not expose it; Pod users reach ComfyUI directly on 8188.
- `PORT_HEALTH=8001`: readiness service for the Hub listing; `/ping` returns 503 until ComfyUI reports device information.
- `PUBLIC_KEY`: optional SSH key for diagnostics. When set, the container starts SSH on 2222; the template does not expose that port.

`RUNPOD_API_KEY` and `GITHUB_PACKAGES_PAT` are local deployment credentials only and must never reach the worker container.

## Build, validate and update

All container builds and runtime tests run in **GitHub Actions**, never on a local workstation. Pushing to `develop` or `main` builds, runs source and template-parity checks, verifies every packaged graph against a CPU-only ComfyUI, and publishes the image.

Paid GPU tests are opt-in through the `gpu_smoke` dispatch input. When set, Actions launches a disposable 48 GB Pod from that exact image digest, renders every packaged workflow at 512 × 512 (each variant generates first, then varies its own output), and checks dimensions, pixel variance, entropy and flatness, and that a variation genuinely differs from its source. Those checks catch blank, flat and passthrough output, not artistic quality.

`scripts/build-workflows.py` regenerates the packaged workflows, in API and UI form, from a single specification, so the two cannot drift; edit that rather than the JSON.

`scripts/test-runpod.py` also runs by hand: `--keep` leaves the Pod up, `--pod <id>` re-runs against a running Pod with randomised seeds, and `--cleanup` deletes it.

Confirm build and GPU status in Actions before treating a revision as tested; `docs/VALIDATION.md` holds the current record.

## Troubleshooting

- **Connect opens ComfyUI with HTTP 403:** ComfyUI's browser-origin guard rejects cross-site page navigations, and a link clicked from the Runpod dashboard counts as cross-site. This image patches the guard at build time to permit only a safe top-level `GET /` navigation. On a Pod built from an older digest, paste `https://<pod-id>-8188.proxy.runpod.net` into a blank tab instead.
- **ComfyUI does not become ready:** first boot downloads about 20.7 GB before ComfyUI starts. Check the Pod logs.
- **Out of GPU memory:** use a 48 GB card, or run `turbo` alone rather than `both`.

## Attribution

Model weights: [Tongyi-MAI/Z-Image-Turbo](https://huggingface.co/Tongyi-MAI/Z-Image-Turbo) and [Tongyi-MAI/Z-Image](https://huggingface.co/Tongyi-MAI/Z-Image), packaged for ComfyUI by [Comfy-Org](https://huggingface.co/Comfy-Org/Z-Image-Turbo). The advanced workflows are Comfy-Org's upstream templates. Check the model licence before commercial use.

## CPU thread sizing

CPU thread pools are sized automatically to the container CPU quota and available CPUs before PyTorch starts, avoiding host-sized pools that can throttle image scaling and export. Set `OMP_NUM_THREADS` and optionally `MKL_NUM_THREADS` to override; startup logs show the selected values. Actual speedup depends on the workload and has not been benchmarked for this revision.

## Editable render size

Set **Render Width** and **Render Height** on the canvas, or **Width** and **Height** in the main controls panel. These fields drive generation directly; resolution presets no longer override them. The added image-resize controls use a center crop to the selected dimensions; change the resize node’s crop setting if needed. Use dimensions supported by the model (multiples of 32 for LTX video, 16 for image workflows). LTX’s two-stage workflows retain their internal half-resolution first pass and upscale to the selected output size. Existing installed workflows and user edits are preserved; open a newly packaged workflow to get these controls.

### Workflow defaults

Seed controls default to randomize, including upstream controls and independent
first-pass/refinement seeds in nested panels. Random seeds use 15 digits where the
node range allows it. Use the native after-generate control, or the added seed mode
selector, to choose Fixed and enter a repeatable seed manually. These choices persist
when the workflow is saved. Model internals are folded into collapsed subgraphs and notes are
removed from packaged canvases. Inputs, editable controls and output previews remain
available. After editing or regenerating workflows, run
`python3 scripts/workflow_defaults.py` to reapply the canvas layout. These changes ship
with the next container image; existing pods need the updated image.
