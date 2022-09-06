import requests
from time import sleep
from random import randrange
from datetime import datetime
from bottle import run, response, Bottle
from pybrake.middleware.bottle import init_app
from bottle.ext import sqlalchemy
from sqlalchemy import create_engine, Column, Integer, Sequence, String
from sqlalchemy.ext.declarative import declarative_base

app = Bottle()

app.config['PYBRAKE'] = dict(
    project_id=999999,
    project_key='xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx',
)

Base = declarative_base()
engine = create_engine('sqlite:////tmp/test.db', echo=True)

app.install(sqlalchemy.Plugin(
    engine,  # SQLAlchemy engine created with create_engine function.
    Base.metadata,  # SQLAlchemy metadata, required only if create=True.
    keyword='db',  # Keyword used to inject session database in a route (
    # default 'db').
    create=True,  # If it is true, execute `metadata.create_all(engine)`
    # when plugin  is applied (default False).
    commit=True,  # If it is true, plugin commit changes after route is
    # executed (default True).
    use_kwargs=False  # If it is true and keyword is not defined, plugin
    # uses **kwargs argument to inject session database (default False).
))
app = init_app(app)

city_list = ["austin", "pune", "santabarbara", "washington"]


class Entity(Base):
    __tablename__ = 'entity'
    id = Column(Integer, Sequence('id_seq'), primary_key=True)
    name = Column(String(50))

    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return "<Entity('%d', '%s')>" % (self.id, self.name)


# API for Hello Application
@app.get('/')
def hello(db):
    sleep(randrange(0, 3))
    print(db.query(Entity).all())
    return "Hello, Welcome to the Weather App!"


# API for current server date
@app.get('/date', method=['GET'])
def getdate():
    return {
        "date": "Current date and time is: %s" % datetime.now()
    }


# API for location details
@app.get('/locations')
def get_location_details():
    return {
        'cities': city_list
    }


# API for weather details for a location
@app.get('/weather/<location_name>')
def get_weather_details(location_name):
    response.headers['Content-Type'] = 'application/json'
    response.headers['Cache-Control'] = 'no-cache'
    if location_name not in city_list:
        response.status = 400
        return {
            'error': 'Not found: Location not found!'
        }
    with requests.get(
            'https://airbrake.github.io/weatherapi/weather/' +
            location_name) as f:
        data = f.json()
        return data


if __name__ == '__main__':
    run(app, host='localhost', port=3000, debug=True, reloader=True)
