# Runpod deployment

Use the repository [README](../README.md) for setup. Publish `ghcr.io/acdevmedia/zimage-comfyui:1` through GitHub Actions, then run `python3 scripts/create-runpod-template.py` to create or update the Z-Image template. Use `--dry-run` to review its payload. The script matches the single account template by recorded id, then by name; the Eros, Sulphur, FLUX and Ideogram templates are not touched.
