# Release notes

## Latest version

- Added:
  - Ability to auth using X-Auth-Token instead of cookie
  - Flag submission tests
  - Beanie ODM to mongodb instead of cringe file(pickle)db
  - MongoDB as DB in docker-compose.yml
- Changed:
  - Migrated to newest pydantic/fastapi verison (pydantic v2, yes)
  - Refactor many things, mainly for typing or making ruff happy.
  - Refactor logging system
  - Some strings text sanitization
  - Refactor some tests
  - Use typing.Annotation for fastapi dependencies

## 0.6.1

- Added:
  - Docs.
  - Notifications about task solves in websockets (only for admin right now)
  - Admin `cleanup_db` endpoint
  - Simple predef CLI interface for API.
- Changed:
  - Version enumeration: removed litera `a` before version.
  - pyproject.toml refactor
  - Add more ways to pass [`admin_checker`](/app/api/admin/__init__.py#L13) dep: user in cookies, token in header, token in query
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
