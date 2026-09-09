# Project Memory

## Context

- Repository: `https://github.com/hang-jin/editaplot`
- Primary supported environment: Windows 10/11 x64 on physical hardware.
- Origin 2024b is the fully verified baseline; Origin/OriginPro 2021–2026b is the compatibility target.

## Decisions

- Parallels support targets Apple Silicon only; Intel Mac is out of scope.
- Keep Origin automation inside the Windows 11 ARM guest. A macOS host may orchestrate the guest through Parallels' native command channel, but must not expose Origin COM over the network.
- Require x64 CPython, x64 Origin, and x64 `OriginExt` inside the guest; native ARM64 Python remains unsupported. On Windows 11 ARM, identify x64 CPython through `sysconfig.get_platform() == "win-amd64"` because `platform.machine()` still reports `ARM64` under emulation.
- Public releases contain no Origin path. On first Skill use, the agent asks the user to start and sign in to the Windows guest, then setup discovers Origin and persists `origin_home` in the untracked `.editaplot-local.json`. When discovery is absent or ambiguous, `setup --origin-home` validates and persists the user-confirmed path. Later Doctor, smoke, and render calls reuse it; their explicit `--origin-home` remains a one-call override.
- Preserve the existing handshake, safety, redaction, and artifact-verification contracts when evaluating virtual-machine support.
- Optional OPJU format templates use `render --format-template-opju`: the worker hash-binds the
  read-only file, draws normally, transfers the source graph page's complete COM Theme tree to the
  result, then resaves and re-exports. This route still requires a real Windows Origin smoke test
  before compatibility can be claimed.
- The user's downstream repository is `https://github.com/OthinusG/editaplot_mac_parallels`. It keeps
  its GitHub Fork relationship. `upstream-main` is an exact upstream mirror; `main` is the published
  upstream-plus-Parallels integration branch. Scheduled synchronization tests a temporary candidate
  on Windows CPython 3.10–3.12 before fast-forwarding `main` and fails closed on conflicts or drift.
  Repository Actions grants `GITHUB_TOKEN` read/write workflow permission. After enabling it on
  2026-09-09, live run 34321597655 passed and kept the exact mirror with no temporary branch left.

## Operational Notes

- Do not store secrets here. Record only where secret configuration lives if that becomes relevant.
- The Apple Silicon qualification VM uses Windows 11 ARM without guest networking. Host-downloaded
  x64 CPython 3.12.10 and a `win_amd64` wheelhouse successfully support offline setup. The pinned
  installer is verified on the host and installed only for the signed-in Windows user.
- The macOS launcher must build the selected guest CPython minor's locked `win_amd64` wheelhouse on
  the host and pass it to guest setup through Parallels Home sharing with `PIP_NO_INDEX=1`; documentation-only offline instructions are insufficient.
- macOS CPython cannot run the Windows Origin bridge. If compatible guest Python is absent, the
  normal launcher stops; only explicit user consent permits `--install-python` to download and
  verify the pinned official x64 installer on macOS and install it for the signed-in guest user.
  An explicit `--install-python` request must force environment recovery even when setup metadata
  already exists, because a stale managed environment may point to a removed base interpreter.
- Origin 2024 SR1 (10.10.178) passed the isolated smoke, program-path readback, OPJU/PNG/PDF/TIF
  export, representative XRD render, and programmatic verify gates under Parallels. The XRD test
  image exposed pre-existing top legend clipping, so that artifact did not receive a human visual-QA pass.
- `prlctl exec --current-user` may return `Invalid argument` when the interactive guest channel is
  stale; opening the VM's Coherence Windows PowerShell app restored it. Never fall back to the
  default `SYSTEM` channel for Origin COM.
