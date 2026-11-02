#!/usr/bin/env python3
"""Select the previously qualified fuxi CDC adapter in a fresh CI checkout.

The generic build source stays in this repository. Board policy is staged only
in the runner's pinned device checkout, leaving the device's remote main alone.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tomllib

DEVICE_REV = '4f066e69836695c9ac73d3728f68a1ebfa008964'
USB_REV = '83be5782ad7227d7d245862ce1ae3272cae14242'
XNU_REV = 'd8b80295118ef25ac3a784134bcf95cd8e88109f'


def replace_once(text, old, new):
    if text.count(old) != 1:
        raise ValueError('source context changed: ' + old[:120])
    return text.replace(old, new, 1)


def prepare(root, device):
    device = device.resolve()
    rev = subprocess.check_output(['git', '-C', str(device), 'rev-parse', 'HEAD'], text=True).strip()
    if rev != DEVICE_REV:
        raise ValueError('unexpected device revision: ' + rev)
    board_path = device / 'board.toml'
    board_text = board_path.read_text()
    board = tomllib.loads(board_text)
    if board['board']['name'] != 'fuxi' or board['ipsw']['build'] != '20H392':
        raise ValueError('this integration is restricted to fuxi / 20H392')
    usb = device / 'drivers/QcomXnuUsbDebug'
    if subprocess.check_output(['git', '-C', str(usb), 'rev-parse', 'HEAD'], text=True).strip() != USB_REV:
        raise ValueError('USB submodule pin differs from the previous fuxi build')
    core_recipe = root / 'scripts/build-xnu-4k-baseline.sh'
    text = core_recipe.read_text()
    # The device's NativeUFS adapter authenticates its OS/SystemOS windows using
    # libVerifiedRootProbe.a. Do not require the unrelated Virtio transport for it.
    old = '''   { [ "${XNU_NATIVE_VIRTIO_BLOCK:-0}" != 1 ] && [ "${XNU_SOURCE_STORAGE:-0}" != 1 ]; }; }; then'''
    new = '''   { [ "${XNU_NATIVE_VIRTIO_BLOCK:-0}" != 1 ] && [ "${XNU_SOURCE_STORAGE:-0}" != 1 ] &&
     [ "${XNU_NATIVE_UFS:-0}" != 1 ]; }; }; then'''
    text = replace_once(text, old, new)
    core_recipe.write_text(text)
    # The current core exports the unstripped executable without the older
    # .noctf suffix. Keep the pinned device prelink recipe on the actual output.
    board_text = replace_once(board_text,
        'mach.development.bcm2837.unstripped.noctf"',
        'mach.development.bcm2837.unstripped"')
    board_text = replace_once(board_text, 'title = "FUXI FIX061 UFS READONLY"',
        'title = "FUXI USB CDC RESTORE 20261102"')
    board_path.write_text(board_text)
    # Tree assembly already copies this pinned device launcher over the core
    # recipe. Validate and keep it: installing a second wrapper is unnecessary.
    wrapper = device / 'scripts/build-xnu-4k-baseline.sh'
    expected_wrapper = '''#!/usr/bin/env bash
set -euo pipefail
FUXI_TREE=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
exec python3 "$FUXI_TREE/scripts/run-fuxi-usb-kernel.py"
'''
    if wrapper.read_text() != expected_wrapper:
        raise ValueError('the pinned device USB launcher changed')
    record = {
        'device_repository': 'Kerfand/UniXNU-fuxi', 'device_revision': DEVICE_REV,
        'usb_repository': 'xiaoleGun/QcomXnuUsbDebug', 'usb_revision': USB_REV,
        'xnu_revision': XNU_REV, 'profile': 'darwin23-fuxi',
        'usb_identity': {'vid': '1209', 'pid': '316d', 'serial': 'FuxiXnuUsbDebug'},
        'exact_stream_takeover': True, 'global_smmu_bypass': False,
        'reset_control_enabled': False, 'hardware_verified_this_build': False,
        'takeover_patch_sha256': hashlib.sha256(
            (device / 'scripts/fuxi-usb-exact-stream.patch').read_bytes()).hexdigest(),
    }
    out = root / 'out/fuxi-usb-ci'
    out.mkdir(parents=True, exist_ok=True)
    (out / 'source-profile.json').write_text(json.dumps(record, indent=2) + '\n')
    print(json.dumps(record, indent=2))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--device', required=True, type=Path)
    a = p.parse_args()
    prepare(Path(__file__).resolve().parents[2], a.device)
