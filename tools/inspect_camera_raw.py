"""Unpack a CSI RAW10 diagnostic frame and make a half-resolution Bayer preview."""
from pathlib import Path
import argparse
import json
import numpy as np
from PIL import Image
p = argparse.ArgumentParser()
p.add_argument('input',type=Path)
p.add_argument('--width', type=int, default=4032)
p.add_argument('--height', type=int, default=3024)
p.add_argument('--stride', type=int)
args = p.parse_args()
assert args.width % 4 == 0 and args.height % 2 == 0
stride = args.stride or args.width * 5 // 4
packed = np.frombuffer(args.input.read_bytes(),dtype=np.uint8).reshape(args.height,stride)
packed = packed[:,:args.width*5//4].reshape(args.height,args.width//4,5).astype(np.uint16)
pixels = np.empty((args.height,args.width//4,4),dtype=np.uint16)
for i in range(4):
    pixels[:,:,i] = (packed[:,:,i] << 2) | ((packed[:,:,4] >> (i*2)) & 3)
pixels = pixels.reshape(args.height,args.width)
rgb = np.stack([pixels[0::2,0::2], (pixels[0::2,1::2]+pixels[1::2,0::2])//2, pixels[1::2,1::2]],axis=-1)
preview = Image.fromarray(np.uint8(np.clip(rgb/1023,0,1)**(1/2.2)*255))
preview.thumbnail((1008,756))
preview.save(args.input.with_suffix('.png'))
report = {'bytes':args.input.stat().st_size,'width':args.width,'height':args.height,'stride':stride,'minimum':int(pixels.min()),'maximum':int(pixels.max()),'mean':float(pixels.mean()),'zero_fraction':float((pixels==0).mean()),'row_mean_min':float(pixels.mean(axis=1).min()),'row_mean_max':float(pixels.mean(axis=1).max())}
args.input.with_suffix('.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
