import json
import pybrake
from datetime import *

from sanic import Sanic
from sanic import response

app = Sanic("WeatherDetails")

notifier = pybrake.Notifier(project_id=999999,
                            project_key='xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx',
                            environment='production')

city_list = ["pune", "austin", "santabarbara"]


# API for Hello Application
@app.route("/")
def run(request):
    return response.text("Hello, Welcome to the Weather App !")


# API for current server date
@app.route("date")
def getdate(request):
    current_datetime = datetime.now()
    return response.text(f"Current date and time is: {current_datetime}")


# API for location details
@app.route("locations")
def get_location_details(request):
    return response.text(" ".join(city_list))


# API for weather details for a location
@app.route("/weather/<location_name>")
def get_weather_details(request, location_name):
    file_name = location_name + ".json"
    if location_name in city_list:
        with open('static/' + file_name) as f:
            data = json.load(f)
            return data
    return "404 Error: Page not Found"



# debug logs enabled with debug = True
app.run(host="0.0.0.0", port=3000, debug=True)
