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
    pybabel extract -F pyproject.toml -o messages.pot .

babel-update:
    pybabel update -i messages.pot -d src/yatb/locale

babel-compile:
    pybabel compile -d src/yatb/locale

babel: babel-extract babel-update babel-compile

precom: fix format

fix:
    {{ ruff }} check --select 'I001,F401,UP035' --fix

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
    git stash push -a -u -m "just-fast-switch-to-main"
    git checkout "{{ branch }}"
    git stash apply "stash@{0}"
    @echo "Ready to commit"

git-back dst src="improvements":
    git stash push -a -u -m "just-fast-switch-to-back"
    git checkout "{{ dst }}"
    git merge "{{ src }}"
    git stash pop "stash@{1}"
    git stash pop "stash@{0}"
    @echo "Ready to commit"

k3s *args:
    docker compose -f docker-compose.k3s.yaml {{ args }}
