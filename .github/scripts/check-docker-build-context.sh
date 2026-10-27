#!/usr/bin/env bash
# Check what reaches the django image, and that deploy/docker keeps LF endings.
#
# Run from anywhere inside the repository:
#
#     bash .github/scripts/check-docker-build-context.sh
#
# Needs git and docker with BuildKit. It pulls no images: the build is
# `FROM scratch`, copying the build context out to a temporary folder so the
# files .dockerignore lets through can be listed.
#
# It creates decoy files (a .env, a secret key, a database dump, an upload...)
# for the duration of the check, and removes only the decoys it created.
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

failures=0
fail() { echo "FAIL: $*"; failures=$((failures + 1)); }
pass() { echo "ok:   $*"; }

echo "== Line endings under deploy/docker"
# Every file must check out with LF, whatever the user's core.autocrlf.
while IFS= read -r line; do
    case "$line" in
        *": eol: lf") ;;
        *) fail "not forced to LF on checkout: ${line%%: eol:*}" ;;
    esac
done < <(git ls-files -z deploy/docker | xargs -0 git check-attr eol --)
# And none may be stored with CRLF (or mixed endings) in the repository itself.
while IFS= read -r line; do
    fail "stored with CRLF or mixed endings:${line##*$'\t'}"
done < <(git ls-files --eol deploy/docker | grep -E '^i/(crlf|mixed)' || true)
[ "$failures" -eq 0 ] && pass "all files under deploy/docker are LF"

echo "== Build context of the django image"
decoys=(
    .env
    deploy/docker/.env
    deploy/docker/.env.local
    qatrack/local_settings.py
    qatrack/local_decoy.py
    deploy/docker/user-data/secret_key.txt
    deploy/docker/backups/db_decoy.dump
    qatrack/media/uploads/decoy.pdf
    qatrack/static/decoy.css
    site.key
    fixtures/site_export.json
    # A site's own Python packages reach the build only through compose.yaml's
    # separate "site-requirements" context, never through this one, so none of
    # them is copied into the image: a requirements file can hold a private
    # index token. The whole folder is checked below.
    deploy/docker/site-requirements/requirements.txt
    deploy/docker/site-requirements/pip.conf
)
created=()
created_dirs=()
out="$(mktemp -d)"
cleanup() {
    for f in ${created[@]+"${created[@]}"}; do rm -f "$f"; done
    for d in ${created_dirs[@]+"${created_dirs[@]}"}; do rmdir "$d" 2>/dev/null || true; done
    rm -rf "$out"
}
trap cleanup EXIT

for f in "${decoys[@]}"; do
    if [ ! -e "$f" ]; then
        d="$(dirname "$f")"
        if [ ! -d "$d" ]; then
            mkdir -p "$d"
            created_dirs+=("$d")
        fi
        # A comment line: should this script be killed before it cleans up, the
        # decoy left behind is harmless in requirements.txt, pip.conf, .env and
        # local_settings.py.
        echo "# decoy created by check-docker-build-context.sh" > "$f"
        created+=("$f")
    fi
done

printf 'FROM scratch\nCOPY . /\n' | docker build --quiet --file - --output "type=local,dest=$out" . >/dev/null

# Paths the image needs (see deploy/docker/django/Dockerfile and settings.BASE_DIR).
present=(
    manage.py
    pyproject.toml
    uv.lock
    README.md
    LICENSE
    qatrack/settings.py
    qatrack/wsgi.py
    fixtures/defaults/qa
    fixtures/defaults/units
    deploy/docker/django/entrypoint.sh
    deploy/docker/django/init.sh
)
# Paths that must never be in the image. deploy/docker/.env holds the database
# password; it is not tracked, so a fresh checkout has none and it is a decoy above.
absent=(
    "${decoys[@]}"
    deploy/docker/site-requirements
    docs
    .git
)

for p in "${present[@]}"; do
    if [ -e "$out/$p" ]; then pass "present: $p"; else fail "missing from the image: $p"; fi
done
for p in "${absent[@]}"; do
    if [ -e "$out/$p" ]; then fail "leaks into the image: $p"; else pass "absent:  $p"; fi
done

if [ "$failures" -gt 0 ]; then
    echo "$failures check(s) failed. Fix .dockerignore or .gitattributes."
    exit 1
fi
echo "All checks passed."
