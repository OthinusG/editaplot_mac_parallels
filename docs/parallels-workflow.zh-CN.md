# Apple Silicon Mac + Parallels 完整工作流

## 支持边界

- Apple Silicon Mac；不兼容 Intel Mac。
- Parallels Desktop 中的 Windows 11 ARM。
- Windows guest 内安装 x64 CPython 3.10–3.12、x64 Origin/OriginPro 和 x64 OriginExt。
- Origin Automation 只在 Windows 当前登录用户会话中运行；不开放远程 COM，不需要 VM 联网。

Windows 11 ARM 下的 x64 Python 可能返回 `platform.machine() == "ARM64"`。EditaPlot 通过
`sysconfig.get_platform() == "win-amd64"` 确认解释器实际为 x64；`win-arm64` Python 不受支持。

## 首次调用与本地绑定

公开仓库和发布 Skill 不包含 Origin 路径，也不包含 `.editaplot-local.json`。第一次调用 Skill 时，
Agent 必须先告知用户启动 Windows VM，并登录将来运行 Origin 的 Windows 用户；用户确认桌面就绪后，
从 macOS 仓库根目录运行：

```bash
./editaplot-parallels.sh
```

仅有一台 VM 时脚本自动选择；存在多台时指定名称：

```bash
./editaplot-parallels.sh --vm "<vm-name>"
```

脚本通过 `--current-user` 进入 Windows，执行 setup 并自动发现 Origin。如果没有发现活动注册且安装候选
不唯一，Agent 只在此时询问用户的 Windows 安装目录，然后持久化：

```bash
./editaplot-parallels.sh --vm "<vm-name>" \
  --origin-home '<origin-installation-directory>'
```

也可以在 guest PowerShell 中直接执行等价命令：

```powershell
Set-Location "<shared-repository-directory>"
.\editaplot.cmd --diagnose
.\editaplot.cmd setup --target "<shared-codex-skill-directory>" `
  --origin-home "<confirmed-origin-directory>"
```

`setup` 会完成四件事：选择兼容的 x64 CPython、创建项目级 `.editaplot-venv`、发布 Skill、
读取活动 `Origin.Application` 注册位置。自动发现或用户确认的 Origin 目录写入已发布 Skill 的
`.editaplot-local.json`。该文件是本地状态，不进入公开发行包。

自动选择规则：优先采用活动的 `Origin.Application`；没有活动启动注册时，只接受唯一的已安装
Origin 候选；多个未激活候选不会猜测。更新 Skill 时若注册信息暂时不可用，会保留上次路径。

## 离线 Windows VM

VM 不需要联网。macOS 已有的 CPython 只能负责下载，不能在 Windows 中加载 `originpro` 或
`OriginExt`，因此 guest 仍需要 x64 Windows CPython。首次配置会先只读探测；如果没有兼容版本，
脚本会停止，Agent 必须说明这是 Windows 用户范围的软件安装并取得明确同意，然后才运行：

```bash
./editaplot-parallels.sh --vm "<vm-name>" --install-python
```

该命令在 macOS 下载锁定的 python.org x64 安装器，核对 SHA-256，再在 Windows 当前用户会话核对
Python Software Foundation 的有效 Authenticode 签名并静默安装；不使用管理员权限，不启用 guest
网络。随后脚本重新读取 guest 的 x64 CPython 小版本，由 macOS 自动下载对应的锁定 `win_amd64`
wheels 到用户缓存。guest setup 使用
`PIP_NO_INDEX=1` 从 Parallels 共享目录离线安装，不会访问 Python 包索引。

下面的手动命令只用于排查自动下载：

```bash
python3 -m pip download \
  --dest .codex-work/wheelhouse \
  --only-binary=:all: \
  --platform win_amd64 \
  --implementation cp \
  --python-version 312 \
  --abi cp312 \
  --requirement requirements-runtime.lock
```

在 Windows 安装 Python 后，也可以手动用共享 wheelhouse 运行 setup：

```cmd
set PIP_NO_INDEX=1
set PIP_FIND_LINKS=<wheelhouse-file-url>
editaplot.cmd setup --target <shared-codex-skill-directory>
```

手动安装只用于自动流程失败后的排查。Python 安装包必须来自
[python.org](https://www.python.org/downloads/windows/)，并在 Windows 中确认 Authenticode 状态为
`Valid`。不要安装 ARM64 Python，也不要从非官方镜像获取安装器。

## macOS 调用 Windows Skill

先获取 VM 名称：

```bash
prlctl list -a
```

后续命令都必须使用 `--current-user`。不要用默认的 `SYSTEM` 通道运行 Origin：Session 0 无法可靠
承载 GUI/COM Automation。

```bash
prlctl exec "<vm-name>" --current-user cmd.exe /d /c \
  "pushd <shared-codex-skill-directory> && editaplot.cmd doctor"
```

若 `--current-user` 返回 `Invalid argument`，先从 Parallels 融合模式打开一次 Windows PowerShell，
确认 Windows 已登录后重试。持续失败时更新 Parallels Tools。长任务被自动暂停时，临时关闭 VM 的
Pause idle，任务结束后恢复原设置。

## 每次绘图

已发布 Skill 会自动读取保存的 Origin 目录，因此下列命令不再需要 `--origin-home`：

```powershell
.\editaplot.cmd doctor
.\editaplot.cmd start <data-file> --intent "<scientific intent>"
.\editaplot.cmd understand <data-file> --template-id <template-id> --output data-understanding.json
.\editaplot.cmd plan <data-file> --template-id <template-id> `
  --claim "<confirmed claim>" `
  --evidence-role <role> `
  --semantic-confirmation-json semantic-confirmation.json `
  --palette-id ocean_coral `
  --output render-plan.json
$smokeDir = Join-Path $env:TEMP ("EditaPlot-origin-smoke-" + (Get-Date -Format "yyyyMMdd-HHmmss"))
.\editaplot.cmd origin-smoke --output-dir $smokeDir
.\editaplot.cmd render render-plan.json
.\editaplot.cmd verify <output-directory>
```

正式成功必须同时具备：可编辑 OPJU、PNG、PDF、TIF、Origin 对象反读通过、源数据未修改，以及人工
视觉检查通过。显式 `--origin-home <directory-or-Origin64.exe>` 仅用于单次切换 Origin；它不会改写
setup 保存的默认值。

## 更新

更新仓库后，在同一个 Windows 登录用户会话重新运行一次 `setup --target ...`。setup 会原子更新
Skill、复用或重建锁定环境、重新探测活动 Origin，并运行 Doctor。普通 `doctor`、smoke 和 render
不会修改 Origin 注册表、DCOM、防火墙或安装目录。

下游仓库保留 Fork 关系，但把上游源码和 Parallels 扩展分开管理：

- `upstream-main` 精确镜像 `hang-jin/editaplot:main`，不包含 Parallels 修改。
- `main` 是发布分支，保留上游源码之上的 Parallels 提交。
- `automation/upstream-sync` 是一次同步使用的临时候选分支。

`.github/workflows/sync-upstream.yml` 每日运行，也可手动触发。它先更新 `upstream-main`，再把
上游提交合并到临时候选分支；候选必须在 Windows 上通过 CPython 3.10、3.11、3.12 的完整测试、
控制面 lint 和公开发布审计，之后才允许以 fast-forward 更新 `main`。无更新时不产生提交。
合并冲突、测试失败、审计失败或测试期间 `main` 被其他提交更新时，发布分支保持不变；候选分支
在流程结束后自动删除。真实 Origin smoke 仍是本地兼容性门禁，GitHub CI 不会把静态测试包装成
Origin 实机验证。
