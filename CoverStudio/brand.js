const $=id=>document.getElementById(id),esc=v=>String(v??'').replace(/[<>&"']/g,c=>({'<':'&lt;','>':'&gt;','&':'&amp;','"':'&quot;',"'":'&#39;'}[c]));
const sku=new URLSearchParams(location.search).get('sku')||'';
function link(path){return path+(path.includes('?')?'&':'?')+'sku='+encodeURIComponent(sku)}
async function api(path,body){const r=await fetch(link(path),body?{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}:{});const data=await r.json();if(!r.ok)throw Error(data.error||r.statusText);return data}
const stages=['产品拆解','封面设计','封面工艺与用纸','内页设计','贴纸与索引','内页工艺与用纸'];
let page=decodeURIComponent(location.hash.slice(1)),rec,f,focusRoute,submit;
if(!stages.includes(page))page=location.pathname==='/covers'?'封面设计':stages[0];
async function load(){rec=await api('/state');f=rec.state.workflow;draw()}
async function change(label,op){try{rec=await api('/change',{base:rec.rev,label,ops:[op]});f=rec.state.workflow;draw();$('status').textContent='已保存 · '+label}catch(e){await load();throw e}}
function dialog(title,fields,callback){$('dialogTitle').textContent=title;$('fields').innerHTML=fields;$('modal').showModal();submit=callback}
const area=(key,label,val='',required=true)=>'<label>'+esc(label)+'<textarea name="'+key+'" '+(required?'required':'')+'>'+esc(val)+'</textarea></label>';
const field=(key,label,val='')=>'<label>'+esc(label)+'<input required name="'+key+'" value="'+esc(val)+'"></label>';
const button=(cmd,label)=>'<button data-cmd="'+cmd+'">'+esc(label)+'</button>';
function move(next){page=next;location.hash=next;draw()}
function tasks(list){return list.map(t=>'<div class="item"><span class="badge">'+esc(t.status)+'</span><div><b>'+esc(t.name)+'</b><small>'+esc(t.output)+'</small><small>下一步 · '+esc(t.next)+'</small>'+
(t.depends.length?'<small>依赖 · '+t.depends.map(k=>esc(f.items.find(i=>i.id===k)?.name||k)).join('、')+'</small>':'')+(t.evidence?'<small>记录 · '+esc(t.evidence)+'</small>':'')+'</div>'+button('task:'+t.id,'更新')+'</div>').join('')}
function overview(){return '<div class="bar"><h2>产品工作流与交付清单</h2>'+button('add','＋ 添加交付物')+'</div><div class="buttons">'+button('design','审阅封面视觉提案 →')+'</div>'+
'<details><summary>产品理念与设计说明书</summary><div class="brief">'+esc(f.brief)+'</div></details>'+
stages.map((s,i)=>{const list=f.items.filter(t=>t.stage===s);return '<details '+(i<2?'open':'')+'><summary>'+s+' · '+list.filter(t=>t.status==='已完成').length+' / '+list.length+'</summary>'+tasks(list)+'</details>'}).join('')}
function designs(){
 const r=f.routes.find(x=>x.id===focusRoute)||f.routes.find(x=>x.id===f.choice)||f.routes[0];focusRoute=r?.id;
 let html='<div class="panel"><div class="bar"><h2>视觉稿</h2>'+button('visual','修改视觉稿')+'</div><p>'+esc(f.visual||'待根据产品理念撰写视觉稿。')+'</p></div>';
 if(r){html+='<h2>全书封排版方案</h2><div class="cards">'+f.routes.map(x=>'<button data-cmd="view:'+esc(x.id)+'" class="route '+(x===r?'active':'')+'"><img alt="展开结构草图" src="/brand/diagram?route='+encodeURIComponent(x.id)+'"><b>'+esc(x.title)+'</b><small> · '+(x.id===f.choice?'已选':'查看')+'</small></button>').join('')+'</div><div class="panel"><h2>'+esc(r.title)+'</h2><p>'+esc(r.intent)+'</p><div class="caps"><span>封底</span><span>书脊</span><span>前封</span></div><img class="board" alt="完整外封结构示意" src="/brand/diagram?route='+encodeURIComponent(r.id)+'"><small>结构示意 · 书脊暂以示意宽度展示，待内页纸张、页数及装订样确定。</small><div class="detailgrid">'+[['元素与遮挡',r.elements],['前封',r.front],['书脊',r.spine],['封底',r.back],['候选工艺',r.craft]].map(([k,v])=>'<p><b>'+k+'</b><br>'+esc(v)+'</p>').join('')+'</div><div class="buttons">'+button('note','给这个方案提意见')+(f.choice!==r.id?button('choose','选中此方案'):(f.approved?'<b>当前方案已确认</b>':'<button class="primary" data-cmd="approve">确认视觉方案，允许生图</button>'))+'</div></div>'}
 if(f.feedback.length)html+='<h2>修改意见</h2>'+f.feedback.map(n=>'<p>'+esc(f.routes.find(r=>r.id===n.route)?.title||'全案')+' · '+esc(n.message)+'</p>').join('');
 if(f.approved){
   const production=rec.state.discussion?.slice().reverse().find(n=>n.message.startsWith('制作请求 · '+f.choice+' · '));
   html+='<div class="panel"><h3>已确认方向的素材制作</h3>'+button('production','把当前方案交给制作 Agent')+(production?'<p>'+esc(production.status)+' · '+esc(production.reply||production.message)+'</p>':'')+'</div>';
 }
 html+='<a href="'+link('/editor')+'">打开此 SKU 的前封图层稿 ↗</a>';
 if(!sku)html='<h2>完整外封 · 审阅稿</h2>'+[['orbit','回望之弧'],['echo','回声地形']].map(([id,title])=>'<section class="panel"><h3>'+title+'</h3><div class="compare-layout"><figure><figcaption>原始排版方案</figcaption><img class="board" alt="原始结构" src="/brand/diagram?route='+id+'"></figure><figure><figcaption>当前材质稿</figcaption><a href="/review?edition='+id+'"><img class="board" alt="'+title+'材质稿" src="/preview?edition='+id+'"></a></figure></div><p>封底　／　书脊（暂定 12 mm）　／　前封</p><a href="/review?edition='+id+'">点选封面，留下修改意见 →</a></section>').join('')+html;
 return html
}
function draw(){
 const done=f.items.filter(i=>i.status==='已完成').length;
 $('sectionName').textContent='INKA+   /   '+page;$('product').textContent=f.name;
 $('headline').innerHTML='<div class="stats"><span><b>'+f.items.length+'</b> 项交付</span><span><b>'+done+'</b> 已完成</span><span><b>'+(f.items.length-done)+'</b> 剩余</span><span>v'+rec.rev+'</span></div>';
 $('nav').innerHTML=stages.map(s=>'<button data-stage="'+s+'" class="'+(s===page?'on':'')+'">'+s+'</button>').join('');
 $('handoff').href=link('/brand/handoff');
 if(page==='产品拆解')$('content').innerHTML=overview();
 else if(page==='封面设计')$('content').innerHTML=designs();
 else $('content').innerHTML='<div class="panel"><div class="bar"><h2>'+page+' · 阶段记录</h2>'+button('stage','填写阶段记录')+'</div><p>'+esc(f.stageNotes[page]||'等待设计与验证，可先记录参考纸样、供应商约束和交接条件。')+'</p>'+tasks(f.items.filter(t=>t.stage===page))+'</div>';
 if(page==='封面工艺与用纸'){
   const params=new URLSearchParams(location.search),id=params.get('delivery'),edition=params.get('jacket');
   if(/^v[0-9]+-[a-f0-9]+$/.test(id||'')&&['','orbit','echo'].includes(edition)){
     const href='/package?'+new URLSearchParams({id,...(edition?{edition}:{})});
     $('content').insertAdjacentHTML('afterbegin','<div class="panel"><h2>本次封面交接</h2><a download href="'+esc(href)+'">下载 '+esc(id.split('-')[0])+' 分层稿与工艺版</a><p>核对版名与套位后，在下方登记纸张、设备或打样结果。</p></div>');
   }
 }

}
$('cancel').onclick=()=>$('modal').close();
$('form').onsubmit=async e=>{e.preventDefault();const b=e.submitter;b.disabled=true;try{await submit(Object.fromEntries(new FormData(e.target)));$('modal').close()}catch(err){alert(err.message)}finally{b.disabled=false}};
$('create').onclick=()=>dialog('新建品牌 SKU',field('name','产品名称')+area('brief','产品理念与组成'),async d=>{const r=await api('/brand/new',d);location.assign(link('/').split('?')[0]+'?sku='+r.sku)});
$('catalog').onchange=e=>location.assign('/?sku='+encodeURIComponent(e.target.value));
document.onclick=async e=>{let b=e.target.closest('button');if(!b)return;
 if(b.dataset.stage){move(b.dataset.stage);return}
 const [cmd,key]=(b.dataset.cmd||'').split(':');
 if(cmd==='production'){
   b.disabled=true;
   try{
    await change('提交已确认方案的素材任务',{action:'comment',message:'制作请求 · '+f.choice+' · 先读本 SKU 的 workflow 和已确认视觉稿。按其元素与遮挡说明制作独立可编辑素材，分别说明前封、书脊、封底的使用位置。实际脊宽未确认，勿输出生产展开稿。'});
    const n=rec.state.discussion.at(-1);await api('/dispatch',{base:rec.rev,note:n.id});await load()
   }finally{b.disabled=false}
 }
 if(cmd==='design')move('封面设计');
 if(cmd==='view'){focusRoute=key;draw()}
 if(cmd==='choose'||cmd==='approve')await change(cmd==='choose'?'选择排版方向':'用户确认视觉方案',{action:cmd==='choose'?'plan_choose':'plan_approve',route:focusRoute});
 if(cmd==='note')dialog('修改意见',area('message','希望调整哪里？'),d=>change('记录视觉反馈',{action:'plan_note',route:focusRoute,...d}));
 if(cmd==='visual')dialog('编辑视觉稿',area('visual','设计叙事与层次',f.visual),d=>change('更新视觉稿，重新审阅',{action:'plan_edit',...d}));
 if(cmd==='stage')dialog(page,area('message','参考、判断与待测事项',f.stageNotes[page]||'',false),d=>change('更新阶段记录',{action:'stage_note',stage:page,...d}));
 if(cmd==='add')dialog('新增交付物',field('name','名称')+field('output','可验收的产物')+'<label>阶段<select name="stage">'+stages.map(s=>'<option>'+s+'</option>').join('')+'</select></label><label>依赖<select multiple name="deps">'+f.items.map(t=>'<option value="'+esc(t.id)+'">'+esc(t.name)+'</option>').join('')+'</select></label>',d=>change('增加产品交付物',{action:'item_add',...d,depends:[...$('form').elements.deps.selectedOptions].map(o=>o.value)}));
 if(cmd==='task'){const t=f.items.find(x=>x.id===key);dialog(t.name,'<label>进度<select name="status">'+['待设计','进行中','待确认','已完成'].map(s=>'<option '+(s===t.status?'selected':'')+'>'+s+'</option>').join('')+'</select></label>'+area('next','下一动作',t.next,false)+area('evidence','交付位置 / 确认依据',t.evidence,false),d=>change('更新 · '+t.name,{action:'item_update',id:key,...d}))}
};
window.onhashchange=()=>{if(!f){location.reload();return}page=decodeURIComponent(location.hash.slice(1));if(!stages.includes(page))page=location.pathname==='/covers'?'封面设计':stages[0];draw()};
window.onunhandledrejection=e=>{$('status').textContent=e.reason.message};
(async()=>{const catalog=await api('/brand/catalog');
 if(location.pathname==='/'&&!new URLSearchParams(location.search).has('sku')&&!location.hash){
   document.querySelector('.shell > aside').hidden=true;
   document.querySelector('.shell').style.display='block';
   $('sectionName').textContent='INKA+';$('product').textContent='SKU 项目';
   $('content').innerHTML=catalog.map(x=>'<a class="panel" style="display:block" href="/?sku='+encodeURIComponent(x.id)+'">'+esc(x.name)+'</a>').join('');
   return;
 }
 $('catalog').innerHTML=catalog.map(x=>'<option value="'+esc(x.id)+'">'+esc(x.name)+'</option>').join('');$('catalog').value=sku;await load()})();

