# Python exception notifier for Airbrake

[![Build Status](https://travis-ci.org/airbrake/pybrake.svg?branch=master)](https://travis-ci.org/airbrake/pybrake)

## Installation

pybrake requires Python 3.4+.

``` shell
pip install -U pybrake
```

## Configuration

To configure the pybrake notifier you will need your Airbrake project's `id` and
`api_key`, these are available from your project's settings page.

```python
import pybrake


notifier = pybrake.Notifier(project_id=123,
                            project_key='FIXME',
                            environment='production')
```

## Sending errors to Airbrake

```python
try:
    raise ValueError('hello')
except Exception as err:
    notifier.notify(err)
```

### Sending errors synchronously

By default, the `notify` function sends errors asynchronously using
`ThreadPoolExecutor` and returns a `concurrent.futures.Future`, a synchronous
API is also made available with the `notify_sync` function:

```python
notice = notifier.notify_sync(err)
if 'id' in notice:
    print(notice['id'])
else:
    print(notice['error'])
```

## Adding custom params

To set custom params you can build and send notice in separate steps:

```python
notice = notifier.build_notice(err)
notice['params']['myparam'] = 'myvalue'
notifier.send_notice(notice)
```

You can also add custom params to every error notice before it's sent to Airbrake
with the `add_filter` function.

```python
def my_filter(notice):
    notice['params']['myparam'] = 'myvalue'
    return notice

notifier.add_filter(my_filter)
```

## Ignoring notices

There may be some notices/errors thrown in your application that you're not
interested in sending to Airbrake, you can ignore these using the `add_filter`
function.

```python
def my_filter(notice):
    if notice['context']['environment'] == 'development':
        # Ignore notices in development environment.
        return None
    return notice

notifier.add_filter(my_filter)
```

## Logging integration

pybrake provides a logging handler that sends your logs to Airbrake.

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

First you need to add your pybrake config to your Django `settings.py` file
using your project's `id` and `api_key`.

```python
AIRBRAKE = dict(
    project_id=123,
    project_key='FIXME',
)
```

The next step is activating the Airbrake middleware.

```python
MIDDLEWARE = [
    ...
    'pybrake.django.AirbrakeMiddleware',
]
```

The last step is configuring the airbrake logging handler. After that you are
ready to start reporting errors to Airbrake from your Django app.

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

The Flask integration leverages Flask signals and therefore requires the blinker
library.

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

The pybrake logger can be silenced by setting the logging level to
`logging.CRITICAL`.

``` python
import logging


logging.getLogger("pybrake").setLevel(logging.CRITICAL)
```

## Development

### Running the tests

```shell
pip install -r test-requirements.txt
pytest
```

### Uploading to PyPI

```shell
python setup.py sdist upload
```
