ruff := "uv run ruff"

sync:
    uv sync --all-extras --all-groups --all-packages

yatb:
    AUTH_SIMPLE_DEBUG_USERNAME="Debug" DEBUG=1 uv run uvicorn yatb.app:app

yatb-reload:
    AUTH_SIMPLE_DEBUG_USERNAME="Debug" DEBUG=1 uv run uvicorn yatb.app:app --reload

debug-yatb:
    AUTH_SIMPLE_DEBUG_USERNAME="Debug" DEBUG=1 uv run debugpy --listen 5678 --wait-for-client -m uvicorn yatb.app:app

cli *args:
    uv run -m ycli {{ args }}

babel-extract:
    uv run pybabel extract -F pyproject.toml --add-location=file -o messages.pot src/yatb

babel-update:
    uv run pybabel update -i messages.pot -d src/yatb/locale -D messages

babel-compile:
    uv run pybabel compile -d src/yatb/locale -D messages
    for catalog in src/yatb/locale/*/LC_MESSAGES/private.po; do if [ -f "$catalog" ]; then uv run pybabel compile -i "$catalog" -o "${catalog%.po}.mo" || exit $?; fi; done

babel: babel-extract babel-update babel-compile

# --- private features: run ONLY on the private branch ---
# Public catalogs arrive through merges; only private.po is updated here.
babel-extract-private:
    uv run pybabel extract -F pyproject.toml --add-location=file -o private.pot src/yatb

babel-update-private:
    uv run python contrib/update_private_catalog.py

babel-private: babel-extract-private babel-update-private babel-compile

precom: fix format

fix:
    {{ ruff }} check --select 'I001,F401,UP035,D213' --fix

format:
    {{ ruff }} format

fix-EXE002:
    {{ ruff }} check --select 'EXE002' --output-format json . | jq '.[] | .filename' -r | xargs chmod -x

reset-rights:
    git diff --numstat | awk '{ if ($1 == "0" && $2 == "0") print $3 }' 
    # | xargs -I{} git checkout HEAD -- "{}"

reset-rights-x:
    git diff --numstat --staged | awk '{ if ($1 == "0" && $2 == "0") print $3 }' 
    # | xargs -I{} git restore --staged -- "{}"
    # | xargs -I{} git restore --staged -- "{}"
    # | xargs -I{} git checkout HEAD -- "{}"

# git cringe workflow

git-main branch="improvements":
    #!/usr/bin/env bash
    set -eu
    STASH_MSG="just-fast-switch-to-main-$(date +%Y-%m-%d-%H-%M-%S)"
    git stash push -a -u -m "$STASH_MSG" || true
    git checkout "{{ branch }}"
    STASH_REF=$(git stash list | grep -m1 -F ": $STASH_MSG" | cut -d: -f1 || true)
    if [ -n "$STASH_REF" ]; then
        git stash apply "$STASH_REF"
    fi
    echo "Ready to commit"

git-back dst src="improvements":
    #!/usr/bin/env bash
    set -eu
    STASH_BACK="just-fast-switch-to-back-$(date +%Y-%m-%d-%H-%M-%S)"
    git stash push -a -u -m "$STASH_BACK" || true
    git checkout "{{ dst }}"
    git merge "{{ src }}"
    MAIN_REF=$(git stash list | grep -m1 -F ": just-fast-switch-to-main" | cut -d: -f1 || true)
    if [ -n "$MAIN_REF" ]; then
        git stash pop "$MAIN_REF"
    fi
    BACK_REF=$(git stash list | grep -m1 -F ": $STASH_BACK" | cut -d: -f1 || true)
    if [ -n "$BACK_REF" ]; then
        git stash pop "$BACK_REF"
    fi
    echo "Ready to commit"

k3s *args:
    docker compose -f docker-compose.k3s.yaml {{ args }}
