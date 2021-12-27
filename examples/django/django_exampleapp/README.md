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

2.  Run the localhost server

```bash
python manage.py runserver 3000
```

3. To retrieve the responses, append the endpoints to the localhost URL with a `/`.

Use the below curl commands to interact with the endpoints. The endpoints require an api-key HTTP header.

```bash
curl "http://localhost:3000/date/" -H 'api-key: b761be830f7c23ebe1c3250d42c43673' 
curl "http://localhost:3000/locations/" -H 'api-key: b761be830f7c23ebe1c3250d42c43673' 
curl "http://localhost:3000/weather/<austin/pune/santabarbara>/" -H 'api-key: b761be830f7c23ebe1c3250d42c43673' 
curl "http://localhost:3000/weather/" -H 'api-key: b761be830f7c23ebe1c3250d42c43673'
```
  
The last curl command will raise `404 Not Found` error.
