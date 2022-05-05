from datetime import datetime

import requests
from django.http import HttpResponse, JsonResponse
from rest_framework import status

# Create your views here.
city_list = ["pune", "austin", "santabarbara", "washington"]


# API for Hello Application
def hello(request):
    return HttpResponse("Hello, Welcome to the Weather App!")


# API for current server date
def getdate(request):
    return JsonResponse(
        data={
            "date": "Current Date and Time is: %s" % datetime.now()
        },
        status=status.HTTP_200_OK
    )


# API for location details
def get_location_details(request):
    return JsonResponse(
        data={
            "locations": city_list
        },
        status=status.HTTP_200_OK
    )


# API for weather details for a location
def get_weather_details(request, location_name):
    if location_name not in city_list:
        return JsonResponse(
            status=status.HTTP_404_NOT_FOUND,
            data={
                "error": "Location not found!"
            }
        )
    with requests.get("https://airbrake.github.io/weatherapi/weather/" +
                      location_name) as f:
        data = f.json()
    return JsonResponse(data, status=status.HTTP_200_OK, safe=False)
