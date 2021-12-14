from django.templatetags.static import static
from django.urls import path
from . import views

urlpatterns = [
    path('date/', views.getdate),
    path('locations/', views.get_location_details),
    path('weather/<location_name>', views.get_weather_details),
]