import os
import asyncio
import requests
from datetime import datetime

import tornado.web
from tornado_sqlalchemy import SQLAlchemy
from tornado_sqlalchemy import SessionMixin
from pybrake.middleware.tornado import init_app

from sqlalchemy import Column, Integer, String

city_list = ["pune", "austin", "santabarbara", "washington"]

# SQL setup
db = SQLAlchemy(url="sqlite:///:memory:")


class User(db.Model):
    __tablename__ = 'user'
    id = Column(Integer, primary_key=True)
    username = Column(String(80), unique=True, nullable=False)
    email = Column(String(120), unique=True, nullable=False)

    def __repr__(self):
        return "<User %r>" % self.username


class Index(SessionMixin, tornado.web.RequestHandler):
    def get(self):
        count = self.session.query(User).count()
        if not count:
            user = User()
            user.username = "test"
            user.email = "test@test.com"
            self.session.add(user)
        self.set_header("Content-Type", "text/html")
        self.render("index.html")


class Date(tornado.web.RequestHandler):
    def get(self):
        self.write({"date": "Current Date and Time is: %s" %
                               datetime.now()})
        self.set_header("Content-Type", "application/json")


class Locations(tornado.web.RequestHandler):
    def get(self):
        self.write({"locations": city_list})
        self.set_header("Content-Type", "application/json")


class Weather(tornado.web.RequestHandler):
    def get(self, location_name):
        if location_name not in city_list:
            # self._reason = "Location not found!"
            raise tornado.web.HTTPError(
                status_code=404,
                reason="Location not found!"
            )
        with requests.get(
                'https://airbrake.github.io/weatherapi/weather/' + location_name
        ) as f:
            self.write(f.json())
            self.set_header("Content-Type","application/json")


async def main():
    db.metadata.create_all(bind=db.engine)
    settings = {
        "db": db,
        "PYBRAKE": {
            "project_id": 99999,
            "project_key": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
        },
        "template_path": os.path.join(os.path.dirname(__file__), "templates")
    }
    app = tornado.web.Application([
        ("/", Index),
        ("/date", Date),
        ("/locations", Locations),
        (r"/weather/?(?P<location_name>[A-Za-z0-9-]+)?", Weather),
    ], **settings)
    print("Serving on localhost:8000...")
    app = init_app(app)
    app.listen(8000)
    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
