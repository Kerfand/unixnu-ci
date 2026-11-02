# fuxi USB CDC build

The `Fuxi USB CDC kernel` workflow builds this framework with the pinned
`Kerfand/UniXNU-fuxi` device at `4f066e69836695c9ac73d3728f68a1ebfa008964`.
It uses `xiaoleGun/QcomXnuUsbDebug` at
`83be5782ad7227d7d245862ce1ae3272cae14242`, the version already consumed by
the previous fuxi USB build. The current upstream default also adds newer
logging hooks; those Darwin22-only additions are not silently applied here.

The device's existing preparation scripts produce a separate `darwin23-fuxi`
profile for XNU 10063.141.1. The board-only exact-stream policy accepts the
firmware's one exact USB stream mapping after halt/revalidation, uses a new
private translated DMA bank, and retains the old mapping for restoration.
It does not enable global SMMU bypass or reuse the old bank. USB resources,
VID/PID 1209:316d, 4 MiB buffering and the panic drain are unchanged.

The fresh runner checkout receives a device recipe launcher so both the
bootstrap and final kernel builds select those hooks. The six per-object
USB options are appended to their existing options. The final kernel must
define the public USB entry points before artifact publication. Power/PHY
remain inherited from the existing UEFI; reboot control is disabled.

The staging step also resolves build-contract changes in this framework:
the native executable uses `.unstripped` instead of the old `.noctf` suffix,
and a NativeUFS owner-verified root must not require the unrelated Virtio
transport. Root verification, policy keys, OS/SystemOS UUIDs and the signed
20H392 inputs remain selected by the pinned device.
The device's independently audited `build/native-ufs/libNativeUfs.a` is used
directly; it is not replaced by the official `build/sheng-ufs/libShengUfs.a`.

The workflow downloads the existing PMGR reference and root policy from
`Kerfand/UniXNU` releases and creates the original trust-cache bundle from
the same 20H392 IPSW. No IPSW, policy, trust cache or Data seed is committed.
The artifact contains a kernel, payload, source identity and USB audit reports.
It does not contain a UEFI boot image or a Data seed. Repack the payload with
the already tested fuxi UEFI, then use temporary `fastboot boot`.

On Windows, start the existing `Capture-USB-Log.cmd` before booting. Select
the current COM port (COM12 in the previous captures). USB success requires
actual enumeration and received kernel bytes; for panic captures also record
pending/overflow/contention/transport counters and `QCOM PANIC END`.
Build/model success alone does not establish hardware acceptance.
