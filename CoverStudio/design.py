"""Editable cover objects use a 100 × 100 local coordinate system; layout uses mm."""
import math
import random
import re
import uuid

LAYOUTS = {
    '居中放射': (80, 108, 86, 80, 37, 80, 107),
    '螺旋聚焦': (59, 134, 77, 80, 38, 65, 125),
    '对角线': (96, 103, 85, 51, 41, 82, 118),
    '左右对置': (114, 125, 66, 47, 74, 110, 120),
    '上下分区': (80, 147, 79, 80, 49, 80, 142),
    '大留白': (107, 153, 48, 59, 56, 105, 151),
}
PRODUCT = dict(name='A5 前封', width=148, height=210, bleed=6)
PROCESS = dict(name='局部 UV', plate='UV GLOSSY', machine='', format='SVG')
NAVY, RED, PAPER = '#173453', '#eb5335', '#ffffff'
PLANE = 'M2 50 L98 7 L66 89 L47 65 L36 82 L34 60 Z'
STAR = 'M50 0 Q55 43 100 50 Q56 55 50 100 Q45 56 0 50 Q44 44 50 0 Z'
def uid():
    return uuid.uuid4().hex[:12]

def recommend(concept):
    rules=[('对角线','飞 翼 航行 出发 旅 追 愿望'),('居中放射','树 日轮 太阳 光芒 绽放'),
           ('螺旋聚焦','时间 年轮 漩涡 月潮'),('左右对置','双 对话 两 对比'),
           ('上下分区','天地 山海 地平线'),('大留白','静 呼吸 留白 极简')]
    ranked=sorted(rules,key=lambda r:-sum(word in concept for word in r[1].split()))
    return [r[0] for r in ranked[:3]]

def obj(key, name, kind, x, y, w, h, fill=NAVY, **more):
    return dict(id=key, name=name, kind=kind, x=x, y=y, w=w, h=h, angle=0,
                fill=fill, locks=[], mask={}, uv=False, **more)

def compose(concept, layout, product):
    x,y,size,tx,ty,ax,ay = LAYOUTS[layout]
    wish = '愿望' in concept
    main = obj('subject', '纸飞机' if wish else concept[:20]+' · 主体占位',
               'plane' if wish else 'ellipse', x,y,size,size*.76,RED)
    main['uv']=wish
    objects = [
        obj('ground','纸张底色','rect',80,111,160,222,PAPER),
        obj('orbit','航线 · 椭圆','ring',ax,ay,122,62,NAVY),
        obj('seal','目的地 · 星芒','path',129,83,11,11,RED,path=STAR),
        main,
        obj('title','封面标题','text',tx,ty,88,16,NAVY,text=concept,font='SimSun'),
        obj('subtitle','英文副题','text',tx,ty+13,69,4.4,NAVY,
            text='A BOOK OF WISHES' if wish else 'NOTEBOOK',font='Georgia'),
    ]
    objects[1]['angle']=-24
    if wish:
        objects.extend([
            obj('trace','飞行轨迹','trail',49,155,86,55,NAVY),
            obj('foot','封面题记','text',80,194,120,3.4,NAVY,text='把还没抵达的地方，先写在这里。',font='SimSun'),
            obj('rule','页脚横线','rect',80,200,126,.26,NAVY),
            obj('edition','页脚','text',80,205,105,2.6,NAVY,text='W I S H   P O S T     /     C O R R E S P O N D E N C E',font='Georgia')
        ])
    sx=(product['width']+2*product['bleed'])/160
    sy=(product['height']+2*product['bleed'])/222
    for o in objects:
        for k in ('x','w'): o[k]*=sx
        for k in ('y','h'): o[k]*=sy
    return objects

def initial(concept='愿望本', product=None):
    p={**PRODUCT, **(product or {})}
    choices=recommend(concept)
    return dict(schema=1,concept=concept,layout=choices[0],choices=choices,
                product=p,process=PROCESS.copy(),texture=TEXTURE_DEFAULT.copy(),
                objects=compose(concept,choices[0],p))

