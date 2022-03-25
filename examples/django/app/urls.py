from django.urls import path
from . import views

urlpatterns = [
    path('', views.hello),
    path('date', views.getdate),
    path('locations', views.get_location_details),
    path('weather/<location_name>', views.get_weather_details),
]
