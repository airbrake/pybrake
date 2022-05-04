import json
from datetime import datetime
from bottle import run, get, response, Bottle
from pybrake.middleware.bottle import init_app


app = Bottle()

app.config['PYBRAKE'] = dict(
    project_id=999999,
    project_key='xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'
)

app = init_app(app)

city_list = ["austin", "pune", "santabarbara"]


# API for Hello Application
@app.get('/')
def hello():
    return "Hello, Welcome to the Weather App!"


# API for current server date
@app.get('/date', method=['GET'])
def getdate():
    return {
        "date": "Current date and time is: %s" % datetime.now()
    }


# API for location details
@app.get('/locations')
def get_location_details():
    return {
        'cities': city_list
    }


# API for weather details for a location
@app.get('/weather/<location_name>')
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


if __name__ == '__main__':
    run(app, host='localhost', port=3000, debug=True, reloader=True)
