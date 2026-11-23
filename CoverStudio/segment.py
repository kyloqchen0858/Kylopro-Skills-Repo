"""Use the existing SAM2 installation with the selected image's own coordinates."""
import json
from pathlib import Path
import sys

import cv2
import numpy as np
import torch
from PIL import Image

folder=Path(sys.argv[1])
info=json.loads((folder/'模型来源.json').read_text(encoding='utf8'))
sys.path.insert(0,str(folder/'vendor'/Path(info['source_dir']).name))
from sam2.build_sam import build_sam2
from sam2.sam2_image_predictor import SAM2ImagePredictor

points=np.asarray(json.load(sys.stdin),dtype=np.float32)
if points.ndim!=2 or points.shape[1]!=3 or not np.isfinite(points).all():
    raise ValueError('Invalid selection points')
img=Image.open(sys.argv[2]).convert('RGB')
img.thumbnail((1600,1600))
width,height=img.size
torch.set_num_threads(4)
model=build_sam2('configs/sam2.1/sam2.1_hiera_t.yaml',str(folder/'models'/Path(info['checkpoint']).name),device='cpu',apply_postprocessing=False)
with torch.inference_mode():
    predictor=SAM2ImagePredictor(model)
    predictor.set_image(np.asarray(img))
    masks,scores,_=predictor.predict(point_coords=points[:,:2]*[width/100,height/100],
                                     point_labels=points[:,2].astype(int),multimask_output=True)
contours,_=cv2.findContours(masks[np.argmax(scores)].astype('uint8'),cv2.RETR_TREE,cv2.CHAIN_APPROX_SIMPLE)
paths=[]
for contour in contours:
    vertices=cv2.approxPolyDP(contour,.6,True).reshape(-1,2)
    if len(vertices)>=3:
        paths.append('M'+' L'.join(f'{100*x/width:.3f},{100*y/height:.3f}' for x,y in vertices)+' Z')
if not paths:raise ValueError('No region selected')
print(json.dumps({'outline':' '.join(paths)}))

