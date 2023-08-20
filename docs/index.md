# Welcome to YATB Docs

YATB - yet another fast and furious jeopardy-CTF taskboard

## Features out-of-the-box

- Flexible auth system with OAuth2 support
- Flexible flags and scoring system
- OpenAPI schema and swagger UI - easy to integrate API
- Extremly simple: you can modificate in any imagniable way
- Telegram notifications for first blood
- Blazing :) fast!

## How to start

1. Clone repo
2. Fix event datetime:
   1. Open [app/config.py](https://github.com/kksctf/yatb/blob/master/app/config.py), setup `EVENT_START_TIME` and `EVENT_END_TIME`. Theese dates **MUST** be in UTC.
   2. or in `yatb.env`.
3. Copy `yatb.example.env` to `yatb.env`, change next values:
   1. tokens:
      1. `JWT_SECRET_KEY` - secret key for JWT cookie sign
      2. `API_TOKEN` - token for automated usage of admin API
      3. `WS_API_TOKEN` - token for admin WS
      4. `FLAG_SIGN_KEY` - flag sign key
   2. `FLAG_BASE` - flag base (part before brackets), i.e. for flag `kks{example_flag}` flag base is `kks`.
   3. `CTF_NAME` - CTF name for frontend
   4. Setup auth ways:
      1. Fill `ENABLED_AUTH_WAYS` list with enabled auth ways, for example, `ENABLED_AUTH_WAYS='["TelegramAuth", "SimpleAuth"]'`
      2. Fill select auth way settings. For reference, see [more about auth ways configs](config.md#Auth%20ways)
   5. [More about config](config.md)
4. Change logos in [app/view/static](https://github.com/kksctf/yatb/tree/master/app/view/static)
5. `docker-compose up -d --build`
6. If you setup any reverse proxy before YATB nginx, you should change `proxy_set_header X-Forwarded-Proto $scheme;` line in [nginx/yatb.conf](https://github.com/kksctf/yatb/blob/master/nginx/yatb.conf#L9): comment entire line or replace `$scheme;` with `https`.

## Stack

- [FastAPI](https://github.com/tiangolo/fastapi)
- [Pydantic](https://github.com/pydantic/pydantic)
- [Jinja](https://github.com/pallets/jinja)
- Bootstrap
