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
