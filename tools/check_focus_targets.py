from pathlib import Path
import numpy as np
from PIL import Image
base = Path(__file__).resolve().parents[1] / 'test-runs/snapshot'
for position in (50,800):
    a=np.array(Image.open(base/f'aura-focus-{position}.pgm'),dtype=float)
    h,w=a.shape
    b=sum(a[dy:dy+h-4,dx:dx+w-4] for dy in range(4) for dx in range(4))/16
    y=slice(h//3,h*2//3,8)
    x=slice(w//3,w*2//3,8)
    v=b[y,x]
    g=np.abs(v-b[y,slice(w//3+4,w*2//3+4,8)])+np.abs(v-b[slice(h//3+4,h*2//3+4,8),x])
    print(position, 'smoothed normalized contrast',g.sum()/v.sum())
    energy=(v-b[y,slice(w//3+4,w*2//3+4,8)])**2+(v-b[slice(h//3+4,h*2//3+4,8),x])**2
    print(position, 'normalized edge energy',energy.mean()/v.mean()**2)
