"""Build matching ComfyUI API and UI graphs from one node specification.

The API form is what the GPU test matrix executes. The UI form is what a user opens in the
sidebar. Generating both from one spec keeps them from drifting, and the slot types below are the
real ones, so the frontend sees the same links it would have serialised itself.
"""
import json

# class_type -> ([(input_name, type), ...] link inputs in definition order, [output types])
SLOTS = {
    'UNETLoader': ([], ['MODEL']),
    'CLIPLoader': ([], ['CLIP']),
    'VAELoader': ([], ['VAE']),
    'LoraLoaderModelOnly': ([('model', 'MODEL')], ['MODEL']),
    'ModelSamplingAuraFlow': ([('model', 'MODEL')], ['MODEL']),
    'CFGNorm': ([('model', 'MODEL')], ['MODEL']),
    'LoadImage': ([], ['IMAGE', 'MASK']),
    'ImageScaleToTotalPixels': ([('image', 'IMAGE')], ['IMAGE']),
    'TextEncodeQwenImageEditPlus': (
        [('clip', 'CLIP'), ('vae', 'VAE'), ('image1', 'IMAGE'), ('image2', 'IMAGE'), ('image3', 'IMAGE')],
        ['CONDITIONING']),
    'CLIPTextEncode': ([('clip', 'CLIP')], ['CONDITIONING']),
    'EmptySD3LatentImage': ([], ['LATENT']),
    'VAEEncode': ([('pixels', 'IMAGE'), ('vae', 'VAE')], ['LATENT']),
    'KSampler': ([('model', 'MODEL'), ('positive', 'CONDITIONING'), ('negative', 'CONDITIONING'),
                  ('latent_image', 'LATENT')], ['LATENT']),
    'VAEDecode': ([('samples', 'LATENT'), ('vae', 'VAE')], ['IMAGE']),
    'SaveImage': ([('images', 'IMAGE')], []),
}


def is_link(value):
    return isinstance(value, list) and len(value) == 2 and isinstance(value[0], str)


def build(spec):
    """spec: list of (node_id, class_type, api_inputs, widget_values, (x, y)).

    Returns (api_graph, ui_graph).
    """
    ids = [s[0] for s in spec]
    assert len(ids) == len(set(ids)), 'duplicate node ids'
    api = {nid: {'class_type': cls, 'inputs': ins} for nid, cls, ins, _w, _p in spec}

    links, link_id = [], 0
    consumers = {}                       # (source node, slot) -> [link ids]
    ui_inputs = {nid: [] for nid in ids}
    for nid, cls, ins, _w, _p in spec:
        declared, _outs = SLOTS[cls]
        for name, typ in declared:
            val = ins.get(name)
            if not is_link(val):
                continue
            src, slot = val
            assert src in ui_inputs, (cls, name, 'links to unknown node', src)
            link_id += 1
            ui_inputs[nid].append({'name': name, 'type': typ, 'link': link_id})
            consumers.setdefault((src, slot), []).append(link_id)
            links.append([link_id, int(src), slot, int(nid), len(ui_inputs[nid]) - 1, typ])
        for name, val in ins.items():
            if is_link(val) and name not in {n for n, _t in declared}:
                raise AssertionError('%s.%s is linked but has no declared slot type' % (cls, name))

    nodes = []
    for order, (nid, cls, _ins, widgets, pos) in enumerate(spec):
        _declared, outs = SLOTS[cls]
        nodes.append({
            'id': int(nid), 'type': cls, 'pos': list(pos), 'size': [320, 120], 'flags': {},
            'order': order, 'mode': 0, 'inputs': ui_inputs[nid],
            'outputs': [{'name': t, 'type': t, 'links': consumers.get((nid, i), []) or None, 'slot_index': i}
                        for i, t in enumerate(outs)],
            'properties': {'Node name for S&R': cls}, 'widgets_values': widgets,
        })
    ui = {'last_node_id': max(int(i) for i in ids), 'last_link_id': link_id, 'nodes': nodes,
          'links': links, 'groups': [], 'config': {}, 'extra': {}, 'version': 0.4}
    return api, ui


def check(api, ui):
    """Structural integrity: unique ids, no dangling links, slots in range, inputs wired back."""
    by_id = {n['id']: n for n in ui['nodes']}
    assert len(by_id) == len(ui['nodes']), 'duplicate node ids'
    seen = set()
    for lid, src, sslot, dst, dslot, typ in ui['links']:
        assert lid not in seen, ('duplicate link id', lid)
        seen.add(lid)
        assert src in by_id and dst in by_id, ('dangling link', lid)
        assert sslot < len(by_id[src]['outputs']), ('source slot out of range', lid)
        assert by_id[src]['outputs'][sslot]['type'] == typ, ('source type mismatch', lid)
        dest = by_id[dst]['inputs']
        assert dslot < len(dest) and dest[dslot]['link'] == lid and dest[dslot]['type'] == typ, \
            ('destination not wired back', lid)
    api_links = sum(1 for n in api.values() for v in n['inputs'].values() if is_link(v))
    assert api_links == len(ui['links']), ('API and UI graphs disagree on link count', api_links, len(ui['links']))
    assert any(n['class_type'] == 'SaveImage' for n in api.values()), 'no SaveImage'
    return True


def dump(path, obj):
    path.write_text(json.dumps(obj, indent=2) + '\n')
