const $ = id => document.getElementById(id);
const safe = v => String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
let head, record, historyRows, layouts, selected='subject', view='art', tool='', gesture, points=[];
let renderId=0, busy=false;
const panelOpen={material:true,globalTexture:true,repeat:false};

const BLEND_OPTIONS=[
  ['normal','正常 Normal'],
  ['multiply','正片叠底 Multiply'],
  ['screen','滤色 Screen'],
  ['overlay','叠加 Overlay'],
  ['soft-light','柔光 Soft Light'],
  ['color-burn','颜色加深 Color Burn'],
  ['darken','变暗 Darken'],
  ['lighten','变亮 Lighten']
];

const GM_DEFAULT={
  enabled:false,
  stops:[
    {offset:0,color:'#0b1638'},
    {offset:0.52,color:'#1d4ed8'},
    {offset:1,color:'#f7f9ff'}
  ],
  invert:false,
  strength:1
};

const GM_PRESETS=[
  {name:'深海蓝白',stops:[{offset:0,color:'#091334'},{offset:0.52,color:'#1d4ed8'},{offset:1,color:'#f5f8ff'}]},
  {name:'群青月海',stops:[{offset:0,color:'#101d4a'},{offset:0.48,color:'#3263be'},{offset:1,color:'#edf5f9'}]},
  {name:'古铜流金',stops:[{offset:0,color:'#1f1410'},{offset:0.52,color:'#b86b2b'},{offset:1,color:'#f9e7be'}]},
  {name:'冷月银炭',stops:[{offset:0,color:'#121821'},{offset:0.55,color:'#697b8e'},{offset:1,color:'#f4f7fa'}]},
  {name:'松青冷瓷',stops:[{offset:0,color:'#0b2427'},{offset:0.5,color:'#2c7a7b'},{offset:1,color:'#eef8f6'}]}
];

const ORG_DEFAULT={
  enabled:false,
  scale:9,
  frequency:0.055,
  octaves:4,
  seed:17,
  inset:2.5,
  feather:0.15,
  rimEnabled:false,
  rimColor:'#d4af37',
  rimWidth:0.55,
  rimOpacity:0.92,
  rimShimmer:true
};

const ORG_PRESETS={
  coastline:{enabled:true,scale:10,frequency:0.055,octaves:4,inset:2.5,feather:0.12,rimEnabled:true,rimColor:'#d4af37',rimWidth:0.55,rimOpacity:0.94,rimShimmer:true},
  torn:{enabled:true,scale:7.5,frequency:0.095,octaves:5,inset:2.0,feather:0.15,rimEnabled:false,rimColor:'#d4af37',rimWidth:0.45,rimOpacity:0.9,rimShimmer:true},
  ink:{enabled:true,scale:13.5,frequency:0.036,octaves:3,inset:3.2,feather:0.85,rimEnabled:false,rimColor:'#c9d4e0',rimWidth:0.5,rimOpacity:0.85,rimShimmer:false}
};

const RIM_SWATCHES=[
  {name:'流金',color:'#d4af37'},
  {name:'香槟金',color:'#e5c77b'},
  {name:'冷银',color:'#c9d4e0'},
  {name:'古铜',color:'#b87344'}
];

const KO_DEFAULT={enabled:false,pad:3.5,feather:2.2,scope:'linework'};
const TEX_DEFAULT={enabled:false,kind:'paper',blend:'multiply',opacity:0.16,scale:1,contrast:1,asset:''};

const object=()=>record.state.objects.find(o=>o.id===selected);
const msg=text=>$('status').textContent=text;
const edition=new URLSearchParams(location.search).get('edition');
const sku=new URLSearchParams(location.search).get('sku');
const scope=edition?'edition='+encodeURIComponent(edition):sku?'sku='+encodeURIComponent(sku):'';
const scoped=path=>scope?path+(path.includes('?')?'&':'?')+scope:path;
if(edition){
  document.body.classList.add('jacket');
  document.querySelector('header .brand a').href='/covers';
  document.querySelector('#shuffle').parentElement.hidden=true;
}
const preview=(rev,mode='art',layout='')=>scoped('/preview?'+new URLSearchParams({rev,mode,...(layout?{layout}:{})}));

