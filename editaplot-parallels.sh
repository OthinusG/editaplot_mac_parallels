#!/bin/sh
set -eu

usage() {
    printf '%s\n' \
        'Usage: ./editaplot-parallels.sh [--vm NAME] [--origin-home WINDOWS_PATH] [--] [EditaPlot arguments...]' \
        'Example: ./editaplot-parallels.sh --vm "Windows 11" -- doctor'
}

fail() {
    printf 'EditaPlot Parallels: %s\n' "$1" >&2
    exit "${2:-2}"
}

vm_name=''
origin_home=''
while [ "$#" -gt 0 ]; do
    case "$1" in
        --vm)
            [ "$#" -ge 2 ] || fail '--vm requires a value.'
            vm_name=$2
            shift 2
            ;;
        --origin-home)
            [ "$#" -ge 2 ] || fail '--origin-home requires a value.'
            origin_home=$2
            shift 2
            ;;
        --help|-h)
            usage
            exit 0
            ;;
        --)
            shift
            break
            ;;
        *)
            break
            ;;
    esac
done

[ "$(uname -m)" = 'arm64' ] || fail 'Apple Silicon macOS is required.' 3
command -v prlctl >/dev/null 2>&1 || fail 'Parallels Desktop Pro or Business CLI (prlctl) was not found.' 3

if [ -z "$vm_name" ]; then
    vm_list=$(prlctl list -a -o name --no-header | sed '/^[[:space:]]*$/d')
    vm_count=$(printf '%s\n' "$vm_list" | awk 'NF { count += 1 } END { print count + 0 }')
    [ "$vm_count" -eq 1 ] || {
        printf '%s\n' "$vm_list" >&2
        fail 'Specify --vm NAME because exactly one virtual machine was not found.' 3
    }
    vm_name=$vm_list
fi

status=$(prlctl status "$vm_name") || fail 'The selected virtual machine was not found.' 3
printf '%s\n' "$status" | grep -qi 'running' ||
    fail 'Start the virtual machine, sign in to Windows, then run this command again.' 3

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
case "$script_dir" in
    "$HOME"/*) relative_repo=${script_dir#"$HOME"/} ;;
    *) fail 'Clone the repository inside the macOS home folder so Parallels can resolve the shared home directory.' 3 ;;
esac

to_guest_path() {
    printf '\\\\%s\\%s\\%s' 'Mac' 'Home' "$(printf '%s' "$1" | sed 's|/|\\|g')"
}

repo_guest=$(to_guest_path "$relative_repo")
skill_relative='.codex/skills/editaplot'
skill_guest=$(to_guest_path "$skill_relative")
local_config="$HOME/$skill_relative/.editaplot-local.json"
win_sep=$(printf '\\')

validate_cmd_text() {
    case "$1" in
        *[\&\|\<\>\^\%\!\"]*) fail 'Arguments containing cmd.exe metacharacters are not supported.' 2 ;;
    esac
}

run_guest_line() {
    prlctl exec "$vm_name" --current-user cmd.exe /d /s /c "$1"
}

configured=false
if [ -f "$local_config" ] && grep -Eq '"origin_home"[[:space:]]*:[[:space:]]*"[^" ]' "$local_config"; then
    configured=true
fi

if [ "$configured" = false ] || [ -n "$origin_home" ]; then
    setup_line="\"$repo_guest${win_sep}editaplot.cmd\" setup --target \"$skill_guest\""
    if [ -n "$origin_home" ]; then
        validate_cmd_text "$origin_home"
        setup_line="$setup_line --origin-home \"$origin_home\""
    fi
    printf '%s\n' 'Configuring EditaPlot in the signed-in Windows user session...' >&2
    run_guest_line "$setup_line" ||
        fail 'Guest setup failed. Keep Windows signed in and do not use the SYSTEM channel.' 4
    if ! [ -f "$local_config" ] || ! grep -Eq '"origin_home"[[:space:]]*:[[:space:]]*"[^" ]' "$local_config"; then
        fail 'Origin was not uniquely discovered. Rerun with --origin-home "<Windows Origin directory>".' 4
    fi
fi

if [ "$#" -eq 0 ]; then
    set -- doctor
fi

command_line="\"$skill_guest${win_sep}editaplot.cmd\""
for argument in "$@"; do
    validate_cmd_text "$argument"
    command_line="$command_line \"$argument\""
done
run_guest_line "$command_line" ||
    fail 'The guest command failed. If --current-user is unavailable, open Windows PowerShell in Coherence mode once and retry.' 4
