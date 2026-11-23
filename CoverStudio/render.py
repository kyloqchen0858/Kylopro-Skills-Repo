import base64
import mimetypes
from html import escape
from design import PLANE, LAYOUTS

def esc(v): return escape(str(v),quote=True)
def transform(o):
    return f"translate({o['x']} {o['y']}) rotate({o['angle']}) scale({o['w']/100} {o['h']/100}) translate(-50 -50)"

def _hex_rgb(color):
    s=str(color or '#000000').lstrip('#')
    if len(s)==3: s=''.join(c*2 for c in s)
    return int(s[0:2],16)/255.0, int(s[2:4],16)/255.0, int(s[4:6],16)/255.0

def _gradient_tables(stops, invert=False, samples=33):
    ordered=sorted(stops,key=lambda item:float(item['offset']))
    parsed=[(float(st['offset']),*_hex_rgb(st['color'])) for st in ordered]
    rs,gs,bs=[],[],[]
    for i in range(samples):
        t=i/(samples-1)
        if invert: t=1.0-t
        if t<=parsed[0][0]:
            _,r,g,b=parsed[0]
        elif t>=parsed[-1][0]:
            _,r,g,b=parsed[-1]
        else:
            r,g,b=parsed[-1][1:]
            for a,b_stop in zip(parsed,parsed[1:]):
                if a[0]<=t<=b_stop[0]:
                    span=max(b_stop[0]-a[0],1e-6)
                    u=(t-a[0])/span
                    r=a[1]+(b_stop[1]-a[1])*u
                    g=a[2]+(b_stop[2]-a[2])*u
                    b=a[3]+(b_stop[3]-a[3])*u
                    break
        rs.append(f'{r:.4f}'); gs.append(f'{g:.4f}'); bs.append(f'{b:.4f}')
    return ' '.join(rs), ' '.join(gs), ' '.join(bs)

def _text_markup(o, fill, extra=''):
    content=o.get('text','文字')
    em=sum(1 if ord(c)>255 else (.32 if c==' ' else .68) for c in content) or 1
    aspect=o['h']/o['w']
    size=min(88,98/(em*aspect))
    anchor='start' if o.get('align')=='left' else 'middle'
    offset=0 if anchor=='start' else 50
    style='italic' if o.get('italic') else 'normal'
    return (f'<text transform="translate({offset} 80) scale({aspect} 1)" text-anchor="{anchor}" '
            f'font-style="{style}" font-family="{esc(o.get("font","Georgia"))}" '
            f'font-size="{size}" fill="{esc(fill)}"{extra}>{esc(content)}</text>')

