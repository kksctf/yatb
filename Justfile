ruff := "uv run ruff"

yatb:
    uv run uvicorn yatb.app:app

precom: fix format

fix:
    {{ ruff }} check --select 'I001,F401,UP035' --fix

format:
    {{ ruff }} format

fix-EXE002:
    {{ ruff }} check --select 'EXE002' --output-format json . | jq '.[] | .filename' -r | xargs chmod -x
