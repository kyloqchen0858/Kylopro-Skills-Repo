"""Open the running workspace, or start the localhost server on first launch."""
import json
import subprocess
import sys
import urllib.request
import webbrowser
from pathlib import Path
ROOT=Path(__file__).resolve().parent
url='http://127.0.0.1:8791'
try:
    with urllib.request.urlopen(url+'/state',timeout=2) as response:
        record=json.load(response)
    if record['state'].get('schema')!=1 or 'objects' not in record['state']:
        raise RuntimeError('端口 8791 已被其他应用占用')
except OSError:
    sys.exit(subprocess.call([sys.executable,str(ROOT/'studio.py'),'serve','--open']))
webbrowser.open(url+'/')

