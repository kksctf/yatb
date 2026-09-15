# YATB Config

Setup config stored in [app/config.py](https://github.com/kksctf/yatb/blob/master/app/config.py) file

## .env

Always populated from `yatb.env`, or from enviroment.

## Main settings

### Debug

- `DEBUG`: enable/disable debug mode. Should be off on production
- `PROFILING`: enable/disable profiling. Enables `?profile=true` query param for viewing PyInstrument output

### Event timing

- `EVENT_START_TIME` / `EVENT_END_TIME`: dates of event start and end. **MUST** be in UTC and offset-aware.

### DB Data

- `DB_NAME`: name of database
- `MONGO`: DSN for connecting to mongodb instance

## **Must** be changed

- `JWT_SECRET_KEY` - secret key for JWT cookie signing.
- `FLAG_SIGN_KEY` - the same, but for dynamic flags.
- `API_TOKEN` - token for accessing admin API without admin user / auth.
- `WS_API_TOKEN` - token for acessing admin WS subscription API.

## CTF Customization

- `FLAG_BASE` - base for flags (i.e. part before brackets), for example: `kks` for flags like `kks{example_flag}`
- `CTF_NAME` - ctf name to be displayed on front

### Auth ways

Note that in addition to enabling the way, you must configure the authentication method itself separately.

Every other authway has separate settings variables prefix.

- `ENABLED_AUTH_WAYS`: list of enabled yatb authentification ways. Defaults to:
  - Simple (login + password)
  - Telegram
  - CTFTime
  - GitHub
  - Discord

#### Simple

prefix: `AUTH_SIMPLE_`

- `AUTH_SIMPLE_DEBUG_USERNAME`: username, which will be promoted to admin, **if DEBUG mode enabled**
- `AUTH_SIMPLE_MIN_PASSWORD_LEN`: minimum password length
- `AUTH_SIMPLE_MIN_USERNAME_LEN`: minimum username length
- `AUTH_SIMPLE_MAX_USERNAME_LEN`: maximum username length

#### Telegram

prefix: `AUTH_TG_`

- `AUTH_TG_BOT_TOKEN`: bot token
- `AUTH_TG_BOT_USERNAME`: bot public username
- `AUTH_TG_ADMIN_USERNAMES`: list of usernames, which will be promoted to admin
- `AUTH_TG_ADMIN_UIDS`: list of admin telegram IDs, which will be promoted to admin

#### OAuth

This auth way is more like an underlying auth way, and is needed as an abstraction for other auth ways.

Since OAuth2 does not specify the fields in which user information is returned, it is impossible to make a universal auth way.

However, almost all settings that are defined for the basic OAuth are valid for all its implementations.

prefix: `AUTH_OAUTH_`

- `AUTH_OAUTH_ADMIN_IDS`: user IDs, which will be promoted to admin (depending on the service)
- `AUTH_OAUTH_CLIENT_ID`: oauth client id
- `AUTH_OAUTH_CLIENT_SECRET`: oauth client secret
- `AUTH_OAUTH_ENDPOINT`: authorize endpoint
- `AUTH_OAUTH_TOKEN_ENDPOINT`: token endpoint
- `AUTH_OAUTH_API_ENDPOINT`: user info / some api endpoint

#### OAuth: CTFTime

prefix: `AUTH_CTFTIME_`

- `AUTH_CTFTIME_ADMIN_IDS`: teams IDs, which users will be promoted to admin
- `AUTH_CTFTIME_CLIENT_ID`: ctftime client id
- `AUTH_CTFTIME_CLIENT_SECRET`: ctftime client secret

#### OAuth: GitHub

prefix: `AUTH_GITHUB_`

- `AUTH_GITHUB_ADMIN_IDS`: user IDs, which will be promoted to admin
- `AUTH_GITHUB_CLIENT_ID`: github client id
- `AUTH_GITHUB_CLIENT_SECRET`: github client secret

#### OAuth: Discord

prefix: `AUTH_DISCORD_`

- `AUTH_DISCORD_ADMIN_IDS`: user IDs, which will be promoted to admin
- `AUTH_DISCORD_CLIENT_ID`: discord client id
- `AUTH_DISCORD_CLIENT_SECRET`: discord client secret

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

- `VERSION`: base string, used for versing string population
