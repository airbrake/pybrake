from datetime import datetime
from wsgiref.simple_server import make_server

import requests
from pybrake.middleware.turbogears import init_app
from sqlalchemy import Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker
from tg import MinimalApplicationConfigurator
from tg import expose, TGController
from tg.configurator.components.sqlalchemy import \
    SQLAlchemyConfigurationComponent
from tg.exceptions import HTTPNotFound
from tg.util import Bunch

DeclarativeBase = declarative_base()

city_list = ["pune", "austin", "santabarbara", "washington"]


class User(DeclarativeBase):
    __tablename__ = 'user'
    id = Column(Integer, primary_key=True)
    username = Column(String(80), unique=True, nullable=False)
    email = Column(String(120), unique=True, nullable=False)

    def __repr__(self):
        return "<User %r>" % self.username


# RootController of our web app, in charge of serving content for /
class RootController(TGController):

    @expose("index.xhtml")
    def index(self):
        count = DBSession.query(User).count()
        if not count:
            user = User()
            user.username = "test"
            user.email = "test@test.com"
            DBSession.add(user)
        return dict(app="Weather")

    @expose("json")
    def date(self):
        return dict(date="Current Date and Time is: %s" % datetime.now())

    @expose("json")
    def locations(self):
        return dict(locations=city_list)

    @expose("json")
    def weather(self, location_name):
        if location_name not in city_list:
            raise HTTPNotFound(detail="Location not found!")
        with requests.get(
                'https://airbrake.github.io/weatherapi/weather/' + location_name) as f:
            return f.json()


# Configure a new minimal application with our root controller.
config = MinimalApplicationConfigurator()
config.register(SQLAlchemyConfigurationComponent)
DBSession = scoped_session(sessionmaker(autoflush=True, autocommit=False))


def init_model(engine):
    DBSession.configure(bind=engine)
    DeclarativeBase.metadata.create_all(engine)


config.update_blueprint({
    'root_controller': RootController(),
    'renderers': ['json', 'kajiki'],  # Enable json in expose
    'default_renderer': 'kajiki',
    'use_sqlalchemy': True,
    'sqlalchemy.url': 'sqlite:///:memory:',
    'model': Bunch(
        DBSession=DBSession,
        init_model=init_model
    ),
    'PYBRAKE': {
        "project_id": 99999,
        "project_key": "xxxxxxxxxxxxxxxxxxxxxxxxxxxx",
    },
})


if __name__ == "__main__":
    # Serve the newly configured web application.
    print("Serving on port 8000...")
    config = init_app(config)
    httpd = make_server('', 8000, config.make_wsgi_app())
    httpd.serve_forever()
