from pathlib import Path
root=Path(__file__).resolve().parents[1]
s=(root/'diagnostic/kali-telecamera-capture.sh').read_text()
s=s.replace('exposure=1800,analogue_gain=0','exposure=3178,analogue_gain=896')
s=s.replace('--stream-skip=8','--stream-skip=60')
s=s.replace('--verbose\nrc=$?', '''--verbose &
capture_pid=$!
sleep 1
python3 - <<'PY'
import ctypes, fcntl, os
class Msg(ctypes.Structure):
    _fields_=[('addr',ctypes.c_uint16),('flags',ctypes.c_uint16),('len',ctypes.c_uint16),('buf',ctypes.c_void_p)]
class Xfer(ctypes.Structure):
    _fields_=[('msgs',ctypes.POINTER(Msg)),('nmsgs',ctypes.c_uint32)]
fd=os.open('/dev/i2c-17',os.O_RDWR)
for reg,length in [(0x0016,2),(0x0100,1),(0x0101,1),(0x0104,1),(0x0202,2),(0x0204,2),(0x020e,8),(0x0218,2),(0x0340,4),(0x0600,2),(0x3ff9,1)]:
    pointer=ctypes.create_string_buffer(reg.to_bytes(2,'big'))
    value=ctypes.create_string_buffer(length)
    msgs=(Msg*2)(Msg(0x1a,0,2,ctypes.addressof(pointer)),Msg(0x1a,1,length,ctypes.addressof(value)))
    fcntl.ioctl(fd,0x0707,Xfer(msgs,2))
    print(f'reg{reg:04x}={value.raw.hex()}',flush=True)
os.close(fd)
PY
grep -Ei 'bob|s3a|tele|camera-analog' /sys/kernel/debug/regulator/regulator_summary
grep -E 'gpio-(30|100|103|123)' /sys/kernel/debug/gpio
wait "$capture_pid"
rc=$?''')
(root/'diagnostic/kali-telecamera-debug-capture.sh').write_bytes(s.encode())
