# Turbogears2 Sample Application for Pybrake

## About the application

The example application provides three GET endpoints:

1. `/date` - returns server date and time.
2. `/locations` - returns list of available locations.
3. `/weather/{locationName}` - returns the weather details for the locations.

## Setup for MinimalApplication

### Steps to run the API

1. Install the dependencies for the application

    ```bash
    pip install -r requirements.txt
    ``` 

2. Go to `weather_minimal` directory

3. You must get both `project_id` & `project_key`.

   Find your `project_id` and `project_key` in your Airbrake account and
   replace them in the below code in your project's `main.py` file.

    ```python
    config.update_blueprint({
        'PYBRAKE': {
            "project_id": 99999,
            "project_key": "xxxxxxxxxxxxxxxxxxxxxxxxxxxx",
        }
    })
    config = init_app(config)
    ```

4. Run the localhost server

    ```bash
    python main.py
    ```

## Setup for FullStackApplication

1. Install the dependencies for the application

    ```bash
    pip install -r requirements.txt
    ``` 

2. Go to `weather-fullstack` directory

3. You must get both `project_id` & `project_key`.

   Find your `project_id` and `project_key` in your Airbrake account and
   replace them in the below code in your project's 
   `weather_fullstack/config/app_cfg.py` file.

    ```python
    base_config.update_blueprint({
        'PYBRAKE': {
            "project_id": 452110,
            "project_key": "9ea9da01b33172fd10d60cbacdd223f9",
        }
    })
    base_config = init_app(base_config)
    ```

4. Run the localhost server

    ```bash 
    python setup.py develop
    gearbox setup-app
    gearbox serve
    ```

## Test Applications

1. To retrieve the responses, append the endpoints to the localhost URL.

   Use the below curl commands to interact with the endpoints.

    ```bash
    curl "http://localhost:8000/date"
    curl "http://localhost:8000/locations"
    curl "http://localhost:8000/weather/<austin/pune/santabarbara>"
    ```

   The below curl command will raise `404 Not Found` error.

    ```bash
    curl -I "http://localhost:8000/weather"
    ```

   The below curl command will raise `500 Internal Server Error`.

    ```bash
    # Should produce an intentional HTTP 500 error and report the error to
    # Airbrake (since `washington` is in the supported cities list but there 
    # is no data for `washington`, an `if` condition is bypassed and the 
    # `data` variable is used but not initialized)
    curl -I "http://localhost:8000/weather/washington"
    ```
