"""Regenerate the packaged Z-Image workflows (API and UI forms) from one spec."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import workflow_graph as g
from workflow_dimensions import apply_dimensions, fit_frame_to_image, sync_api

ROOT = Path(__file__).resolve().parents[1]
CLIP = 'qwen_3_4b.safetensors'
VAE = 'ae.safetensors'
# Turbo is the distilled 8-step model at CFG 1.0; base is the 25-step model at CFG 4.0. Both follow
# the upstream templates: res_multistep with the simple schedule and an AuraFlow shift of 3.
VARIANTS = {
    'TURBO': dict(unet='z_image_turbo_bf16.safetensors', steps=8, cfg=1.0, prefix='ZImage/turbo'),
    'BASE': dict(unet='z_image_bf16.safetensors', steps=25, cfg=4.0, prefix='ZImage/base'),
}
PROMPT = ('A cinematic wide shot of a lighthouse on a rocky headland at dusk, long exposure sea, '
          'low cloud catching the last light, muted teal and amber palette.')
EDIT_PROMPT = 'Reframe the same scene at golden hour with warm low sun and calmer water.'
NEG = 'blurry, low resolution, jpeg artifacts, watermark, signature, text overlay, deformed, extra limbs'


def spec(variant, img2img):
    v = VARIANTS[variant]
    prompt = EDIT_PROMPT if img2img else PROMPT
    s = [('1', 'UNETLoader', {'unet_name': v['unet'], 'weight_dtype': 'default'}, [v['unet'], 'default'], (40, 40)),
         ('2', 'ModelSamplingAuraFlow', {'model': ['1', 0], 'shift': 3.0}, [3.0], (380, 40)),
         ('3', 'CLIPLoader', {'clip_name': CLIP, 'type': 'lumina2', 'device': 'default'},
          [CLIP, 'lumina2', 'default'], (40, 180)),
         ('4', 'VAELoader', {'vae_name': VAE}, [VAE], (40, 320)),
         ('5', 'CLIPTextEncode', {'clip': ['3', 0], 'text': prompt}, [prompt], (380, 180)),
         ('6', 'CLIPTextEncode', {'clip': ['3', 0], 'text': NEG}, [NEG], (380, 340))]
    if img2img:
        # Scale the source first: an unbounded upload would otherwise encode a latent of any size.
        s += [('7', 'LoadImage', {'image': 'upload_your_image.png'}, ['upload_your_image.png', 'image'], (40, 480)),
              ('8', 'ImageScaleToTotalPixels',
               {'image': ['7', 0], 'upscale_method': 'lanczos', 'megapixels': 1.0, 'resolution_steps': 16},
               ['lanczos', 1.0], (380, 480)),
              ('9', 'VAEEncode', {'pixels': ['8', 0], 'vae': ['4', 0]}, [], (720, 480))]
        denoise = 0.6
    else:
        s += [('9', 'EmptySD3LatentImage', {'width': 1280, 'height': 720, 'batch_size': 1}, [1280, 720, 1], (720, 480))]
        denoise = 1.0
    s += [('10', 'KSampler', {'model': ['2', 0], 'positive': ['5', 0], 'negative': ['6', 0],
                              'latent_image': ['9', 0], 'seed': 0, 'steps': v['steps'], 'cfg': v['cfg'],
                              'sampler_name': 'res_multistep', 'scheduler': 'simple', 'denoise': denoise},
           [0, 'randomize', v['steps'], v['cfg'], 'res_multistep', 'simple', denoise], (1060, 180)),
          ('11', 'VAEDecode', {'samples': ['10', 0], 'vae': ['4', 0]}, [], (1400, 180)),
          ('12', 'SaveImage', {'images': ['11', 0], 'filename_prefix': v['prefix']}, [v['prefix']], (1560, 180))]
    return s


def main():
    plan = [('01', 'TURBO', False, 'Text_to_Image'), ('02', 'TURBO', True, 'Image_to_Image'),
            ('03', 'BASE', False, 'Text_to_Image'), ('04', 'BASE', True, 'Image_to_Image')]
    for num, variant, img2img, label in plan:
        api, ui = g.build(spec(variant, img2img))
        apply_dimensions(ui)
        sync_api(api,ui)
        fit_frame_to_image(api, ui, 16)
        g.check(api, ui)
        name = '%s_%s_%s.json' % (num, variant, label)
        g.dump(ROOT / 'versions/1/api' / name, api)
        g.dump(ROOT / 'versions/1/workflows' / name, ui)
        print('built', name, '(%d nodes, %d links)' % (len(api), len(ui['links'])))


if __name__ == '__main__':
    main()
