#### made by `kks`
# YATB

## Getting started
`$ python3 -m pip install -r requirements-dev.txt`

## Launch
`$ python3 -m uvicorn main:app --host 0.0.0.0 --port 80`

* `--log-level=debug`/`--log-level=info` - debug level.
* `--reload`: if you want crazy autoreload
* `--proxy-headers`: if you want nginx
* `--forwarded-allow-ips *`: if you want nginx

## Dev
You can enable YATB_DEBUG env (True by default) and login through `/docs` or debug buttons on login page.

First pair of buttons signing up and signing in as admin, second - as basic user
