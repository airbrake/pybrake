**Django Sample Application for Pybrake**

**About the application:**

The example application provides three GET endpoints:

/date - gets the system date from the server
/locations - gets the supported locations for use with the /weather endpoint
/weather/{locationName} - gets the weather for a location; valid values for locationName can be found using the /locations endpoint

**Steps to run the API:**

1. Install the dependencies for the application with command - "pip3 install -r requirements.txt"
2. Run the localhost server with command - python manage.py runserver 3000 or python manage.py runserver 127.10.10.10:3000
3. To retrieve the responses, append the endpoints to the localhost URL with a '/'.


Use the below curl commands to interact with the endpoints. The endpoints require an api-key HTTP header.

curl "http://localhost:3000/date" -H 'api-key: b761be830f7c23ebe1c3250d42c43673'
curl "http://localhost:3000/locations" -H 'api-key: b761be830f7c23ebe1c3250d42c43673'
curl "http://localhost:3000/weather/<austin/pune/santabarbara>" -H 'api-key: b761be830f7c23ebe1c3250d42c43673'
curl "http://localhost:3000/weather/<random-city-name>" -H 'api-key: b761be830f7c23ebe1c3250d42c43673'
  
The last curl command will raise 404 Not Found error.



