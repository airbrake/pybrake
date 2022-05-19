from datetime import *
from random import randrange
from time import sleep
from wsgiref.simple_server import make_server

import requests
from pybrake.middleware.pyramid import init_pybrake_config
from pyramid.config import Configurator
from pyramid.response import Response
from pyramid.view import view_config
from pyramid_basemodel import Base, BaseMixin
from sqlalchemy import Column, String

city_list = ["pune", "austin", "santabarbara", "washington"]

PYBRAKE_CONFIG = dict(
    project_id=999999,
    project_key='xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx',
)


class User(Base, BaseMixin):
    __tablename__ = "user"
    name = Column(String(80), unique=True, nullable=False)
    email = Column(String(120), unique=True, nullable=False)

    def __repr__(self):
        return "<User %r>" % self.name


# API for Hello Application
@view_config(route_name='hello')
def hello(request):
    sleep(randrange(0, 3))
    print(User.query.all())
    return Response('Hello, Welcome to the Weather App!')


# API for current server date
@view_config(route_name='date', renderer='json')
def date(request):
    return {
        'date': 'Current Date and Time is: %s' % datetime.now()
    }


# API for location details
@view_config(route_name='locations', renderer='json')
def locations(request):
    return {
        'locations': city_list
    }


# API for weather details for a location
@view_config(route_name='weather', renderer='json')
def weather(request):
    location_name = request.matchdict.get('location_name')
    if location_name not in city_list:
        request.response.status = 400
        return {
            'errors': {
                'message': 'Location not found!'
            }
        }
    if location_name == 'washington':
        5 / 0
    with requests.get(
            'https://airbrake.github.io/weatherapi/weather/' + location_name) as f:
        return f.json()


if __name__ == '__main__':
    settings = {
        'reload_all': True,
        'debug_all': True,
        'PYBRAKE': PYBRAKE_CONFIG,
        'sqlalchemy.url': 'sqlite:////tmp/test.db',
        'basemodel.should_create_all': True,
        'fixtures': True,
    }
    with Configurator(settings=settings) as config:
        config.include('pyramid_basemodel')
        config.include('pyramid_tm')
        config.add_route('hello', '/')
        config.add_route('date', 'date')
        config.add_route('locations', 'locations')
        config.add_route('weather', 'weather/{location_name}')
        config.scan(".")

        config = init_pybrake_config(config)
        app = config.make_wsgi_app()

    server = make_server('0.0.0.0', 3000, app)
    server.serve_forever()
