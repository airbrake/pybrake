from contextvars import ContextVar
from datetime import *

import requests
from pybrake.middleware.sanic import init_app
from sanic import Sanic
from sanic import response
from sqlalchemy import INTEGER, Column, String, select, insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker

app = Sanic(__name__)

bind = create_async_engine("sqlite+aiosqlite:///./test.db", echo=True)
Base = declarative_base()

app.config["PYBRAKE"] = dict(
    project_id=9999,
    project_key="xxxxxxxxxxxxxxxxxxxxxxxxx",
    environment="test",
    performance_stats=True,  # False to disable APM
)

_base_model_session_ctx = ContextVar("session")

app = init_app(app, bind)


@app.middleware("request")
async def inject_session(request):
    request.ctx.session = sessionmaker(bind, AsyncSession,
                                       expire_on_commit=False)()
    request.ctx.session_ctx_token = _base_model_session_ctx.set(
        request.ctx.session)


@app.middleware("response")
async def close_session(request, response):
    if hasattr(request.ctx, "session_ctx_token"):
        _base_model_session_ctx.reset(request.ctx.session_ctx_token)
        await request.ctx.session.close()


def setup_database():
    @app.listener('after_server_start')
    async def connect_to_db(*args, **kwargs):
        async with bind.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    @app.listener('after_server_stop')
    async def disconnect_from_db(*args, **kwargs):
        async with bind.begin() as conn:
            await conn.close()


class User(Base):
    __tablename__ = "user"

    id = Column(INTEGER, primary_key=True)
    username = Column(String(80), unique=True, nullable=False)
    email = Column(String(120), unique=True, nullable=False)

    def __repr__(self):
        return "<User %r>" % self.username


city_list = ["pune", "austin", "santabarbara", "washington"]


# API for Hello Application
@app.route("/")
async def run(request):
    session = request.ctx.session
    async with session.begin():
        stmt = select(User)
        result = await session.execute(stmt)
        res = result.scalar()
        if not res:
            stmt = insert(User).values(username="test", email="test@test.com")
            await session.execute(stmt)
    return response.html("""
        <html lang="en">
            <head>
              <meta http-equiv="Content-Type" content="text/html; charset=UTF-8"/>
              <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1.0"/>
              <title>Cherrypy Weather App</title>
            </head>
            <body>
                <H1>Hello, Welcome to Cherrypy Weather App.</H1>
            </body>
        </html>
    """)


# API for current server date
@app.route("date")
def getdate(request):
    return response.json({
        'date': "Current Date and Time is: %s" % datetime.now()
    })


# API for location details
@app.route("locations")
def get_location_details(request):
    return response.json({'locations': city_list})


# API for weather details for a location
@app.route("/weather/<location_name>")
def get_weather_details(request, location_name):
    if location_name not in city_list:
        raise response.json({'error': 'Location not found!'}, 400)
    with requests.get(
            'https://airbrake.github.io/weatherapi/weather/' + location_name) as f:
        return response.json(f.json())


# debug logs enabled with debug = True
if __name__ == "__main__":
    setup_database()
    app.run(host="0.0.0.0", port=3000, debug=True, auto_reload=True)
