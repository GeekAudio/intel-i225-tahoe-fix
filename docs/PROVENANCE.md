# 驱动来源与完整性

核对日期：2026-10-24。

## 固定来源

- 仓库：[0xHJK/Intel-NUC9-i7-9850H-macOS](https://github.com/0xHJK/Intel-NUC9-i7-9850H-macOS)
- 固定提交：`df21255aaad44876aa2a572972521e1ad8069da5`
- 路径：`EFI-macOS-Sonoma-14.3-OpenCore/EFI/OC/Kexts/AppleIntelI210Ethernet.kext`
- 本包：从本机 EFI 工作副本复制，未改动驱动内容；四个文件与上述固定提交逐文件一致。

| 文件（kext 内相对路径） | 字节数 | SHA-256 |
| --- | ---: | --- |
| `Contents/Info.plist` | 4054 | `71aade8f8316c0a07b8c4a737fa99c043727cdc251bdeeeafba50cbd17b42c66` |
| `Contents/MacOS/AppleIntelI210Ethernet` | 552080 | `c2639077ffe5f491e5624782bd59fbc916730fb0c4515b2b5cee004073a40841` |
| `Contents/_CodeSignature/CodeResources` | 761 | `32d34cac6cdb584d0eaa68b06a2b1a0179db168852d8916d67280d769547b134` |
| `Contents/version.plist` | 474 | `ef6830c6e45c8e9f5330e9865e4265964b29ddb3d6dfc3acb15d2e1f94bec1bd` |

上游 Git blob SHA-1 分别是 `6fc4a50cb58aff42928372bfae4fa0b4057fdea9`、`27b84e17b4005969466688743252df61e64a15a7`、`c4832a05aefbc3336ab4be6e62bf767717ef5fba`、`fdf1a91a363dc56341844f07ba056759942f174a`。Git blob SHA-1 包含 Git 对象头，与直接对文件运行 `shasum` 不同。

## 元数据

```text
CFBundleIdentifier        com.apple.driver.AppleIntelI210Ethernet
CFBundleVersion           2.3.1
CFBundleShortVersionString 2.3.1
DTPlatformVersion         12.6
DTPlatformBuild           21G410
Mach-O architectures      x86_64 / arm64e
```

元数据指向 macOS 12.6 构建。本机使用的是 x86_64 路线；二进制包含 arm64e 不代表本仓库在 Apple Silicon 上测试或适用。

`Info.plist` 的 `AppleIntelI210` personality 按 `IOPCIPrimaryMatch=0x15338086` 匹配；另一个 `AppleIntelI225` personality 的 `IONameMatch` 已含 `pci8086,15f3` 等 ID。两个 personality 的 `IOClass` 都是 `AppleIntelI210`，`IOProbeScore` 都是 1000。不要据此推断未经实测的芯片支持、速率或驱动选择先后。

## 签名检查的准确说法

对本包的**绝对路径**执行：

```sh
codesign -dvvv /绝对路径/AppleIntelI210Ethernet.kext
codesign --verify --verbose=2 /绝对路径/AppleIntelI210Ethernet.kext
codesign --verify --ignore-resources --verbose=2 /绝对路径/AppleIntelI210Ethernet.kext
```

显示的签名链：

```text
Authority=Software Signing
Authority=Apple Code Signing Certification Authority
Authority=Apple Root CA
Signed Time=Dec 20, 2022
```

完整 `--verify` 返回 `resource envelope is obsolete (custom omit rules)`。忽略资源的检查返回成功，同时明确写着 `valid on disk (not all contents verified)` 和 `satisfies its Designated Requirement`。

因此这里表述为“保留 Apple 签名信息，与固定上游提交逐文件一致”，不声称“当前系统完整资源封套验证通过”。本仓库未重签名、未增添 I225 personality。

## 许可边界

`LICENSE` 适用于本仓库新增的文档、配置示例和脚本。它不改变或重新授予 Apple 驱动文件的许可；Apple 驱动文件保留原权利归属。本项目是配置与实测资料整理，不是自行开发的 Apple 网卡驱动。
