# Z-Image bundle maintenance brief

Build the Runpod ComfyUI bundle for `acdevmedia/comfy-zimage`, publishing `ghcr.io/acdevmedia/zimage-comfyui:1` and immutable per-commit tags through GitHub Actions. Do not build Docker images locally; this workstation has neither the storage nor the CPU budget.

Z-Image runs on ComfyUI's **native** support: `supported_models.ZImage`, the `z_image` text encoder and `nodes_zimage.py`. No custom node and no Diffusers pipeline, which is what keeps this package simpler than the Ideogram one. Keep it that way.

Weights come from Comfy-Org's ComfyUI-split repositories, pinned by revision, size and SHA256. They are ungated, so `HF_TOKEN` is optional; do not reintroduce a hard token requirement.

Turbo is the default variant at eight steps and CFG 1.0; base is 25 steps at CFG 4.0. Both share the Qwen3-4B text encoder and the VAE, so `MODEL_MODE` filtering must keep shared components in every mode. Load the text encoder with `CLIPLoader` type `lumina2`: ComfyUI exposes no `z_image` type, and a Qwen3-4B encoder routes to the Z-Image encoder for any type that is not FLUX.

Every packaged workflow ships in both UI and API form so the GPU matrix can execute it. Text-to-image and image-to-image are both required for every variant.

Use source validation locally, image build plus CPU graph-schema checks in Actions, and real Runpod GPU generation before claiming runtime behaviour or output quality. `README.md` and `docs/VALIDATION.md` describe the current deployment state.
