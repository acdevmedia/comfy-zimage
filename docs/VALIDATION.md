# Validation status — Z-Image

## Not yet validated on a GPU

This package has had no GPU run. Source checks, template parity, pinned-weight metadata and
weight-reference checks pass, and every packaged API graph is schema-checked against a CPU-only
ComfyUI during the image build, which catches unknown node types and missing required inputs.

None of that establishes that the model renders well, or at all. Dispatch the build workflow with
`gpu_smoke=true`, or run `scripts/test-runpod.py --keep`, and record the result here before treating
a revision as tested.

## What the automated checks do and do not cover

Generation checks assert dimensions, pixel variance, entropy and flatness. They catch blank frames,
near-flat frames and image-to-image runs that return the source unchanged. They do not judge
composition, prompt adherence or artefacts: a corrupted render with heavy texture raises entropy and
passes. Inspect the uploaded PNGs.
