# Deploy and production

In general, deploy is pretty simple: 
1. Install requirements.txt (`pip install -r requirements.txt`)

2. Setup some enviroment vars:

    1. **Disable debug with `YATB_DEBUG=False`**
    2. If you want to get firstblood notifications, set `TG_BOT_TOKEN`
    3. Also, for ctftime auth you need to setup `OAUTH_CLIENT_ID`, `OAUTH_CLIENT_SECRET` from your event page on ctftime.
    4. `DB_NAME` describes path to db, by default it stores at PWD/file_db.db
    5. `ENABLE_METRICS` - enables prometeus metrics endpoint.

3. Check [config](app/config.py) for some values, that you maybe want to change:
    
    1. `_DEGUG` - enable, or disable some debug features, like login/password login, debug admin account.
    2. `CHAT_ID` - used for firstblood notifications.
    3. `OAUTH_ADMIN_IDs` - **list of oauth IDs, that will get admin account.**
    4. `EVENT_START_TIME`/`EVENT_END_TIME` - self-describable
    5. `JWT_SECRET_KEY` - **secret key for JWT, change this!**
    6. `FASTAPI_DOCS_URL`/`FASTAPI_REDOC_URL`/`FASTAPI_OPENAPI_URL` - fastapi docs url. Maybe you want to change this to something else... :hm:
    7. `MONITORING_URL` - endpoint for prometeus. 
    8. `VERSION` - just a fancy string.

4. Run `python3 -m uvicorn main:app --host 0.0.0.0 --port 80`
    
    Also some useful args: 
    * `--log-level=debug`/`--log-level=info` - debug level.
    * `--reload`: if you want crazy autoreload, **can broke DB!**
    * `--proxy-headers`: if you want nginx
    * `--forwarded-allow-ips *`: if you want nginx

5. Also, in repository available `Dockerfile.production`, ready for production with nginx
