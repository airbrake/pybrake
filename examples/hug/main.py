import datetime
import json
import os
from datetime import datetime

import hug
import requests
from falcon import HTTP_400, HTTP_500, HTTPError
from pybrake.middleware.hug import init_app

from sqlalchemy import INTEGER, Column, String, select, insert
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base

engine = create_engine('sqlite:///./test.db')
Base = declarative_base()

PYBRAKE_CONFIG = {
    "PYBRAKE": {
        "project_id": 99999,
        "project_key": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
    }
}

api = hug.API(__name__)
PYBRAKE_CONFIG = init_app(api, PYBRAKE_CONFIG, engine)

DIRECTORY = os.path.dirname(os.path.realpath(__file__))
city_list = ["pune", "austin", "santabarbara", "washington"]


class User(Base):
    __tablename__ = "user"

    id = Column(INTEGER, primary_key=True)
    username = Column(String(80), unique=True, nullable=False)
    email = Column(String(120), unique=True, nullable=False)

    def __repr__(self):
        return "<User %r>" % self.username


@hug.get("/", output=hug.output_format.html, api=api)
def index(**kwargs):
    with engine.begin() as conn:
        stmt = select(User)
        result = conn.execute(stmt)
        res = result.scalar()
        if not res:
            stmt = insert(User).values(username="test",
                                       email="test@test.com")
            conn.execute(stmt)
    with open(os.path.join(DIRECTORY, "templates/index.html")) as document:
        return document.read()


@hug.get("/date", api=api)
def date():
    return {"date": datetime.now()}


@hug.get("/locations", api=api)
def locations():
    return {"locations": city_list}


@hug.get("/weather/{location_name}", api=api)
def get_weather_details(location_name, resp):
    if location_name not in city_list:
        resp.status = HTTP_400
        resp.text = json.dumps({'error': 'Location not found!'})
        return
    if location_name == "washington":
        resp.status = HTTP_500
        resp.text = json.dumps(
            {'error': "Washington's data is not available!"})
        raise HTTPError(
            status=HTTP_500,
            title=str("Washington's data is not available!")
        )

    with requests.get(
            'https://airbrake.github.io/weatherapi/weather/' + location_name) as f:
        resp.status = f.status_code
        resp.text = f.content


if __name__ == "__main__":
    Base.metadata.create_all(engine)
    hug.API(__name__).http.serve()
