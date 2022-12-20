# YATB Config

Config setup stored in [app/config.py](https://github.com/kksctf/yatb/blob/master/app/config.py) file

## .env

Setting are populated from `yatb.env`, if you use local uvicorn startup (usually debug)

And from `yatb_production.env`, if you use docker-compose setup (usually production)

## Main settings

- `DEBUG`: enable/disable debug mode. Should be off on production
- `EVENT_START_TIME` / `EVENT_END_TIME`: dates of event start and end. **MUST** be in UTC and offset-native. I prefer setting it directly in `config.py` rather than .env

## **Must** be changed

- `JWT_SECRET_KEY` - secret key for JWT cookie signing.
- `FLAG_SIGN_KEY` - the same, but for dynamic flags.
- `API_TOKEN` - token for accessing admin API without admin user / auth.
- `WS_API_TOKEN` - token for acessing admin WS subscription API.

## CTF Customization

- `FLAG_BASE` - base for flags (i.e. part before brackets), for example: `kks` for flags like `kks{example_flag}`
- `CTF_NAME` - ctf name to be displayed on front

## TG Notifications

- `BOT_TOKEN` - token from botfather
- `CHAT_ID` - chat id of chat for notifications (channel/group/PM)

## FastAPI URLs

There are some params for hiding fastapi docs:

- `FASTAPI_DOCS_URL` - default swagger
- `FASTAPI_REDOC_URL` - redoc
- `FASTAPI_OPENAPI_URL` - openapi schema

## Monitoring

- `MONITORING_URL` - endpoint for prom metrics

## JWT settings

- `JWT_ALGORITHM` - jwt algo
- `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` - jwt token lifetime

## Misc

- `DB_NAME`: Path to DB file
- `VERSION`: base string, used for versing string population
