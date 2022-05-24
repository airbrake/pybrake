# CherryPy Sample Application for Pybrake

## About the application

The example application provides three GET endpoints:

1. `/date` - returns server date and time
2. `/locations` - returns list of available locations
3. `/weather/{locationName}` - returns the weather details for the locations.

## Steps to run the API

1. Install the dependencies for the application

    ```bash
    pip install -r requirements.txt
    ```

2. You must get both project_id & project_key. To find your project_id and project_key from Airbrake account and replace it in below code in your project's `main.py` file in config `dict`.

    ```python
    "PYBRAKE": {
        'project_id': 999999,
        'project_key': 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx',
        'environment': 'test'
    },
    ```

3. Run the localhost server

    ```bash
    python main.py
    ```

4. To retrieve the responses, append the endpoints to the localhost URL.

   Use the below curl commands to interact with the endpoints.

    ```bash
    curl "http://localhost:3000/date"
    curl "http://localhost:3000/locations"
    curl "http://localhost:3000/weather/<austin/pune/santabarbara>"
    ```

   The below curl command will raise `404 Not Found` error.

    ```bash
    curl -I "http://localhost:3000/weather"
    ```

   The below curl command will raise `500 Internal server error` error.

    ```bash
    # Should produce an intentional HTTP 500 error and report the error to Airbrake (since `washington` is in the supported cities list but there is no data for `washington`, an `if` condition is bypassed and the `data` variable is used but not initialized)
    curl -I "http://localhost:3000/weather/washington"
    ```
