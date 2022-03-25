# Django Sample Application for Pybrake

## About the application:

The example application provides three GET endpoints:

1. `/date` - returns server date and time. 
2. `/locations` - returns list of available locations. 
3. `/weather/{locationName}` - returns the weather details for the locations.

## Steps to run the API:

1. Install the dependencies for the application

```bash
pip3 install -r requirements.txt
```

2. You must set both project_id & project_key in `settings.py`.

To find your project_id and project_key from Airbrake account and replace it in below code in your project's `settings.py` file.

```python
AIRBRAKE = dict(
    project_id=999999,  # Insert your Project ID here
    project_key='xxxxxxxxxxxxxxxxxxxxxxxxxxxxx', # Insert your Project Key here
)
```

3. Run the localhost server

```bash
python manage.py runserver 3000
```

4. To retrieve the responses, append the endpoints to the localhost URL 
   with a `/`. Use the below curl commands to interact with the endpoints.

```bash
# Working Routes
curl "http://localhost:3000/date" 
curl "http://localhost:3000/locations" 
curl "http://localhost:3000/weather/<austin/pune/santabarbara>"

# Should produce an HTTP 404 error
curl -I "http://localhost:3000/weather"

# Should produce an intentional HTTP 500 error and report the error to Airbrake (since `washington` is not in the supported cities list, an `if` condition is bypassed and the `data` variable is used but not initialized)
curl -I "http://localhost:3000/weather/washington"
```
