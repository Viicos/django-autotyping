# Changelog

## 0.5.0 (2024-02-18)

This release brings basic support for template loading functions (e.g. `render_to_string`).

- Fixed some typos in readme and docstrings (#50)
- Fixes and tests for `DJAS002/3` (#53)
- Add support for template loading functions (#56)
- Remove outdated VSCode limitation in docs (#57)

## 0.4.0 (2024-02-04)

This release brings improvements to the model creation related comemod:
- `DJAS002` was refactored and now provides better types for fields (instead of `Any`).
  It is now split into two rules: `DJAS002` and `DJAS003`.

- Fix README rendering for PyPI (#43)
- Add draft implementation for `call_command` overloads (#45)
- Refactor and improve support for model creation (#46)
- Update to `ruff==0.2.0`, add new rules (#47)
- Typos and updates to docs (#48)

## 0.3.0 (2024-01-23)

- Add more tests for DJAS001, test DJAS010 (#34)
- Add support for custom user model (#35)
- Add animated example (#38)
- Add support for settings typing (#37)

## 0.2.0 (2024-01-15)

- Complete refactor of the library (no post migrate signal, management commands)
- Added tests, docs

## 0.1.0 (2023-12-17)

- Add support for custom dynamic stubs
- Support duplicate models across apps
- Various improvements to the codebase

## 0.0.1 (2023-12-05)

- Initial release
