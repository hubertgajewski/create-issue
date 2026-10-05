#!/bin/sh

set -eu

PROGRAM=${0##*/}
PACKAGE_BASE_URL=https://gitlab.com/api/v4/projects/85407514/packages/generic/create-issue
INSTALLATION_GUIDE=https://gitlab.com/hubertgajewski-ai/create-issue/-/blob/main/docs/installation.md

# Generated from release-contract.json; tests require an exact match.
CLIENT_ROOT_ENTRIES='claude-code=.claude/skills codex=.agents/skills cursor=.agents/skills gemini=.agents/skills'
CLIENT_LABEL_ENTRIES='claude-code=Claude Code|codex=Codex|cursor=Cursor|gemini=Gemini CLI'
UNSUPPORTED_CLIENTS='claude-chat'

supported_clients() {
    list=
    for client_entry in $CLIENT_ROOT_ENTRIES; do
        list="${list:+$list, }${client_entry%%=*}"
    done
    printf '%s' "$list"
}

usage() {
    cat <<EOF
Usage: $PROGRAM [--client CLIENT] [--scope user|project] [--version vMAJOR.MINOR.PATCH] [--update] [--asset-dir DIR]

Downloads a versioned Create Issue package, verifies its SHA-256 checksum, and
installs it in the selected client's skill directory. In a terminal, missing
client and scope values are prompted for. Automation must provide both.
--asset-dir is for verified offline assets; it must contain the archive and checksum.

Supported clients: $(supported_clients)
EOF
}

fail() {
    printf '%s: %s\n' "$PROGRAM" "$*" >&2
    exit 1
}

# Resolves a contract skill root under the selected root. A `.`, `..`, or empty segment,
# including the one a leading or trailing `/` produces, is rejected rather than skipped.
assert_safe_parent() {
    selected_root=$1
    relative_parent=$2
    case /$relative_parent/ in
        */../*|*/./*|*//*) fail "client destination '$relative_parent' is not a safe relative path; nothing was written" ;;
    esac

    current=$selected_root
    previous_ifs=$IFS
    IFS=/
    set -f
    set -- $relative_parent
    set +f
    IFS=$previous_ifs
    for component in "$@"; do
        current=$current/$component
        if [ -L "$current" ]; then
            fail "$current is a symbolic-link ancestor; replace it manually before installing"
        fi
        if [ -e "$current" ] && [ ! -d "$current" ]; then
            fail "$current is not a directory; replace it manually before installing"
        fi
    done
    case $current/ in
        "$selected_root"/*) ;;
        *) fail "installer destination escapes the selected installation root" ;;
    esac
    safe_parent=$current
}

client=
scope=
version=v1.0.0
update=false
asset_dir=

while [ "$#" -gt 0 ]; do
    case $1 in
        --client|--scope|--version|--asset-dir)
            [ "$#" -ge 2 ] || fail "$1 requires a value"
            case $1 in
                --client) client=$2 ;;
                --scope) scope=$2 ;;
                --version) version=$2 ;;
                --asset-dir) asset_dir=$2 ;;
            esac
            shift 2
            ;;
        --update)
            update=true
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *) fail "unknown argument: $1" ;;
    esac
done

printf '%s\n' "$version" | grep -Eq '^v(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$' ||
    fail "--version must be a semantic version such as v1.0.0"

guided=false
if [ -z "$client" ] || [ -z "$scope" ]; then
    [ -t 0 ] || fail "--client and --scope are required in non-interactive mode"
    guided=true
fi

if [ -z "$client" ]; then
    printf 'Choose your AI client:\n' >&2
    old_ifs=$IFS
    IFS='|'
    set -- $CLIENT_LABEL_ENTRIES
    IFS=$old_ifs
    for label_entry in "$@"; do
        printf '  %-18s %s\n' "${label_entry%%=*}" "${label_entry#*=}" >&2
    done
    attempts=0
    client_valid=false
    while [ "$attempts" -lt 3 ]; do
        printf 'Client ID: ' >&2
        IFS= read -r client || fail "input ended before a client was selected; no files were changed"
        for client_entry in $CLIENT_ROOT_ENTRIES; do
            case $client_entry in "$client="*) client_valid=true; break ;; esac
        done
        [ "$client_valid" = false ] || break
        attempts=$((attempts + 1))
        printf "Unsupported client ID '%s'. Try again.\n" "$client" >&2
    done
    [ "$client_valid" = true ] || fail "no supported client was selected after 3 attempts; no files were changed"
fi

if [ -z "$scope" ]; then
    attempts=0
    while [ "$attempts" -lt 3 ]; do
        printf 'Install for this user or this project? [user/project]: ' >&2
        IFS= read -r scope || fail "input ended before a scope was selected; no files were changed"
        case $scope in user|project) break ;; esac
        attempts=$((attempts + 1))
        printf "Scope must be 'user' or 'project'. Try again.\n" >&2
    done
    case $scope in user|project) ;; *) fail "no valid scope was selected after 3 attempts; no files were changed" ;; esac
fi

skill_root=
client_known=false
for client_entry in $CLIENT_ROOT_ENTRIES; do
    case $client_entry in
        "$client="*) skill_root=${client_entry#*=}; client_known=true; break ;;
    esac
done
if [ "$client_known" = false ]; then
    case " $UNSUPPORTED_CLIENTS " in
        *" $client "*)
            fail "client '$client' has no local skill directory; see $INSTALLATION_GUIDE#other-installation-environments"
            ;;
        *) fail "unsupported client '$client'; supported clients: $(supported_clients)" ;;
    esac
fi

case $scope in
    project)
        root=$(pwd -P) || fail "could not resolve the project installation root"
        ;;
    user)
        [ -n "${HOME:-}" ] || fail "HOME is not set; cannot resolve the user installation directory"
        root=$(CDPATH= cd "$HOME" 2>/dev/null && pwd -P) ||
            fail "could not resolve the user installation root: $HOME"
        ;;
    *) fail "--scope must be 'user' or 'project'" ;;
esac
assert_safe_parent "$root" "$skill_root"
parent=$safe_parent
destination=$parent/create-issue

if { [ -e "$destination" ] || [ -L "$destination" ]; } && [ "$update" != true ]; then
    fail "$destination already exists; inspect the new release, then rerun with --update to replace it"
fi
if [ -L "$destination" ]; then
    fail "$destination is a symbolic link; replace it manually before using --update"
fi

if [ "$guided" = true ]; then
    printf '\nClient: %s\nScope: %s\nDestination: %s\nRelease: %s\n' "$client" "$scope" "$destination" "$version" >&2
    printf 'Continue? [y/N]: ' >&2
    IFS= read -r confirmation || fail "installation cancelled; no files were changed"
    case $confirmation in y|Y|yes|YES|Yes) ;; *) fail "installation cancelled; no files were changed" ;; esac
fi

archive="create-issue-$version.tar.gz"
checksum="$archive.sha256"
tmp_root=
stage=
backup=
lock=
lock_owned=false
activation_owned=false
stage_leaf=
marker=.create-issue-installing

cleanup() {
    status=$?
    if [ "$status" -ne 0 ] && [ "$activation_owned" = true ] && [ -f "$destination/$marker" ]; then
        rm -rf -- "$destination"
    fi
    if [ "$status" -ne 0 ] && [ -n "$stage_leaf" ] && [ -f "$destination/$stage_leaf/$marker" ]; then
        rm -rf -- "$destination/$stage_leaf"
    fi
    if [ "$status" -ne 0 ] && [ -n "$backup" ] && { [ -e "$backup/create-issue" ] || [ -L "$backup/create-issue" ]; } && ! { [ -e "$destination" ] || [ -L "$destination" ]; }; then
        if ! mv "$backup/create-issue" "$destination" 2>/dev/null; then
            printf '%s: rollback failed; the previous installation remains at %s/create-issue\n' "$PROGRAM" "$backup" >&2
        fi
    fi
    [ -z "$stage" ] || rm -rf -- "$stage"
    if [ -n "$backup" ] && { [ -e "$backup/create-issue" ] || [ -L "$backup/create-issue" ]; }; then
        printf '%s: previous installation preserved at %s/create-issue\n' "$PROGRAM" "$backup" >&2
    elif [ -n "$backup" ]; then
        rm -rf -- "$backup"
    fi
    if [ "$lock_owned" = true ] && [ -n "$lock" ]; then
        rm -f -- "$lock/owner"
        rmdir "$lock" 2>/dev/null || true
    fi
    [ -z "$tmp_root" ] || rm -rf -- "$tmp_root"
    trap - EXIT HUP INT TERM
    exit "$status"
}
trap cleanup EXIT
trap 'exit 129' HUP
trap 'exit 130' INT
trap 'exit 143' TERM

umask 077
tmp_root=$(mktemp -d "${TMPDIR:-/tmp}/create-issue-install.XXXXXX") || fail "could not create a private temporary directory"

if [ -n "$asset_dir" ]; then
    [ -f "$asset_dir/$archive" ] || fail "offline archive not found: $asset_dir/$archive"
    [ -f "$asset_dir/$checksum" ] || fail "offline checksum not found: $asset_dir/$checksum"
    cp "$asset_dir/$archive" "$tmp_root/$archive"
    cp "$asset_dir/$checksum" "$tmp_root/$checksum"
else
    command -v curl >/dev/null 2>&1 || fail "curl is required to download release assets"
    package_version=${version#v}
    asset_url="$PACKAGE_BASE_URL/$package_version"
    curl --fail --location --silent --show-error --proto '=https' --tlsv1.2 --max-filesize 67108864 \
        --output "$tmp_root/$archive" "$asset_url/$archive" || fail "failed to download $archive for $version"
    curl --fail --location --silent --show-error --proto '=https' --tlsv1.2 --max-filesize 4096 \
        --output "$tmp_root/$checksum" "$asset_url/$checksum" || fail "failed to download the checksum for $version"
fi

expected=$(awk 'NR == 1 { print $1 }' "$tmp_root/$checksum")
case $expected in
    ''|*[!0-9a-f]*) fail "the checksum file for $version is malformed" ;;
esac
[ "${#expected}" -eq 64 ] || fail "the checksum file for $version is malformed"
if command -v sha256sum >/dev/null 2>&1; then
    actual=$(sha256sum "$tmp_root/$archive" | awk '{ print $1 }')
elif command -v shasum >/dev/null 2>&1; then
    actual=$(shasum -a 256 "$tmp_root/$archive" | awk '{ print $1 }')
else
    fail "sha256sum or shasum is required to verify release assets"
fi
[ "$actual" = "$expected" ] ||
    fail "checksum mismatch for $archive: expected $expected, got $actual; no files were installed"

mkdir "$tmp_root/extracted"
tar -tzf "$tmp_root/$archive" > "$tmp_root/members" || fail "could not inspect $archive"
member_count=$(wc -l < "$tmp_root/members" | tr -d '[:space:]')
[ "$member_count" -le 10000 ] || fail "release package exceeds the 10000-entry safety limit"
tar -tvzf "$tmp_root/$archive" > "$tmp_root/member-types" || fail "could not inspect archive entry types"
while IFS= read -r member_details; do
    case $member_details in
        -*) ;;
        d*) ;;
        *) fail "release package contains a link or special file" ;;
    esac
done < "$tmp_root/member-types"
expanded_bytes=$(tar -xOzf "$tmp_root/$archive" | head -c 134217729 | wc -c | tr -d '[:space:]')
[ "$expanded_bytes" -le 134217728 ] || fail "release package exceeds the 134217728-byte extraction safety limit"
while IFS= read -r member; do
    member=${member%/}
    case $member in
        create-issue|create-issue/*) ;;
        *) fail "release package contains a path outside create-issue/" ;;
    esac
    case /$member/ in
        */../*|*/./*|*//*) fail "release package contains an unsafe path" ;;
    esac
done < "$tmp_root/members"
tar -xzf "$tmp_root/$archive" -C "$tmp_root/extracted" || fail "could not extract $archive"
package="$tmp_root/extracted/create-issue"
[ -f "$package/SKILL.md" ] || fail "release package is missing create-issue/SKILL.md"
[ -f "$package/.claude-plugin/plugin.json" ] || fail "release package is missing version metadata"
for required_dir in references scripts agents; do
    [ -d "$package/$required_dir" ] || fail "release package is missing create-issue/$required_dir/"
done
if find "$package" -type l -print | grep -q .; then
    fail "release package contains symbolic links"
fi
manifest_version=$(sed -n 's/^[[:space:]]*"version"[[:space:]]*:[[:space:]]*"\([^"]*\)"[[:space:]]*,\{0,1\}[[:space:]]*$/\1/p' "$package/.claude-plugin/plugin.json")
[ "$manifest_version" = "${version#v}" ] || fail "release package version does not match requested version $version"

assert_safe_parent "$root" "$skill_root"
[ "$safe_parent" = "$parent" ] || fail "installer destination changed while the package was being verified"
mkdir -p "$parent"
assert_safe_parent "$root" "$skill_root"
[ "$safe_parent" = "$parent" ] || fail "installer destination changed while the package was being verified"
lock="$parent/.create-issue.install.lock"
if ! mkdir "$lock" 2>/dev/null; then
    fail "another installation is active or left $lock; verify no installer is running before removing that lock"
fi
lock_owned=true
printf '%s\n' "$$" > "$lock/owner"
stage=$(mktemp -d "$parent/.create-issue.stage.XXXXXX") || fail "could not create a staging directory beside $destination"
cp -R "$package"/. "$stage" || fail "could not stage the release package"
[ ! -e "$stage/$marker" ] || fail "release package contains the reserved activation marker"
: > "$stage/$marker"
stage_leaf=${stage##*/}

assert_safe_parent "$root" "$skill_root"
[ "$safe_parent" = "$parent" ] || fail "installer destination changed while the package was being verified"
if { [ -e "$destination" ] || [ -L "$destination" ]; } && [ "$update" != true ]; then
    fail "$destination appeared while the package was being verified; no files were installed"
fi
if [ -L "$destination" ]; then
    fail "$destination became a symbolic link while the package was being verified; no files were installed"
fi
if [ -e "$destination" ] || [ -L "$destination" ]; then
    backup=$(mktemp -d "$parent/.create-issue.backup.XXXXXX") || fail "could not create a rollback directory"
    mv "$destination" "$backup/create-issue" || fail "could not move the existing installation for replacement"
fi
assert_safe_parent "$root" "$skill_root"
[ "$safe_parent" = "$parent" ] || fail "installer destination changed during activation"
mv "$stage" "$destination" || fail "could not activate the staged installation"
[ -f "$destination/$marker" ] || fail "destination changed during activation; the staged package was not activated"
activation_owned=true
stage=
[ -f "$destination/SKILL.md" ] || fail "activated installation failed final validation"
rm -f -- "$destination/$marker" || fail "could not finalize the activated installation"
activation_owned=false
if [ -n "$backup" ]; then
    if rm -rf -- "$backup"; then
        backup=
    else
        printf '%s: installed successfully, but the previous installation could not be removed from %s/create-issue\n' "$PROGRAM" "$backup" >&2
    fi
fi

case $client in
    claude-code) first_command='/create-issue <what the issue is about>' ;;
    codex) first_command='$create-issue <what the issue is about>' ;;
    cursor) first_command='/create-issue <what the issue is about> in Agent chat' ;;
    *) first_command='Describe the issue you want drafted and approve the create-issue activation prompt' ;;
esac

printf 'Installed Create Issue %s\n' "$version"
printf 'Destination: %s\n' "$destination"
printf 'Verification: SHA-256 %s\n' "$actual"
printf 'First draft: %s\n' "$first_command"
