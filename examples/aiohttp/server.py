from datetime import datetime

import aiohttp_jinja2
import jinja2
import requests
from aiohttp import web
from pybrake.middleware.aiohttp import pybrake_middleware
from sqlalchemy import Column, Integer, String, select, insert
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base

city_list = ["austin", "pune", "santabarbara", "washington"]

routes = web.RouteTableDef()

# SQL setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./sql_app.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

Base = declarative_base(bind=engine)

pybrake_middleware = pybrake_middleware(sqlEngine=engine)


class User(Base):
    __tablename__ = 'user'
    id = Column(Integer, primary_key=True)
    username = Column(String(80), unique=True, nullable=False)
    email = Column(String(120), unique=True, nullable=False)

    def __repr__(self):
        return "<User %r>" % self.username


@routes.get('/')
def index(request):
    with engine.begin() as conn:
        stmt = select(User)
        result = conn.execute(stmt)
        res = result.scalar()
        if not res:
            stmt = insert(User).values(username="test", email="test@test.com")
            conn.execute(stmt)
    return aiohttp_jinja2.render_template('index.html', request, {})


@routes.get('/date')
def getdate(request):
    return web.json_response(data={
        "date": "Current date and time is: %s" % datetime.now()
    })


@routes.get('/locations')
def get_location_details(request):
    return web.json_response(data={
        'cities': city_list
    })


# API for weather details for a location
@routes.get('/weather/{location_name}')
def get_weather_details(request):
    location_name = request.match_info['location_name']
    if location_name not in city_list:
        return web.json_response(data={
            'error': 'Not found: Location not found!'
        }, status=404)
    with requests.get(
            'https://airbrake.github.io/weatherapi/weather/' + location_name) as f:
        data = f.json()
        return web.json_response(data=data)


if __name__ == '__main__':
    app = web.Application(middlewares=[pybrake_middleware])
    aiohttp_jinja2.setup(app,
                         loader=jinja2.FileSystemLoader(
                             './templates'))
    app['PYBRAKE'] = dict(
        project_id=999999,
        project_key='xxxxxxxxxxxxxxxxxxxxx',
        environment='develop'  # optional
    )
    app.add_routes(routes)
    Base.metadata.create_all(engine)
    web.run_app(app)