BLENDS=('normal','screen','multiply','overlay','soft-light','color-burn','darken','lighten')
TEXTURE_KINDS=('paper','grain','fiber','asset')
TEXTURE_BLENDS=('multiply','overlay','soft-light')
TEXTURE_DEFAULT=dict(enabled=False,kind='paper',blend='multiply',opacity=0.16,scale=1.0,contrast=1.0,asset='')
GRADIENT_MAP_DEFAULT=dict(
    enabled=False,
    stops=[
        dict(offset=0.0,color='#0b1638'),
        dict(offset=0.52,color='#1d4ed8'),
        dict(offset=1.0,color='#f7f9ff'),
    ],
    invert=False,
    strength=1.0,
)
ORGANIC_DEFAULT=dict(
    enabled=False,
    scale=9.0,
    frequency=0.055,
    octaves=4,
    seed=17,
    inset=2.5,
    feather=0.15,
    rimEnabled=False,
    rimColor='#d4af37',
    rimWidth=0.55,
    rimOpacity=0.92,
    rimShimmer=True,
)
KNOCKOUT_DEFAULT=dict(
    enabled=False,
    pad=3.5,
    feather=2.2,
    scope='linework',
)

GEOMETRY={'x','y','w','h','angle'}
CONTENT={'name','fill','text','font','italic','align','asset','source','kind','path','duotone','pen','unitWidth','unitHeight','blend','opacity','gradientMap'}
MASK={'mask','uv','deboss','foil','previewOnly'}
KINDS={'linework','rect','ellipse','ring','path','plane','trail','text','image'}
MASK_KEYS={'cut','fade','strokes','crop','outline','organic','knockout'}
HEX_RE=re.compile(r'^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$')

def _hex_color(value, label='颜色'):
    s=str(value or '').strip()
    if not HEX_RE.fullmatch(s):
        raise ValueError(f'{label}须为十六进制色值')
    if len(s)==4:
        s='#'+''.join(c*2 for c in s[1:])
    return s.lower()

def _finite(value, lo, hi, label):
    n=float(value)
    if not math.isfinite(n) or n<lo or n>hi:
        raise ValueError(f'{label}须为 {lo} 至 {hi}')
    return n

def validate_gradient_map(gm):
    if gm is None or gm=={}:
        return None
    if not isinstance(gm,dict) or set(gm)-{'enabled','stops','invert','strength'}:
        raise ValueError('渐变映射参数无效')
    out=dict(GRADIENT_MAP_DEFAULT)
    if 'enabled' in gm:
        if not isinstance(gm['enabled'],bool): raise ValueError('渐变映射开关须为布尔值')
        out['enabled']=gm['enabled']
    if 'invert' in gm:
        if not isinstance(gm['invert'],bool): raise ValueError('反转参数须为布尔值')
        out['invert']=gm['invert']
    if 'strength' in gm:
        out['strength']=_finite(gm['strength'],0.0,1.0,'渐变映射强度')
    if 'stops' in gm:
        stops=gm['stops']
        if not isinstance(stops,list) or not (2<=len(stops)<=5):
            raise ValueError('渐变映射需包含 2 至 5 个色标')
        cleaned=[]
        for st in stops:
            if not isinstance(st,dict) or set(st)-{'offset','color'}:
                raise ValueError('渐变色标格式无效')
            cleaned.append(dict(
                offset=_finite(st.get('offset',0),0.0,1.0,'色标位置'),
                color=_hex_color(st.get('color','#000000'),'色标颜色'),
            ))
        cleaned.sort(key=lambda item:item['offset'])
        out['stops']=cleaned
    return out

def validate_organic(org):
    if org is None or org=={}:
        return None
    allowed=set(ORGANIC_DEFAULT)
    if not isinstance(org,dict) or set(org)-allowed:
        raise ValueError('有机边缘参数无效')
    out=dict(ORGANIC_DEFAULT)
    for k in ('enabled','rimEnabled','rimShimmer'):
        if k in org:
            if not isinstance(org[k],bool): raise ValueError('有机边缘开关须为布尔值')
            out[k]=org[k]
    if 'scale' in org: out['scale']=_finite(org['scale'],0.0,40.0,'噪点位移幅度')
    if 'frequency' in org: out['frequency']=_finite(org['frequency'],0.005,0.3,'噪点频率')
    if 'octaves' in org:
        octv=int(org['octaves'])
        if not 1<=octv<=6: raise ValueError('噪点层数须为 1 至 6')
        out['octaves']=octv
    if 'seed' in org:
        seed=int(org['seed'])
        if not 0<=seed<=9999: raise ValueError('随机种子须为 0 至 9999')
        out['seed']=seed
    if 'inset' in org: out['inset']=_finite(org['inset'],0.0,30.0,'内缩边距')
    if 'feather' in org: out['feather']=_finite(org['feather'],0.0,5.0,'边缘羽化')
    if 'rimColor' in org: out['rimColor']=_hex_color(org['rimColor'],'描边颜色')
    if 'rimWidth' in org: out['rimWidth']=_finite(org['rimWidth'],0.1,4.0,'描边宽度')
    if 'rimOpacity' in org: out['rimOpacity']=_finite(org['rimOpacity'],0.0,1.0,'描边不透明度')
    return out

