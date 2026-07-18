# Release notes

## Latest version

- Added:
  - A
- Changed:
  - B
- Depricated:
  - C
- Deleted:
  - E
- Fixed:
  - F
- Security:
  - G

## 0.7.2

- Added:
  - FastUI PoC
  - Dynamic Tasks microservice (DTC) and its integration into yatb: container building, static tasks builder manager, service runner for TCP services from generic docker-composes, `builder_and_service` task type, kubevirt VM spec (WIP)
  - S3 base infra for super-simple docker-compose deploy (garage s3 server); s3 serve moved to a separate python package
  - Dockerized minimal yatb installation
  - htmx + bulma frontend MVP
  - i18n/l10n PoC (babel)
  - Google OAuth
  - Feature flags PoC
  - Nix support for dev environment
  - `TaskID`/`UserID` newtype ids instead of raw `uuid.UUID`
  - `YAMLModel` that preserves yaml file structure between loading and dumping
  - `display_name` user field (backported)
  - `PRIVATE_SCOREBOARD` feature
  - Navbar burger
  - Scoreboard with task names
  - `api_admin_task_delete`, `api_admin_find_flag_owner` endpoints
  - `user_search` to ng-admin
  - Force rebuild option for task building
  - Archive generation for tasks
  - IPv6 support
- Changed:
  - Migrated from my beanie fork back to upstream
  - Gigantic refactoring all over the codebase
  - Migrated from PDM to UV
  - Migrated from tons of requirements.txt to a single pyproject.toml
  - Migrated from requests to httpx
  - Migrated to lifespan
  - Complete rework of EBaseModel/EBaseModelV2 meta system
  - Restructured project: `app` -> `yatb` -> `src/yatb`, `cli` -> `src/cli`, `dynamic_tasks_app` -> `src/dtc`
  - Improved scoreboard: UX, scalability, fluid layout and faster renderer
  - Better (dynamic) flags check
  - Better task sync, now allows changing scoring
  - Improved CLI
  - Normalize admin usernames in TG_AUTH
- Deleted:
  - Old admin panel
  - Old useless DB code
  - `flag_sign_key`
- Fixed:
  - Many tests. They now work on DEBUG=False build of code, because running tests in debug mode is something strange.
  - DTC race condition in start task
  - Scoreboard rendering and stability
  - Many UI fixes: table header, task header contrast, flag submit form, pill wrapping, task filters, sticky footer, navbar
  - Docker and Nix build problems

## 0.6.3a0

- Added:
  - Forensic category to front
  - Fake `TokenAuth` auth way for usage of `_fake_admin_user` even if `SimpleAuth` is disabled. It is always active auth way
  - `unhide` CLI command. `unhide` unhides all tasks
  - Better handling `TelegramAuth` while generation firstblood message
  - `rev` alias for `binary` category
  - `api_admin_user_recalc_score` endpoint
  - `api_admin_recalc_tasks` endpoint
  - Solve statistics per task in scoreboard
- Changed:
  - Colorscheme a little
  - Splitted and somewhere refactored CLI interface to many small modules, moved it inside package
  - Migration to my (`https://github.com/Rubikoid/beanie.git@encoder-fix`) fork of beanie, because of broken upstream and unclear PR [beanie!785](https://github.com/roman-right/beanie/pull/785) status
  - Refactored `api_scoreboard_get_internal*`, removed copypaste
  - Migration from nginx to caddy for serving static files - nginx broken for no reason, so migration to caddy was the simplest fix
  - Heavily improved `prepare_tasks` CLI cmd
  - Improved sorting scoreboard, make it more stable
  - `api_detele_everything` is a little safer now
- Depricated:
  - NGINX as static files proxy
- Fixed:
  - Added few missed modules to logger
  - Timezone while formatting time before display it in scoreboard.

## 0.6.2a2

- Fixed:
  - Chaotic point changes in scoreboard on flag submit

## 0.6.2a1

- Fixed:
  - Few fixes

## 0.6.2a0

- Added:
  - Ability to auth using X-Auth-Token instead of cookie
  - Flag submission tests
  - Beanie ODM to mongodb instead of cringe file(pickle)db
  - MongoDB as DB in docker-compose.yml
  - More documentation about auth ways
- Changed:
  - Migrated to newest pydantic/fastapi verison (pydantic v2, yes)
  - Refactor many things, mainly for typing or making ruff happy.
  - Refactor logging system
  - Some strings text sanitization
  - Refactor some tests
  - Use typing.Annotation for fastapi dependencies
  - Rename some OAUTH settings to make it better-looking
  - More documentation fixes
- Fixes:
  - Some optimization in jinja formatting
  - Optimize scoreboard generation

## 0.6.1

- Added:
  - Docs.
  - Notifications about task solves in websockets (only for admin right now)
  - Admin `cleanup_db` endpoint
  - Simple predef CLI interface for API.
- Changed:
  - Version enumeration: removed litera `a` before version.
  - pyproject.toml refactor
  - Add more ways to pass [`admin_checker`](https://github.com/kksctf/yatb/blob/master/app/api/admin/__init__.py#L13) dep: user in cookies, token in header, token in query
  - Some strings sanitization

## a0.6.0

- Added:
  - Extended check for default tokens/keys in production mode
  - Ressurect mode for DB during save, if docker created folder named `file.db` istead of normal file
  - User delete enpoint in admin API.
  - User password change in admin API.
  - Extended validation for users in SimpleAuth: username len should be in \[2,32\], pw len should be bigger than 8
- Changed:
  - Global rework on the mechanism the models are exposed to admin/public API.
  - Bumped `reqirements.txt`
  - `reqirements.txt` and `reqirements-dev.txt` splitted to two separate files. Now for getting dev-env you have to install both
  - Python version bumped to 3.10
- Fixed:
  - Tests

<!---

## Latest version

- Added:
  - A
- Changed:
  - B
- Depricated:
  - C
- Deleted:
  - E
- Fixed:
  - F
- Security:
  - G

-->
