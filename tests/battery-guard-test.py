"""Exercise the actual shell guard's pure policy path without phone access."""
from pathlib import Path
import subprocess

guard = Path(__file__).resolve().parents[1] / 'port/kali-overlay/usr/local/sbin/aura-first-boot-guard'
cases = [
    (['250', '14', 'Good', '0', '0'], 'low'),
    (['250', '5', 'Good', '1', '0'], 'low'),
    (['250', '2', 'Good', '1', '0'], 'low'),
    (['250', '2', 'Good', '0', '0'], 'critical'),
    (['250', '3', 'Good', '0', '0'], 'low'),
    (['250', '15', 'Good', '0', '0'], 'normal'),
    (['99', '5', 'Good', '1', '0'], 'fault'),
    (['431', '5', 'Good', '1', '0'], 'fault'),
    (['430', '5', 'Good', '1', '0'], 'low'),
    (['100', '5', 'Good', '1', '0'], 'low'),
    (['250', '50', 'Overheat', '1', '0'], 'fault'),
    (['250', '50', '', '1', '0'], 'fault'),
    (['', '50', 'Good', '1', '0'], 'fault'),
    (['250', '', 'Good', '1', '0'], 'fault'),
    (['-10', '50', 'Good', '1', '0'], 'fault'),
    (['250', '50', 'Good', '1', '1'], 'expired'),
]
for args, expected in cases:
    result = subprocess.run(['/bin/sh', str(guard), '--evaluate', *args],
                            check=True, capture_output=True, text=True)
    assert result.stdout.strip() == expected, (args, result.stdout, expected)
print(f'{len(cases)} battery guard cases passed (low-charge recovery, critical shutdown, temperature and health protection).')
