import json
import os
from datetime import datetime
from wsgiref.simple_server import make_server

import falcon
import falcon_sqla
import jinja2
import requests
from pybrake.middleware.falcon import init_app
from sqlalchemy import INTEGER, Column, String, select, insert
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base

engine = create_engine('sqlite:///./test.db')
Base = declarative_base()
manager = falcon_sqla.Manager(engine)

app = falcon.App(middleware=[manager.middleware])

PYBRAKE_CONFIG = {
    "PYBRAKE": {
        "project_id": 999999,
        "project_key": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
    }
}

# _base_model_session_ctx = ContextVar("session")

app, PYBRAKE_CONFIG = init_app(app, PYBRAKE_CONFIG, engine)


class User(Base):
    __tablename__ = "user"

    id = Column(INTEGER, primary_key=True)
    username = Column(String(80), unique=True, nullable=False)
    email = Column(String(120), unique=True, nullable=False)

    def __repr__(self):
        return "<User %r>" % self.username


city_list = ["pune", "austin", "santabarbara", "washington"]


def load_template(name):
    path = os.path.join('templates', name)
    with open(os.path.abspath(path), 'r') as fp:
        return jinja2.Template(fp.read())


# API for Hello Application
class Weather:
    def on_get(self, req, resp):
        template = load_template('index.html')
        resp.status = falcon.HTTP_200  # This is the default status
        resp.content_type = falcon.MEDIA_HTML  # Default is JSON, so override

        with engine.begin() as conn:
            stmt = select(User)
            result = conn.execute(stmt)
            res = result.scalar()
            if not res:
                stmt = insert(User).values(username="test",
                                           email="test@test.com")
                conn.execute(stmt)

        resp.text = template.render()


# API for current server date
class Date:
    def on_get(self, req, resp):
        resp.status = falcon.HTTP_200
        resp.text = json.dumps({
            'date': "Current Date and Time is: %s" % datetime.now()
        })


# API for location details
class Locations:
    def on_get(self, req, resp):
        resp.status = falcon.HTTP_200
        resp.text = json.dumps({'locations': city_list})


# API for weather details for a location
class WeatherLocation:
    def on_get(self, req, resp, location_name):
        if location_name not in city_list:
            resp.status = falcon.HTTP_400
            resp.text = json.dumps({'error': 'Location not found!'})
            return
        if location_name == "washington":
            resp.status = falcon.HTTP_500
            resp.text = json.dumps({'error': "Washington's data is not available!"})
            raise falcon.HTTPError(
                status=falcon.HTTP_500,
                title=str("Washington's data is not available!")
            )

        with requests.get(
                'https://airbrake.github.io/weatherapi/weather/' + location_name) as f:
            resp.status = f.status_code
            resp.text = f.content


weather = Weather()
app.add_route('/', weather)

date = Date()
app.add_route('/date', date)

locations = Locations()
app.add_route('/locations', locations)

weather_location = WeatherLocation()
app.add_route('/weather/{location_name}', weather_location)

# debug logs enabled with debug = True
if __name__ == "__main__":
    with make_server('', 8000, app) as httpd:
        print('Serving on port 8000...')
        Base.metadata.create_all(engine)

        # Serve until process is killed
        httpd.serve_forever()
