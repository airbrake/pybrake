# Bottle Sample Application for Pybrake

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

To find your project_id and project_key from Airbrake account and replace it in below code in your project's `main.py` file.

```python
AIRBRAKE = dict(
    project_id=999999,  # Insert your Project ID here
    project_key='xxxxxxxxxxxxxxxxxxxxxxxxxxxxx', # Insert your Project Key here
)
```

3. Run the localhost server

```bash
python main.py
```

3. To retrieve the responses, append the endpoints to the localhost URL with a `/`.

Use the below curl commands to interact with the endpoints.

```bash
curl "http://localhost:3000/date" 
curl "http://localhost:3000/locations"
curl "http://localhost:3000/weather/<austin/pune/santabarbara>"
curl "http://localhost:3000/weather"
```
  
The last curl command will raise `404 Not Found` error.
