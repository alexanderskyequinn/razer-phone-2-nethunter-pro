"""Run the native boundary mock with synthetic credentials and firmware replies."""
import os
import subprocess
import tempfile

binary = '/var/tmp/aura-fpc-bio-mock'
base = dict(os.environ, AURA_MOCK_ACCOUNT='1', AURA_MOCK_ENROLL='1')
command = [binary, '--account-enroll', '1001', '2', '0123456789abcdef0123456789abcdef']
cases = [('good', 0), ('wrong-pin', 1), ('throttled', 1), ('stale-token', 1),
         ('token-reject', 1), ('missing-handle', 1), ('unsafe-handle', 1),
         ('existing', 1), ('cancel', 4), ('save-fail', 1), ('close-fail', 1)]
count = 0
for name, expected in cases:
    result = subprocess.run(command, input=b'2468\n', stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            env=dict(base, AURA_MOCK='account-enroll-' + name), timeout=10)
    assert result.returncode == expected, (name, result.returncode, result.stdout.decode())
    assert b'2468' not in result.stdout, 'Synthetic credential leaked to output'
    count += 1
for name, expected in (('good', 0), ('missing-handle', 1)):
    result = subprocess.run([*command[:2], '1000', *command[3:]], input=b'2468\n',
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            env=dict(base, AURA_MOCK='account-enroll-' + name, AURA_MOCK_UID='1000'), timeout=10)
    assert result.returncode == expected, (name, result.returncode, result.stdout.decode())
    count += 1
for value in (b'', b'123\n', b'2468', b'24\x0068\n', b'x468\n', b'2'*65+b'\n'):
    result = subprocess.run(command, input=value, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            env=dict(base, AURA_MOCK='account-enroll-invalid-pin'), timeout=10)
    assert result.returncode == 1, (value, result.returncode, result.stdout.decode())
    count += 1
with tempfile.TemporaryFile() as file:
    file.write(b'2468\n')
    file.seek(0)
    result = subprocess.run(command, stdin=file, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            env=dict(base, AURA_MOCK='account-enroll-invalid-source'), timeout=10)
    assert result.returncode == 1, (result.returncode, result.stdout.decode())
    count += 1
print(f'Native account enrollment: {count} synthetic cases passed')
