from datetime import datetime

import requests
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pybrake.middleware.fastapi import init_app
from sqlalchemy import Column, Integer, String
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from starlette.responses import JSONResponse

app = FastAPI(debug=True)
app.extra["PYBRAKE"] = dict(
    project_id=999999,
    project_key='xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx',
    environment="test",
    performance_stats=True,  # False to disable APM
)

# SQL setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./sql_app.db"

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

app = init_app(app, engine)

city_list = ["pune", "austin", "santabarbara", "washington"]


# API for Hello Application
@app.get("/", response_class=HTMLResponse)
async def root():
    print(db.query(User).all())
    html_content = """
        <html>
            <head>
                <title>Welcome to the weather app.</title>
            </head>
            <body>
                <h1>Hello, Welcome to the weather app.</h1>
            </body>
        </html>
        """
    return HTMLResponse(content=html_content, status_code=200)


# API for current server date
@app.get("/date")
async def date():
    current_datetime = datetime.now()
    return {"Current date and time": current_datetime}


# API for location details
@app.get("/locations")
async def locations():
    return {"locations list": city_list}


# API for weather details for a location
@app.get("/weather/{location_name}")
async def weather(location_name):
    if location_name not in city_list:
        return JSONResponse(content={
            "message": "Location not found!"
        }, status_code=404)
    with requests.get(
            'https://airbrake.github.io/weatherapi/weather/' + location_name
    ) as f:
        data = f.json()
        return data
