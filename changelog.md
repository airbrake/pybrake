# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.7.0] - 2022-09-02

### Added

- Add support for Falcon framework with sample example
- Add support for Hug framework with sample example
- Add queue for backlog thread for failed request data

### Fixed

- Fastapi/Sanic middleware does not support lack of SqlAlchemy package [229](https://github.com/airbrake/pybrake/issues/229)

## [1.6.0] - 2022-07-08

### Added

- Add sample example for AIOHTTP Framework

### Changed

- Improve AIOHTTP middleware with APM support of Jinja Template, SqlAlchemy

### Fixed

- Fix for AIOHTTP middleware's "none type object has no attribute while handling error" 

## [1.5.0] - 2022-06-07

### Added

- Masonite Middleware with sample example

### Changed

- Bump bottle from 0.12.19 to 0.12.20 in /examples/bottle

## [1.4.0] - 2022-05-31

### Added

- Sanic Middleware
- Sample example for Pyramid, CherryPy, Sanic, & FastAPI middleware

## [1.3.0] - 2022-05-26

### Added

- Changelog file
- Pyramid middleware
- CherryPy middleware
- FastAPI middleware

## [1.2.0] - 2022-05-11

### Added

- Bottle middleware
- Bottle sample example

### Fixed

- Errors are filtered out when middleware is involved in backtrace [#191](https://github.com/airbrake/pybrake/issues/191)

## [1.1.0] - 2022-05-09

### Changed

- Package Restructure
- Add Django sample example
- Update Flask sample example

### Fixed

- Fix query stats send to the Airbrake

## [1.0.6] - 2022-04-13

### Changed

- Improve pytest

### Fixed

- 400 Bad Request: Did not attempt to load JSON data because the request
  Content-Type was not 'application/json' on Flask request filter [#183](https://github.com/airbrake/pybrake/issues/183)
- Fix pylint

## [1.0.5] - 2022-03-23

### Changed

- Improve test reliability by cleaning state after running
  test_celery_integration
- README: tweak breakdowns docs, queue example to include groups, indent with 4 spaces instead of 2 python style

### Fixed

- Fixed pylint errors and disabled argument for import warning
- Flask integration order of filters does not apply blocklist to request
  object [#132](https://github.com/airbrake/pybrake/issues/132)
- blocklist_filter attempts to change Immutable [#133](https://githubcom/airbrake/pybrake/issues/133)

## [1.0.4] - 2021-06-07

### Changed

- notifier: make sure performance_stats are always True

### Fixed

- remote_settings: don't overwrite hosts with None:- When `apm_host` or 
  `error_host` is undefined, it'll overwrite whatever value is in the 
  current remote config. We don't want that to happen.
- .pylintrc: disable 'consider-using-with':- This is just noise at the time 
  of writing this commit, but we should probably address it in the future.
- Pybrake query notifier throws error when query is a psycopg2 Composed
  object [#156](https://github.com/airbrake/pybrake/issues/156)
- Fixes exception for unhashable type: 'Composed' [#157](https://github.com/airbrake/pybrake/pull/157)

## [1.0.3] - 2021-04-13

### Fixed

- Flask Middleware :- Return response when performance_stats is false

## [1.0.2] - 2021-02-16

### Removed

- remote_settings: delete print that's left from debugging

## [1.0.1] - 2021-02-16

### Changed

- Change naming style for remote_settings, settings_data

### Fixed

- remote_settings: fix fetching config route (The config route setting has no 
effect due to a bug where pybrake doesn't read that value prior to making a 
GET request to the notifier config server. The fix is to call `config_route()`
on every notifier config GET call. Additionally, we are adding a logic that 
prevents remote settings to crash the background thread in case `config_route` 
is a bad value (HTTP lib would raise an error). When an error happens such as
403 Forbidden, we make a 2nd request to the old config route, which was known
to work)

## [1.0.0] - 2021-01-21

### Added

- Pybrake SDK
- Middleware for Flask, Django, celery, aiohttp frameworks

[Unreleased]: https://github.com/airbrake/pybrake/compare/v1.7.0...HEAD
[1.7.0]: https://github.com/airbrake/pybrake/compare/v1.6.0...v1.7.0
[1.6.0]: https://github.com/airbrake/pybrake/compare/v1.5.0...v1.6.0
[1.5.0]: https://github.com/airbrake/pybrake/compare/v1.4.0...v1.5.0
[1.4.0]: https://github.com/airbrake/pybrake/compare/v1.3.0...v1.4.0
[1.3.0]: https://github.com/airbrake/pybrake/compare/v1.2.0...v1.3.0
[1.2.0]: https://github.com/airbrake/pybrake/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/airbrake/pybrake/compare/v0.2.0...v1.1.0
[1.0.6]: https://github.com/airbrake/pybrake/compare/v1.0.5...v1.0.6
[1.0.5]: https://github.com/airbrake/pybrake/compare/v1.0.4...v1.0.5
[1.0.4]: https://github.com/airbrake/pybrake/compare/v1.0.3...v1.0.4
[1.0.3]: https://github.com/airbrake/pybrake/compare/v1.0.2...v1.0.3
[1.0.2]: https://github.com/airbrake/pybrake/compare/v1.0.1...v1.0.2
[1.0.1]: https://github.com/airbrake/pybrake/compare/v1.0.0...v1.0.1
[1.0.0]: https://github.com/airbrake/pybrake/compare/v0.4.6...v1.0.0
