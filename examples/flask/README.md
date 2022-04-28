# Flask Sample Application for Pybrake

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
2. You must get both project_id & project_key.

To find your project_id and project_key from Airbrake account and replace it in below code in your project's `server.py` file.

```python
app.config["PYBRAKE"] = dict(
    project_id="XXXXXXXXXXXX",
    project_key="XXXXXXXXXXXX",
    environment="test",
    error_notifications=True,  # False to disable error notification
    performance_stats=True,  # False to disable APM
    query_stats=True,  # False to disable query monitoring
    queue_stats=True  # False to disable queue monitoring
)
```

3. Run the localhost server

```bash
python3 server.py
```

3. To retrieve the responses, append the endpoints to the localhost URL.

Use the below curl commands to interact with the endpoints.

```bash
curl "http://localhost:3000/date" 
curl "http://localhost:3000/locations"
curl "http://localhost:3000/weather/<austin/pune/santabarbara>"
curl "http://localhost:3000/weather"
curl "http://localhost:3000/weather/Ahmedabad"
```

The second last curl command will raise `404 Not Found` error.
The last curl command will raise `400 Location not found!` error.
