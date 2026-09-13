FROM python:3.12-slim

WORKDIR /build-manager

RUN python3 -m venv .venv
RUN .venv/bin/pip install --no-cache-dir \
    "cyclopts==2.9.3" \
    "rich==13.7.1" \
    "httpx==0.22.0" \
    "pydantic-settings==2.3.4" \
    "miniopy-async==1.20.1"

COPY manager.py manager.py

ENTRYPOINT ["/build-manager/.venv/bin/python3", "/build-manager/manager.py"]
