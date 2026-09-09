# Apple Silicon Parallels Origin Handshake

## Scope

Support the existing EditaPlot CLI inside a Windows 11 on ARM Parallels guest. The public Skill starts without an Origin path. On first use, the agent asks the user to start and sign in to the guest, then the macOS launcher enters the current-user session, discovers Origin, and persists its directory in Skill-local configuration. Intel Mac, native macOS rendering, remote COM, and GUI automation are out of scope.

The supported runtime remains x64 CPython 3.10–3.12 with x64 Origin/OriginPro and the locked x64 `originpro`/`OriginExt` packages. Windows 11 ARM may report the operating-system machine as `ARM64`, so the gate verifies the interpreter build platform as `win-amd64`. A native `win-arm64` Python process remains unsupported.

## Setup and persisted default

No `.editaplot-local.json` or machine-specific path is shipped. `editaplot.cmd setup` uses the active `Origin.Application` registration when it resolves to an existing `Origin64.exe`. If the launch registration is absent, setup may use the only installed Origin candidate; it must not guess when multiple inactive installations exist. The resolved directory is written to the untracked `.editaplot-local.json` as `origin_home`. When automatic discovery is absent or ambiguous, `setup --origin-home <directory-or-Origin64.exe>` validates and persists the user-confirmed path.

Subsequent `doctor`, `origin-smoke`, and `render` calls automatically use the persisted value. An explicit `--origin-home` on a command overrides the persisted default for that invocation. Updating the Skill preserves the previous value when Origin discovery is temporarily unavailable.

## Offline dependency bootstrap

The Windows guest does not need network access. Before first setup, the macOS launcher obtains the
selected guest CPython minor from the dependency-free diagnostic command, downloads the exact
locked `win_amd64` wheels into the macOS user cache, and exposes that directory through Parallels
Home sharing. Guest setup runs with `PIP_NO_INDEX=1` and `PIP_FIND_LINKS` pointing at that cache.
The cache is reusable and contains no Origin path or user data.

## CLI contract

The following commands accept an optional explicit installation constraint:

```text
editaplot.cmd doctor --origin-home <directory-or-Origin64.exe>
editaplot.cmd origin-smoke --origin-home <directory-or-Origin64.exe> --output-dir <directory>
editaplot.cmd render --origin-home <directory-or-Origin64.exe> <render-plan.json>
```

When supplied, the path must resolve to an existing `Origin64.exe`. EditaPlot prepends its directory to the worker `PATH`, but does not install Origin, change COM registration, or modify the registry.

Doctor compares the explicit executable with the active `Origin.Application` registration. A mismatch makes `ready_for_render` false and adds `origin_installation_mismatch` to `manual_blockers`.

Every live Origin session reads the actual program directory from Origin after COM activation. A mismatch closes the EditaPlot-owned instance and fails with:

```json
{
  "code": "origin_installation_mismatch",
  "stage": "validate_origin_home"
}
```

Successful environment and compatibility reports include `origin_home_verified: true`; they do not add a second Parallels-specific rendering backend.

## Acceptance criteria

- Directory and direct `Origin64.exe` inputs normalize to the same installation.
- Missing files and non-`Origin64.exe` files fail before worker launch.
- Doctor cannot report render readiness when the registered Origin differs from the requested installation.
- Smoke and render workers inherit the explicit Origin directory through a private environment constraint.
- A live isolated session verifies Origin's own program-path readback before initializing a project.
- Failure cleanup, error redaction, job serialization, smoke artifacts, and render verification remain unchanged.
- Existing commands without `--origin-home` remain backward compatible and use the setup-time default when present.
- Windows 11 ARM accepts only an x64 (`win-amd64`) CPython build; native ARM64 Python remains rejected.
- Setup persists the active Origin directory, refuses ambiguous inactive candidates, and preserves an existing default when rediscovery is unavailable.
- Public release artifacts contain neither `.editaplot-local.json` nor an Origin installation path.
- First use stops until the user has started and signed in to the guest; the macOS launcher uses only `--current-user`.
- `setup --origin-home` validates and persists the path supplied after unsuccessful or ambiguous discovery.
- First setup downloads only the selected guest Python minor's locked `win_amd64` wheels on macOS and installs them in the offline guest without contacting an index.
- Explicit per-command `--origin-home` overrides the persisted default.

## Verification

- Focused unit tests cover path normalization, command propagation, Doctor mismatch, live match, and live mismatch cleanup.
- Run the Origin session, Doctor, smoke CLI, and core CLI test subsets.
- Final Parallels qualification still requires a real Windows 11 ARM guest with the user-selected Origin installation; macOS unit tests cannot establish COM compatibility.
