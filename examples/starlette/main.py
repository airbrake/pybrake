import os
from datetime import datetime
import requests

from starlette.applications import Starlette
from starlette.responses import JSONResponse, HTMLResponse
from starlette.routing import Route
from pybrake.middleware.starlette import init_app

from sqlalchemy import Column, Integer, String
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

DIRECTORY = os.path.dirname(os.path.realpath(__file__))
city_list = ["pune", "austin", "santabarbara", "washington"]

# SQL setup
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

db = SessionLocal()


class User(Base):
    __tablename__ = 'user'
    id = Column(Integer, primary_key=True)
    username = Column(String(80), unique=True, nullable=False)
    email = Column(String(120), unique=True, nullable=False)

    def __repr__(self):
        return "<User %r>" % self.username


Base.metadata.create_all(bind=engine)


async def index(request):
    db.query(User).all()
    html_content = """
            <html>
                <head>
                    <title>Welcome to the Starlette weather app.</title>
                </head>
                <body>
                    <h1>Hello, Welcome to the Starlette weather app.</h1>
                </body>
            </html>
            """
    return HTMLResponse(content=html_content, status_code=200)


async def date(req):
    return JSONResponse({"date": "Current Date and Time is: %s" % datetime.now()})


async def locations(req):
    return JSONResponse({"locations": city_list} )


async def weather(req):
    location_name = req.path_params['location_name']
    if location_name not in city_list:
        return JSONResponse(content={
            "message": "Location not found!"
        }, status_code=404)
    with requests.get(
            'https://airbrake.github.io/weatherapi/weather/' + location_name
    ) as f:
        return JSONResponse(f.json())


app = Starlette(debug=True, routes=[
    Route('/', index),
    Route('/date', date),
    Route('/locations', locations),
    Route('/weather/{location_name}', weather),
])


app.state.PYBRAKE = {
    "project_id": 99999,
    "project_key": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
}

app = init_app(app, engine)
