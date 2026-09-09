from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(os.name == "nt", reason="macOS POSIX launcher test")


def test_first_use_runs_setup_only_through_current_user(tmp_path: Path) -> None:
    home = tmp_path / "home"
    repository = home / "editaplot"
    repository.mkdir(parents=True)
    source = Path(__file__).resolve().parents[1] / "editaplot-parallels.sh"
    launcher = repository / source.name
    shutil.copy2(source, launcher)
    (repository / "editaplot.cmd").touch()

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    (bin_dir / "uname").write_text("#!/bin/sh\nprintf 'arm64\\n'\n", encoding="utf-8")
    log = tmp_path / "prlctl.log"
    (bin_dir / "prlctl").write_text(
        "#!/bin/sh\n"
        "case \"$1\" in\n"
        "  list) printf 'Windows 11\\n' ;;\n"
        "  status) printf 'running\\n' ;;\n"
        f"  exec) printf '%s\\n' \"$*\" >> '{log}'; "
        "case \"$*\" in *--diagnose*) "
        "printf '{\"selected\":{\"version_info\":[3,12,10]}}\\n';; esac ;;\n"
        "esac\n",
        encoding="utf-8",
    )
    (bin_dir / "python3").write_text(
        "#!/bin/sh\n"
        "case \"$1\" in\n"
        "  -c) printf '12\\n' ;;\n"
        "  -m) exit 0 ;;\n"
        "esac\n",
        encoding="utf-8",
    )
    os.chmod(bin_dir / "uname", 0o700)
    os.chmod(bin_dir / "prlctl", 0o700)
    os.chmod(bin_dir / "python3", 0o700)

    completed = subprocess.run(
        ["/bin/sh", str(launcher)],
        cwd=repository,
        env={"HOME": str(home), "PATH": f"{bin_dir}:/usr/bin:/bin"},
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 4
    invocation = log.read_text(encoding="utf-8")
    assert "--current-user" in invocation
    assert " setup --target " in invocation
    assert "PIP_NO_INDEX=1" in invocation
    assert "PIP_FIND_LINKS=" in invocation
    assert "Origin was not uniquely discovered" in completed.stderr


def test_missing_guest_python_requires_consent_then_bootstraps_offline(tmp_path: Path) -> None:
    home = tmp_path / "home"
    repository = home / "editaplot"
    repository.mkdir(parents=True)
    launcher = repository / "editaplot-parallels.sh"
    shutil.copy2(Path(__file__).resolve().parents[1] / launcher.name, launcher)
    (repository / "editaplot.cmd").touch()

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log = tmp_path / "prlctl.log"
    download_log = tmp_path / "download.log"
    checksum_log = tmp_path / "checksum.log"
    installed = tmp_path / "python-installed"
    (bin_dir / "uname").write_text("#!/bin/sh\nprintf 'arm64\\n'\n", encoding="utf-8")
    (bin_dir / "prlctl").write_text(
        "#!/bin/sh\n"
        "case \"$1\" in\n"
        "  list) printf 'Windows 11\\n' ;;\n"
        "  status) printf 'running\\n' ;;\n"
        f"  exec) printf '%s\\n' \"$*\" >> '{log}'; case \"$*\" in\n"
        "    *powershell.exe*) exit 0 ;;\n"
        f"    *--diagnose*) if [ -f '{installed}' ]; then "
        "printf '{\"selected\":{\"version_info\":[3,12,10]}}\\n'; else "
        "printf '{\"ok\":false,\"error\":{\"code\":\"python_command_unavailable\"}}\\n'; exit 1; fi ;;\n"
        f"    *python-3.12.10-amd64.exe*) touch '{installed}' ;;\n"
        "  esac ;;\n"
        "esac\n",
        encoding="utf-8",
    )
    (bin_dir / "python3").write_text(
        "#!/bin/sh\n"
        "case \"$1\" in\n"
        "  -c) printf '12\\n' ;;\n"
        "  -m) exit 0 ;;\n"
        "esac\n",
        encoding="utf-8",
    )
    (bin_dir / "curl").write_text(
        "#!/bin/sh\n"
        f"printf '%s\\n' \"$*\" >> '{download_log}'\n"
        "while [ \"$#\" -gt 0 ]; do\n"
        "  if [ \"$1\" = '--output' ]; then shift; : > \"$1\"; fi\n"
        "  shift\n"
        "done\n",
        encoding="utf-8",
    )
    (bin_dir / "shasum").write_text(
        "#!/bin/sh\n"
        f"printf '%s\\n' \"$*\" >> '{checksum_log}'\n"
        "[ -f \"$3\" ] || exit 1\n"
        "printf '67b5635e80ea51072b87941312d00ec8927c4db9ba18938f7ad2d27b328b95fb  %s\\n' \"$3\"\n",
        encoding="utf-8",
    )
    for executable in bin_dir.iterdir():
        os.chmod(executable, 0o700)

    env = {"HOME": str(home), "PATH": f"{bin_dir}:/usr/bin:/bin"}
    refused = subprocess.run(
        ["/bin/sh", str(launcher)],
        cwd=repository,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    approved = subprocess.run(
        ["/bin/sh", str(launcher), "--install-python"],
        cwd=repository,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert refused.returncode == 4
    assert "explicit consent" in refused.stderr
    assert "--install-python" in refused.stderr
    assert approved.returncode == 4
    assert installed.exists()
    assert "https://www.python.org/ftp/python/3.12.10/python-3.12.10-amd64.exe" in download_log.read_text()
    assert ".part" in checksum_log.read_text()
    invocation = log.read_text(encoding="utf-8")
    assert "Get-AuthenticodeSignature" in invocation
    assert "Python Software Foundation" in invocation
    assert "InstallAllUsers=0" in invocation
    assert "PIP_NO_INDEX=1" in invocation
