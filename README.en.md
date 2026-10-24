# Intel I225-V Ethernet workaround for macOS Tahoe

[中文说明与完整步骤](README.md)

[Download v1.0.0](https://github.com/GeekAudio/intel-i225-tahoe-fix/releases/latest) · [SHA-256 checksums](SHA256SUMS)

This repository records a working Ethernet configuration on an ASUS Z690 / Core i7-12700K / Intel I225-V (`8086:15f3`) system running macOS 26.7.1 (`25G241`, Darwin 25.6.0), with OpenCore 1.0.8.

The tested combination is `AppleIntelI210Ethernet.kext 2.3.1`, a `device-id` override of `0x1533`, `built-in=01`, and the appended boot argument `e1000=0`, with AppleIGC disabled. DHCP, default routing and connectivity worked, with a negotiated **1000baseT full-duplex** link. This is not a throughput measurement or a guarantee of 2.5GbE, I226 support, or long-term sleep stability.

## Why this exists

The original AppleIGC 1.9d2 configuration repeatedly hit `m->m_flags & M_PKTHDR` in `uipc_mbuf.c:4839`. A roughly 40-hour observation window after disabling AppleIGC recorded no recurrence of that network signature across 38 RTC wakes, but Ethernet was unavailable. I210 injection subsequently restored Ethernet. The 40-hour window describes **AppleIGC disabled**, not a 40-hour stress test of the replacement.

This is configuration-level evidence, not a source-level diagnosis of AppleIGC. A [similar upstream report](https://github.com/SongXiaoXi/AppleIGC/issues/35) provides independent context.

## Installation outline

1. Back up your complete EFI and prepare a bootable fallback. Edit a working copy first.
2. Disable AppleIGC and any competing driver for this NIC. Copy `Kexts/AppleIntelI210Ethernet.kext` into `EFI/OC/Kexts/` and merge its `Kernel > Add` entry from `examples/config.fragment.plist`.
3. Determine **your NIC's PCI path**. Merge the example DeviceProperties at that path: `device-id` is four bytes `33 15 00 00`, `built-in` is one byte `01`. The supplied PCI path belongs to the test machine.
4. Append `e1000=0` once to your existing `NVRAM > Add > 7C436110-AB2A-4BBB-A880-FE41995C9F82 > boot-args`. Preserve every existing argument. Ensure that GUID's `NVRAM > Delete` array contains `boot-args`.
5. Validate the **complete config** using `plutil -lint` and the official `ocvalidate` matching your OpenCore version. Optionally run the read-only checker below. Review the diff, copy to the correct ESP, `sync`, unmount/remount and verify hashes, then reboot.

```sh
python3 tools/check_config.py /path/to/EFI/OC/config.plist \
  --pci-path 'YOUR_CONFIRMED_PCI_PATH'
```

The example plist is a fragment, not a bootable EFI or a replacement for your config. The checker reproduces this configuration; it does not validate runtime behavior or replace `ocvalidate`. The tested kext entry has empty MinKernel/MaxKernel fields; this does not establish support for other macOS versions.

No security-setting changes were added for this workaround. The test system already had settings required by unrelated drivers. Loading under fully default SIP/AMFI/SecureBootModel settings has not been established here.

## Important evidence boundaries

- The bundled `Info.plist` already contains an `AppleIntelI225` personality including `pci8086,15f3`. The tested override is retained for reproduction, but its necessity has **not** been established by an A/B test.
- E1000 dext aborts occurred after the first successful boot and were still recorded on October 24, 2026. `e1000=0` is a tested configuration component, not proof that every dext is blocked. `dk.e1000=0` was not tested here.
- 1000baseT is the observed link negotiation, not a universal driver speed limit inferred from the I210 name.
- Interface numbering can change. Identify Ethernet with `networksetup -listallhardwareports` before checking `ifconfig enX`; verify routing and actual traffic, then test sustained transfer and sleep/wake separately.

If the replacement fails, boot your fallback EFI and restore the pre-change backup. Re-enabling the original AppleIGC configuration may also restore the original panic.

## Provenance and license

The four bundled driver files match [upstream commit df21255aaad44876aa2a572972521e1ad8069da5](https://github.com/0xHJK/Intel-NUC9-i7-9850H-macOS/tree/df21255aaad44876aa2a572972521e1ad8069da5/EFI-macOS-Sonoma-14.3-OpenCore/EFI/OC/Kexts/AppleIntelI210Ethernet.kext) byte for byte. Apple signing metadata is preserved. Full resource verification reports an obsolete resource envelope; verification with resources ignored succeeds and is not equivalent to full verification. See [provenance](docs/PROVENANCE.md) and [local evidence](docs/EVIDENCE.zh-CN.md).

Apple driver files remain the property of their respective rights holders. New documentation, examples and scripts are MIT licensed. Remove private identifiers and credentials before sharing diagnostic files.
