#!/usr/bin/env python3
"""只读核对本仓库已测试的 I225-V / Tahoe 配置组合。

用法：python3 tools/check_config.py /path/to/EFI/OC/config.plist \
          --pci-path 'PciRoot(0x0)/Pci(0x1C,0x3)/Pci(0x0,0x0)'
依赖：Python 3 标准库，无需安装第三方包。

脚本绝不写入任何文件或 ESP；不输出完整配置、MAC、IP、三码或 boot-args。
它不替代同版本 OpenCore 的 ocvalidate，也不检测硬件、驱动加载或联网运行态。
返回值：0 = 所查项目通过；1 = 配置不匹配；2 = 参数或文件读取失败。
"""

import argparse
import plistlib
import struct
import sys
from pathlib import Path
from xml.parsers.expat import ExpatError


NVRAM_GUID = "7C436110-AB2A-4BBB-A880-FE41995C9F82"
KEXT_NAME = "AppleIntelI210Ethernet.kext"
EXECUTABLE = "Contents/MacOS/AppleIntelI210Ethernet"
PLIST_PATH = "Contents/Info.plist"
CONFLICTS = {"appleigc.kext", "simplevgbe.kext"}
PLIST_ERRORS = (OSError, ValueError, TypeError, plistlib.InvalidFileException,
                OverflowError, ExpatError, RecursionError)


class QuietParser(argparse.ArgumentParser):
    def error(self, message):
        self.exit(2, "FAIL 参数无效；请使用 --help 查看用法。\n")


def read_plist(path):
    with path.open("rb") as stream:
        result = plistlib.load(stream)
    if not isinstance(result, dict):
        raise ValueError("plist root must be a dictionary")
    return result


def section(value, key):
    result = value.get(key) if isinstance(value, dict) else None
    return result if isinstance(result, dict) else {}


def bundle_name(entry):
    value = entry.get("BundlePath", "")
    if not isinstance(value, str):
        return ""
    return value.replace("\\", "/").rstrip("/").rsplit("/", 1)[-1].lower()


def supports_x86_64(path):
    """Read Mach-O headers only; accept thin or universal x86_64 executables."""
    with path.open("rb") as stream:
        header = stream.read(8)
        if len(header) != 8:
            return False
        magic = header[:4]
        if magic in (b"\xcf\xfa\xed\xfe", b"\xfe\xed\xfa\xcf"):
            endian = "<" if magic == b"\xcf\xfa\xed\xfe" else ">"
            return struct.unpack(endian + "I", header[4:])[0] == 0x01000007
        formats = {
            b"\xca\xfe\xba\xbe": (">", 20),
            b"\xbe\xba\xfe\xca": ("<", 20),
            b"\xca\xfe\xba\xbf": (">", 32),
            b"\xbf\xba\xfe\xca": ("<", 32),
        }
        if magic not in formats:
            return False
        endian, entry_size = formats[magic]
        count = struct.unpack(endian + "I", header[4:])[0]
        if not 1 <= count <= 64:
            return False
        found = False
        for _ in range(count):
            architecture = stream.read(entry_size)
            if len(architecture) != entry_size:
                return False
            found |= struct.unpack(endian + "I", architecture[:4])[0] == 0x01000007
        return found


def main():
    parser = QuietParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("config", type=Path, help="待核对的 config.plist（只读）")
    parser.add_argument("--pci-path", required=True, help="该机器有线网卡的完整 PCI 路径")
    args = parser.parse_args()
    if not args.pci_path.strip():
        parser.error("empty PCI path")
    try:
        config = read_plist(args.config)
    except PLIST_ERRORS:
        print("FAIL 无法读取有效的 config.plist；请检查文件、权限和 plist 格式。")
        return 2

    failures = 0
    read_error = False

    def check(condition, message):
        nonlocal failures
        print(("PASS " if condition else "FAIL ") + message)
        failures += not condition

    entries = section(config, "Kernel").get("Add")
    valid_entries = isinstance(entries, list) and all(isinstance(item, dict) for item in entries)
    check(valid_entries, "Kernel > Add 是有效条目数组。")
    entries = entries if valid_entries else []
    check(all(isinstance(item.get("Enabled"), bool) for item in entries),
          "Kernel > Add 各条目的 Enabled 均为布尔值。")
    enabled = [item for item in entries if item.get("Enabled") is True]
    i210 = [item for item in enabled if bundle_name(item) == KEXT_NAME.lower()]
    check(len(i210) == 1, "恰好启用一条 AppleIntelI210Ethernet.kext。")
    if len(i210) == 1:
        entry = i210[0]
        check(entry.get("BundlePath") == KEXT_NAME, "I210 BundlePath 与本仓库安装位置一致。")
        check(entry.get("ExecutablePath") == EXECUTABLE, "I210 ExecutablePath 正确。")
        check(entry.get("PlistPath") == PLIST_PATH, "I210 PlistPath 正确。")
        check(entry.get("Arch") in ("Any", "x86_64"), "I210 Arch 允许 x86_64。")
        if entry.get("MinKernel") or entry.get("MaxKernel"):
            print("WARN I210 设置了内核版本范围；请另行确认它包含实际 Tahoe Darwin 25 版本。")
    check(not any(bundle_name(item) in CONFLICTS for item in enabled),
          "未启用冲突的 AppleIGC.kext / SimpleVGBE.kext。")

    nvram = section(config, "NVRAM")
    boot_args = section(section(nvram, "Add"), NVRAM_GUID).get("boot-args")
    tokens = boot_args.split() if isinstance(boot_args, str) else []
    check([token for token in tokens if token.startswith("e1000=")] == ["e1000=0"],
          "NVRAM > Add 的 boot-args 含单个 e1000=0，且没有其它 e1000= 值。")
    deleted = section(nvram, "Delete").get(NVRAM_GUID)
    check(isinstance(deleted, list) and "boot-args" in deleted,
          "NVRAM > Delete 的对应 GUID 包含 boot-args。")

    properties = section(section(section(config, "DeviceProperties"), "Add"), args.pci_path)
    check(properties.get("device-id") == bytes.fromhex("33150000"),
          "指定 PCI 路径的 device-id 是 Data 33150000。")
    check(properties.get("built-in") == b"\x01", "指定 PCI 路径的 built-in 是 Data 01。")

    kext = args.config.parent / "Kexts" / KEXT_NAME
    info_path = kext / PLIST_PATH
    executable_path = kext / EXECUTABLE
    try:
        info = read_plist(info_path)
        check(True, "config 同目录 Kexts 中的 I210 Info.plist 可读取。")
        check(info.get("CFBundleVersion") == "2.3.1", "I210 CFBundleVersion 是本仓库使用的 2.3.1。")
        check(info.get("CFBundleExecutable") == "AppleIntelI210Ethernet", "I210 CFBundleExecutable 正确。")
    except PLIST_ERRORS:
        print("FAIL 无法读取 config 同目录 Kexts 中的 I210 Info.plist；配置片段须先合并到含实际驱动的 OC 目录。")
        read_error = True
    try:
        check(supports_x86_64(executable_path), "config 同目录 Kexts 中的 I210 可执行文件包含 x86_64 架构。")
    except OSError:
        print("FAIL 无法读取 config 同目录 Kexts 中的 I210 可执行文件；配置片段须先合并到含实际驱动的 OC 目录。")
        read_error = True
    print("WARN 本脚本不替代 ocvalidate，也不确认运行态驱动加载或网络连通性。")
    return 2 if read_error else (1 if failures else 0)


if __name__ == "__main__":
    sys.exit(main())
