"""Cover Studio. Python 3.10+; the core uses the standard library."""
import argparse
import base64
import hashlib
import json
import math
import os
import random
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import urllib.parse
import webbrowser
import zipfile
import io
from contextlib import closing
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from design import initial, apply, LAYOUTS, uid
from render import render

ROOT=Path(__file__).resolve().parent
DEFAULT=ROOT/'projects'/'wish'
def dump(data):return json.dumps(data,ensure_ascii=False,allow_nan=False)
class Conflict(ValueError):pass

class Project:
    def __init__(self,folder):
        self.dir=Path(folder).resolve()
    def db(self):
        if not (self.dir/'project.sqlite').exists(): raise ValueError('请先创建工程')
        return sqlite3.connect(self.dir/'project.sqlite',timeout=10)
    def init(self,concept,p=None):
        self.dir.mkdir(parents=True,exist_ok=True)
        (self.dir/'assets').mkdir(exist_ok=True)
        state=initial(concept,p)
        with closing(sqlite3.connect(self.dir/'project.sqlite')) as db,db:
            db.execute('create table if not exists versions(id integer primary key,parent integer,label text,state text,created text default current_timestamp)')
            db.execute('begin immediate')
            if db.execute('select 1 from versions limit 1').fetchone():raise ValueError('工程已存在')
            db.execute('insert into versions(parent,label,state) values(null,?,?)',('建立封面 · '+concept,dump(state)))
    def read(self,rev=None):
        with closing(self.db()) as db:
            row=db.execute('select id,state from versions where id=?',(rev,)).fetchone() if rev else db.execute('select id,state from versions order by id desc limit 1').fetchone()
        if not row:raise ValueError('版本不存在')
        return dict(rev=row[0],state=json.loads(row[1]))
    def history(self):
        with closing(self.db()) as db:return [dict(rev=i,parent=p,label=l) for i,p,l in db.execute('select id,parent,label from versions order by id desc')]
    def change(self,req):
        with closing(self.db()) as db,db:
            db.execute('begin immediate')
            latest,raw=db.execute('select id,state from versions order by id desc limit 1').fetchone()
            if req['base']!=latest:raise Conflict('工程已被更新，请重新查看后再改')
            live=json.loads(raw)
            latest_flow=live.get('workflow')
            parent=req.get('from',latest)
            if parent!=latest:
                row=db.execute('select state from versions where id=?',(parent,)).fetchone()
                if not row:raise ValueError('历史版本不存在')
                raw=row[0]
            s=json.loads(raw)
            if parent!=latest:
                s['discussion']=live.get('discussion',[])
                if latest_flow:s['workflow']=latest_flow
            for op in req['ops']:
                asset=op.get('values',{}).get('asset') if isinstance(op.get('values'),dict) else None
                if not asset and op.get('action')=='texture':
                    asset=op.get('asset')
                if asset and (not re.fullmatch(r'[a-f0-9]{64}\.(png|jpg|webp)',asset) or not (self.dir/'assets'/asset).is_file()):raise ValueError('请先导入素材')
                apply(s,op)
            render(s,self.dir)
            cur=db.execute('insert into versions(parent,label,state) values(?,?,?)',(parent,req['label'],dump(s)))
            return dict(rev=cur.lastrowid,state=s)
    def undo_design(self,base):
        """Undo the latest design step while retaining current collaboration records."""
        with closing(self.db()) as db,db:
            db.execute('begin immediate')
            rev,parent,raw=db.execute('select id,parent,state from versions order by id desc limit 1').fetchone()
            if rev!=base:raise Conflict('工程已更新，请刷新后重试')
            current=json.loads(raw)
            fields=('objects','texture','process','layout','choices','materialFocus','concept','product','generatedSource')
            while parent:
                prior=parent
                parent,raw=db.execute('select parent,state from versions where id=?',(prior,)).fetchone()
                previous=json.loads(raw)
                if any(current.get(k)!=previous.get(k) for k in fields):
                    for k in fields:
                        if k in previous:current[k]=previous[k]
                        else:current.pop(k,None)
                    row=db.execute('insert into versions(parent,label,state) values(?,?,?)',(prior,'撤销画面修改 · 回到 v'+str(prior),dump(current)))
                    return dict(rev=row.lastrowid)
            raise ValueError('已经是最早的设计状态')

    def brief(self):
        from inventory import handoff
        r=self.read()
        s=r['state']
        lines=[handoff(r) if 'workflow' in s else s['concept'],f"工程 {self.dir} · v{r['rev']}",
               f"使用 {ROOT/'studio.py'} --project {self.dir} 的 state / apply，提交前重读当前版本与锁。",
               f"续作规范 {ROOT/'skill'/'cover-studio'/'SKILL.md'}"]
        for n in s.get('discussion',[]):
            if n['status'] in ('待处理','处理中'):
                lines.append(f"{n['id']} [{n['status']}] {n['targetName']} ({n['target']}) · {n['message']}")
                lines.extend(str(self.dir/'assets'/key) for key in n.get('refs',[]))
        if 'workflow' in s:
            for db in sorted((self.dir/'jackets').glob('*/project.sqlite')):
                lines.append(Project(db.parent).brief())
        return '\n'.join(lines)

    def asset(self,data):
        if data.startswith(b'\x89PNG\r\n\x1a\n'):ext='png'
        elif data.startswith(b'\xff\xd8\xff'):ext='jpg'
        elif data[:4]==b'RIFF' and data[8:12]==b'WEBP':ext='webp'
        else:raise ValueError('支持 PNG、JPEG、WebP')
        key=hashlib.sha256(data).hexdigest()+'.'+ext
        dest=self.dir/'assets'/key
        if not dest.exists():
            with tempfile.NamedTemporaryFile(dir=dest.parent,delete=False) as f:f.write(data)
            os.replace(f.name,dest)
        return key
    def export(self,rev=None):
        record=self.read(rev); s=record['state']
        out=self.dir/'exports';out.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=out) as tmp:
            stage=Path(tmp)/'package';stage.mkdir()
            has_deboss=any(o.get('deboss') for o in s['objects'])
            modes=[('print','ART'),('plate','UV'),('overlay','UV-preview')]
            has_foil=any(o.get('foil') for o in s['objects'])
            if has_deboss:modes.append(('deboss','DEBOSS'))
            if has_foil:modes.append(('foil','FOIL'))
            if has_deboss or has_foil:modes.append(('art','material-preview'))
            for mode,name in modes:
                (stage/(name+'.svg')).write_text(render(s,self.dir,mode,True),encoding='utf8')
            tex=s.get('texture') or {}
            compositing=dict(
                globalTexture=tex if tex.get('enabled') else None,
                gradientMaps=[o['name'] for o in s['objects'] if o.get('gradientMap',{}).get('enabled')],
                organicMasks=[o['name'] for o in s['objects'] if o.get('mask',{}).get('organic',{}).get('enabled')],
                textKnockouts=[o['name'] for o in s['objects'] if o.get('mask',{}).get('knockout',{}).get('enabled')],
            )
            note=dict(version=record['rev'],concept=s['concept'],product=s['product'],process=s['process'],
                      foilObjects=[o['name'] for o in s['objects'] if o.get('foil')],uvObjects=[o['name'] for o in s['objects'] if o['uv']],compositing=compositing,
                      status='工艺候选，实机待打样')
            (stage/'job.json').write_text(dump(note),encoding='utf8')
            import xml.etree.ElementTree as ET
            mapping=ET.Element('handoff',{'plate':s['process']['plate'],'format':s['process']['format']})
            for o in s['objects']:ET.SubElement(mapping,'object',{'id':'o-'+o['id'],'name':o['name']})
            if tex.get('enabled'):ET.SubElement(mapping,'object',{'id':'global-texture','name':'全局质感层'})
            ET.ElementTree(mapping).write(stage/'layers.xml',encoding='utf-8',xml_declaration=True)
            (stage/'交接说明.txt').write_text('ART.svg 为分组彩稿，UV.svg 为同原点黑版，透明区留空。UV-preview.svg 中青色为覆盖提示。\n版名：'+s['process']['plate']+'。设备：'+(s['process']['machine'] or '待印厂指定')+'。\n尺寸以 job.json 的毫米参数为准。文字保留活字，交接时核对字体。透明渐变、SVG 合成滤镜（渐变映射/有机边缘/全局纸纹）和软边须由接单方确定是否栅格化或转实地。运行 Illustrator.jsx 另存 AI 并回读。',encoding='utf-8-sig')
            if tex.get('enabled'):
                with (stage/'交接说明.txt').open('a',encoding='utf8') as instructions:
                    instructions.write(f'\n全局质感层已合成至 ART.svg 顶层（类型：{tex.get("kind","paper")}，混合：{tex.get("blend","multiply")}，不透明度：{round(float(tex.get("opacity",0.16))*100)}%）。')
            if has_deboss:
                with (stage/'交接说明.txt').open('a',encoding='utf8') as instructions:
                    instructions.write('\nDEBOSS.svg 为同原点无墨压凹候选版。material-preview.svg 含纸纹与模拟压痕。压凹字形请与接单方核对后转曲并试压。')
            if has_foil:
                with (stage/'交接说明.txt').open('a',encoding='utf8') as instructions:
                    instructions.write('\nFOIL.svg 为同原点局部描金候选黑版。预览金色仅示意，箔色、线宽、套准与纸张须按印厂打样确认。')
            shutil.copy(ROOT/'Illustrator.jsx',stage)
            dest=out/('v'+str(record['rev'])+'-'+uid())
            stage.rename(dest)
        return dest
    def segment(self,key,points):
        if not re.fullmatch(r'[a-f0-9]{64}\.(png|jpg|webp)',key):raise ValueError('无效素材')
        sam=Path(os.environ.get('COVER_SAM_HOME',str(ROOT.parent/'INKA_品牌工作流/设计稿转换/本地对象分割')))
        exe=sam/'.venv'/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
        if not exe.exists():raise ValueError('未找到 SAM2 环境，请设置 COVER_SAM_HOME')
        r=subprocess.run([str(exe),str(ROOT/'segment.py'),str(sam),str(self.dir/'assets'/key)],input=dump(points),encoding='utf8',capture_output=True,timeout=180)
        if r.returncode:raise ValueError('SAM2 未完成：'+r.stderr[-450:])
        return json.loads(r.stdout.strip().splitlines()[-1])

