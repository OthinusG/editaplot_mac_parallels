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

VM 不需要联网。可在 macOS 下载 Python 官方 x64 安装包和 Windows wheelhouse，再通过共享目录使用：

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

在 Windows 安装 Python 后，用共享 wheelhouse 运行 setup：

```cmd
set PIP_NO_INDEX=1
set PIP_FIND_LINKS=<wheelhouse-file-url>
editaplot.cmd setup --target <shared-codex-skill-directory>
```

Python 安装包必须来自 [python.org](https://www.python.org/downloads/windows/)，并在 Windows 中确认
Authenticode 状态为 `Valid`。不要安装 ARM64 Python，也不要从非官方镜像获取安装器。

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

下游仓库通过 `.github/workflows/sync-upstream.yml` 每日获取并合并
`hang-jin/editaplot:main`，也可在 GitHub Actions 页面手动触发。无冲突时更新直接进入下游 `main`；
发生冲突时工作流失败且不会推送半成品，需要在本地解决冲突并完成测试后再推送。
