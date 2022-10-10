import time
import traceback
from urllib.parse import quote as urllib_quote

from tg import hooks
from tg.appwrappers.errorpage import ErrorPageApplicationWrapper
from tg.controllers.decoratedcontroller import DecoratedController
from tg.request_local import request, response
from tg.configurator.components.error_reporting import \
    ErrorReportingConfigurationComponent
from tg import MinimalApplicationConfigurator

from ..metrics import (
    set_active as set_active_metrics,
    get_active as get_active_metrics,
    start_span,
    end_span,
)
from ..notifier import Notifier
from ..route_metric import RouteMetric

try:
    import backlash  # pylint: disable=unused-import
except ImportError:
    # pylint: disable=raise-missing-from
    raise ModuleNotFoundError('No module named "backlash". Backlash is used '
                              'to track error.')

try:
    # pylint: disable=ungrouped-imports
    from tg.configurator.components.sqlalchemy import \
        SQLAlchemyConfigurationComponent
    from sqlalchemy import event
except ImportError:
    _sqla_available = False
else:
    old_setup_sqlalchemy = SQLAlchemyConfigurationComponent.setup_sqlalchemy


    def _patch_setup_sqlalchemy(self, conf, app):
        old_setup_sqlalchemy(self, conf, app)
        _sqla_instrument(conf['tg.app_globals'].sa_engine, conf['pybrake'])


    SQLAlchemyConfigurationComponent.setup_sqlalchemy = _patch_setup_sqlalchemy

_UNKNOWN_ROUTE = "UNKNOWN"


class AirbrakeMiddleware:
    def __init__(self, notifier):
        self.notifier = notifier

    def report(self, traceback_ex):
        environ = traceback_ex.context.get('environ', {})
        is_backlash_event = getattr(traceback_ex.exc_value, 'backlash_event',
                                    False)
        if is_backlash_event:
            # Just a Stack Dump request from backlash
            _handle_exception(self.notifier, traceback_ex.exception, environ)
        else:
            # This is a real crash
            _handle_exception(self.notifier, traceback_ex.exception, environ)


def init_app(config):
    if 'pybrake' in config.configure():
        raise ValueError("pybrake is already injected")
    if 'PYBRAKE' not in config.configure():
        raise ValueError("app.settings['PYBRAKE'] is not defined")

    notifier = Notifier(**config.get_blueprint_value('PYBRAKE'))
    pybrake_config = notifier.config

    config.update_blueprint({
        'pybrake': notifier,
        # Exception handling
        "trace_errors.reporters": [AirbrakeMiddleware(notifier)],
    })
    # Exception handling
    if config.__class__ == MinimalApplicationConfigurator:
        config.register(ErrorReportingConfigurationComponent)
        config.register_application_wrapper(ErrorPageApplicationWrapper,
                                            after=True)

    # Route stats

    old_call = DecoratedController._call

    def _patch_call(self, action, params, remainder=None, context=None):
        if pybrake_config.get("performance_stats"):
            _before_request(request)
        try:
            return old_call(self, action, params, remainder, context)
        except Exception as er:
            context.response.status_code = 500
            raise er
        finally:
            if pybrake_config.get("performance_stats"):
                _after_request(notifier)
        # return res

    DecoratedController._call = _patch_call

    # Route Breakdown stats
    def before_template_render(*args, **kwargs):
        start_span("template")

    def after_template_render(*args, **kwargs):
        end_span("template")

    hooks.register('before_render_call', before_template_render)
    hooks.register('after_render_call', after_template_render)

    return config


def _sqla_instrument(engine, notifier):
    event.listen(engine, "before_cursor_execute", _before_cursor(notifier))
    event.listen(engine, "after_cursor_execute", _after_cursor(notifier))


def _before_cursor(notifier):
    def _sqla_before_cursor_execute(
            conn, cursor, statement, parameters, context, executemany
    ):
        if not notifier.config.get("performance_stats"):
            return
        start_span("sql")

    return _sqla_before_cursor_execute


def _after_cursor(notifier):
    def _sqla_after_cursor_execute(
            conn, cursor, statement, parameters, context, executemany
    ):
        if not notifier.config.get("performance_stats"):
            return
        end_span("sql")
        metric = get_active_metrics()
        if metric is not None:
            try:
                traceback_frm = traceback.extract_stack(limit=12)[0]
            except IndexError as er:  # pylint: disable=unused-variable
                traceback_frm = None
            notifier.queries.notify(
                query=statement,
                method=getattr(metric, "method", ""),
                route=getattr(metric, "route", ""),
                start_time=metric.start_time,
                end_time=time.time(),
                function=traceback_frm.name if traceback_frm else '',
                file=traceback_frm.filename if traceback_frm else '',
                line=traceback_frm.lineno if traceback_frm else 0,
            )

    return _sqla_after_cursor_execute


def _before_request(*remainder, **params):
    if request.controller_url:
        route = request.controller_url
    elif request.path:
        route = request.path
    else:
        route = _UNKNOWN_ROUTE
    metric = RouteMetric(method=request.method, route=route)
    set_active_metrics(metric)


def _after_request(notifier):
    metric = get_active_metrics()
    if metric is not None:
        metric.status_code = response.status_code
        metric.content_type = response.content_type
        metric.end_time = time.time()
        notifier.routes.notify(metric)
        set_active_metrics(None)


def get_host(environ):
    scheme = environ.get('wsgi.url_scheme')
    if 'HTTP_X_FORWARDED_HOST' in environ:
        result = environ['HTTP_X_FORWARDED_HOST']
    elif 'HTTP_HOST' in environ:
        result = environ['HTTP_HOST']
    else:
        result = environ['SERVER_NAME']
        if (scheme, str(environ['SERVER_PORT'])) not \
                in (('https', '443'), ('http', '80')):
            result += ':' + environ['SERVER_PORT']
    if result.endswith(':80') and scheme == 'http':
        result = result[:-3]
    elif result.endswith(':443') and scheme == 'https':
        result = result[:-4]
    return result


def get_current_url(environ, root_only=False, strip_querystring=False,
                    host_only=False):
    tmp = [environ['wsgi.url_scheme'], '://', get_host(environ)]
    cat = tmp.append
    if host_only:
        return ''.join(tmp) + '/'
    cat(urllib_quote(environ.get('SCRIPT_NAME', '').rstrip('/')))
    if root_only:
        cat('/')
    else:
        cat(urllib_quote('/' + environ.get('PATH_INFO', '').lstrip('/')))
        if not strip_querystring:
            qs = environ.get('QUERY_STRING')
            if qs:
                cat('?' + qs)
    return ''.join(tmp)


def request_filter(notice, environ):
    if request is None:
        return notice

    ctx = notice["context"]
    ctx["method"] = environ.get('REQUEST_METHOD')
    ctx["url"] = get_current_url(environ, strip_querystring=True)
    ctx["route"] = request.controller_url
    ctx["userAddr"] = request.client_addr

    if getattr(request, 'identity', None):
        user = {}
        for s in ["username", "name", "user_id"]:
            if hasattr(getattr(request, 'identity'), s):
                user[s] = getattr(getattr(request, 'identity'), s)
        ctx["user"] = user

    notice["params"]["request"] = dict(
        body=dict(request.body),
        data=environ.get(' wsgi.input'),
        params=dict(request.params),
        cookies=dict(request.cookies),
        headers=dict(request.headers),
        environ=environ,
        query_string=environ.get('QUERY_STRING'),
    )

    return notice


def _handle_exception(notifier, exception, environ):
    notice = notifier.build_notice(exception)
    notice = request_filter(notice, environ)
    notifier.send_notice(notice)
