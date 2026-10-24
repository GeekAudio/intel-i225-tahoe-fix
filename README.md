# Intel I225-V · macOS Tahoe 有线网卡修复

[English](README.en.md)

[下载 v1.0.0 修复包](https://github.com/GeekAudio/intel-i225-tahoe-fix/releases/latest) · [文件校验清单](SHA256SUMS)

在 ASUS Z690 + Intel I225-V（`8086:15f3`）上，用 `AppleIntelI210Ethernet.kext 2.3.1` 替代出现网络 panic 的 AppleIGC，恢复 macOS Tahoe 的有线连接。这里整理的是一台机器实际使用的配置与排查证据，供相同问题复现与对照。

**已实测：驱动加载、DHCP、默认路由与联网正常，链路协商为 1000baseT 全双工。** 本仓库不承诺 2.5GbE、所有 I225/I226 型号或长期睡眠稳定性。

## 本机验证范围

| 项目 | 结果 |
| --- | --- |
| 硬件 | ASUS Z690 / Core i7-12700K / Intel I225-V，原始 PCI ID `8086:15f3` |
| 系统 | macOS 26.7.1，build `25G241`；Darwin `25.6.0` |
| OpenCore | 1.0.8 |
| 替换的驱动 | `com.sxx.AppleIGC`，`CFBundleVersion=1.9d2` |
| 当前加载 | `com.apple.driver.AppleIntelI210Ethernet`，版本 `2.3.1` |
| 已测试组合 | I210 kext + `device-id=0x1533` + `built-in=01` + `e1000=0` |
| 首次恢复 | 2026-10-21；2026-10-24 再次确认 I210 仍在加载 |
| 链路实测 | 1000baseT，全双工，flow control；该结果不等于吞吐测速 |

## 适合什么问题

本机使用 AppleIGC 时，多次出现以下内核断言，调用栈经过网络输入线程：

```text
assertion failed: m->m_flags & M_PKTHDR
uipc_mbuf.c:4839
dlil_create_input_thread
```

禁用 AppleIGC 后，历史观察窗口约 40 小时、38 次 RTC 唤醒没有再次记录同签名网络 panic，但有线接口也随之消失。随后采用本仓库组合恢复有线。

这个对照支持本机绕开 AppleIGC；它没有证明驱动内部是哪条代码写坏 mbuf，也不代表所有同签名 panic 都来自 AppleIGC。上游有[相近硬件和相同断言的报告 #35](https://github.com/SongXiaoXi/AppleIGC/issues/35)。更完整的证据与未验证项见 [验证记录](docs/EVIDENCE.zh-CN.md)。

## 下载内容

| 路径 | 内容 |
| --- | --- |
| `Kexts/AppleIntelI210Ethernet.kext` | 本机使用的 2.3.1 驱动包，未修改内容 |
| `examples/config.fragment.plist` | `Kernel > Add` 和 `DeviceProperties > Add` 示例，仅包含有线相关内容 |
| `examples/boot-args.txt` | 需要追加的单个参数 `e1000=0` |
| `tools/check_config.py` | 检查是否复现本机组合的只读脚本，依赖 Python 3 |
| `SHA256SUMS` | 发布文件的 SHA-256 清单 |
| [来源说明](docs/PROVENANCE.md) | 固定上游提交、逐文件哈希、签名检查边界 |

**配置片段不能直接当完整 `config.plist` 启动，也不能覆盖整段 boot-args。** PCI 路径是本机的示例，必须改成你自己的有线网卡路径。

## 安装

### 1. 保存可回退的 EFI

备份整份当前 EFI，并准备可以启动的备用 EFI / U 盘。确认目标 ESP 后再挂载；盘号可能在重启后变化，不要复制别人的 `disk0s1`。

在工作副本上编辑。保留当前 SMBIOS、三码、其他硬件配置和已有启动参数。

### 2. 停用旧有线驱动，放入 I210

在 `Kernel > Add` 中将 `AppleIGC.kext` 设为 `Enabled=false`，或移除该条目。检查同一网卡是否还由其他替代驱动认领，例如 `SimpleVGBE`。不要同时启用两套。

把本仓库的 `Kexts/AppleIntelI210Ethernet.kext` 复制到目标 `EFI/OC/Kexts/`。按照 [配置片段](examples/config.fragment.plist) 添加一条 `Kernel > Add`：

```text
Arch           x86_64
BundlePath     AppleIntelI210Ethernet.kext
Enabled        true
ExecutablePath Contents/MacOS/AppleIntelI210Ethernet
PlistPath      Contents/Info.plist
MinKernel      （空）
MaxKernel      （空）
```

本机条目的版本上下限为空；这只是在复现现状，不代表其他 macOS 版本经过测试。若共用 EFI 启动多个系统，应按自己的系统版本规划加载范围。

### 3. 合并有线网卡属性

查清有线网卡的 OpenCore PCI 路径后，把示例属性合并到该节点，保留节点里其他需要的键。本机路径为：

```text
PciRoot(0x0)/Pci(0x1C,0x2)/Pci(0x0,0x0)
```

| 属性 | 类型 | 示例值 |
| --- | --- | --- |
| `device-id` | Data，4 字节 | `33 15 00 00`（base64 `MxUAAA==`，小端 `0x1533`） |
| `built-in` | Data，1 字节 | `01`（base64 `AQ==`） |
| `device_type` | String | `Ethernet` |
| `model` | String | `Intel I210 Ethernet` |

`model` 只是显示名称，不会把物理芯片变成 I210。

**关于仿冒的必要性：** 随包 `Info.plist` 同时有 `AppleIntelI210` 和 `AppleIntelI225` personality，后者已经包含 `pci8086,15f3`。因此本仓库只记录“带 `0x1533` 仿冒的组合已成功”，没有做过去掉仿冒的对照，不能断言该属性对每台机器都必需。

### 4. 追加启动参数

在以下位置现有 `boot-args` 字符串的末尾，以空格分隔，**仅追加一次**：

```text
e1000=0
```

位置：`NVRAM > Add > 7C436110-AB2A-4BBB-A880-FE41995C9F82 > boot-args`。同时确认 `NVRAM > Delete > 同一 GUID` 的数组含 `boot-args`，以使配置中的值能在启动时重新写入。

这是本机已测试的参数。首次成功启动后仍生成过 E1000 dext 的 abort 报告，2026-10-24 也仍有新记录，因此它**不等于完全消除所有 dext 启动或崩溃**。本仓库没有验证 `dk.e1000=0`，不将它作为额外必装项。

### 5. 校验后落盘

用与你的 OpenCore 同版本的官方 `ocvalidate` 检查**完整配置**，并核对引用的文件存在：

```sh
plutil -lint /你的工作副本/EFI/OC/config.plist
/你的OpenCore工具目录/ocvalidate /你的工作副本/EFI/OC/config.plist
python3 tools/check_config.py /你的工作副本/EFI/OC/config.plist \
  --pci-path 'PciRoot(0x0)/Pci(0x1C,0x2)/Pci(0x0,0x0)'
```

以上 PCI 路径也要替换。只读脚本检查本仓库组合，不替代 `ocvalidate` 或重启实测。**不要对片段运行 `ocvalidate` 并将结果视为整份配置验证。**

确认差异只涉及目标有线驱动、目标网卡属性及追加的参数。同步到目标 ESP 后执行 `sync`，卸载再挂载，比较配置及驱动 SHA-256，确认 FAT 写入已保存，然后重启。

本次整理没有额外调整 SIP、AMFI 或 SecureBootModel。测试机原本已有其他驱动所需的安全设置，因此本仓库没有证明此旧 kext 在完整默认安全策略下可加载，也不提供一份适合所有机器的安全开关组合。

## 重启后的判断

```sh
kmutil showloaded | grep -E 'AppleIntelI210Ethernet|AppleIGC|SimpleVGBE'
networksetup -listallhardwareports
ifconfig enX
route -n get default
```

把 `enX` 换成实际的 Ethernet 接口。接口编号可能变化，不要把 `en0` 当作安装成功的硬性标准。

应确认：I210 已加载、旧驱动未加载、接口出现、获取地址、`status: active`、默认路由及实际联网正常。链路速率以 `ifconfig` 为准，吞吐请另用局域网测速验证。之后再分别测试拔插网线、持续传输、重启与多次睡眠唤醒。

检查 `en0` 是否换了设备，记录接口归属；不要为了修有线顺手更换 ROM、序列号或清空所有网络配置。

## 回滚

如果无接口、不能联网、睡眠后断线或出现新的 panic，先用备用 EFI 启动，恢复操作前的完整 EFI 备份。若采用手工回退，应停用 I210 条目、还原目标 PCI 节点原属性、只移除本次追加的参数，恢复改前的驱动选择并重新校验。

本机改前的安全回退状态是“禁用 AppleIGC，有线不可用，使用其他可用网络”。重新启用原 AppleIGC 可能同时带回原来的 panic，不应把它描述为稳定修复。

## 来源与反馈

驱动来自 [0xHJK/Intel-NUC9-i7-9850H-macOS 的固定提交](https://github.com/0xHJK/Intel-NUC9-i7-9850H-macOS/tree/df21255aaad44876aa2a572972521e1ad8069da5/EFI-macOS-Sonoma-14.3-OpenCore/EFI/OC/Kexts/AppleIntelI210Ethernet.kext)，与本地使用包逐文件一致。它保留 Apple 签名信息；完整资源封套校验存在旧格式限制，见 [来源说明](docs/PROVENANCE.md)。感谢 Apple、原仓库维护者以及 AppleIGC 社区的诊断记录。

反馈请提供原始 PCI ID、macOS build、OpenCore 版本、实际加载的有线驱动、链路协商结果和具体复现条件。上传配置或日志前移除三码、MAC、内网地址、账号和 token。Apple 驱动文件的权利归原权利人；本仓库新增说明、示例与脚本采用 MIT 许可，见 [LICENSE](LICENSE)。
