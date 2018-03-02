# Python exception notifier for Airbrake

[![Build Status](https://travis-ci.org/airbrake/pybrake.svg?branch=master)](https://travis-ci.org/airbrake/pybrake)

## Installation

pybrake requires Python 3.5+.

``` shell
pip install -U pybrake
```

## Usage

Creating notifier:

```python
import pybrake


notifier = pybrake.Notifier(project_id=123,
                            project_key='abc',
                            environment='production')
```

Sending errors to Airbrake:

```python
try:
    raise ValueError('hello')
except Exception as err:
    future = notifier.notify(err)
    # future has type concurrent.futures.Future
    notice = future.result()
```

By default `notify` sends errors asynchronously using `ThreadPoolExecutor` and returns a `concurrent.futures.Future`, but synchronous API is also available:

```python
notice = notifier.notify_sync(err)
if 'id' in notice:
    print(notice['id'])
else:
    print(notice['error'])
```

You can also set custom params on all reported notices:

```python
def my_filter(notice):
    notice['params']['myparam'] = 'myvalue'
    return notice

notifier.add_filter(my_filter)
```

Or ignore notices:

```python
def my_filter(notice):
    if notice['context']['environment'] == 'development':
        # Ignore notices in development environment.
        return None
    return notice

notifier.add_filter(my_filter)
```

## Logging integration

pybrake provide logging handler that sends your logs to Airbrake:

```python
import logging
import pybrake


airbrake_handler = pybrake.LoggingHandler(notifier=notifier,
                                          level=logging.ERROR)

logger = logging.getLogger('test')
logger.addHandler(airbrake_handler)

logger.error('something bad happened')
```

## Development

Runn tests:

```shell
pip install -r test-requirements.txt
pytest
```

Upload to PyPI:

```shell
python setup.py sdist upload
```
