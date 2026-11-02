#!/usr/bin/env python3
"""Bundle original 20H392 trust caches and build the CDC test payload."""
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
from unixnu.cli import parser
from unixnu.config import Context
from unixnu.ipsw import Ipsw

device = Path(os.environ['UNIXNU_DEVICE'])
ctx = Context(parser().parse_args(['ipsw', 'info', '-D', str(device)]))
if ctx.board['ipsw']['build'] != '20H392':
    raise SystemExit('unexpected IPSW build')
source = Ipsw(ctx)
inputs = [source.extract(name) for name in ('StaticTrustCache', 'Cryptex1,SystemTrustCache')]
out = ROOT / 'out/fuxi-usb-ci'
out.mkdir(parents=True, exist_ok=True)
trust = out / 'trustcache.bin'
subprocess.run([sys.executable, device / 'scripts/make-trust-cache-bundle.py',
                str(trust), *map(str, inputs)], check=True)
subprocess.run([str(ROOT / 'unixnu'), 'build', 'payload', '-D', str(device),
                '--trust-cache', str(trust)], cwd=ROOT, check=True)
tree = ctx.tree
kernel = ctx.work / 'kernel/kernel.macho'
symbols = subprocess.check_output(['llvm-nm', '--defined-only', str(kernel)], text=True)
required = ('_qcom_usb_debug_init', '_qcom_usb_debug_write', '_qcom_usb_debug_poll',
            '_qcom_usb_debug_panic_prepare', '_qcom_usb_debug_panic_drain')
names = {line.split()[-1] for line in symbols.splitlines() if line.split()}
missing = sorted(set(required) - names)
if missing:
    raise SystemExit('USB archive missing from final kernel: ' + ', '.join(missing))
record = {'linked_usb_symbols': list(required), 'kernel': str(kernel),
          'payload': str(ctx.work / 'payload/payload.img'),
          'hardware_verified': False, 'data_seed_included': False}
(out / 'linked-usb.json').write_text(json.dumps(record, indent=2) + '\n')
print(json.dumps(record, indent=2))
