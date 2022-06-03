from masonite.providers import Provider
from ..tasks.WeatherTest import WeatherTest
from pybrake.middleware.masonite import (
    PybrakeNotifier, PybrakeErrorListener, PybrakeRouteMiddleware
)


class AppProvider(Provider):
    def __init__(self, application):
        self.application = application

    def register(self):
        self.application.bind(
            "pybrake", PybrakeNotifier(self.application)
        )
        self.application.make("event").listen("masonite.exception.*",
                                              [PybrakeErrorListener])
        self.application.make("middleware").add([PybrakeRouteMiddleware])
        self.application.make('scheduler').add(
            WeatherTest().every_minute()
        )

    def boot(self):
        pass
