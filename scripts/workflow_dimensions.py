"""Expose editable render dimensions without changing sampler or model settings."""
import json
import uuid
from pathlib import Path

LATENTS = {'EmptySD3LatentImage', 'EmptyFlux2LatentImage', 'EmptyLatentImage', 'EmptyLTXVLatentVideo'}
RESIZE = 'Resize reference to render width and height'
FITTED = 'Resize image to the fitted frame'

def link_parts(link):
    if isinstance(link, dict):
        return [link[k] for k in ('id','origin_id','origin_slot','target_id','target_slot','type')]
    return list(link[:6])

def remove_input_link(graph, node, slot):
    inp = node['inputs'][slot]
    lid = inp.get('link')
    if lid is None:
        return
    graph['links'] = [l for l in graph.get('links', []) if link_parts(l)[0] != lid]
    for source in graph.get('nodes', []):
        for output in source.get('outputs', []):
            if output.get('links'):
                output['links'] = [x for x in output['links'] if x != lid]
    for field in graph.get('inputs', []):
        if field.get('linkIds'):
            field['linkIds'] = [x for x in field['linkIds'] if x != lid]
    inp['link'] = None

def apply_dimensions(data, default=None):
    """Return whether this workflow supports visual sizing; operate idempotently."""
    # Native studio nodes already expose width/height from INPUT_TYPES.
    if any(n['type'] in ('AcdevFluxStudio','AcdevIdeogramStudio') for n in data['nodes']):
        return True
    # Existing controls panels: unlink preset selectors, making their widgets editable.
    exposed = {}
    panel_types = {g['id'] for g in data.get('definitions',{}).get('subgraphs',[])}
    for node in data['nodes']:
        if node['type'] not in panel_types:
            continue
        for slot, inp in enumerate(node.get('inputs', [])):
            label = (inp.get('label') or inp['name']).lower()
            for dim in ('width','height'):
                if dim in label and inp.get('widget'):
                    exposed[dim] = (node, slot)
    if len(exposed) == 2:
        for node, slot in exposed.values():
            remove_input_link(data, node, slot)
        # Preset-only selectors no longer drive the controls panel.
        data['nodes'] = [n for n in data['nodes'] if n['type'] != 'ResolutionSelector' or any(o.get('links') for o in n.get('outputs', []))]
        return True

    definitions = {g['id']: g for g in data.get('definitions',{}).get('subgraphs',[])}
    # Traverse instantiated subgraphs, avoiding unused definitions in upstream templates.
    contexts = []
    def walk(graph, parents):
        contexts.append((graph, parents))
        for node in graph['nodes']:
            if node['type'] in definitions:
                walk(definitions[node['type']], parents+[(graph,node)])
    walk(data, [])
    targets = []
    for graph, parents in contexts:
        for node in graph['nodes']:
            if node['type'] in LATENTS:
                for index, dim in enumerate(('width','height')):
                    inputs = node.setdefault('inputs', [])
                    slot = next((i for i,x in enumerate(inputs) if x['name'] == dim), None)
                    if slot is None:
                        slot = len(inputs); inputs.append({'name':dim,'type':'INT','widget':{'name':dim},'link':None})
                    targets.append((graph,parents,node,slot,dim))
            elif node['type'] == 'ImageScaleToTotalPixels' or (node['type']=='ResizeImageMaskNode' and default==(768,448)):
                # Explicit dimensions replace automatic megapixel sizing for image edits.
                node['type'] = 'ImageScale'
                node.setdefault('properties',{})['Node name for S&R'] = 'ImageScale'
                node['title'] = RESIZE
                node['inputs'] = [x for x in node.get('inputs',[]) if x['name'] in ('image','input')]
                node['inputs'][0]['name']='image'
                method = 'lanczos'
                size = default or (1280,720)
                node['widgets_values'] = [method,size[0],size[1],'center']
                node.pop('widgets_values_named',None)
                for dim in ('width','height'):
                    slot=len(node['inputs']);node['inputs'].append({'name':dim,'type':'INT','widget':{'name':dim},'link':None})
                    targets.append((graph,parents,node,slot,dim))
            elif node['type']=='ImageScale' and node.get('title')==RESIZE:
                for slot, inp in enumerate(node['inputs']):
                    if inp['name'] in ('width','height'):targets.append((graph,parents,node,slot,inp['name']))
    if not targets:
        return False
    if default is None:
        latent = next((n for _,_,n,_,_ in targets if n['type'] in LATENTS), None)
        default = tuple(latent['widgets_values'][:2]) if latent else (1280,720)
    max_node=max(n['id'] for graph,_ in contexts for n in graph['nodes'])
    max_link=max([link_parts(l)[0] for graph,_ in contexts for l in graph.get('links',[])]+[0])
    controls={}
    for index,dim in enumerate(('width','height')):
        control=next((n for n in data['nodes'] if n.get('title')=='Render '+dim.title() and n['type']=='PrimitiveInt'),None)
        if control is None:
            max_node+=1
            control={'id':max_node,'type':'PrimitiveInt','title':'Render '+dim.title(),'pos':[-400,index*150],'size':[300,110],'flags':{},'order':0,'mode':0,
                     'inputs':[],'outputs':[{'name':'INT','type':'INT','links':[]}], 'properties':{'Node name for S&R':'PrimitiveInt'},'widgets_values':[default[index],'fixed']}
            data['nodes'].append(control)
        controls[dim]=control
    def connect(graph,node,slot,origin,origin_slot):
        nonlocal max_link
        old = node['inputs'][slot].get('link')
        if old is not None:
            parts = next(link_parts(l) for l in graph['links'] if link_parts(l)[0] == old)
            if parts[1:3] == [origin,origin_slot]:return
        remove_input_link(graph,node,slot)
        max_link+=1;lid=max_link
        values=[lid,origin,origin_slot,node['id'],slot,'INT']
        if graph is data and (not graph.get('links') or not isinstance(graph['links'][0],dict)):
            graph.setdefault('links',[]).append(values)
        else:
            graph.setdefault('links',[]).append(dict(zip(('id','origin_id','origin_slot','target_id','target_slot','type'),values)))
        node['inputs'][slot]['link']=lid
        if origin==-10:
            graph['inputs'][origin_slot]['linkIds'].append(lid)
        else:
            source=next(n for n in graph['nodes'] if n['id']==origin)
            out=source['outputs'][origin_slot];out['links']=(out.get('links') or [])+[lid]
        graph.setdefault('state',{})['lastLinkId']=lid
    boundary={}
    def route(graph,parents,node,slot,dim):
        if graph is data:
            connect(graph,node,slot,controls[dim]['id'],0);return
        key=(graph['id'],dim)
        if key not in boundary:
            name='render_'+dim
            inputs=graph.setdefault('inputs',[])
            idx=next((i for i,x in enumerate(inputs) if x['name']==name),None)
            if idx is None:
                idx=len(inputs);inputs.append({'id':str(uuid.uuid5(uuid.NAMESPACE_URL,graph['id']+'/'+name)), 'name':name,'label':'Render '+dim.title(),'type':'INT','linkIds':[],'pos':[0,20*idx]})
            boundary[key]=idx
        idx=boundary[key]
        connect(graph,node,slot,-10,idx)
        parent,instance=parents[-1]
        ins=instance.setdefault('inputs',[])
        instance_slot=next((i for i,x in enumerate(ins) if x['name']=='render_'+dim),None)
        if instance_slot is None:
            instance_slot=len(ins);ins.append({'name':'render_'+dim,'label':'Render '+dim.title(),'type':'INT','link':None})
            instance['size'][1]=max(instance['size'][1],120+30*len(ins))
        # Only route once per instance, even when it drives several internal nodes.
        if ins[instance_slot].get('link') is None:
            route(parent,parents[:-1],instance,instance_slot,dim)
    for graph,parents,node,slot,dim in targets:
        route(graph,parents,node,slot,dim)
    # Keep an established controls panel compact when its widget ordering is explicit.
    control_ids={c['id'] for c in controls.values()}
    dimension_links=[link_parts(l) for l in data['links'] if link_parts(l)[1] in control_ids]
    destinations={l[3] for l in dimension_links}
    if len(destinations)==1:
        panel=next(n for n in data['nodes'] if n['id'] in destinations)
        widgets=[i for i in panel.get('inputs',[]) if i.get('widget')]
        values=panel.get('widgets_values',[])
        if panel['type'] in definitions and len(values)==len(widgets):
            for dim in ('width','height'):
                slot=next(i for i,x in enumerate(panel['inputs']) if x['name']=='render_'+dim)
                remove_input_link(data,panel,slot)
                inp=panel['inputs'][slot];inp['widget']={'name':inp['name']}
                values.append(controls[dim]['widgets_values'][0])
                panel.setdefault('widgets_values_named',{})[inp['name']]=values[-1]
            data['nodes']=[n for n in data['nodes'] if n['id'] not in control_ids]
    data['last_node_id']=max_node;data['last_link_id']=max_link
    data.setdefault('state',{})['lastNodeId']=max_node
    return True