async function api(path,body){
  const response=await fetch(scoped(path),body===undefined?{}:{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
  const value=await response.json();
  if(!response.ok)throw Error(value.error||response.statusText);
  return value;
}

async function load(rev){
  head=await api('/state'); record=rev&&rev!==head.rev?await api('/state?rev='+rev):head;
  historyRows=await api('/history');
  if(!object())selected=record.state.objects.find(o=>o.id===record.state.materialFocus)?.id||record.state.objects.find(o=>o.kind==='image'&&!o.previewOnly)?.id||record.state.objects.at(-1)?.id;
  await draw();
}

async function commit(label,ops){
  if(busy)throw Error('上一笔修改正在保存，请稍后再试');
  busy=true;
  try{
    const result=await api('/change',{base:head.rev,from:record.rev,label,ops});
    tool='';points=[];await load(result.rev);msg('已保存 · '+label);
  }catch(e){await load();msg(e.message);throw e}finally{busy=false}
}

const edit=(values,label)=>commit(label,[{action:'edit',id:selected,values}]);
const mask=(values,label)=>edit({mask:{...object().mask,...values}},label);
const setTexture=(values,label)=>commit(label,[{action:'texture',values}]);

function fmtNum(v){
  const n=Number(v);
  return Number.isFinite(n)?String(Math.round(n*100)/100):String(v??'');
}
function input(label,key,val,type='text'){
  const shown=type==='number'?fmtNum(val):val;
  return '<label>'+label+'<input name="'+key+'" type="'+type+'" '+(type==='number'?'step="any" data-orig="'+safe(shown)+'" ':'')+'value="'+safe(shown)+'"></label>';
}
function button(action,title,cls=''){return '<button type="button" '+(cls?'class="'+cls+'" ':'')+'data-act="'+action+'">'+title+'</button>'}
function slider(id,label,val,min,max,step,unit='',attr=''){
  const shown=unit==='%'?Math.round(Number(val)*100)+'%':Number(val).toFixed(step<0.1?3:step<1?2:0).replace(/\.?0+$/,'')+(unit?' '+unit:'');
  return '<div class="slider-row"><div class="slider-head"><span>'+label+'</span><span class="val" data-val-for="'+id+'">'+shown+'</span></div>'+
    '<input id="'+id+'" type="range" min="'+min+'" max="'+max+'" step="'+step+'" value="'+val+'" data-unit="'+unit+'" '+attr+'></div>';
}

function gmConfig(o){
  const raw=o.gradientMap||{};
  const stops=Array.isArray(raw.stops)&&raw.stops.length>=2?raw.stops.map(s=>({offset:Number(s.offset),color:s.color})):GM_DEFAULT.stops.map(s=>({...s}));
  return {...GM_DEFAULT,...raw,stops};
}
function orgConfig(o){return {...ORG_DEFAULT,...(o.mask?.organic||{})}}
function koConfig(o){return {...KO_DEFAULT,...(o.mask?.knockout||{})}}
function texConfig(){return {...TEX_DEFAULT,...(record.state.texture||{})}}

function gradientCss(stops,invert=false){
  const list=[...stops].sort((a,b)=>a.offset-b.offset);
  const mapped=invert?list.map(s=>({offset:1-s.offset,color:s.color})).reverse():list;
  return 'linear-gradient(90deg,'+mapped.map(s=>s.color+' '+Math.round(s.offset*100)+'%').join(',')+')';
}

function layerTags(o){
  const tags=[];
  if(o.gradientMap?.enabled)tags.push('<span class="tag blue">映射</span>');
  if(o.mask?.organic?.enabled)tags.push('<span class="tag gold">'+(o.mask.organic.rimEnabled?'金边':'有机')+'</span>');
  if(o.mask?.knockout?.enabled)tags.push('<span class="tag teal">避让</span>');
  if(o.uv)tags.push('<span class="tag">UV</span>');
  if(o.locks.length)tags.push('<span class="tag">锁</span>');
  return tags.length?'<span class="layer-tags">'+tags.join('')+'</span>':'';
}

async function draw(){
  const {state:s,rev}=record;
  $('heading').textContent=s.concept;$('concept').value=s.concept;
  $('format').textContent=s.product.name+'  /  '+s.product.width+' × '+s.product.height+' mm  /  出血 '+s.product.bleed+' mm';
  $('layoutName').textContent=s.layout;$('version').textContent='版本 '+rev+(rev!==head.rev?' · 历史':'');
  $('choices').innerHTML=edition?'':s.choices.map(l=>'<button data-layout="'+safe(l)+'" class="'+(l===s.layout?'active':'')+'"><img src="'+preview(rev,'layout',l)+'">'+safe(l)+'</button>').join('');
  $('layouts').innerHTML=layouts.map(l=>'<option '+(s.layout===l?'selected':'')+'>'+safe(l)+'</option>').join('');
  $('history').innerHTML=historyRows.map((h,index)=>'<button data-rev="'+h.rev+'" class="'+(h.rev===rev?'active':'')+'"><img loading="lazy" '+(index<4?'src="'+preview(h.rev)+'"':'hidden')+'><span>'+safe(h.label)+'<br>v'+h.rev+(h.parent?' ← v'+h.parent:'')+'</span></button>').join('');
  $('layers').innerHTML=[...s.objects].reverse().map(o=>'<button data-layer="'+o.id+'" class="'+(o.id===selected?'active':'')+'"><i></i><span class="layer-name">'+safe(o.name)+'</span>'+layerTags(o)+'</button>').join('');
  document.querySelectorAll('#layers i').forEach(i=>i.style.background=s.objects.find(o=>o.id===i.parentNode.dataset.layer).fill);
  document.querySelectorAll('[data-mode]').forEach(b=>b.classList.toggle('active',b.dataset.mode===view));
  const parent=historyRows.find(r=>r.rev===rev)?.parent;
  $('actions').innerHTML=(parent?button('compare','与上一步比较'):'')+(rev!==head.rev?button('restore','从此版本继续')+button('latest','返回最新'):'');
  $('process').elements.plate.value=s.process.plate;$('process').elements.machine.value=s.process.machine;
  $('process').elements.format.value=s.process.format;
  discussion();props();
  if(!edition)renderGlobalTexture();
  if(rev===head.rev&&parent)$('actions').insertAdjacentHTML('afterbegin',button('undoDesign','撤销上一次画面修改'));
  await canvas();
}

async function canvas(){
  const seq=++renderId, res=await fetch(preview(record.rev,view==='mask'?'mask:'+selected:view));
  if(!res.ok)throw Error('预览失败');const svg=await res.text();
  if(seq!==renderId)return;
  $('canvas').innerHTML=svg;
  outlineSelection();
  if(tool==='sam')drawPoints();
}

function outlineSelection(){
  const svg=$('canvas').querySelector('svg');if(!svg)return;
  svg.querySelector('.selected-box')?.remove();
  if(!tool||!object()||view==='plate')return;
  const o=object(),rect=document.createElementNS(svg.namespaceURI,'rect');
  for(const [k,v] of Object.entries({x:o.x-o.w/2,y:o.y-o.h/2,width:o.w,height:o.h/1,transform:'rotate('+o.angle+' '+o.x+' '+o.y+')',fill:'none',stroke:'#1d4e66','stroke-width':'.4','stroke-dasharray':'1.5 1',class:'selected-box'}))rect.setAttribute(k,v);
  svg.append(rect);
}

function renderGradientMapCard(o){
  const gm=gmConfig(o);
  const stopLabels=gm.stops.length===2?['暗部','高光']:['暗部','中间调','高光'];
  const presetHtml=GM_PRESETS.map((p,idx)=>
    '<button type="button" class="preset-chip" data-gm-preset="'+idx+'"><span class="preset-dot" style="background:'+gradientCss(p.stops)+'"></span>'+p.name+'</button>'
  ).join('');
  const stopsHtml=gm.stops.map((st,i)=>(
    '<div class="stop-cell"><span><b>'+(stopLabels[i]||('色标 '+(i+1)))+'</b><em data-gm-pct="'+i+'">'+Math.round(st.offset*100)+'%</em></span>'+
    '<input type="color" data-gm-color="'+i+'" value="'+safe(st.color)+'">'+
    '<input type="range" data-gm-offset="'+i+'" min="0" max="1" step="0.01" value="'+st.offset+'"></div>'
  )).join('');
  return '<div class="fx-card '+(gm.enabled?'is-on':'')+'" id="gmCard">'+
    '<div class="fx-head"><span class="fx-title">渐变映射上色 <small>Gradient Map</small></span><input id="gmEnabled" class="switch" type="checkbox" '+(gm.enabled?'checked':'')+'></div>'+
    '<div class="gm-bar" id="gmBar" style="background:'+gradientCss(gm.stops,gm.invert)+'"></div>'+
    '<div class="fx-body" '+(gm.enabled?'':'hidden')+'>'+
      '<div class="preset-row">'+presetHtml+'</div>'+
      '<div class="row" style="justify-content:space-between;margin:2px 0">'+
        '<div class="seg-btn"><button type="button" data-gm-count="2" class="'+(gm.stops.length===2?'active':'')+'">2 色</button><button type="button" data-gm-count="3" class="'+(gm.stops.length===3?'active':'')+'">3 色</button></div>'+
        '<label style="display:inline-flex;align-items:center;gap:4px"><input id="gmInvert" type="checkbox" '+(gm.invert?'checked':'')+'> 反转色带</label>'+
      '</div>'+
      '<div class="stop-grid">'+stopsHtml+'</div>'+
      slider('gmStrength','映射强度',gm.strength,0,1,0.02,'%') +
    '</div>'+
    (gm.enabled?'':'<p class="hint">将任意黑白/灰度纹理重映射到自定义 2–3 色带，一键统一色调。</p>')+
  '</div>';
}

function renderOrganicCard(o){
  const org=orgConfig(o);
  const swatches=RIM_SWATCHES.map(sw=>
    '<button type="button" class="swatch-dot" title="'+sw.name+'" data-rim-color="'+sw.color+'" style="background:'+sw.color+'"></button>'
  ).join('');
  return '<div class="fx-card '+(org.enabled?'is-on':'')+'" id="orgCard">'+
    '<div class="fx-head"><span class="fx-title">不规则噪点边缘 <small>有机边缘 + 金边</small></span><input id="orgEnabled" class="switch gold" type="checkbox" '+(org.enabled?'checked':'')+'></div>'+
    '<div class="fx-body" '+(org.enabled?'':'hidden')+'>'+
      '<div class="preset-row">'+
        '<button type="button" class="preset-chip" data-org-preset="coastline">海岸线金边</button>'+
        '<button type="button" class="preset-chip" data-org-preset="torn">撕纸毛边</button>'+
        '<button type="button" class="preset-chip" data-org-preset="ink">水墨晕边</button>'+
      '</div>'+
      slider('orgScale','噪点位移幅度',org.scale,0,36,0.5,'mm') +
      slider('orgFreq','海岸线细节频率',org.frequency,0.01,0.18,0.005,'') +
      slider('orgOctaves','分形细节层数',org.octaves,1,6,1,'') +
      slider('orgInset','边缘内缩留白',org.inset,0,20,0.5,'mm') +
      slider('orgFeather','边缘羽化',org.feather,0,3,0.05,'mm') +
      '<div class="seed-row"><label style="margin:0;flex:1">形态种子</label><input id="orgSeed" type="number" min="0" max="9999" step="1" value="'+org.seed+'">'+button('orgSeed','换形态 ↻')+'</div>'+
      '<div class="fx-head" style="margin-top:6px;padding-top:7px;border-top:1px solid var(--line)"><span class="fx-title">沿边缘金属描边 <small>1–2px 细金边</small></span><input id="orgRimEnabled" class="switch gold" type="checkbox" '+(org.rimEnabled?'checked':'')+'></div>'+
      '<div class="fx-body" style="margin-top:2px" '+(org.rimEnabled?'':'hidden')+'>'+
        '<div class="row" style="margin:0;justify-content:space-between">'+
          '<div class="preset-row">'+swatches+'</div>'+
          '<input id="orgRimColor" type="color" value="'+safe(org.rimColor)+'" style="width:44px;height:26px;padding:1px">'+
        '</div>'+
        slider('orgRimWidth','描边宽度',org.rimWidth,0.2,2.5,0.05,'mm') +
        slider('orgRimOpacity','描边不透明度',org.rimOpacity,0,1,0.02,'%') +
        '<label style="display:inline-flex;align-items:center;gap:5px"><input id="orgRimShimmer" type="checkbox" '+(org.rimShimmer?'checked':'')+'> 金箔高光微闪</label>'+
      '</div>'+
    '</div>'+
    (org.enabled?'':'<p class="hint">用分形噪点打碎规则裁切，保持内部纹理清晰不扭曲，可选 1–2px 细金边描边。</p>')+
  '</div>';
}

function renderKnockoutCard(o){
  if(o.kind!=='text')return '';
  const ko=koConfig(o);
  return '<div class="fx-card '+(ko.enabled?'is-on':'')+'" id="koCard">'+
    '<div class="fx-head"><span class="fx-title">文字底层线条避让 <small>反向羽化遮罩</small></span><input id="koEnabled" class="switch" type="checkbox" '+(ko.enabled?'checked':'')+'></div>'+
    '<div class="fx-body" '+(ko.enabled?'':'hidden')+'>'+
      slider('koPad','避让外扩间距',ko.pad,0.5,12,0.25,'mm') +
      slider('koFeather','羽化柔和度',ko.feather,0,8,0.2,'mm') +
      '<label>避让目标<select id="koScope"><option value="linework" '+(ko.scope==='linework'?'selected':'')+'>仅挖空下方矢量线条（保留背景纹理）</option><option value="below" '+(ko.scope==='below'?'selected':'')+'>挖空下方全部非底图层</option></select></label>'+
    '</div>'+
    (ko.enabled?'':'<p class="hint">替代纯白实心底块：自动生成带羽化的反向遮罩，挖空文字下方线条同时保留底层纹理。</p>')+
  '</div>';
}

function renderGlobalTexture(){
  const tex=texConfig();
  const opPct=Math.round(tex.opacity*100);
  $('globalTexture').innerHTML=
    '<details data-panel="globalTexture" '+(panelOpen.globalTexture?'open':'')+'>'+
      '<summary><span>全局质感层</span><span class="summary-pill '+(tex.enabled?'on':'')+'">'+(tex.enabled?'已启用 · '+opPct+'%':'未启用')+'</span></summary>'+
      '<div class="fx-head"><span class="fx-title">顶层纸纹 / 噪点融合 <small>导出时合成</small></span><input id="texEnabled" class="switch gold" type="checkbox" '+(tex.enabled?'checked':'')+'></div>'+
      '<div class="fx-body" '+(tex.enabled?'':'hidden')+'>'+
        '<div class="fieldgrid">'+
          '<label>质感类型<select id="texKind">'+
            [['paper','细纹艺术纸'],['grain','细腻胶片噪点'],['fiber','冷白棉纸纤维'],['asset','自定义贴图']].map(([k,v])=>'<option value="'+k+'" '+(tex.kind===k?'selected':'')+'>'+v+'</option>').join('')+
          '</select></label>'+
          '<label>混合模式<select id="texBlend">'+
            [['multiply','正片叠底 Multiply'],['overlay','叠加 Overlay'],['soft-light','柔光 Soft Light']].map(([k,v])=>'<option value="'+k+'" '+(tex.blend===k?'selected':'')+'>'+v+'</option>').join('')+
          '</select></label>'+
        '</div>'+
        slider('texOpacity','质感不透明度',tex.opacity,0,0.6,0.01,'%') +
        (tex.kind==='asset'
          ?'<label>上传自定义纸纹图<input type="file" id="texFile" accept="image/png,image/jpeg,image/webp"></label>'+(tex.asset?'<p class="hint">已载入自定义贴图 '+tex.asset.slice(0,10)+'…</p>':'<p class="hint">请选择一张纸纹或噪点图。</p>')
          :slider('texScale','颗粒 / 纸纹粗细',tex.scale,0.3,3,0.1,'x') + slider('texContrast','质感对比度',tex.contrast,0.4,2.2,0.05,'x'))+
        '<p class="hint">覆盖画布最顶层，消除元素贴纸感；导出交接稿 ART.svg 时自动合成，UV/压凹单版自动排除。</p>'+
      '</div>'+
      (tex.enabled?'':'<p class="hint">在最顶层叠加 multiply / overlay 纸纹或颗粒，统一整张画面的印刷质感。</p>')+
    '</details>';
}

const layerDrafts=new Map();
function jacketProps(o){
  const feedback=$('layerFeedback');
  feedback.hidden=false;
  const current=record.rev===head.rev;
  const notes=(record.state.discussion||[]).filter(n=>!n.target||n.target===o.id||!record.state.objects.some(layer=>layer.id===n.target)).reverse();
  feedback.innerHTML='<h3>'+safe(o.name)+'</h3>'+
    (current?'<form id="inlineNote"><label>给这层的意见<textarea required name="message" rows="3">'+safe(layerDrafts.get(o.id)||'')+'</textarea></label><details><summary>附参考图</summary><input name="reference" type="file" accept="image/png,image/jpeg,image/webp" multiple></details><button>保存意见</button></form>':'')+
    notes.map(n=>'<article><small>'+safe(n.targetName)+' · '+safe(n.status)+'</small><p>'+safe(n.message)+'</p>'+
      (n.refs||[]).filter(()=>n.purpose!=='合成前素材').map(key=>'<a target="_blank" href="'+scoped('/assets/'+encodeURIComponent(key))+'"><img width="48" alt="参考图" src="'+scoped('/assets/'+encodeURIComponent(key))+'"></a>').join('')+
      (n.reply?'<p>'+safe(n.reply)+'</p>':'')+
      (current&&n.status==='待处理'?'<button type="button" data-withdraw="'+safe(n.id)+'">撤回意见</button>':'')+'</article>').join('')+
    (current&&notes.some(n=>n.status==='待处理')?button('handoff','复制待处理意见给 Agent')+' <a target="_blank" href="'+scoped('/brand/handoff')+'">查看交接单</a>':'');
  if(current){
    const drafts=(record.state.discussion||[]).filter(n=>n.purpose==='合成前素材'&&n.status==='待处理');
    for(const n of drafts){
      const asset=n.refs?.[0];if(!asset)continue;
      feedback.insertAdjacentHTML('beforeend','<div class="sample"><img width="120" alt="待评素材" src="'+scoped('/assets/'+encodeURIComponent(asset))+'"><button type="button" data-compose="'+safe(n.id)+'">将此素材加入画布</button></div>');
    }
  }
  const image=o.kind==='image';
  const stops=o.gradientMap?.stops;
  $('props').innerHTML=(image?'<details class="sample"><summary>单独查看素材</summary><div class="samplepair"><figure><img src="'+scoped('/assets/'+o.asset)+'"><figcaption>导入素材</figcaption></figure><figure><img id="materialSample"><figcaption>当前处理</figcaption></figure></div></details>':'')+
    '<form id="values"><div class="fieldgrid">'+
    [['中心 X','x'],['中心 Y','y'],['宽 mm','w'],['高 mm','h'],['旋转 °','angle']].map(([l,k])=>input(l,k,o[k],'number')).join('')+
    (image?input('图像调色','tint',stops?.at(-1)?.color||'#ffffff','color'):input('颜色','fill',o.fill,'color'))+'</div>'+
    (o.kind==='text'?input('文字','text',o.text)+input('字体','font',o.font||'Georgia'):'')+
    '<button>应用属性</button></form>'+
    (image?'<label>原位替换图片<input type="file" id="file" accept="image/png,image/jpeg,image/webp"></label>':'');
  samplePreview();
}
function delivery(id){
  $('delivery').innerHTML='<a download href="'+scoped('/package?id='+encodeURIComponent(id))+'">下载 '+safe(id.split('-')[0])+' 分层交接包</a>　<a href="/covers?delivery='+encodeURIComponent(id)+'&jacket='+encodeURIComponent(edition||'')+'#'+encodeURIComponent('封面工艺与用纸')+'">进入工艺与用纸 →</a>';
}
function props(){
  const o=object();if(!o){$('layerFeedback').hidden=true;$('props').textContent='添加元素开始设计';return}if(edition){jacketProps(o);return}const m=o.mask;
  const activeCount=(o.gradientMap?.enabled?1:0)+(m.organic?.enabled?1:0)+(m.knockout?.enabled?1:0);
  $('props').innerHTML=(o.kind==='image'?'<section class="sample"><b>素材加工 · '+safe(o.name)+'</b><div class="samplepair"><figure><img alt="原始素材" src="'+scoped('/assets/'+o.asset)+'"><figcaption>原始素材</figcaption></figure><figure><img id="materialSample" alt="加工预览"><figcaption>处理效果</figcaption></figure></div>'+button('saveRecipe','导出素材配方')+' <label class="recipe-input">套用配方<input id="loadRecipe" type="file" accept=".json"></label></section>':'')+'<form id="values">'+input('名称','name',o.name)+
    '<div class="fieldgrid">'+[['中心 X','x'],['中心 Y','y'],['宽 mm','w'],['高 mm','h'],['旋转 °','angle']].map(([l,k])=>input(l,k,o[k],'number')).join('')+input('颜色','fill',o.fill,'color')+'</div>'+
    '<div class="fieldgrid"><label>混合模式<select name="blend">'+BLEND_OPTIONS.map(([k,v])=>'<option value="'+k+'" '+(k===(o.blend||'normal')?'selected':'')+'>'+v+'</option>').join('')+'</select></label>'+
    '<label>不透明度（0–1）<input name="opacity" type="number" min="0" max="1" step=".01" value="'+(o.opacity??1)+'"></label></div>'+
    (o.kind==='text'?input('文字','text',o.text)+input('字体','font',o.font||'Garamond')+'<label style="display:inline-flex;align-items:center;gap:5px;margin-bottom:6px"><input id="italic" type="checkbox" '+(o.italic?'checked':'')+'> 斜体</label>':'')+
    '<button style="width:100%">应用属性</button></form>'+
    '<div class="row">'+button('up','上移一层')+button('down','下移一层')+'</div>'+
    '<div class="check-row">'+[['layout','构图'],['asset','素材'],['mask','蒙版']].map(([k,l])=>'<label><input type="checkbox" data-lock="'+k+'" '+(o.locks.includes(k)?'checked':'')+'>锁'+l+'</label>').join('')+
    '<label><input id="uv" type="checkbox" '+(o.uv?'checked':'')+'> 局部 UV</label></div>'+
    '<details data-panel="material" '+(panelOpen.material?'open':'')+'>'+
      '<summary><span>素材与蒙版</span>'+(activeCount?'<span class="summary-pill on">'+activeCount+' 项合成启用</span>':'')+'</summary>'+
      renderGradientMapCard(o)+
      renderOrganicCard(o)+
      renderKnockoutCard(o)+
      '<div style="margin-top:10px;padding-top:9px;border-top:1px solid var(--line)">'+
        '<label>原位替换图片<input type="file" id="file" accept="image/png,image/jpeg,image/webp"></label>'+
        (o.source?'<p class="hint">'+safe(o.source)+'</p>':'')+
        '<label>使用对象轮廓遮挡<select id="cut"><option value="">无</option>'+
        record.state.objects.filter(r=>r.id!==o.id).map(r=>'<option value="'+r.id+'" '+(m.cut===r.id?'selected':'')+'>'+safe(r.name)+'</option>').join('')+'</select></label>'+
        '<div class="row">'+button('fade',m.fade?'移除渐隐':'渐变淡出')+button('crop','裁切范围')+'</div>'+
        '<label>蒙版画笔大小（对象宽度 %）<input id="brushSize" type="number" value="6" min=".1" max="100" step=".5"></label>'+
        '<div class="row">'+button('erase','画笔擦除')+button('paint','画笔补回')+button('move','移动工具')+'</div>'+
        (o.kind==='image'?'<div class="row">'+button('sam','点选 SAM2')+button('segment','计算选区')+'</div>':'')+
      '</div>'+
    '</details>'+
    '<details data-panel="repeat" '+(panelOpen.repeat?'open':'')+'><summary>绕中心旋转复制</summary><form id="repeat"><div class="fieldgrid">'+input('中心 X','cx',o.x,'number')+input('中心 Y','cy',o.y,'number')+input('角度 °','degrees',30,'number')+input('份数','count',5,'number')+'</div><button>复制</button></form></details>';
  samplePreview();
}

let sampleTimer, sampleSerial=0;
function samplePreview(values={}){
  const target=$('materialSample'), o=object(), serial=++sampleSerial;
  clearTimeout(sampleTimer);
  if(!target||!o)return;
  sampleTimer=setTimeout(async()=>{
    try{
      const res=await fetch(scoped('/material-preview'),{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({rev:record.rev,id:o.id,values})});
      if(!res.ok)throw Error((await res.json()).error);
      const url=URL.createObjectURL(await res.blob());
      if(serial!==sampleSerial||!target.isConnected){URL.revokeObjectURL(url);return}
      target.onload=target.onerror=()=>URL.revokeObjectURL(url);target.src=url;
    }catch(err){if(serial===sampleSerial)msg(err.message)}
  },120);
}
function readGradientMapForm(){
  const o=object();
  const base=gmConfig(o);
  const colors=[...document.querySelectorAll('[data-gm-color]')];
  const offsets=[...document.querySelectorAll('[data-gm-offset]')];
  const stops=colors.map((el,i)=>({offset:Number(offsets[i]?.value??base.stops[i]?.offset??0),color:el.value}));
  return {
    enabled:$('gmEnabled').checked,
    stops:stops.length>=2?stops:base.stops,
    invert:$('gmInvert')?.checked??base.invert,
    strength:Number($('gmStrength')?.value??base.strength)
  };
}

function readOrganicForm(){
  const o=object();
  const base=orgConfig(o);
  return {
    enabled:$('orgEnabled').checked,
    scale:Number($('orgScale')?.value??base.scale),
    frequency:Number($('orgFreq')?.value??base.frequency),
    octaves:Number($('orgOctaves')?.value??base.octaves),
    seed:Math.max(0,Math.min(9999,Math.round(Number($('orgSeed')?.value??base.seed)))),
    inset:Number($('orgInset')?.value??base.inset),
    feather:Number($('orgFeather')?.value??base.feather),
    rimEnabled:$('orgRimEnabled')?.checked??base.rimEnabled,
    rimColor:$('orgRimColor')?.value??base.rimColor,
    rimWidth:Number($('orgRimWidth')?.value??base.rimWidth),
    rimOpacity:Number($('orgRimOpacity')?.value??base.rimOpacity),
    rimShimmer:$('orgRimShimmer')?.checked??base.rimShimmer
  };
}

function readKnockoutForm(){
  const o=object();
  const base=koConfig(o);
  return {
    enabled:$('koEnabled').checked,
    pad:Number($('koPad')?.value??base.pad),
    feather:Number($('koFeather')?.value??base.feather),
    scope:$('koScope')?.value??base.scope
  };
}

function readTextureForm(){
  const base=texConfig();
  return {
    enabled:$('texEnabled').checked,
    kind:$('texKind')?.value??base.kind,
    blend:$('texBlend')?.value??base.blend,
    opacity:Number($('texOpacity')?.value??base.opacity),
    scale:Number($('texScale')?.value??base.scale),
    contrast:Number($('texContrast')?.value??base.contrast),
    asset:base.asset||''
  };
}

function coordinates(e){
  const svg=$('canvas').querySelector('svg');
  return new DOMPoint(e.clientX,e.clientY).matrixTransform(svg.getScreenCTM().inverse());
}
function local(pt,o){
  const rad=-o.angle*Math.PI/180,dx=pt.x-o.x,dy=pt.y-o.y;
  return [50+(dx*Math.cos(rad)-dy*Math.sin(rad))*100/o.w,50+(dx*Math.sin(rad)+dy*Math.cos(rad))*100/o.h];
}
function drawPoints(){
  const svg=$('canvas').querySelector('svg');if(!svg)return;
  for(const p of points){
    const c=document.createElementNS(svg.namespaceURI,'circle');
    c.setAttribute('cx',p.world.x);c.setAttribute('cy',p.world.y);c.setAttribute('r','1.4');c.setAttribute('fill',p.label?'#05b77b':'#f33');svg.append(c);
  }
}

$('canvas').oncontextmenu=e=>e.preventDefault();
$('canvas').onpointerdown=e=>{
  const pt=coordinates(e);const hit=e.target.closest('[data-object]')?.dataset.object;
  if(tool==='sam'){
    const xy=local(pt,object());
    if(xy.every(n=>n>=0&&n<=100)){points.push({xy,label:e.button===2?0:1,world:pt});drawPoints()}
    return;
  }
  if(!tool&&hit){selected=hit;props();document.querySelectorAll('[data-layer]').forEach(b=>b.classList.toggle('active',b.dataset.layer===hit))}
  if(!tool&&!hit)return;
  const o=object();if(o.locks.includes(tool?'mask':'layout')){msg('该属性已锁定');return}
  const svg=$('canvas').querySelector('svg'),path=document.createElementNS(svg.namespaceURI,'polyline');
  if(tool){path.setAttribute('fill','none');path.setAttribute('stroke','#df5b51');path.setAttribute('stroke-width','1');svg.append(path)}
  gesture={start:pt,pts:[local(pt,o)],world:[pt],path,id:selected};$('canvas').setPointerCapture(e.pointerId);
};
$('canvas').onpointermove=e=>{
  if(!gesture)return;const pt=coordinates(e),o=object();
  if(tool){gesture.pts.push(local(pt,o));gesture.world.push(pt);gesture.path.setAttribute('points',gesture.world.map(p=>p.x+','+p.y).join(' '))}
  else $('canvas').querySelector('[data-object="'+selected+'"]')?.setAttribute('transform','translate('+(pt.x-gesture.start.x)+' '+(pt.y-gesture.start.y)+')');
};
$('canvas').onpointercancel=()=>{gesture=null;canvas()};
$('canvas').onpointerup=async e=>{
  if(!gesture)return;const g=gesture;gesture=null;const o=object(),pt=coordinates(e);
  if(tool){const size=Number($('brushSize').value);
    await mask({strokes:[...(o.mask.strokes||[]),{points:g.pts,size,restore:tool==='paint'}]},'手修蒙版 · '+o.name)}
  else if(Math.hypot(pt.x-g.start.x,pt.y-g.start.y)>.1)await edit({x:o.x+pt.x-g.start.x,y:o.y+pt.y-g.start.y},'移动 · '+o.name);
};

// Track <details> open state so re-renders preserve panel collapse/expand
document.addEventListener('toggle',e=>{
  const p=e.target.dataset?.panel;
  if(p)panelOpen[p]=e.target.open;
},true);

// Live numeric readouts & gradient bar preview while dragging sliders/color pickers
document.addEventListener('input',e=>{
  const t=e.target;
  if(t.closest('#inlineNote'))layerDrafts.set(selected,t.value);
  if(t.closest('[data-panel="material"]')&&object()?.kind==='image'){
    if(t.id.startsWith('gm')||t.hasAttribute('data-gm-color')||t.hasAttribute('data-gm-offset'))samplePreview({gradientMap:readGradientMapForm()});
    if(t.id.startsWith('org'))samplePreview({mask:{...object().mask,organic:readOrganicForm()}});
  }
  if(t.type==='range'&&t.id){
    const out=document.querySelector('[data-val-for="'+t.id+'"]');
    if(out){
      const unit=t.dataset.unit||'';
      const step=Number(t.step||1);
      out.textContent=unit==='%'?Math.round(Number(t.value)*100)+'%':Number(t.value).toFixed(step<0.1?3:step<1?2:0).replace(/\.?0+$/,'')+(unit?' '+unit:'');
    }
  }
  if(t.dataset.gmColor!==undefined||t.dataset.gmOffset!==undefined){
    if(t.dataset.gmOffset!==undefined){
      const lbl=document.querySelector('[data-gm-pct="'+t.dataset.gmOffset+'"]');
      if(lbl)lbl.textContent=Math.round(Number(t.value)*100)+'%';
    }
    const bar=$('gmBar');
    if(bar){
      const gm=readGradientMapForm();
      bar.style.background=gradientCss(gm.stops,gm.invert);
    }
  }
});

document.addEventListener('submit',async e=>{
  e.preventDefault();const form=e.target;const data=Object.fromEntries(new FormData(form));
  if(form.id==='inlineNote'){
    const id=selected;const refs=[];for(const file of form.elements.reference.files)refs.push(await uploadFile(file));
    await commit('图层意见 · '+object().name,[{action:'comment',target:id,refs,message:data.message.trim()}]);
    layerDrafts.delete(id);props();return;
  }
  if(form.id==='conceptForm'){openBrief(true);return}
  if(form.id==='values'){
    const o=object(),changes={},nums=new Set(['x','y','w','h','angle','opacity']);
    for(const [k,val] of Object.entries(data)){
      if(k==='tint')continue;
      const field=form.elements[k];
      if(field?.dataset?.orig!==undefined&&val===field.dataset.orig)continue;
      const value=nums.has(k)||typeof o[k]==='number'?Number(val):val;
      const prev=k==='opacity'?(o.opacity??1):k==='blend'?(o.blend||'normal'):o[k];
      if(value!==prev)changes[k]=value;
    }
    if(Object.keys(changes).length)await edit(changes,'调整 · '+o.name);
  }
  if(form.id==='repeat')await commit('绕中心旋转复制',[{action:'repeat',id:selected,pivot:[data.cx,data.cy],degrees:data.degrees,count:data.count}]);
  if(form.id==='process')await commit('修改工艺配置',[{action:'process',...data}]);
});

document.addEventListener('change',async e=>{
  const t=e.target,o=object();
  if(t.name==='tint'){
    await edit({gradientMap:{enabled:true,strength:1,stops:[{offset:0,color:'#000000'},{offset:1,color:t.value}]}},'图像调色 · '+o.name);return;
  }
  if(t.name==='fill'&&t.closest('#values')){
    const values={fill:t.value};if(o.gradientMap?.enabled)values.gradientMap=null;
    await edit(values,'改色 · '+o.name);return;
  }
  if(t.id==='loadRecipe'&&t.files.length){
    const recipe=JSON.parse(await t.files[0].text());
    if(recipe.schema!=='cover-material/1'||!recipe.effects)throw Error('请选择素材配方 JSON');
    const {gradientMap,organic,blend,opacity}=recipe.effects;
    await edit({gradientMap,mask:{...o.mask,organic},blend,opacity},'套用素材配方 · '+o.name);
    return
  }
  if(t.name==='blend'&&t.closest('#values')){await edit({blend:t.value},'切换混合模式 · '+o.name);return}
  if(t.id==='italic')await edit({italic:t.checked},'调整字形');
  if(t.dataset.lock)await commit('更新对象锁',[{action:'lock',id:selected,locks:[...document.querySelectorAll('[data-lock]:checked')].map(n=>n.dataset.lock)}]);
  if(t.id==='uv')await edit({uv:t.checked},'分配工艺 · '+o.name);
  if(t.id==='cut')await mask({cut:t.value},'调整轮廓遮挡 · '+o.name);
  if(t.id==='file'&&t.files.length){
    const f=t.files[0],r=await fetch(scoped('/asset'),{method:'POST',body:f});const a=await r.json();if(!r.ok)throw Error(a.error);
    const source=f.name;
    const newMask={...o.mask};delete newMask.outline;
    await edit({kind:'image',asset:a.asset,source,mask:newMask},'原位替换 · '+o.name);
  }
  // Gradient Map controls
  if(['gmEnabled','gmInvert','gmStrength'].includes(t.id)||t.dataset.gmColor!==undefined||t.dataset.gmOffset!==undefined){
    const gm=readGradientMapForm();
    await edit({gradientMap:gm},(gm.enabled?'渐变映射 · ':'关闭渐变映射 · ')+o.name);
  }
  // Organic Edge + Metallic Rim controls
  if(['orgEnabled','orgScale','orgFreq','orgOctaves','orgInset','orgFeather','orgSeed','orgRimEnabled','orgRimColor','orgRimWidth','orgRimOpacity','orgRimShimmer'].includes(t.id)){
    const organic=readOrganicForm();
    await mask({organic},(organic.enabled?'有机边缘 · ':'关闭有机边缘 · ')+o.name);
  }
  // Text Line Knockout controls
  if(['koEnabled','koPad','koFeather','koScope'].includes(t.id)){
    const knockout=readKnockoutForm();
    await mask({knockout},(knockout.enabled?'文字底层避让 · ':'关闭文字避让 · ')+o.name);
  }
  // Global Texture controls
  if(['texEnabled','texKind','texBlend','texOpacity','texScale','texContrast'].includes(t.id)){
    const tex=readTextureForm();
    await setTexture(tex,tex.enabled?'调整全局质感层':'关闭全局质感层');
  }
  if(t.id==='texFile'&&t.files.length){
    const asset=await uploadFile(t.files[0]);
    const tex={...readTextureForm(),enabled:true,kind:'asset',asset};
    await setTexture(tex,'载入自定义全局纸纹');
  }
});

document.addEventListener('click',async e=>{
  const b=e.target.closest('button');if(!b)return;
  const d=b.dataset,a=d.act,o=object();
  if(a==='saveRecipe'&&o){
    const recipe={schema:'cover-material/1',effects:{gradientMap:gmConfig(o),organic:orgConfig(o),blend:o.blend||'normal',opacity:o.opacity??1}};
    const url=URL.createObjectURL(new Blob([JSON.stringify(recipe,null,2)],{type:'application/json'}));
    const link=document.createElement('a');link.href=url;link.download=o.name+'-配方.json';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
  }
  if(d.mode){view=d.mode;tool='';await draw()}
  if(d.layer){selected=d.layer;tool='';points=[];await draw()}
  if(d.rev){tool='';await load(Number(d.rev))}
  if(d.layout||b.id==='useLayout'){const layout=d.layout||$('layouts').value;await commit('采用构图 · '+layout,[{action:'layout',layout}])}
  if(b.id==='shuffle')await commit('随机三版构图',[{action:'choices'}]);
  if(b.id==='recommend')await commit('按概念推荐构图',[{action:'choices',recommend:true}]);
  if(b.id==='add'){$('elementDialog').showModal();refreshDraft()}
  if(a==='stageAsset'){
    const f=$('elementFile').files[0];if(!f)throw Error('请先选择素材图片');
    const key=await uploadFile(f),name=$('elementName').value.trim()||f.name;
    await commit('素材待评 · '+name,[{action:'comment',target:'',purpose:'合成前素材',refs:[key],message:name+'\n'+($('draftNote').value.trim()||'请先审阅素材效果。')}]);
    $('elementDialog').close();$('elementForm').reset();refreshDraft();return;
  }
  if(d.compose){
    const note=record.state.discussion.find(n=>n.id===d.compose&&n.status==='待处理');
    if(!note)throw Error('素材状态已更新');
    const key=note.refs[0],res=await fetch(scoped('/assets/'+encodeURIComponent(key)));
    if(!res.ok)throw Error('素材读取失败');
    const bitmap=await createImageBitmap(await res.blob());const h=55*bitmap.height/bitmap.width;bitmap.close();
    await commit('加入已审素材',[{action:'add',kind:'image',name:note.message.split('\n')[0],values:{asset:key,w:55,h,source:'待评素材 '+note.id}},{action:'reply',note:note.id,status:'已处理',reply:'已加入画布'}]);
    selected=record.state.objects.at(-1).id;await draw();return;
  }
  if(a==='undoDesign'){
    const res=await api('/undo',{base:head.rev});await load(res.rev);msg('已撤销上一次画面修改');return;
  }
  if(d.withdraw){await commit('撤回图层意见',[{action:'withdraw',note:d.withdraw}]);return}
  if(a==='handoff'){
    const res=await fetch(scoped('/brand/handoff'));if(!res.ok)throw Error('交接单读取失败');
    await navigator.clipboard.writeText(await res.text());msg('已复制交接单，可粘贴到当前 Agent 对话');return;
  }
  if(a==='compare'){
    const parent=historyRows.find(r=>r.rev===record.rev).parent;
    $('compare').querySelector('.pair').innerHTML=[parent,record.rev].map(v=>'<div>版本 '+v+'<img src="'+preview(v)+'"></div>').join('');$('compare').showModal();
  }
  if(b.id==='closeDialog')$('compare').close();
  if(a==='latest')await load();
  if(a==='restore')await commit('从 v'+record.rev+' 继续',[]);
  if(a==='up'||a==='down')await commit('调整叠放顺序',[{action:'order',id:selected,by:a==='up'?1:-1}]);
  if(a==='fade')await mask({fade:!o.mask.fade},'调整渐变蒙版');
  if(a==='crop'){
    const val=prompt('左、上、宽、高（对象的百分比）',(o.mask.crop||[0,0,100,100]).join(','));if(val!==null)await mask({crop:val.split(',').map(Number)},'裁切 · '+o.name);
  }
  if(['erase','paint','move','sam'].includes(a)){tool=a==='move'?'':a;points=[];outlineSelection();msg(a==='sam'?'在图片上左键选入、右键排除，然后计算选区':tool?'在画布上拖动画笔，松开保存':'可拖动画布元素')}
  if(a==='segment'){
    if(!points.length)throw Error('请先在图片上点选');msg('正在本机提取轮廓…');
    const outline=await api('/segment',{asset:o.asset,points:points.map(p=>[...p.xy,p.label])});
    await mask(outline,'SAM2 点选轮廓');view='mask';await draw();msg('可继续用画笔修边，或回看上一步')
  }
  // Gradient Map presets & stop count
  if(d.gmPreset!==undefined&&o){
    const p=GM_PRESETS[Number(d.gmPreset)];
    const gm={...gmConfig(o),enabled:true,stops:p.stops.map(s=>({...s}))};
    await edit({gradientMap:gm},'渐变映射 · '+p.name);
  }
  if(d.gmCount&&o){
    const count=Number(d.gmCount),cur=gmConfig(o);
    const stops=count===2?[cur.stops[0],cur.stops.at(-1)]:cur.stops.length===3?cur.stops:[cur.stops[0],{offset:0.52,color:'#1d4ed8'},cur.stops.at(-1)];
    await edit({gradientMap:{...cur,enabled:true,stops}},'切换为 '+count+' 色渐变映射');
  }
  // Organic Edge presets, seed randomize & metallic rim swatches
  if(d.orgPreset&&o){
    const preset=ORG_PRESETS[d.orgPreset];
    const organic={...orgConfig(o),...preset};
    await mask({organic},'有机边缘预设 · '+b.textContent.trim());
  }
  if(a==='orgSeed'&&o){
    const organic={...readOrganicForm(),enabled:true,seed:Math.floor(Math.random()*999)+1};
    await mask({organic},'更换有机边缘形态 · '+o.name);
  }
  if(d.rimColor&&o){
    const organic={...readOrganicForm(),enabled:true,rimEnabled:true,rimColor:d.rimColor};
    await mask({organic},'切换边缘金属色 · '+o.name);
  }
  if(b.id==='export'){const r=await api('/export',{rev:record.rev});delivery(r.package);msg('已生成 v'+record.rev+' 交接稿')}
});

window.addEventListener('unhandledrejection',e=>{msg(e.reason?.message||String(e.reason));e.preventDefault()});

let briefMode='note',noteTarget='';
function openBrief(isNew,target=''){
  briefMode=isNew?'new':'note';noteTarget=target;
  $('briefForm').reset();$('briefName').value=$('concept').value;
  $('nameLine').hidden=!isNew;
  $('briefHeading').textContent=isNew?'从设计对话开始':target?'修改 · '+object().name:'修改 · 整张封面';
  $('briefDialog').showModal();$('message').focus();
}
let draftUrl='';
function refreshDraft(){
  const show=Boolean(edition)&&$('elementKind').value==='image';
  $('assetDraft').hidden=!show;
  if(draftUrl){URL.revokeObjectURL(draftUrl);draftUrl=''}
  const file=$('elementFile').files[0],img=$('draftPreview');
  img.hidden=!show||!file;
  if(show&&file){draftUrl=URL.createObjectURL(file);img.src=draftUrl}
}
$('elementKind').addEventListener('change',refreshDraft);
$('elementFile').addEventListener('change',refreshDraft);
$('elementDialog').addEventListener('close',()=>{if(draftUrl){URL.revokeObjectURL(draftUrl);draftUrl=''}});
async function uploadFile(f){
  const r=await fetch(scoped('/asset'),{method:'POST',body:f});const data=await r.json();
  if(!r.ok)throw Error(data.error);return data.asset;
}
function discussion(){
  const notes=record.state.discussion||[];
  $('notes').innerHTML=notes.slice().reverse().map(n=>'<article><small>'+safe(n.targetName)+' · '+safe(n.status)+'</small><p>'+safe(n.message)+'</p>'+
     (n.refs||[]).map(f=>'<a target="_blank" href="/assets/'+safe(f)+(edition?'?edition='+encodeURIComponent(edition):'')+'"><img alt="'+safe(n.purpose)+'" src="/assets/'+safe(f)+(edition?'?edition='+encodeURIComponent(edition):'')+'"></a>').join('')+
     (n.reply?'<p>'+safe(n.reply)+'</p>':'')+
     (n.status==='待处理'&&record.rev===head.rev?'<button type="button" data-run="'+safe(n.id)+'">交给本机 Agent</button>':'')+'</article>').join('');
}
document.addEventListener('click',async e=>{
 const b=e.target.closest('button');if(!b)return;
 if(b.hasAttribute('data-dismiss'))b.closest('dialog').close();
 if(b.id==='remove'&&object())await commit('删除 · '+object().name,[{action:'remove',id:selected}]);
 if(b.id==='layerNote'&&object())openBrief(false,selected);
 if(b.id==='discuss')openBrief(false);
 if(b.dataset.run){
   b.disabled=true;
   try{await api('/dispatch',{base:head.rev,note:b.dataset.run});await load();msg('Agent 已开始处理，可继续查看画布')}
   catch(err){b.disabled=false;msg(err.message)}
 }
});
document.addEventListener('contextmenu',e=>{
 const layer=e.target.closest('[data-layer]');
 if(layer){e.preventDefault();selected=layer.dataset.layer;draw().then(()=>edition?document.querySelector('#inlineNote textarea')?.focus():openBrief(false,selected))}
});
document.addEventListener('submit',async e=>{
 const form=e.target;
 if(!['briefForm','elementForm'].includes(form.id))return;
 e.preventDefault();const submit=form.querySelector('button:not([type=button])');submit.disabled=true;
 try{
 if(form.id==='briefForm'){
   const refs=[];for(const f of $('references').files)refs.push(await uploadFile(f));
   const brief={message:$('message').value.trim(),refs,purpose:$('purpose').value,target:noteTarget};
   if(briefMode==='new'){const result=await api('/new',{base:head.rev,concept:$('briefName').value.trim(),brief});await load(result.rev)}
   else await commit('提交意见 · '+(noteTarget?object().name:'整张封面'),[{action:'comment',...brief}]);
   $('briefDialog').close();msg('设计说明已保存，打开对话记录可交给本机 Agent。');
 }else{
   const kind=$('elementKind').value,name=$('elementName').value.trim();
   const values=kind==='text'?{text:name,font:'Garamond',w:50,h:9}:{};
   if(kind==='image'){
     const f=$('elementFile').files[0];if(!f)throw Error('请选择图片文件');
     values.asset=await uploadFile(f);values.source=f.name;
     const bitmap=await createImageBitmap(f);values.w=55;values.h=55*bitmap.height/bitmap.width;bitmap.close();
   }
   await commit('添加 · '+name,[{action:'add',kind,name,values}]);
   selected=record.state.objects.at(-1).id;await draw();form.reset();$('elementDialog').close();
 }
 }finally{submit.disabled=false}
});
(async()=>{layouts=await api('/layouts');await load();const packages=await api('/packages');if(packages.length)delivery(packages[0]);setInterval(async()=>{
  if(busy||gesture||tool||document.activeElement?.matches('input,select,textarea')||document.querySelector('dialog[open]')||record.rev!==head.rev)return;
  const r=await api('/state');if(r.rev!==head.rev){await load();msg('已显示 Agent 的最新修改')}
},2500)})();
