# Python exception notifier for Airbrake

[![Build Status](https://travis-ci.org/airbrake/pybrake.svg?branch=master)](https://travis-ci.org/airbrake/pybrake)

## Installation

pybrake requires Python 3.4+.

``` shell
pip install -U pybrake
```

## Usage

Creating notifier:

```python
import pybrake


notifier = pybrake.Notifier(project_id=123,
                            project_key='FIXME',
                            environment='production')
```

Sending errors to Airbrake:

```python
try:
    raise ValueError('hello')
except Exception as err:
    notifier.notify(err)
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

## Django integration

First you need to add pybrake config to your Django settings.py file:

```python
AIRBRAKE = dict(
    project_id=123,
    project_key='FIXME',
)
```

Then you can activate Airbrake middleware:

```python
MIDDLEWARE = [
    ...
    'pybrake.django.AirbrakeMiddleware',
]
```

And configure logging handler:

```python
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'airbrake': {
            'level': 'ERROR',
            'class': 'pybrake.LoggingHandler',
        },
    },
    'loggers': {
        'app': {
            'handlers': ['airbrake'],
            'level': 'ERROR',
            'propagate': True,
        },
    },
}
```

## Flask integration

Flask integration uses Flask signals and therefore requires blinker library.

```python
from flask import Flask
import pybrake.flask



app = Flask(__name__)

app.config['PYBRAKE'] = dict(
    project_id=123,
    project_key='FIXME',
)
app = pybrake.flask.init_app(app)
```

## Disabling pybrake logs

pybrake logger can be silenced using following code:

``` python
import logging


logging.getLogger("pybrake").setLevel(logging.CRITICAL)
```

## Development

Run tests:

```shell
pip install -r test-requirements.txt
pytest
```

Upload to PyPI:

```shell
python setup.py sdist upload
```
