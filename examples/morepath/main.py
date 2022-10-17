from datetime import datetime

import morepath
import requests
import sqlalchemy
from more.jinja2 import Jinja2App
from morepath_sqlalchemy.app import Session
from morepath_sqlalchemy.model import Base
from sqlalchemy import INTEGER, Column, String, select, insert
from webob.exc import HTTPNotFound, HTTPServerError
from pybrake.middleware.morepath import init_app


engine = sqlalchemy.create_engine("sqlite:///:memory:")
Session.configure(bind=engine)

city_list = ["pune", "austin", "santabarbara", "washington"]


class User(Base):
    __tablename__ = "user"

    id = Column(INTEGER, primary_key=True)
    username = Column(String(80), unique=True, nullable=False)
    email = Column(String(120), unique=True, nullable=False)

    def __repr__(self):
        return "<User %r>" % self.username


class App(Jinja2App):
    pass


@App.template_directory()
def get_template_directory():
    return "templates"


class Weather(object):
    def __init__(self, data):
        self.data = data


@App.path(path='')
class Root(object):
    pass


@App.path(path='/locations')
class Locations(object):
    pass


@App.path(path='/date')
class Date(object):
    pass


@App.json(model=Weather)
def weather_default(self, request):
    return self.data


@App.path(path='weather/{location_name}', model=Weather)
def weather_data(location_name):
    if location_name not in city_list:
        raise HTTPNotFound("Location not found!")

    with requests.get(
            'https://airbrake.github.io/weatherapi/weather/' + location_name) as f:
        return Weather(f.json())


@App.json(model=Locations)
def locations(self, request):
    return {"locations": city_list}


@App.json(model=Date)
def date(self, request):
    return {"date": "Current date and time is: %s" % datetime.now()}


@App.html(model=Root, template="index.jinja2")
def hello_doc(self, request):
    with engine.begin() as conn:
        stmt = select(User)
        result = conn.execute(stmt)
        res = result.scalar()
        if not res:
            stmt = insert(User).values(username="test",
                                       email="test@test.com")
            conn.execute(stmt)
    return {}


if __name__ == '__main__':
    App.init_settings({
        "PYBRAKE": {
            "project_id": 99999,
            "project_key": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
        }
    })
    Base.metadata.create_all(engine)
    morepath.commit(App)
    app = App()
    app = init_app(app, engine)
    morepath.run(app)
