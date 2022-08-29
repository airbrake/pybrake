import requests
from datetime import datetime
from pycnic.core import Handler

from sqlalchemy import create_engine, Column, Integer, String, Sequence, \
    select, insert
from sqlalchemy.ext.declarative import declarative_base

from pybrake.middleware.pycnic import PybrakeEnableWSGI

engine = create_engine('sqlite:///:memory:', echo=True)
Base = declarative_base()

city_list = ["austin", "pune", "santabarbara", "washington"]


class Entity(Base):
    __tablename__ = 'entity'
    id = Column(Integer, Sequence('id_seq'), primary_key=True)
    name = Column(String(50))

    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return "<Entity('%d', '%s')>" % (self.id, self.name)


class Hello(Handler):

    def get(self, name="World"):
        with engine.begin() as conn:
            stmt = select(Entity)
            result = conn.execute(stmt)
            res = result.scalar()
            if not res:
                stmt = insert(Entity).values(name=name)
                conn.execute(stmt)
        return {"message": "Hello, Welcome to the Weather App!"}


class Date(Handler):

    def get(self):
        return {
            "date": "Current date and time is: %s" % datetime.now()
        }


class Locations(Handler):

    def get(self):
        return {
            "locations": city_list
        }


class Weather(Handler):

    def get(self, location_name):
        if location_name not in city_list:
            return {
                'error': 'Not found: Location not found!'
            }
        with requests.get(
                'https://airbrake.github.io/weatherapi/weather/' +
                location_name) as f:
            return f.json()


class App(PybrakeEnableWSGI):
    config = {
        'PYBRAKE': dict(
            project_id=99999,
            project_key='xxxxxxxxxxxxxxxxxxxxxxxxxxx',
        )
    }
    sqlDBEngine = engine
    
    debug = True
    routes = [
        ("/", Hello()),
        ("/date", Date()),
        ("/locations", Locations()),
        ("/weather/([\w]+)", Weather()),
    ]


if __name__ == "__main__":

    from wsgiref.simple_server import make_server
    Base.metadata.create_all(engine)
    try:
        print("Serving on 0.0.0.0:3000...")
        make_server('127.0.0.1', 3000, App).serve_forever()
    except KeyboardInterrupt:
        pass
