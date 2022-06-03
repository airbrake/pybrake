"""Task Module Description"""
import time
from masonite.scheduling import Task
from pybrake.middleware.masonite import schedule_task


class WeatherTest(Task):

    name = "WeatherTest"

    @schedule_task
    def handle(self):
        time.sleep(10)
