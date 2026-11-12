from pathlib import Path
root=Path(__file__).resolve().parents[1]
s=(root/'diagnostic/aura-focus-sweep.py').read_text()
s=s.replace('Bounded lens-motion test: retain sharpness numbers only, never images.','Bounded telephoto motion test; diagnostic images only with --save-targets.')
s=s.replace("os.open('/dev/v4l-subdev20', os.O_RDWR)","os.open(subprocess.check_output(['media-ctl','-e','lc898217xc 17-0072'],text=True).strip(), os.O_RDWR)")
s=s.replace("n['info']['props'].get('api.libcamera.location') == 'back'","n['info']['props'].get('device.product.name') == 'imx351'")
s=s.replace('(50, 800)','(60, 610)').replace('/tmp/aura-focus-','/tmp/aura-telefocus-')
s=s.replace('[50, 200, 400, 600, 800, 400, 50]','[60, 200, 400, 610, 400, 60]')
(root/'diagnostic/aura-telefocus-sweep.py').write_text(s)
