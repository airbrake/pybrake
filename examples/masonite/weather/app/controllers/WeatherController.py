"""A WeatherController Module."""
from datetime import datetime

import requests
from app.models.User import User
from masonite.controllers import Controller
from masonite.response import Response
from masonite.views import View

city_list = ["pune", "austin", "santabarbara", "washington"]


class WeatherController(Controller):
    """WelcomeController Controller Class."""

    def show(self, view: View):
        users = User.all()
        if not users.count():
            user = User()
            users = user.register(dictionary={
                'name': 'Test',
                'email': 'test@test.com',
                'password': 'password',
            })
        print(users)
        return view.render("welcome")

    def date(self):
        return {
            'date': "Current Date and Time is: %s" % datetime.now()
        }

    def locations(self):
        return {
            'locations': city_list
        }

    def weather(self, location_name, response: Response):
        if location_name not in city_list:
            response.status(400)
            return {
                'error': 'Location not found!'
            }
        with requests.get(
                'https://airbrake.github.io/weatherapi/weather/' + location_name) as f:
            return f.json()
