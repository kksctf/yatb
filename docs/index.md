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
2. Open [app/schema/auth/\_\_init\_\_.py](https://github.com/kksctf/yatb/blob/master/app/schema/auth/__init__.py#L76)
3. Disable auth ways, that you don't need <(more about auth ways)>
4. Open [app/config.py](https://github.com/kksctf/yatb/blob/master/app/config.py), setup `EVENT_START_TIME` and `EVENT_END_TIME`. Theese dates **MUST** be in UTC.
5. Open `yatb_production.env`, change next values:
      1. tokens:
         1. `YATB_JWT_SECRET_KEY` - secret key for JWT cookie sign
         2. `YATB_API_TOKEN` - token for automated usage of admin API
         3. `YATB_WS_API_TOKEN` - token for admin WS
         4. `YATB_FLAG_SIGN_KEY` - flag sign key
      2. `YATB_FLAG_BASE` - flag base (part before brackets), i.e. for flag `kks{example_flag}` flag base is `kks`.
      3. `YATB_CTF_NAME` - CTF name for frontend
      4. Setup auth way that you selected in 2.
      5. [More about config](config.md)
6. Change logos in [app/view/static](https://github.com/kksctf/yatb/tree/master/app/view/static)
7. `touch file_db.db` - this is important step. You have to create (at least empty) file `file_db.db`, otherwise docker will create folder with that name (thanks to voluems) and you may loose DB.
8. `docker-compose up -d --build`
9. If you setup any reverse proxy before YATB nginx, you should change `proxy_set_header X-Forwarded-Proto $scheme;` line in [nginx/yatb.conf](https://github.com/kksctf/yatb/blob/master/nginx/yatb.conf#L9): comment entire line or replace `$scheme;` with `https`.

## Stack

- [FastAPI](https://github.com/tiangolo/fastapi)
- [Pydantic](https://github.com/pydantic/pydantic)
- [Jinja](https://github.com/pallets/jinja)
- Bootstrap
