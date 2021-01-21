# Python exception notifier for Airbrake

![Build Status](https://github.com/airbrake/pybrake/workflows/pybrake/badge.svg)

## Installation

pybrake requires Python 3.6+.

``` shell
pip install -U pybrake
```

## Configuration

You **must** set both `project_id` & `project_key`.

To find your `project_id` and `project_key` navigate to your project's
_Settings_ and copy the values from the right sidebar.

![][project-idkey]

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

## Filtering keys

With `keys_blocklist` option you can specify list of keys containing sensitive information that must be filtered out, e.g.:

```python
notifier = pybrake.Notifier(
    ...
    keys_blocklist=[
        'password',           # exact match
        re.compile('secret'), # regexp match
    ],
)
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

First, configure `project_id` and `project_key` in `settings.py`:

```python
AIRBRAKE = dict(
    project_id=123,
    project_key='FIXME',
)
```

Next, activate the Airbrake middleware:

```python
MIDDLEWARE = [
    ...
    'pybrake.django.AirbrakeMiddleware',
]
```

Finally, configure the airbrake logging handler:

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

Now you are ready to start reporting errors to Airbrake from your Django app.

## Flask integration

The Flask integration leverages Flask signals and therefore requires the
[blinker](https://pythonhosted.org/blinker/) library.

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

## aiohttp integration (python 3.5+)

Setup airbrake's middleware and config for your web application:

```python
# app.py

from aiohttp import web
from pybrake.aiohttp import create_airbrake_middleware

airbrake_middleware = create_airbrake_middleware()

app = web.Application(middlewares=[airbrake_middleware])

app['airbrake_config'] = dict(
  project_id=123,
  project_key='FIXME',
  environment='production'  # optional
)
```

Also, you can pass custom handlers to `create_airbrake_middleware`:

```python
# middlewares.py

import aiohttp_jinja2
from pybrake.aiohttp import create_airbrake_middleware


async def handle_404(request):
    return aiohttp_jinja2.render_template('404.html', request, {})


async def handle_500(request):
    return aiohttp_jinja2.render_template('500.html', request, {})


def setup_middlewares(app):
    airbrake_middleware = create_airbrake_middleware({
        404: handle_404,
        500: handle_500
    })

    app.middlewares.append(airbrake_middleware)
```

## Disabling pybrake logs

The pybrake logger can be silenced by setting the logging level to
`logging.CRITICAL`.

``` python
import logging


logging.getLogger("pybrake").setLevel(logging.CRITICAL)
```

## Sending route stats

`notifier.routes.notify` allows sending route stats to Airbrake. The library
provides integrations with Django and Flask. (your routes are tracked
automatically). You can also use this API manually:

```py
from pybrake import RouteMetric

metric = RouteMetric(method=request.method, route=route)
metric.status_code = response.status_code
metric.content_type = response.headers.get("Content-Type")
metric.end_time = time.time()

notifier.routes.notify(metric)
```

## Sending route breakdowns

`notifier.routes.breakdowns.notify` allows sending performance breakdown stats
to Airbrake. You can use this API manually:

```py
import pybrake import RouteBreakdowns

metric = RouteBreakdowns(method=request.method, route=route)
metric.response_type = response.headers.get("Content-Type")
metric.end_time = time.time()

notifier.routes.notify(metric)
```

## Sending query stats

`notifier.queries.notify` allows sending SQL query stats to Airbrake. The
library provides integration with Django (your queries are tracked
automatically). You can also use this API manually:

```py
notifier.queries.notify(
    query="SELECT * FROM foos",
    method=request.method,
    route=route,
    start_time=time.time(),
    end_time=time.time(),
)
```

## Sending queue stats

`notifier.queues.notify` allows sending queue (job) stats to Airbrake. The
library provides integration with Celery (your queues are tracked
automatically). You can also use this API manually:

```py
from pybrake import QueueMetric

metric = QueueMetric(queue="foo_queue")
notifier.queues.notify(metric)
```

## Development

### Running the tests

```shell
pip install -r requirements.txt
pip install -r test-requirements.txt
pytest
```

### Uploading to PyPI

```shell
python setup.py sdist upload
```

### Remote configuration

Every 10 minutes the notifier issues an HTTP GET request to fetch remote
configuration. This might be undesirable while running tests. To suppress this
HTTP call, you need to pass `remote_config=False` to the notifier.

[project-idkey]: https://s3.amazonaws.com/airbrake-github-assets/pybrake/project-id-key.png