def render(s, directory, mode='art', embed=False):
    p=s['product']; w=p['width']+2*p['bleed']; h=p['height']+2*p['bleed']
    defs=[]; defined_ids=set(); groups=[]

    def define(id_key, value):
        if id_key not in defined_ids:
            defined_ids.add(id_key)
            defs.append(value)

    def asset_src(asset):
        src='assets/'+asset
        if embed:
            data=(directory/'assets'/asset).read_bytes()
            mime=mimetypes.guess_type(asset)[0] or 'image/png'
            src='data:'+mime+';base64,'+base64.b64encode(data).decode()
        return src

    def gradient_map_filter(o):
        gm=o.get('gradientMap')
        if not gm or not gm.get('enabled'):
            return ''
        stops=gm.get('stops') or [{'offset':0.0,'color':'#0b1638'},{'offset':0.52,'color':'#1d4ed8'},{'offset':1.0,'color':'#f7f9ff'}]
        rs,gs,bs=_gradient_tables(stops,bool(gm.get('invert',False)))
        strength=float(gm.get('strength',1.0))
        fid='gm-'+o['id']
        blend_step=''
        if strength<0.999:
            blend_step=f'<feComposite in="gmMap" in2="SourceGraphic" operator="arithmetic" k1="0" k2="{strength:.4f}" k3="{1.0-strength:.4f}" k4="0"/>'
        define(fid,
            f'<filter id="{fid}" color-interpolation-filters="sRGB">'
            '<feColorMatrix type="saturate" values="0" result="gmGray"/>'
            '<feComponentTransfer in="gmGray" result="gmMap">'
            f'<feFuncR type="table" tableValues="{rs}"/>'
            f'<feFuncG type="table" tableValues="{gs}"/>'
            f'<feFuncB type="table" tableValues="{bs}"/>'
            '</feComponentTransfer>'
            f'{blend_step}</filter>'
        )
        return f' filter="url(#{fid})"'

    def organic_filter(o, org, color=None):
        fid=('orgm-' if color else 'org-')+o['id']
        scale=float(org.get('scale',9.0))
        freq=float(org.get('frequency',0.055))
        octaves=int(org.get('octaves',4))
        seed=int(org.get('seed',17))
        inset=float(org.get('inset',2.5))
        feather=float(org.get('feather',0.15))
        erode_mm=min(min(o['w'],o['h'])*0.30, inset+scale*0.48)
        parts=[]
        if erode_mm>0.05:
            parts.append(f'<feGaussianBlur in="SourceAlpha" stdDeviation="{erode_mm:.3f}" result="orgErode"/>')
            parts.append('<feComponentTransfer in="orgErode" result="orgBase"><feFuncA type="linear" slope="24" intercept="-20.2"/></feComponentTransfer>')
            base_in='orgBase'
        else:
            base_in='SourceAlpha'
        parts.append(f'<feTurbulence type="fractalNoise" baseFrequency="{freq:.4f}" numOctaves="{octaves}" seed="{seed}" result="orgNoise"/>')
        parts.append(f'<feDisplacementMap in="{base_in}" in2="orgNoise" scale="{scale:.3f}" xChannelSelector="R" yChannelSelector="G" result="orgDisp"/>')
        parts.append('<feComponentTransfer in="orgDisp" result="orgSharp"><feFuncA type="linear" slope="10" intercept="-4.5"/></feComponentTransfer>')
        if feather>0.05:
            parts.append(f'<feGaussianBlur in="orgSharp" stdDeviation="{feather:.3f}" result="orgMask"/>')
            mask_in='orgMask'
        else:
            mask_in='orgSharp'
        parts.append(f'<feComposite in="SourceGraphic" in2="{mask_in}" operator="in" result="orgArt"/>')
        if org.get('rimEnabled') and not color:
            rim_w=float(org.get('rimWidth',0.55))
            rim_sigma=max(0.18,rim_w/0.85)
            rim_color=esc(org.get('rimColor','#d4af37'))
            rim_opacity=float(org.get('rimOpacity',0.92))
            parts.append(f'<feGaussianBlur in="orgSharp" stdDeviation="{rim_sigma:.3f}" result="rimBlur"/>')
            parts.append('<feComponentTransfer in="rimBlur" result="rimRing"><feFuncA type="table" tableValues="0 0 0 0.18 0.88 1 0.88 0.18 0 0 0"/></feComponentTransfer>')
            parts.append(f'<feFlood flood-color="{rim_color}" flood-opacity="{rim_opacity:.3f}" result="rimFlood"/>')
            parts.append('<feComposite in="rimFlood" in2="rimRing" operator="in" result="rimBase"/>')
            if org.get('rimShimmer',True):
                parts.append('<feColorMatrix in="orgNoise" type="matrix" values="0 0 0 0 1 0 0 0 0 0.96 0 0 0 0 0.78 0.8 0.8 0 0 -0.78" result="rimGlintRaw"/>')
                parts.append('<feComposite in="rimGlintRaw" in2="rimRing" operator="in" result="rimGlint"/>')
                parts.append('<feBlend in="rimBase" in2="rimGlint" mode="screen" result="rimStroke"/>')
                rim_final='rimStroke'
            else:
                rim_final='rimBase'
            parts.append(f'<feMerge><feMergeNode in="orgArt"/><feMergeNode in="{rim_final}"/></feMerge>')
        define(fid,
            f'<filter id="{fid}" x="-28%" y="-28%" width="156%" height="156%" color-interpolation-filters="sRGB">'
            +''.join(parts)+'</filter>'
        )
        return fid

    def shape(o,color=None):
        k=o['kind']; f=esc(color or o['fill'])
        if k=='image':
            asset=o.get('asset','')
            if not asset:return '<rect width="100" height="100" fill="#ddd"/>'
            if color and o['mask'].get('outline'):
                return f'<path fill="{f}" fill-rule="evenodd" d="{esc(o["mask"]["outline"])}"/>'
            src=asset_src(asset)
            if color:
                key='alpha'+o['id']
                define(key,f'<mask id="{key}" x="0" y="0" width="100" height="100" maskUnits="userSpaceOnUse"><image width="100" height="100" preserveAspectRatio="none" filter="url(#white)" xlink:href="{esc(src)}"/></mask>')
                return f'<rect width="100" height="100" fill="{f}" mask="url(#{key})"/>'
            tint=gradient_map_filter(o)
            if not tint and o.get('duotone')=='copper':
                key='copperMoon'
                define(key,'<filter id="copperMoon" color-interpolation-filters="sRGB"><feColorMatrix type="saturate" values="0"/><feComponentTransfer><feFuncR type="table" tableValues=".12 .42 .80 .98 1"/><feFuncG type="table" tableValues=".07 .13 .28 .58 .90"/><feFuncB type="table" tableValues=".13 .19 .22 .39 .74"/></feComponentTransfer></filter>')
                tint=f' filter="url(#{key})"'
            return f'<image{tint} width="100" height="100" preserveAspectRatio="none" xlink:href="{esc(src)}"/>'
        if k=='text':
            return _text_markup(o, color or o['fill'])
        if k=='linework':
            return f'<g transform="scale({100/o["unitWidth"]} {100/o["unitHeight"]})"><path d="{esc(o["path"])}" fill="none" stroke="{f}" stroke-width="{float(o["pen"])}" stroke-linecap="round" stroke-linejoin="round"/></g>'
        if k=='rect':return f'<rect width="100" height="100" fill="{f}"/>'
        if k=='ellipse':return f'<circle cx="50" cy="50" r="50" fill="{f}"/>'
        if k=='ring':return f'<circle cx="50" cy="50" r="49" fill="none" stroke="{f}" stroke-width=".7"/>'
        if k=='trail':return f'<path d="M0 100 C6 68 20 40 45 48 C86 66 61 98 46 76 C32 53 77 25 100 0" fill="none" stroke="{f}" stroke-width=".9" stroke-dasharray="2.4 2.5"/>'
        d=PLANE if k=='plane' else o.get('path','')
        body=f'<path d="{esc(d)}" fill="{f}" fill-rule="evenodd"/>'
        if k=='plane' and not color:
            body+='<path d="M34 60 L98 7 L47 65 L36 82 Z" fill="#9c321f"/><path d="M2 50 L98 7 L34 60 Z" fill="#ffb38c"/>'
        return body

    def layer(o,color=None, cut=True):
        key=o['id']; m=o['mask']; body=shape(o,color)
        if not color and o['kind']!='image' and o.get('gradientMap',{}).get('enabled'):
            body=f'<g{gradient_map_filter(o)}>{body}</g>'
        def wrap(content,attr,ref_id): return f'<g {attr}="url(#{ref_id})">{content}</g>'
        if m.get('strokes') or m.get('fade'):
            base='url(#fade)' if m.get('fade') else 'white'
            marks=[f'<rect width="100" height="100" fill="{base}"/>']
            for stroke in m.get('strokes',[]):
                pts=stroke['points']; color2='white' if stroke.get('restore') else 'black'
                size=float(stroke['size'])
                marks.append(f'<circle cx="{float(pts[0][0])}" cy="{float(pts[0][1])}" r="{size/2}" fill="{color2}"/>')
                pairs=' '.join(f'{float(x)},{float(y)}' for x,y in pts)
                marks.append(f'<polyline points="{pairs}" fill="none" stroke="{color2}" stroke-width="{size}" stroke-linecap="round" stroke-linejoin="round"/>')
            define('m'+key,f'<mask id="m{key}" maskUnits="userSpaceOnUse" x="0" y="0" width="100" height="100">{"".join(marks)}</mask>')
            body=wrap(body,'mask','m'+key)
        if m.get('outline') or m.get('crop'):
            if m.get('outline'):
                define('p'+key,f'<clipPath id="p{key}"><path d="{esc(m["outline"])}" clip-rule="evenodd"/></clipPath>')
                body=wrap(body,'clip-path','p'+key)
            if m.get('crop'):
                x,y,cw,ch=map(float,m['crop'])
                define('c'+key,f'<clipPath id="c{key}"><rect x="{x}" y="{y}" width="{cw}" height="{ch}"/></clipPath>')
                body=wrap(body,'clip-path','c'+key)
        body=f'<g transform="{transform(o)}">{body}</g>'
        org=m.get('organic')
        if org and org.get('enabled'):
            fid=organic_filter(o,org,color)
            body=f'<g filter="url(#{fid})">{body}</g>'
        if cut and m.get('cut'):
            ref=next(i for i in s['objects'] if i['id']==m['cut'])
            cutter=layer(ref,'black',False)
            define('k'+key,f'<mask id="k{key}" maskUnits="userSpaceOnUse" x="0" y="0" width="{w}" height="{h}"><rect width="{w}" height="{h}" fill="white"/>{cutter}</mask>')
            body=wrap(body,'mask','k'+key)
        return body

    # Collect active text/object knockout masks for underlying vector line avoidance
    knockouts=[]
    for idx,obj_item in enumerate(s['objects']):
        ko=obj_item.get('mask',{}).get('knockout')
        if ko and ko.get('enabled'):
            knockouts.append((idx,obj_item,ko))

    def knockout_mask_for(idx, o):
        if not knockouts or mode not in ('art','print','overlay','plate'):
            return ''
        applicable=[]
        for k_idx,ko_obj,ko_cfg in knockouts:
            if k_idx<=idx: continue
            scope=ko_cfg.get('scope','linework')
            if scope=='linework' and o['kind'] in ('linework','ring','trail'):
                applicable.append((ko_obj,ko_cfg))
            elif scope=='below' and idx>0 and not o.get('previewOnly') and o['id']!='ground' and o['kind']!='text':
                applicable.append((ko_obj,ko_cfg))
        if not applicable:
            return ''
        ko_id='ko-'+'-'.join(item[0]['id'] for item in applicable)
        if ko_id not in defined_ids:
            cutouts=[]
            for ko_obj,ko_cfg in applicable:
                pad=float(ko_cfg.get('pad',3.5))
                feather=float(ko_cfg.get('feather',2.2))
                filt=''
                if feather>0.05:
                    f_id='kof-'+ko_obj['id']
                    define(f_id,f'<filter id="{f_id}" x="-60%" y="-60%" width="220%" height="220%"><feGaussianBlur stdDeviation="{feather:.3f}"/></filter>')
                    filt=f' filter="url(#{f_id})"'
                if ko_obj['kind']=='text':
                    stroke_u=max(0.5,pad*200.0/max(ko_obj['h'],0.5))
                    txt=_text_markup(ko_obj,'black',f' stroke="black" stroke-width="{stroke_u:.2f}" stroke-linejoin="round" stroke-linecap="round"')
                    cutouts.append(f'<g{filt}><g transform="{transform(ko_obj)}">{txt}</g></g>')
                else:
                    cutouts.append(f'<g{filt}>{layer(ko_obj,"black",False)}</g>')
            define(ko_id,f'<mask id="{ko_id}" maskUnits="userSpaceOnUse" x="0" y="0" width="{w}" height="{h}"><rect width="{w}" height="{h}" fill="white"/>{"".join(cutouts)}</mask>')
        return ko_id

    for idx,o in enumerate(s['objects']):
        if mode=='print' and (o.get('foil') or o.get('deboss') or o.get('previewOnly')):continue
        if mode in ('foil','deboss') and not o.get(mode):continue
        if mode=='plate' and not o['uv']:continue
        if mode.startswith('mask:') and o['id']!=mode[5:]:continue
        if mode=='layout':
            if o['id'] not in ('subject','orbit','title','seal','foot'):continue
            color='#c5b6a1' if o['id']=='subject' else '#acbfc5'
            if o['kind']=='text': body=layer(o,'#31475a')
            else:
                proxy={**o,'kind':'rect' if o['kind'] not in ('ring','ellipse') else o['kind']}
                body=layer(proxy,color)
        else:
            body=layer(o,'black' if mode in ('plate','deboss','foil') or mode.startswith('mask:') else None)
            ko_id=knockout_mask_for(idx,o)
            if ko_id:
                body=f'<g mask="url(#{ko_id})">{body}</g>'
        style=''
        if mode in ('art','print','overlay'):
            style=f' opacity="{float(o.get("opacity",1))}" style="mix-blend-mode:{esc(o.get("blend","normal"))}"'
        groups.append(f'<g{style} id="o-{o["id"]}" data-object="{o["id"]}"><title>{esc(o["name"])}</title>{body}</g>')

    if mode=='layout':
        guides={
            '居中放射':'M80 10V210 M10 107H150 M23 50L137 164 M23 164L137 50',
            '螺旋聚焦':'M8 12 Q151 10 151 115 Q151 197 74 197 Q12 197 12 143 Q12 103 48 103 Q78 103 78 129 Q78 147 61 147',
            '对角线':'M9 193L151 28',
            '左右对置':'M78 14V207 M10 118H150',
            '上下分区':'M9 83H151 M9 177H151',
            '大留白':'M82 129H141V180H82Z'
        }
        groups.insert(0,f'<path d="{guides[s["layout"]]}" transform="scale({w/160} {h/222})" fill="none" stroke="#969e92" stroke-width=".45" stroke-dasharray="2 1.4"/>')
    if mode=='overlay':
        for idx,o in enumerate(s['objects']):
            if o['uv']:
                uv_body=layer(o,'#00bac5')
                ko_id=knockout_mask_for(idx,o)
                if ko_id: uv_body=f'<g mask="url(#{ko_id})">{uv_body}</g>'
                groups.append('<g opacity=".68">'+uv_body+'</g>')

    # Global top-level texture overlay (composited in live view & export ART/material-preview)
    tex=s.get('texture') or {}
    if mode in ('art','print','overlay') and tex.get('enabled') and float(tex.get('opacity',0))>0:
        t_kind=tex.get('kind','paper')
        t_blend=tex.get('blend','multiply')
        t_opacity=float(tex.get('opacity',0.16))
        t_scale=max(0.25,min(4.0,float(tex.get('scale',1.0))))
        t_contrast=max(0.3,min(2.5,float(tex.get('contrast',1.0))))
        if t_kind=='asset' and tex.get('asset'):
            src=asset_src(tex['asset'])
            tex_el=f'<image width="{w}" height="{h}" preserveAspectRatio="xMidYMid slice" xlink:href="{esc(src)}"/>'
        else:
            if t_kind=='grain':
                bf=f'{1.25/t_scale:.4f}'; octv=2
            elif t_kind=='fiber':
                bf=f'{0.12/t_scale:.4f} {0.72/t_scale:.4f}'; octv=3
            else:
                bf=f'{0.45/t_scale:.4f}'; octv=4
            if t_blend=='multiply':
                slope=0.75*t_contrast
                intercept=1.0-0.62*t_contrast
            else:
                slope=1.15*t_contrast
                intercept=0.5*(1.0-slope)
            define('globalTex',
                '<filter id="globalTex" x="0%" y="0%" width="100%" height="100%" color-interpolation-filters="sRGB">'
                f'<feTurbulence type="fractalNoise" baseFrequency="{bf}" numOctaves="{octv}" seed="73" result="gtNoise"/>'
                '<feColorMatrix in="gtNoise" type="matrix" values="0.333 0.333 0.333 0 0  0.333 0.333 0.333 0 0  0.333 0.333 0.333 0 0  0 0 0 0 1" result="gtMono"/>'
                '<feComponentTransfer in="gtMono">'
                f'<feFuncR type="linear" slope="{slope:.4f}" intercept="{intercept:.4f}"/>'
                f'<feFuncG type="linear" slope="{slope:.4f}" intercept="{intercept:.4f}"/>'
                f'<feFuncB type="linear" slope="{slope:.4f}" intercept="{intercept:.4f}"/>'
                '</feComponentTransfer></filter>'
            )
            tex_el=f'<rect width="{w}" height="{h}" fill="#808080" filter="url(#globalTex)"/>'
        groups.append(f'<g id="global-texture" data-global-texture="true" opacity="{t_opacity:.3f}" style="mix-blend-mode:{esc(t_blend)};pointer-events:none"><title>全局质感层</title>{tex_el}</g>')

    bg=f'<rect width="{w}" height="{h}" fill="white"/>' if mode=='layout' or mode.startswith('mask:') else ''
    return (f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="{w}mm" height="{h}mm" viewBox="0 0 {w} {h}">'
            '<defs><linearGradient id="fade" x2="0" y2="1" gradientUnits="objectBoundingBox"><stop stop-color="white"/><stop offset="1" stop-color="black"/></linearGradient><filter id="white"><feColorMatrix type="matrix" values="0 0 0 0 1 0 0 0 0 1 0 0 0 0 1 0 0 0 1 0"/></filter>'
            +''.join(defs)+'</defs>'+bg+''.join(groups)+'</svg>')
