# -*- coding: utf-8 -*-
"""Main Controller"""

from datetime import datetime

import requests
from tg import expose
from tg import tmpl_context
from tg.exceptions import HTTPNotFound
from weather_fullstack import model
from weather_fullstack.controllers.error import ErrorController
from weather_fullstack.lib.base import BaseController
from weather_fullstack.model import DBSession

__all__ = ['RootController']

city_list = ["pune", "austin", "santabarbara", "washington"]


class RootController(BaseController):
    """
    The root controller for the weather-fullstack application.

    All the other controllers and WSGI applications should be mounted on this
    controller. For example::

        panel = ControlPanelController()
        another_app = AnotherWSGIApplication()

    Keep in mind that WSGI applications shouldn't be mounted directly: They
    must be wrapped around with :class:`tg.controllers.WSGIAppController`.

    """
    error = ErrorController()

    def _before(self, *args, **kw):
        tmpl_context.project_name = "weather_fullstack"

    @expose("weather_fullstack.templates.index")
    def index(self):
        count = DBSession.query(model.auth.User).count()
        if not count:
            user = model.auth.User()
            user.user_name = "test"
            user.email_address = "test@test.com"
            user.display_name = "test"
            user.password = "test"
            DBSession.add(user)
        return dict(app="Weather")

    @expose("json")
    def date(self):
        return dict(date="Current Date and Time is: %s" % datetime.now())

    @expose("json")
    def locations(self):
        return dict(locations=city_list)

    @expose("json")
    def weather(self, location_name):
        if location_name not in city_list:
            raise HTTPNotFound(detail="Location not found!")
        with requests.get(
                'https://airbrake.github.io/weatherapi/weather/' + location_name) as f:
            return f.json()
