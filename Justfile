ruff := "uv run ruff"

yatb:
    uv run uvicorn yatb.app:app

debug_yatb:
    uv run debugpy --listen 5678 --wait-for-client -m uvicorn yatb.app:app

cli *args:
    uv run -m yatb.cli {{ args }}

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