def dispatch_agent(project,base,note_id):
    import threading
    executable=shutil.which('codex')
    if not executable:raise ValueError('未找到 Codex CLI，其他 Agent 可通过 skill 读取并处理此意见')
    current=project.read()
    flow=current['state'].get('workflow')
    if flow and not flow['approved']:raise ValueError('当前 SKU 须先确认视觉方案才能启动制作 Agent')
    note=next((n for n in current['state'].get('discussion',[]) if n['id']==note_id),None)
    if not note or note['status']!='待处理':raise ValueError('该意见已处理或不存在')
    images=[]
    for key in note.get('refs',[]):
        if not re.fullmatch(r'[a-f0-9]{64}\.(png|jpg|webp)',key):raise ValueError('参考图无效')
        source=project.dir/'assets'/key
        if not source.is_file():raise ValueError('参考图不存在')
        images.extend(['-i',str(source)])
    project.change(dict(base=base,label='Agent 接单',ops=[dict(action='reply',note=note_id,reply='处理中',status='处理中')]))
    def work():
        prompt=(f'封面协作任务。仅操作当前工程 {project.dir}。读取 {ROOT}/skill/cover-studio/SKILL.md。'
                f'使用 {sys.executable} 和 {ROOT}/studio.py --project "{project.dir}" state / import / apply。'
                f'处理编号 {note_id} 的设计意见；附件仅为注明用途的参考。保留锁定对象，禁用米黄、纸黄底色。'
                '优先使用工作台内置像素合成管线：黑白材质 + gradientMap（渐变映射）、mask.organic（有机边缘与细金边）、mask.knockout（文字底层线条避让，勿垫纯白实心底块）及全局 texture 纸纹层。'
                '需要新图请使用可用图像工具，验证素材确实存在后导入。完成后用 reply 记录实际变更或具体缺口。')
        try:
            run=subprocess.run([executable,'exec','--skip-git-repo-check','--sandbox','workspace-write','-C',str(project.dir),*images,'-'],
                input=prompt,encoding='utf8',errors='replace',capture_output=True,timeout=900,
                creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            detail=(run.stderr.strip().splitlines() or ['执行未完成'])[-1][:220]
            result='Agent 已结束；可重试或补充说明。' if run.returncode==0 else '执行失败：'+detail
        except (OSError,subprocess.TimeoutExpired) as e:result='执行中断：'+str(e)[:220]
        for _ in range(4):
            r=project.read()
            item=next((n for n in r['state'].get('discussion',[]) if n['id']==note_id),None)
            if not item or item['status']!='处理中':return
            try:
                project.change(dict(base=r['rev'],label='Agent 返回',ops=[dict(action='reply',note=note_id,status='待处理',reply=result)]))
                return
            except Conflict:continue
    threading.Thread(target=work,daemon=True).start()
    return {'started':True}

def handler(root_project):
    class Handler(BaseHTTPRequestHandler):
        def reply(self,code,body,kind):
            self.send_response(code);self.send_header('Content-Type',kind);self.send_header('Content-Length',str(len(body)))
            self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');self.end_headers();self.wfile.write(body)
        def run(self,post):
            url=urllib.parse.urlsplit(self.path); path=url.path;q=dict(urllib.parse.parse_qsl(url.query))
            if self.headers.get('Host') not in (f'127.0.0.1:{self.server.server_port}',f'localhost:{self.server.server_port}'):raise ValueError('仅允许本机连接')
            project=root_project
            sku=q.get('sku','')
            if sku:
                if not re.fullmatch(r'[a-f0-9]{12}',sku):raise ValueError('无效 SKU')
                project=Project(root_project.dir.parent/sku)
                if not (project.dir/'project.sqlite').is_file():raise ValueError('SKU 不存在')
            edition=q.get('edition')
            if edition:
                if sku or edition not in ('orbit','echo'):raise ValueError('无效封面版本')
                project=Project(project.dir/'jackets'/edition)
            if path=='/covers':path='/'
            if post:
                origin=self.headers.get('Origin')
                if origin and origin!='http://'+self.headers['Host']:raise ValueError('来源不符')
                n=int(self.headers.get('Content-Length','0'))
                if n<0 or n>48*1024*1024:raise ValueError('文件过大')
                body=self.rfile.read(n)
                if path=='/asset':result={'asset':project.asset(body)}
                else:
                    req=json.loads(body)
                    if path=='/brand/new':
                        from proposals import workflow
                        name=req['name'].strip();brief=req['brief'].strip()
                        if not name or not brief:raise ValueError('填写产品名称与理念')
                        key=uid();other=Project(root_project.dir.parent/key);other.init(name)
                        with closing(other.db()) as db,db:
                            state=other.read()['state'];state['workflow']=workflow(name,brief)
                            db.execute('update versions set state=? where id=1',(dump(state),))
                        result={'sku':key}
                    elif path=='/material-preview':
                        state=project.read(req['rev'])['state']
                        item=next((o for o in state['objects'] if o['id']==req['id']),None)
                        if not item or item['kind']!='image':raise ValueError('请选择位图素材')
                        values=req.get('values',{})
                        if set(values)-{'mask','blend','gradientMap','opacity'}:raise ValueError('无效的预览参数')
                        if values:apply(state,dict(action='edit',id=item['id'],values=values))
                        import copy
                        sample=copy.deepcopy(item)
                        sample['x']=sample['w']/2;sample['y']=sample['h']/2;sample['angle']=0
                        sample['mask'].pop('cut',None)
                        state['product']=dict(width=sample['w'],height=sample['h'],bleed=0)
                        from design import obj
                        state['objects']=[obj('samplepaper','预览衬底','rect',sample['x'],sample['y'],sample['w'],sample['h'],'#b9c3cc'),sample]
                        state.pop('texture',None)
                        return self.reply(200,render(state,project.dir,'art',True).encode(),'image/svg+xml')
                    elif path=='/change':result=project.change(req)
                    elif path=='/undo':result=project.undo_design(req['base'])
                    elif path=='/dispatch':result=dispatch_agent(project,req['base'],req['note'])
                    elif path=='/segment':result=project.segment(req['asset'],req['points'])
                    elif path=='/export':
                        folder=project.export(req.get('rev'))
                        result={'folder':str(folder),'package':folder.name}
                    elif path=='/new':
                        concept=req['concept'].strip()
                        if not concept:raise ValueError('请输入概念')
                        # Explicit new concept as a version; existing designs stay in history.
                        with closing(project.db()) as db,db:
                            db.execute('begin immediate')
                            latest,raw=db.execute('select id,state from versions order by id desc limit 1').fetchone()
                            if req['base']!=latest:raise Conflict('工程已更新')
                            if json.loads(raw).get('workflow'):raise ValueError('请从品牌工作台新建 SKU')
                            s=initial(concept,json.loads(raw)['product'])
                            if req.get('brief'):
                                apply(s,{'action':'comment',**req['brief']})
                            cur=db.execute('insert into versions(parent,label,state) values(?,?,?)',(latest,'新概念 · '+concept,dump(s)))
                            result=dict(rev=cur.lastrowid,state=s)
                    else:raise ValueError('未知请求')
            elif path.startswith('/assets/') and re.fullmatch(r'/assets/[a-f0-9]{64}\.(png|jpg|webp)',path):
                import mimetypes
                return self.reply(200,(project.dir/path[1:]).read_bytes(),mimetypes.guess_type(path)[0])
            elif path=='/package':
                name=q.get('id','')
                if not re.fullmatch(r'v[0-9]+-[a-f0-9]+',name):raise ValueError('交接包编号无效')
                folder=project.dir/'exports'/name
                if not (folder/'job.json').is_file():raise ValueError('找不到交接包')
                buf=io.BytesIO()
                with zipfile.ZipFile(buf,'w',zipfile.ZIP_DEFLATED) as archive:
                    for file in folder.iterdir():
                        if file.is_file():archive.write(file,file.name)
                data=buf.getvalue()
                self.send_response(200)
                self.send_header('Content-Type','application/zip')
                self.send_header('Content-Disposition','attachment; filename="cover-'+name+'.zip"')
                self.send_header('Content-Length',str(len(data)))
                self.end_headers();self.wfile.write(data);return
            elif path=='/packages':
                result=[d.name for d in sorted((project.dir/'exports').glob('v*-*'),key=lambda d:d.stat().st_mtime,reverse=True) if (d/'job.json').is_file()][:1]
            elif path=='/brand/catalog':
                result=[]
                for file in sorted(root_project.dir.parent.glob('*/project.sqlite')):
                    key=file.parent.name
                    if file.parent!=root_project.dir and not re.fullmatch(r'[a-f0-9]{12}',key):continue
                    rec=Project(file.parent).read()['state']; flow=rec.get('workflow')
                    if flow:result.append({'id':'' if file.parent==root_project.dir else key,'name':flow['name']})
            elif path=='/brand/handoff':
                from inventory import handoff
                return self.reply(200,project.brief().encode(),'text/plain; charset=utf-8')
            elif path=='/brand/diagram':
                from proposals import spread
                return self.reply(200,spread(q.get('route','')).encode(),'image/svg+xml')
            elif path in ('/','/brand.js','/brand.css') and (path!='/' or project.dir==DEFAULT or project.read()['state'].get('workflow')):
                filename={'/':'brand.html','/brand.js':'brand.js','/brand.css':'brand.css'}[path]
                return self.reply(200,(ROOT/filename).read_bytes(),{'/':'text/html','/brand.js':'text/javascript','/brand.css':'text/css'}[path]+'; charset=utf-8')
            elif path=='/review':return self.reply(200,(ROOT/('index.html' if edition else 'review.html')).read_bytes(),'text/html; charset=utf-8')
            elif path=='/state':result=project.read(q.get('rev'))
            elif path=='/history':result=project.history()
            elif path=='/layouts':result=list(LAYOUTS)
            elif path=='/preview':
                s=project.read(q.get('rev'))['state']
                if 'layout' in q:
                    for o in s['objects']:o['locks']=[]
                    apply(s,{'action':'layout','layout':q['layout']})
                svg=render(s,project.dir,q.get('mode','art'),bool(edition or sku))
                return self.reply(200,svg.encode(),'image/svg+xml')
            elif path in ('/','/editor','/ui.js','/style.css'):
                filename={'/editor':'index.html','/':'index.html','/ui.js':'ui.js','/style.css':'style.css'}[path]
                return self.reply(200,(ROOT/filename).read_bytes(),{'/editor':'text/html','/':'text/html','/ui.js':'text/javascript','/style.css':'text/css'}[path]+'; charset=utf-8')
            else:return self.reply(404,b'Not found','text/plain')
            self.reply(200,dump(result).encode(),'application/json; charset=utf-8')
        def dispatch(self,post):
            try:self.run(post)
            except (ValueError,KeyError,TypeError,IndexError,OSError,subprocess.SubprocessError) as e:
                self.reply(409 if isinstance(e,Conflict) else 400,dump({'error':str(e)}).encode(),'application/json')
        def log_message(self, format, *args):
            if sys.stderr:super().log_message(format, *args)
        def do_GET(self):self.dispatch(False)
        def do_POST(self):self.dispatch(True)
    return Handler

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--project',type=Path,default=DEFAULT)
    sub=parser.add_subparsers(dest='cmd',required=True)
    new=sub.add_parser('init');new.add_argument('--concept',default='愿望本')
    for k,v in [('width',148),('height',210),('bleed',6)]:new.add_argument('--'+k,type=float,default=v)
    serve=sub.add_parser('serve');serve.add_argument('--port',type=int,default=8791);serve.add_argument('--open',action='store_true')
    for cmd in ('state','history','export','handoff'):sub.add_parser(cmd)
    sub.add_parser('apply').add_argument('request',type=Path)
    sub.add_parser('import').add_argument('file',type=Path)
    preview=sub.add_parser('preview');preview.add_argument('output',type=Path);preview.add_argument('--mode',default='art')
    args=parser.parse_args(); p=Project(args.project)
    if args.cmd=='init':
        if min(args.width,args.height)<=0 or args.bleed<0:raise ValueError('尺寸无效')
        p.init(args.concept,dict(width=args.width,height=args.height,bleed=args.bleed))
    elif args.cmd=='serve':
        if sys.stdout is None:sys.stdout=open(os.devnull,'w',encoding='utf8')
        if sys.stderr is None:sys.stderr=open(os.devnull,'w',encoding='utf8')
        if not (p.dir/'project.sqlite').exists():p.init('工作台' if p.dir==DEFAULT else '愿望本')
        with ThreadingHTTPServer(('127.0.0.1',args.port),handler(p)) as server:
            url='http://127.0.0.1:'+str(server.server_port)
            print(url,flush=True)
            if args.open:webbrowser.open(url+"/")
            server.serve_forever()
    elif args.cmd=='state':print(dump(p.read()))
    elif args.cmd=='handoff':
        from inventory import handoff
        print(p.brief())
    elif args.cmd=='history':print(dump(p.history()))
    elif args.cmd=='export':print(p.export())
    elif args.cmd=='apply':print(dump(p.change(json.loads(args.request.read_text(encoding='utf-8-sig')))))
    elif args.cmd=='import':print(p.asset(args.file.read_bytes()))
    elif args.cmd=='preview':args.output.write_text(render(p.read()['state'],p.dir,args.mode,True),encoding='utf8')
if __name__=='__main__':main()

