# Release notes

## Latest version

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

## Template

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
