import json
import pybrake
from datetime import datetime
from bottle import run, get, response

notifier = pybrake.Notifier(project_id=999999,
                            project_key='xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx',
                            environment='production')

city_list = ["austin", "pune", "santabarbara"]


# API for Hello Application
@get('/')
def hello():
    return "Hello, Welcome to the Weather App!"


# API for current server date
@get('/date', method=['GET'])
def getdate():
    return {
        "date": "Current date and time is: %s" % datetime.now()
    }


# API for location details
@get('/locations')
def get_location_details():
    return {
        'cities': city_list
    }


# API for weather details for a location
@get('/weather/<location_name>')
def get_weather_details(location_name):
    response.headers['Content-Type'] = 'application/json'
    response.headers['Cache-Control'] = 'no-cache'
    file_name = location_name + ".json"
    if location_name not in city_list:
        response.status = 400
        return {
            'error': 'Not found: Location not found!'
        }
    try:
        with open('static/' + file_name) as f:
            data = json.load(f)
            return data
    except Exception as e:
        response.status = 500
        return {
            'error': str(e)
        }


run(host='localhost', port=3000, debug=True)