def sync_api(api, ui):
    """Keep flat API fixtures aligned with the UI dimensions used by GPU tests."""
    for node in ui['nodes']:
        nid=str(node['id'])
        if node['type']=='PrimitiveInt' and node.get('title','').startswith('Render '):
            api[nid]={'class_type':'PrimitiveInt','inputs':{'value':node['widgets_values'][0]}}
        elif nid in api:
            if node['type']=='ImageScale' and api[nid]['class_type']=='ImageScaleToTotalPixels':
                old=api[nid]['inputs'];api[nid]={'class_type':'ImageScale','inputs':{'image':old['image'],'upscale_method':old['upscale_method'],'crop':'center'}}
            for inp in node.get('inputs',[]):
                if inp['name'] in ('width','height') and inp.get('link') is not None:
                    link=next(link_parts(l) for l in ui['links'] if link_parts(l)[0]==inp['link'])
                    api[nid]['inputs'][inp['name']]=[str(link[1]),link[2]]

def fit_expression(mine, other, step):
    """One side of a frame with area a*b and the proportions of a c x d image, on the model's grid."""
    return 'max(64,round(sqrt(a*b*%s/%s)/%d)*%d)'%(mine,other,step,step)

def fit_frame_to_image(api, ui, step):
    """Size the first image's resize from the image itself, so no part of it is cropped away.

    Render Width and Height set the frame's area and the upload sets its proportions: a head-to-toe
    portrait stays head to toe, and a typed size that already matches the image comes back unchanged.
    """
    scale = next((n for n in ui['nodes'] if n['type'] == 'ImageScale' and n.get('title') == RESIZE), None)
    if scale is None:
        return False
    slots = {inp['name']: slot for slot, inp in enumerate(scale['inputs'])}
    def origin(name):
        return next(link_parts(l)[1] for l in ui['links'] if link_parts(l)[0] == scale['inputs'][slots[name]]['link'])
    image, width, height = origin('image'), origin('width'), origin('height')
    for name in ('width', 'height'):
        remove_input_link(ui, scale, slots[name])
    size, fit_w, fit_h = (ui['last_node_id'] + offset for offset in (1, 2, 3))
    next_link = ui['last_link_id']
    def connect(source, source_slot, target, target_slot, kind):
        nonlocal next_link
        next_link += 1
        ui['links'].append([next_link, source['id'], source_slot, target['id'], target_slot, kind])
        output = source['outputs'][source_slot]
        output['links'] = (output.get('links') or []) + [next_link]
        target['inputs'][target_slot]['link'] = next_link
    x, y = scale['pos']
    getter = {'id': size, 'type': 'GetImageSize', 'pos': [x - 340, y + 330], 'size': [320, 120], 'flags': {}, 'order': 0, 'mode': 0,
              'inputs': [{'name': 'image', 'type': 'IMAGE', 'link': None}],
              'outputs': [{'name': name, 'type': 'INT', 'links': None, 'slot_index': i} for i, name in enumerate(('width', 'height', 'batch_size'))],
              'title': 'Size of your image', 'properties': {'Node name for S&R': 'GetImageSize'}, 'widgets_values': []}
    def fit(node_id, title, expression, row):
        return {'id': node_id, 'type': 'ComfyMathExpression', 'pos': [x, y + 330 + row * 200], 'size': [320, 180], 'flags': {}, 'order': 0, 'mode': 0,
                'inputs': [{'name': 'expression', 'type': 'STRING', 'link': None, 'widget': {'name': 'expression'}}] +
                          [{'name': 'values.' + letter, 'type': 'FLOAT,INT,BOOLEAN', 'link': None} for letter in 'abcd'],
                'outputs': [{'name': 'FLOAT', 'type': 'FLOAT', 'links': None, 'slot_index': 0}, {'name': 'INT', 'type': 'INT', 'links': None, 'slot_index': 1},
                            {'name': 'BOOL', 'type': 'BOOLEAN', 'links': None, 'slot_index': 2}],
                'title': title, 'properties': {'Node name for S&R': 'ComfyMathExpression'}, 'widgets_values': [expression]}
    width_node = fit(fit_w, 'Fit Frame Width', fit_expression('c', 'd', step), 0)
    height_node = fit(fit_h, 'Fit Frame Height', fit_expression('d', 'c', step), 1)
    ui['nodes'] += [getter, width_node, height_node]
    nodes = {n['id']: n for n in ui['nodes']}
    connect(nodes[image], 0, getter, 0, 'IMAGE')
    for node in (width_node, height_node):
        connect(nodes[width], 0, node, 1, 'INT')
        connect(nodes[height], 0, node, 2, 'INT')
        connect(getter, 0, node, 3, 'INT')
        connect(getter, 1, node, 4, 'INT')
    connect(width_node, 1, scale, slots['width'], 'INT')
    connect(height_node, 1, scale, slots['height'], 'INT')
    scale['title'] = FITTED
    scale['widgets_values'][3] = 'disabled'
    ui['last_node_id'], ui['last_link_id'] = fit_h, next_link
    api[str(size)] = {'class_type': 'GetImageSize', 'inputs': {'image': [str(image), 0]}}
    for node_id, expression in ((fit_w, width_node), (fit_h, height_node)):
        api[str(node_id)] = {'class_type': 'ComfyMathExpression', 'inputs': {
            'expression': expression['widgets_values'][0], 'values.a': [str(width), 0], 'values.b': [str(height), 0],
            'values.c': [str(size), 0], 'values.d': [str(size), 1]}}
    api[str(scale['id'])]['inputs'].update(width=[str(fit_w), 1], height=[str(fit_h), 1], crop='disabled')
    return True

def main():
    root=Path(__file__).resolve().parents[1]
    for path in sorted(root.glob('versions/*/workflows/*.json')):
        if path.name.startswith('LTX25_'):continue
        data=json.loads(path.read_text())
        defaults=(768,448) if 'Ingredients' in path.name else None
        if apply_dimensions(data,defaults):
            text=json.dumps(data,indent=2,ensure_ascii=False)+'\n'
            if json.loads(path.read_text())!=data:path.write_text(text)
            api_path=path.parent.parent/'api'/path.name
            if api_path.exists():
                api=json.loads(api_path.read_text());sync_api(api,data)
                api_path.write_text(json.dumps(api,indent=2,ensure_ascii=False)+'\n')

if __name__=='__main__':main()
