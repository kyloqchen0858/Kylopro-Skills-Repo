"""Brand-stage records and annotated full-jacket composition studies (not generated art)."""
from copy import deepcopy
from html import escape
from math import sin
from design import uid
from inventory import item, wish_items, STATUS

STAGES=['封面设计','封面工艺与用纸','内页设计','内页工艺与用纸']
OPTIONS=[
 dict(id='echo',title='回声地形',motif='散点 → 等高线 → 未闭合的轮廓',intent='把一年里的零散记录看成测绘点。靠近时，它们逐渐连成一片能辨认的地形；轮廓留一道开口，给改变主意留位置。',
 elements='稀疏坐标点、同源的三组等高线、一块冷白遮片。书名落在遮片上，少量细线从字的两侧重新出现。',
 front='远看先读 Becoming；近看轮廓在遮片下断开再接续。最内圈偏离中心，留下尚未形成的部分。',
 spine='水平基准线越过书脊。书名纵排，待实测脊宽后决定是否保留文字。',
 back='轮廓逐渐拆成散点。品牌题记 Creating memories for my future self. 与毛利谚语分层排，留足呼吸空间。',
 craft='建议打两种纸样：只印墨线、同一条外轮廓套压凹。先比较细线与折位，再定工艺。'),
 dict(id='archive',title='未来的档案',motif='记录碎片 → 半透明叠页 → 回望索引',intent='从未来翻阅今天留下的东西。用三张错位的档案页容纳不同时间的记录，最上层始终留一块空白。',
 elements='手稿局部、照片的取景边、透明描图页和一条贯穿书脊的索引线。素材只露出局部，叠页遮住标题的一小段边缘。',
 front='三个错位的矩形把视线推向右上。书名与最上层纸页共用左边线，过去的痕迹从下层露出。',
 spine='按三个纸页的高度分段，接封底的索引线。窄脊时仅保留 INKA+。',
 back='把前封的片段排成可回看的索引，在索引下排英文谚语。阅读动作从前封的重叠转为封底的展开。',
 craft='候选为哑面纸配合一处透明亮层。纸页的透明感先用印色模拟，再用实物比较局部光泽。'),
 dict(id='orbit',title='回望之弧',motif='偏心圆 → 裁切视窗 → 两条交错时间线',intent='沿着一条弧走向未知，转身时才看见走过的轨迹。放大的圆越过裁切边，小圆回到过去的交点。',
 elements='偏心大弧、放射刻线、一个清晰的视窗。弧在视窗前出现、在书名后消失，形成前后两层时间。',
 front='主圆刻意越过右边缘，小圆落在左下。标题卡在两条弧的相切处，由尺度和遮挡建立主次。',
 spine='一条不间断的弧线横跨书脊；文字独立成层，为窄脊准备无字方案。',
 back='将轨迹收束为一枚小圆，旁排谚语，开本时才看见它与前封大圆的对应。',
 craft='以珠光白烫色配一条压凹弧作候选。银灰屏幕线仅标示位置，实物的反光、深度需要打样。')]
def workflow(name,brief='',wish=False):
    return dict(name=name,brief=brief,items=wish_items() if wish else [item('brief','产品范围与交付拆解','产品拆解','产品理念、组件、工艺与依赖清单',status='进行中')],visual=('一年里，愿望会从模糊的感受逐渐形成，也可以改写。远看以轮廓和书名字阶建立秩序，近看从遮挡、反复出现的线和纸面反光里发现变化。外封展开时，封底的记录回应前封尚未闭合的愿景。' if wish else ''),routes=deepcopy(OPTIONS) if wish else [],choice=None,approved=False,feedback=[],paper={},stageNotes={},spine=None)
