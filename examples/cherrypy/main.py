import json
import pybrake
from datetime import *

import cherrypy
import simplejson

notifier = pybrake.Notifier(project_id=999999,
                            project_key='xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx',
                            environment='production')


city_list = ["pune", "austin", "santabarbara"]


class WeatherDetails(object):
    # API for Hello Application
    @cherrypy.expose
    def index(self):
        return "Hello world!"

    # API for current server date
    @cherrypy.expose
    def date(self):
        current_datetime = datetime.now()
        html = "Current Date and Time is: %s" % current_datetime
        return html

    # API for location details
    @cherrypy.expose
    def locations(self):
        locations_list = simplejson.dumps(city_list)
        return locations_list

    # API for weather details for a location
    @cherrypy.expose
    def weather(self, location_name):
        file_name = location_name + ".json"
        if location_name in city_list:
            with open('static/' + file_name, "r") as f:
                data = json.load(f)
                return data
        raise cherrypy.HTTPError(404, 'Not Found')


if __name__ == '__main__':
    cherrypy.quickstart(WeatherDetails())
