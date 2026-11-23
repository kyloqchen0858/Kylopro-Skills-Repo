import json
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.request import urlopen, Request
from http.server import ThreadingHTTPServer
from studio import Project, handler, dump
from inventory import handoff

class BrandTest(unittest.TestCase):
    def test_two_skus_progress_and_approval(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Project(Path(tmp)/'wish')
            root.init('试用工程')
            with ThreadingHTTPServer(('127.0.0.1',0),handler(root)) as server:
                worker=threading.Thread(target=server.serve_forever,daemon=True);worker.start()
                try:
                    base='http://127.0.0.1:'+str(server.server_port)
                    req=Request(base+'/brand/new',data=dump(dict(name='另一个 SKU',brief='待设计挂历')).encode(),headers={'Content-Type':'application/json'})
                    key=json.load(urlopen(req))['sku']
                    p=Project(root.dir.parent/key)
                    def apply(op):return p.change(dict(base=p.read()['rev'],label=op['action'],ops=[op]))
                    apply(dict(action='item_add',name='挂历支座',stage='产品拆解',output='结构草图',depends=['brief']))
                    apply(dict(action='item_update',id='brief',status='已完成',next='验证结构',evidence='用户确认记录'))
                    self.assertIn('余 1 项',handoff(Project(p.dir).read()))
                    from proposals import OPTIONS
                    apply(dict(action='plan_edit',visual='草图',routes=OPTIONS[:1]))
                    with self.assertRaises(ValueError):apply(dict(action='plan_approve',route='echo'))
                    apply(dict(action='plan_choose',route='echo'))
                    self.assertFalse(p.read()['state']['workflow']['approved'])
                    apply(dict(action='plan_approve',route='echo'))
                    apply(dict(action='plan_note',message='调整封底',route='echo'))
                    self.assertFalse(p.read()['state']['workflow']['approved'])
                    self.assertNotIn('workflow',root.read()['state'])
                finally:server.shutdown()

