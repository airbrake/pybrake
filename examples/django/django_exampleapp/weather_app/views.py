import json
from datetime import *
import simplejson
from django.http import HttpResponse, JsonResponse, Http404, HttpResponseNotFound
from rest_framework import status
from rest_framework.utils import json

# Create your views here.
city_list = ["pune", "austin", "santabarbara"]


# API for current server date
def getdate(request):
    current_datetime = datetime.now()
    html = "Current Date and Time is: %s" % current_datetime
    return HttpResponse(html, {"status": "success"}, status=status.HTTP_200_OK)


def get_location_details(request):
    return HttpResponse(simplejson.dumps(city_list), content_type='application/json', status=status.HTTP_200_OK)


def get_weather_details(request, location_name):
    file_name = location_name + ".json"
    if location_name in city_list:
        try:
            with open('static/' + file_name) as f:
                data = json.load(f)
        except IOError:
            return HttpResponseNotFound("No Response")
        return JsonResponse(data, status=status.HTTP_200_OK, safe=False)
