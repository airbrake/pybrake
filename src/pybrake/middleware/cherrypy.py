import time
import typing as t
from sys import exc_info as _exc_info

import cherrypy
from cherrypy.process import plugins
from pybrake.notifier import Notifier

from .. import Notifier
from .. import RouteMetric
from ..metrics import (
    set_active as set_active_metrics,
    get_active as get_active_metrics,
    start_span,
    end_span,
)

try:
    from jinja2 import Template
except ImportError:
    _jinja_available = False
else:
    _jinja_available = True

try:
    from sqlalchemy import event
except ImportError:
    _sqla_available = False
else:
    _sqla_available = True


def request_filter(notice):
    request = cherrypy.request
    if request is None:
        return notice
    ctx = notice["context"]
    ctx["method"] = request.method
    ctx["route"] = request.path_info

    try:
        user_addr = request.remote.ip
    except IndexError:
        user_addr = request.wsgi_environ.get('REMOTE_ADDR')
    if user_addr:
        ctx["userAddr"] = user_addr

    if request.login:
        ctx["user"] = request.login

    notice["params"]["request"] = dict(
        body=request.body.__dict__,
        cookie=dict(request.cookie),
        headers=dict(request.headers),
        request_line=request.request_line,
        url_args=request.args,
        script_name=request.script_name,
        kwargs=request.kwargs,
        query_string=dict(request.query_string),
        environ=dict(request.wsgi_environ),
    )
    return notice


class PybrakeAPM(cherrypy.Tool):
    def __init__(self):
        cherrypy.Tool.__init__(self, 'before_handler',
                               self.start_timer,
                               priority=1)

    def _setup(self, **kwargs):
        cherrypy.Tool._setup(self)
        cherrypy.request.hooks.attach('on_end_request',
                                      self.end_timer,
                                      priority=0)

    def start_timer(self, **kwargs):
        notifier = cherrypy.config.get('pybrake')
        if not notifier.config.get("performance_stats"):
            return

        metric = RouteMetric(method=cherrypy.request.method,
                             route=cherrypy.request.path_info)
        set_active_metrics(metric)

    def end_timer(self, **kwargs):
        notifier = cherrypy.config.get('pybrake')
        if not notifier.config.get("performance_stats"):
            return
        metric = get_active_metrics()
        if metric is not None:
            metric.status_code = int(cherrypy.response.status[:3]) if \
                isinstance(cherrypy.response.status, str) \
                else cherrypy.response.status
            metric.content_type = cherrypy.response.headers.get("Content-Type")
            metric.end_time = time.time()
            notifier.routes.notify(metric)
            set_active_metrics(None)


cherrypy.tools.pybrake_apm = PybrakeAPM()


class PybrakeErrorNotifier(cherrypy.Tool):
    def __init__(self):
        cherrypy.Tool.__init__(self, 'before_error_response',
                               self.error_notifier,
                               priority=1)

    def _setup(self, **kwargs):
        cherrypy.Tool._setup(self)

    def error_notifier(self, **kwargs):
        notifier = cherrypy.config.get('pybrake')
        notifier.notify(_exc_info()[1])


cherrypy.tools.pybrake_error = PybrakeErrorNotifier()


class PybrakeQueryStats(cherrypy.Tool):
    def __init__(self):
        cherrypy.Tool.__init__(self, 'on_start_resource',
                               self.start_timer,
                               priority=21)

    def _setup(self, **kwargs):
        cherrypy.Tool._setup(self)

    def start_timer(self, **kwargs):
        notifier = cherrypy.config.get('pybrake')
        if not notifier.config.get("performance_stats"):
            return

        if _sqla_available:
            event.listen(cherrypy.request.db.bind, "before_cursor_execute",
                         _before_sql_cursor(notifier.config))
            event.listen(cherrypy.request.db.bind, "after_cursor_execute",
                         _after_sql_cursor(notifier.config))


cherrypy.tools.pybrake_query_stats = PybrakeQueryStats()


def _before_sql_cursor(config):
    def _sqla_before_cursor_execute(
            conn, cursor, statement, parameters, context,
            executemany
    ):
        if not config.get("performance_stats"):
            return
        start_span("sql")

    return _sqla_before_cursor_execute


def _after_sql_cursor(config):
    def _sqla_after_cursor_execute(
            conn, cursor, statement, parameters, context,
            executemany
    ):
        notifier = cherrypy.config.get('pybrake')
        if not config.get("performance_stats"):
            return
        end_span("sql")
        metric = get_active_metrics()
        if metric is not None:
            notifier.queries.notify(
                query=statement,
                method=getattr(metric, "method", ""),
                route=getattr(metric, "route", ""),
                start_time=metric.start_time,
                end_time=time.time(),
            )

    return _sqla_after_cursor_execute


class PybrakePlugin(plugins.SimplePlugin):
    def __init__(self, bus, project_id, project_key, ORMBase=None, **kw):
        """
        The plugin is registered to the CherryPy engine and therefore
        is part of the bus (the engine *is* a bus) registry.
        We use this plugin to create the notifier instance and apply patch
        for Error notification and APM.
        :param project_id: Airbrake project id
        :param project_key: Airbrake project key
        :param kw:
        """

        plugins.SimplePlugin.__init__(self, bus)
        self.project_id = project_id
        self.project_key = project_key
        self.ORMBase = ORMBase
        self.kwargs = kw

        self.bus.subscribe('pybrake.bind', self.bind)

        self.notifier = None

    def start(self):
        self.notifier = Notifier(
            project_id=self.project_id,
            project_key=self.project_key,
            **self.kwargs
        )
        self.notifier.add_filter(request_filter)

        # Patch of route breakdown
        if _jinja_available:
            old_template_render = Template.render

            def patch_template_render(self, *args: t.Any, **kwargs: t.Any):
                start_span("template")
                res = old_template_render(self, *args, *kwargs)
                end_span("template")
                return res

            Template.render = patch_template_render

    def create(self):
        if 'pybrake' in cherrypy.config:
            raise ValueError("pybrake is already injected")
        self.start()
        cherrypy.config.update({
            'pybrake': self.notifier,
            'tools.pybrake_apm.on': True,
            'tools.pybrake_error.on': True,
            'tools.pybrake_query_stats.on': True,
        })

    def bind(self, session):
        session.configure(bind=self.notifier)
