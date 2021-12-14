import json
import os
from datetime import *
import simplejson
from django.conf.global_settings import STATIC_ROOT
from django.http import HttpResponse, JsonResponse, Http404
from rest_framework import status
from rest_framework.utils import json

# Create your views here.
city_list = ["austin", "pune", "santabarbara"]


# API for current server date
def getdate(request):
    current_datetime = datetime.now()
    html = "Current Date and Time is: %s" % current_datetime
    return HttpResponse(html, {"status": "success"}, status=status.HTTP_200_OK)


def get_location_details(request):
    return HttpResponse(simplejson.dumps(city_list), content_type='application/json', status=status.HTTP_200_OK)


def get_weather_details(request, location_name):
    result = []
    for city in city_list:
        print(city)
        location_name = city + ".json"
        print(location_name)
        try:
            with open('static/' + location_name) as f:
                result.append(json.load(f))
        except IOError:
            raise Http404()
        return JsonResponse(result, status=status.HTTP_200_OK,safe=False)


