import json
from datetime import *
from wsgiref.simple_server import make_server
import pybrake
import simplejson
from pyramid.config import Configurator
from pyramid.httpexceptions import HTTPException
from pyramid.response import Response

city_list = ["pune", "austin", "santabarbara"]

notifier = pybrake.Notifier(project_id=999999,
                            project_key='xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx',
                            environment='production')


# API for Hello Application
def hello(request):
    return Response('Hello, Welcome to the Weather App!')


# API for current server date
def date(request):
    current_datetime = datetime.now()
    html = "Current Date and Time is: %s" % current_datetime
    return Response(html)


# API for location details
def locations(request):
    locations_list = simplejson.dumps(city_list)
    return Response(locations_list)


# API for weather details for a location
def weather(request, location_name):
    file_name = location_name + ".json"
    if location_name in city_list:
        with open('static/' + file_name, "r") as f:
            data = json.load(f)
            return Response(data)
    raise HTTPException(status_code=404, detail="Location not found")


if __name__ == '__main__':
    with Configurator() as config:
        config.add_route('hello', '/')
        config.add_route('date', '/date')
        config.add_route('locations', '/locations')
        config.add_route('weather', '/weather/{location_name}')
        config.add_view(hello, route_name='hello')
        config.add_view(date, route_name='date')
        config.add_view(locations, route_name='locations')
        config.add_view(weather, route_name='weather')
        app = config.make_wsgi_app()
    server = make_server('0.0.0.0', 3000, app)
    server.serve_forever()