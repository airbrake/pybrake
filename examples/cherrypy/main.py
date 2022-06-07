import os
from datetime import datetime

import cherrypy
import requests
from cp_sqlalchemy import SQLAlchemyTool, SQLAlchemyPlugin
from jinja2 import Environment, FileSystemLoader
from pybrake.middleware.cherrypy import PybrakePlugin
from sqlalchemy import Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base

config = {
    "PYBRAKE": {
        'project_id': 999999,
        'project_key': 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx',
        'environment': 'test'
    },
    '/': {
        'tools.db.on': True
    }
}

Base = declarative_base()

city_list = ["pune", "austin", "santabarbara", "washington"]

# GET CURRENT DIRECTORY
CUR_DIR = os.path.dirname(os.path.abspath(__file__))
env = Environment(loader=FileSystemLoader(CUR_DIR), trim_blocks=True)


class User(Base):
    __tablename__ = 'user'
    id = Column(Integer, primary_key=True)
    username = Column(String(80), unique=True, nullable=False)
    email = Column(String(120), unique=True, nullable=False)

    def __repr__(self):
        return "<User %r>" % self.username


class WeatherDetails(object):

    @property
    def db(self):
        return cherrypy.request.db

    # API for Hello Application
    @cherrypy.expose
    def index(self):
        res = self.db.query(User).all()
        if not res:
            self.db.add(User(username="test", email="test@test.com"))
            self.db.commit()
        template = env.get_template("index.html")
        return template.render()

    # API for current server date
    @cherrypy.expose
    @cherrypy.tools.json_out()
    def date(self):
        return {
            'date': "Current Date and Time is: %s" % datetime.now()
        }

    # API for location details
    @cherrypy.expose
    @cherrypy.tools.json_out()
    def locations(self):
        return {
            'locations': city_list
        }

    # API for weather details for a location
    @cherrypy.expose
    @cherrypy.tools.json_out()
    def weather(self, location_name):
        if location_name not in city_list:
            raise cherrypy.HTTPError(404, 'Location not found!')
        with requests.get(
                'https://airbrake.github.io/weatherapi/weather/' + location_name) as f:
            return f.json()


if __name__ == '__main__':
    cherrypy.tools.db = SQLAlchemyTool()
    cherrypy.tree.mount(WeatherDetails(), '/', config)

    sqlalchemy_plugin = SQLAlchemyPlugin(
        cherrypy.engine, Base, 'sqlite:///./sql_app.db'
    )
    sqlalchemy_plugin.subscribe()
    sqlalchemy_plugin.create()

    pybrake_plugin = PybrakePlugin(
        cherrypy.engine, **config.get('PYBRAKE')
    )
    pybrake_plugin.subscribe()
    pybrake_plugin.create()

    cherrypy.quickstart(WeatherDetails(), config=config)