def edit_flow(state,op):
    f=state['workflow'];a=op['action']
    if a=='item_add':
        name=op['name'].strip();output=op['output'].strip()
        if not name or not output:raise ValueError('请填写名称和交付物')
        deps=op.get('depends',[])
        if set(deps)-{i['id'] for i in f['items']}:raise ValueError('依赖项目不存在')
        f['items'].append(item(uid(),name,op['stage'],output,' '.join(deps)))
    elif a=='item_update':
        target=next((i for i in f['items'] if i['id']==op['id']),None)
        if not target or op['status'] not in STATUS:raise ValueError('无效的项目或进度')
        if op['status']=='已完成' and not op['evidence'].strip():raise ValueError('完成时请记录验收依据')
        target.update(status=op['status'],next=op['next'],evidence=op['evidence'])
    elif a=='plan_edit':
        if 'visual' in op:f['visual']=str(op['visual'])
        if 'brief' in op:f['brief']=str(op['brief'])
        if 'routes' in op:
            routes=op['routes']
            required=set(OPTIONS[0])
            if not isinstance(routes,list) or any(not required.issubset(r) for r in routes):raise ValueError('版式方案缺少设计说明')
            if len({r['id'] for r in routes})!=len(routes):raise ValueError('方案编号重复')
            f['routes']=routes;f['choice']=None
        f['approved']=False
    elif a=='plan_note':
        note=str(op['message']).strip()
        if not note:raise ValueError('请输入修改意见')
        f['feedback'].append(dict(route=op.get('route'),message=note));f['approved']=False
    elif a in ('plan_choose','plan_approve'):
        route=next((r for r in f['routes'] if r['id']==op.get('route')),None)
        if not route:raise ValueError('请选择有效方案')
        if a=='plan_approve' and (not f['visual'].strip() or f['choice']!=route['id']):raise ValueError('请先选定有视觉稿的方案')
        f['choice']=route['id'];f['approved']=a=='plan_approve'
    elif a=='stage_note':
        stage=op['stage']
        if stage not in STAGES[1:]:raise ValueError('未知阶段')
        f['stageNotes'][stage]=str(op['message'])
    else:raise ValueError('未知操作')
    if a.startswith('plan_'):
        task=next((i for i in f['items'] if i['id']=='visual'),None)
        if task:
            task.update(status='已完成' if f['approved'] else '待确认',evidence='用户确认方案 '+f['choice'] if f['approved'] else '',next='按已确认方向准备素材' if f['approved'] else '审阅视觉稿与排版方案')

def spread(route):
    """Diagram units. The central band is deliberately schematic."""
    tone='#859ba4'; ink='#25343d'
    parts=['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 620 420" width="620" height="420"><rect width="620" height="420" fill="white"/>']
    def path(d,color=tone,width=1,fill='none'):
        parts.append(f'<path d="{d}" stroke="{color}" stroke-width="{width}" fill="{fill}"/>')
    def label(x,y,txt,size=11,font='Georgia',fill=ink):
        parts.append(f'<text x="{x}" y="{y}" font-family="{font}" font-size="{size}" fill="{fill}">{escape(txt)}</text>')
    if route=='echo':
        for i in range(26):
            x=295+i*6;y=170+i*1.6
            path(f'M {x} -5 C {x-135} {y-75} {x+40} {y-40} {x-14} {y+20} S {x-185} 325 {x-96} 427',tone if i%5 else ink,.7 if i%5 else 1.3)
        for i in range(70):
            x=26+(i*39)%207;y=45+(i*31)%258
            parts.append(f'<circle cx="{x}" cy="{y}" r="{.65+(i%4)*.16}" fill="{tone}"/>')
        parts.append('<rect x="358" y="125" width="245" height="105" fill="white"/>')
        label(369,153,'The',17);label(366,193,'Becoming',46);label(369,217,'Journal',23)
    elif route=='archive':
        for i in range(3):
            x=328+i*21;y=68+i*28
            path(f'M{x} {y}h180v179h-180z',tone,1,['#eff2f4','#dce4e6','#fff'][i])
            for j in range(5):path(f'M{x+11} {y+85+j*8}h{79-j*7}',tone,.6)
        for i in range(3):
            path(f'M32 {72+i*62}h58v43H32z',tone,1,'#f2f4f5');path(f'M102 {90+i*62}h101',tone,.6)
        path('M30 289H520',tone,1)
        label(385,165,'The Becoming',27);label(385,194,'Journal',30)
    elif route=='orbit':
        for i in range(13):
            parts.append(f'<ellipse cx="524" cy="125" rx="{125+i*9}" ry="{101+i*7}" fill="none" stroke="{tone}" stroke-width="{.6 if i%3 else 1.2}"/>')
        path('M55 271 Q300 440 670 95',ink,1.4)
        for i in range(13):path(f'M{50+i*10} {260+i*2}l-3 12',tone,.8)
        parts.append('<circle cx="85" cy="273" r="27" stroke="#626e79" fill="white"/><rect x="338" y="222" width="250" height="67" fill="white"/>')
        label(344,248,'The Becoming',33);label(345,278,'Journal',29)
    else:label(345,182,'Layout study',25)
    for x in (300,320):path(f'M{x} 0V420','#9ea7ae',.65)
    parts.append('<text transform="translate(314 276) rotate(-90)" font-family="Georgia" font-size="8">THE BECOMING JOURNAL</text>')
    label(26,336,'Creating memories for my future self.',12)
    label(26,359,'I walk backwards into the future',10);label(26,373,'with my eyes fixed on my past.',10)
    label(345,374,'一 年 愿 望 本',11,'serif');label(543,393,'INKA+',12)
    return ''.join(parts)+'</svg>'