def validate_knockout(ko):
    if ko is None or ko=={}:
        return None
    if not isinstance(ko,dict) or set(ko)-{'enabled','pad','feather','scope'}:
        raise ValueError('文字避让参数无效')
    out=dict(KNOCKOUT_DEFAULT)
    if 'enabled' in ko:
        if not isinstance(ko['enabled'],bool): raise ValueError('文字避让开关须为布尔值')
        out['enabled']=ko['enabled']
    if 'pad' in ko: out['pad']=_finite(ko['pad'],0.0,25.0,'避让外扩')
    if 'feather' in ko: out['feather']=_finite(ko['feather'],0.0,15.0,'避让羽化')
    if 'scope' in ko:
        if ko['scope'] not in ('linework','below'): raise ValueError('避让范围须为 linework 或 below')
        out['scope']=ko['scope']
    return out

def validate_texture(tex, current=None):
    base=dict(TEXTURE_DEFAULT)
    if isinstance(current,dict): base.update(current)
    if not isinstance(tex,dict) or set(tex)-set(TEXTURE_DEFAULT):
        raise ValueError('全局质感参数无效')
    if 'enabled' in tex:
        if not isinstance(tex['enabled'],bool): raise ValueError('全局质感开关须为布尔值')
        base['enabled']=tex['enabled']
    if 'kind' in tex:
        if tex['kind'] not in TEXTURE_KINDS: raise ValueError('未知质感类型')
        base['kind']=tex['kind']
    if 'blend' in tex:
        if tex['blend'] not in TEXTURE_BLENDS: raise ValueError('未知质感混合模式')
        base['blend']=tex['blend']
    if 'opacity' in tex: base['opacity']=_finite(tex['opacity'],0.0,1.0,'质感不透明度')
    if 'scale' in tex: base['scale']=_finite(tex['scale'],0.25,4.0,'质感缩放')
    if 'contrast' in tex: base['contrast']=_finite(tex['contrast'],0.3,2.5,'质感对比度')
    if 'asset' in tex: base['asset']=str(tex['asset'] or '')
    return base

