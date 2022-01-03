import json
import pybrake
from datetime import *
from bottle import route, run, template, static_file

notifier = pybrake.Notifier(project_id=999999,
                            project_key='xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx',
                            environment='production')

city_list = ["austin", "pune", "santabarbara"]


# API for Hello Application
@route('/')
def hello():
    return "Hello, Welcome to the Weather App!"


# API for current server date
@route('/date', method=['GET'])
def getdate():
    current_datetime = datetime.now()
    return template("Current date and time is: {{current_datetime}}", current_datetime=current_datetime)


# API for location details
@route('/locations', method=['GET'])
def get_location_details():
    return " ".join(city_list)


# API for weather details for a location
@route('/weather/<location_name>', method=['GET'])
def get_weather_details(location_name):
    file_name = location_name + ".json"
    if location_name in city_list:
        with open('static/' + file_name) as f:
            data = json.load(f)
            return data
    return "404 Error: Page not Found"


run(host='localhost', port=3000, debug=True)
