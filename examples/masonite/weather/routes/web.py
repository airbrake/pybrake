from masonite.routes import Route

ROUTES = [
    Route.get("/", "WeatherController@show"),
    Route.get("/date", "WeatherController@date"),
    Route.get("/locations", "WeatherController@locations"),
    Route.get("/weather/@location_name:string", "WeatherController@weather"),
]
