ruff := "uv run ruff"

fix:
    {{ ruff }} check

fix-EXE002:
    {{ ruff }} check --select 'EXE002' --output-format json . | jq '.[] | .filename' -r | xargs chmod -x
