import json
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
import xml.etree.ElementTree as ET
from http.server import ThreadingHTTPServer
from pathlib import Path
from design import LAYOUTS
from render import render
from studio import DEFAULT, ROOT, Conflict, Project, handler

class WorkflowTest(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.p=Project(Path(self.temp.name)/'移动工程')
        self.p.init('愿望本')

    def change(self,*ops):
        return self.p.change({'base':self.p.read()['rev'],'label':'验收','ops':list(ops)})

    def test_versions_geometry_masks(self):
        for layout in LAYOUTS:self.change({'action':'layout','layout':layout})
        base=self.p.read()['rev']
        self.change({'action':'lock','id':'subject','locks':['asset']})
        with self.assertRaises(ValueError):self.change({'action':'edit','id':'subject','values':{'fill':'#000000'}})
        with self.assertRaises(Conflict):self.p.change(dict(base=base,label='旧版',ops=[]))
        request={'base':self.p.read()['rev'],'label':'蒙版编辑','ops':[{'action':'edit','id':'subject','values':{'mask':{'cut':'seal','fade':True,'crop':[0,2,95,82],'strokes':[{'size':5,'points':[[1,2],[3,4]]}]}}}]}
        f=self.p.dir/'request.json';f.write_text(json.dumps(request),encoding='utf8')
        subprocess.run([sys.executable,str(ROOT/'studio.py'),'--project',str(self.p.dir),'apply',str(f)],check=True,stdout=subprocess.DEVNULL)
        self.change({'action':'repeat','id':'seal','pivot':[80,111],'degrees':20,'count':3})
        art=self.p.export()
        for name in ['ART','UV','UV-preview']:
            svg=ET.parse(art/(name+'.svg')).getroot()
            self.assertEqual(svg.get('viewBox'),'0 0 160 222')
            self.assertEqual(len({n.get('id') for n in svg.iter() if n.get('id')}),len([n for n in svg.iter() if n.get('id')]))
        self.assertIn('polyline',(art/'UV.svg').read_text())
        self.p.change({'base':self.p.read()['rev'],'from':base,'label':'分支','ops':[]})
        self.assertEqual(self.p.history()[0]['parent'],base)

    def test_compositing_pipeline_and_export(self):
        # Import a tiny 2x2 valid PNG asset for image-based compositing tests
        import base64
        tiny_png=base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAIAAAACCAIAAAD91JpzAAAAEElEQVR4nGP4z8AARAwQCgAf7gP9i18U1AAAAABJRU5ErkJggg==')
        asset_key=self.p.asset(tiny_png)
        # 1. Gradient Map + Organic Edge + Metallic Rim + Expanded Blend Mode
        self.change(
            {'action':'edit','id':'subject','values':{
                'kind':'image','asset':asset_key,'source':'test-moon.png','blend':'overlay','opacity':0.92,
                'gradientMap':{
                    'enabled':True,
                    'stops':[{'offset':0.0,'color':'#091334'},{'offset':0.52,'color':'#1d4ed8'},{'offset':1.0,'color':'#f5f8ff'}],
                    'invert':False,'strength':0.85
                },
                'mask':{
                    'organic':{
                        'enabled':True,'scale':10.0,'frequency':0.055,'octaves':4,'seed':23,
                        'inset':2.5,'feather':0.15,'rimEnabled':True,'rimColor':'#d4af37',
                        'rimWidth':0.55,'rimOpacity':0.95,'rimShimmer':True
                    }
                }
            }},
            # 2. Text Underlying Line Avoidance (Knockout)
            {'action':'edit','id':'title','values':{
                'mask':{'knockout':{'enabled':True,'pad':3.5,'feather':2.2,'scope':'linework'}}
            }},
            # 3. Global Texture Overlay
            {'action':'texture','values':{
                'enabled':True,'kind':'paper','blend':'multiply','opacity':0.18,'scale':1.1,'contrast':1.05
            }}
        )
        # Validate SVG structure, filters, masks, unique IDs and export behavior
        art_dir=self.p.export()
        art_text=(art_dir/'ART.svg').read_text(encoding='utf8')
        uv_text=(art_dir/'UV.svg').read_text(encoding='utf8')
        overlay_text=(art_dir/'UV-preview.svg').read_text(encoding='utf8')
        for label,text in [('ART',art_text),('UV',uv_text),('UV-preview',overlay_text)]:
            svg=ET.fromstring(text)
            ids=[n.get('id') for n in svg.iter() if n.get('id')]
            self.assertEqual(len(set(ids)),len(ids),f'Duplicate SVG IDs in {label}')
        # Gradient Map filter present in ART, absent in UV black plate
        self.assertIn('id="gm-subject"',art_text)
        self.assertIn('feComponentTransfer',art_text)
        self.assertNotIn('id="gm-subject"',uv_text)
        # Organic Edge + Gold Rim filter present in ART; monochrome organic mask present in UV
        self.assertIn('id="org-subject"',art_text)
        self.assertIn('feTurbulence',art_text)
        self.assertIn('feDisplacementMap',art_text)
        self.assertIn('#d4af37',art_text)
        self.assertIn('id="orgm-subject"',uv_text)
        self.assertNotIn('#d4af37',uv_text)
        # Text knockout mask generated and applied to orbit/trace linework
        self.assertIn('id="ko-title"',art_text)
        self.assertIn('id="kof-title"',art_text)
        self.assertIn('mask="url(#ko-title)"',art_text)
        # Global texture layer composited in ART & UV-preview, excluded from UV plate
        self.assertIn('id="global-texture"',art_text)
        self.assertIn('id="globalTex"',art_text)
        self.assertIn('id="global-texture"',overlay_text)
        self.assertNotIn('id="global-texture"',uv_text)
        # job.json records compositing metadata
        job=json.loads((art_dir/'job.json').read_text(encoding='utf8'))
        self.assertTrue(job['compositing']['globalTexture']['enabled'])
        self.assertEqual(job['compositing']['gradientMaps'],['纸飞机'])
        self.assertEqual(job['compositing']['organicMasks'],['纸飞机'])
        self.assertEqual(job['compositing']['textKnockouts'],['封面标题'])
        # Validation checks
        with self.assertRaises(ValueError):
            self.change({'action':'edit','id':'subject','values':{'gradientMap':{'enabled':True,'stops':[{'offset':0,'color':'#000'}]}}})
        with self.assertRaises(ValueError):
            self.change({'action':'edit','id':'subject','values':{'mask':{'organic':{'enabled':True,'rimColor':'not-a-color'}}}})
        with self.assertRaises(ValueError):
            self.change({'action':'texture','values':{'enabled':True,'kind':'asset','asset':'missing.png'}})
        # Custom asset texture works when asset is imported
        self.change({'action':'texture','values':{'enabled':True,'kind':'asset','asset':asset_key,'blend':'overlay','opacity':0.2}})
        custom_art=render(self.p.read()['state'],self.p.dir,'print',True)
        self.assertIn('id="global-texture"',custom_art)
        self.assertIn('data:image/png;base64,',custom_art)

    def test_browser_and_cli(self):
        from playwright.sync_api import sync_playwright
        import os
        chrome=os.environ.get('COVER_CHROME')
        if not chrome:
            chrome=r'C:\Program Files\Google\Chrome\Application\chrome.exe'
        with ThreadingHTTPServer(('127.0.0.1',0),handler(self.p)) as server, sync_playwright() as pw:
            thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
            try:
                browser=pw.chromium.launch(executable_path=chrome if Path(chrome).exists() else None)
                page=browser.new_page(viewport={'width':1400,'height':940})
                page.goto('http://127.0.0.1:'+str(server.server_port))
                page.locator('#canvas svg').wait_for()
                page.locator('#concept').fill('世界树');page.locator('#conceptForm button').click()
                page.locator('#message').fill('冷白底，居中构图')
                page.locator('#briefForm button').last.click()
                page.wait_for_function("document.querySelector('h1').textContent==='世界树'")
                page.locator('#add').click()
                page.locator('#elementName').fill('独立题签')
                page.locator('#elementForm button').last.click()
                page.locator('[data-layer]',has_text='独立题签').wait_for()
                page.locator('#remove').click()
                page.locator('[data-layer]',has_text='独立题签').wait_for(state='detached')
                self.assertEqual(page.locator('#choices img').count(),3)
                page.locator('#choices button').first.click()
                page.get_by_text('已保存 · 采用构图',exact=False).wait_for()
                page.locator('[data-layer="subject"]').click()
                page.locator('#cut').select_option('orbit')
                page.get_by_text('已保存 · 调整轮廓遮挡',exact=False).wait_for()
                page.locator('[data-act="erase"]').click()
                box=page.locator('#canvas').bounding_box()
                x=box['x']+box['width']*.5;y=box['y']+box['height']*.5
                page.mouse.move(x,y);page.mouse.down();page.mouse.move(x+8,y+8);page.mouse.up()
                page.get_by_text('已保存 · 手修蒙版',exact=False).wait_for()
                page.locator('[data-lock="mask"]').check()
                page.get_by_text('已保存 · 更新对象锁',exact=False).wait_for()
                result=subprocess.check_output([sys.executable,str(ROOT/'studio.py'),'--project',str(self.p.dir),'state'])
                import locale
                frm=json.loads(result.decode(locale.getpreferredencoding(False)))
                target=next(o for o in frm['state']['objects'] if o['id']=='subject')
                self.assertEqual(target['locks'],['mask'])
                self.assertEqual(len(target['mask']['strokes']),1)
                page.reload();page.locator('#canvas svg').wait_for()
                page.locator('[data-act="compare"]').click()
                self.assertTrue(page.locator('#compare').is_visible())
                browser.close()
            finally:server.shutdown()

if __name__=='__main__':unittest.main()

