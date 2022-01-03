import json
import pybrake
from datetime import *

import simplejson
from fastapi import FastAPI, HTTPException

app = FastAPI()

notifier = pybrake.Notifier(project_id=999999,
                            project_key='xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx',
                            environment='production')

city_list = ["pune", "austin", "santabarbara"]


# API for Hello Application
@app.get("/")
async def root():
    return {"message": "Hello, Welcome to the weather app"}


# API for current server date
@app.get("/date")
async def date():
    current_datetime = datetime.now()
    return {"Current date and time": current_datetime}


# API for location details
@app.get("/locations")
async def locations():
    locations_list = simplejson.dumps(city_list)
    return {"locations list": locations_list}


# API for weather details for a location
@app.get("/weather/{location_name}")
async def weather(location_name):
    file_name = location_name + ".json"
    if location_name in city_list:
        with open('static/' + file_name, "r") as f:
            data = json.load(f)
            return data
    raise HTTPException(status_code=404, detail="Location not found")