def apply(state, op):
    action=op['action']
    if action.startswith(('plan_','item_','stage_')):
        from proposals import edit_flow
        edit_flow(state,op)
        return state
    objects=state['objects']
    def get(key):
        for o in objects:
            if o['id']==key: return o
        raise ValueError('对象不存在')
    if action=='choices':
        state['choices']=recommend(state['concept']) if op.get('recommend') else op.get('choices',random.sample(list(LAYOUTS),3))
        if len(state['choices'])!=3 or any(k not in LAYOUTS for k in state['choices']): raise ValueError('请选择三个构图')
    elif action=='layout':
        if any('layout' in o['locks'] for o in objects): raise ValueError('请先解锁构图')
        target=compose(state['concept'],op['layout'],state['product'])
        for o in objects:
            other=next((t for t in target if t['id']==o['id']),None)
            if other:
                for k in GEOMETRY: o[k]=other[k]
        state['layout']=op['layout']
    elif action=='process':
        for k in ('plate','machine','name'):
            if k in op: state['process'][k]=str(op[k])[:100]
        if 'format' in op:
            if op['format'] not in ('SVG','AI','PDF'):raise ValueError('请选择 SVG、AI 或 PDF')
            state['process']['format']=op['format']
    elif action=='texture':
        raw=op.get('values',{k:v for k,v in op.items() if k!='action'})
        state['texture']=validate_texture(raw,state.get('texture'))
    elif action=='comment':
        message=str(op['message']).strip()
        if not message:raise ValueError('请输入设计意见')
        target=op.get('target','')
        name=get(target)['name'] if target else '整张封面'
        state.setdefault('discussion',[]).append(dict(id=uid(),message=message,target=target,targetName=name,
            refs=op.get('refs',[]),purpose=op.get('purpose','风格与材质'),status='待处理'))
    elif action=='withdraw':
        note=next((n for n in state.get('discussion',[]) if n['id']==op['note']),None)
        if not note or note['status']!='待处理':raise ValueError('只能撤回待处理意见')
        note['status']='已撤回'
    elif action=='reply':
        note=next((n for n in state.get('discussion',[]) if n['id']==op['note']),None)
        if not note or note.get('status')=='已撤回':raise ValueError('意见不存在或已撤回')
        note.update(reply=str(op['reply']),status=op.get('status','已处理'))
    elif action=='remove':
        o=get(op['id'])
        if o['locks']:raise ValueError('请先解锁对象再删除')
        for other in objects:
            if other['mask'].get('cut')==o['id'] and 'mask' in other['locks']:raise ValueError('该对象被已锁蒙版引用')
        for other in objects:
            if other['mask'].get('cut')==o['id']:other['mask'].pop('cut')
        objects.remove(o)
    elif action=='add':
        o=obj(uid(),op.get('name','新元素'),op.get('kind','rect'),80,111,32,32)
        objects.append(o)
        apply(state,dict(action='edit',id=o['id'],values=op.get('values',{})))
    else:
        o=get(op['id'])
        if action=='lock':
            locks=op['locks']
            if set(locks)-{'layout','asset','mask'}: raise ValueError('未知锁')
            o['locks']=locks
        elif action=='edit':
            values=op['values']
            if set(values)-(GEOMETRY|CONTENT|MASK): raise ValueError('不支持的属性')
            for lock, keys in [('layout',GEOMETRY),('asset',CONTENT),('mask',MASK)]:
                if lock in o['locks'] and keys.intersection(values): raise ValueError('对象已锁定 '+lock)
            for k in GEOMETRY.intersection(values):
                n=float(values[k])
                if not math.isfinite(n) or abs(n)>10000 or (k in ('w','h') and n<=0): raise ValueError('尺寸或位置无效')
                values[k]=n
            for field in ('unitWidth','unitHeight','pen'):
                if field in values:values[field]=_finite(values[field],0.001,100000,field)
            if 'opacity' in values:
                alpha=float(values['opacity'])
                if not 0<=alpha<=1:raise ValueError('不透明度须为 0 至 1')
                values['opacity']=alpha
            if 'blend' in values and values['blend'] not in BLENDS:raise ValueError('未知混合模式')
            if 'gradientMap' in values:
                gm=validate_gradient_map(values['gradientMap'])
                if gm is None:
                    values=dict(values); values.pop('gradientMap',None); o.pop('gradientMap',None)
                else:
                    values=dict(values,gradientMap=gm)
            if 'mask' in values:
                m=dict(values['mask']) if isinstance(values['mask'],dict) else values['mask']
                if not isinstance(m,dict) or set(m)-MASK_KEYS: raise ValueError('蒙版参数无效')
                if m.get('cut'):
                    ref=get(m['cut'])
                    if ref is o: raise ValueError('不能用自身遮挡自身')
                if 'crop' in m and not (len(m['crop'])==4 and all(0<=float(i)<=100 for i in m['crop'])): raise ValueError('裁切参数须为 0–100')
                if m.get('fade') not in (None,False,True): raise ValueError('渐变参数无效')
                for stroke in m.get('strokes',[]):
                    if not 0<float(stroke['size'])<=200 or len(stroke['points'])<1: raise ValueError('笔触无效')
                    if any(len(pt)!=2 or any(not math.isfinite(float(n)) for n in pt) for pt in stroke['points']): raise ValueError('笔触坐标无效')
                if 'organic' in m:
                    org=validate_organic(m['organic'])
                    if org is None: m.pop('organic',None)
                    else: m['organic']=org
                if 'knockout' in m:
                    ko=validate_knockout(m['knockout'])
                    if ko is None: m.pop('knockout',None)
                    else: m['knockout']=ko
                values=dict(values,mask=m)
            o.update(values)
            if o['kind'] not in KINDS: raise ValueError('未知元素类型')
        elif action=='order':
            if 'layout' in o['locks']: raise ValueError('构图已锁')
            i=objects.index(o); objects.pop(i); objects.insert(max(0,min(len(objects),i+int(op['by']))),o)
        elif action=='repeat':
            cx,cy=map(float,op['pivot']); step=float(op['degrees'])
            count=int(op['count'])
            if not 1<=count<=72: raise ValueError('复制数量为 1–72')
            import copy
            for i in range(1,count+1):
                rad=math.radians(i*step); dx=o['x']-cx; dy=o['y']-cy
                twin=copy.deepcopy(o)
                twin.update(id=uid(),name=o['name']+' '+str(i),x=cx+dx*math.cos(rad)-dy*math.sin(rad),
                            y=cy+dx*math.sin(rad)+dy*math.cos(rad),angle=o['angle']+i*step)
                objects.append(twin)
        else: raise ValueError('未知操作')
    return state

