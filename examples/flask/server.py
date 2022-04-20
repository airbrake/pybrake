from argparse import ArgumentParser
from random import randrange
from time import sleep

from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from pybrake.middleware.flask import init_app

parser = ArgumentParser()
parser.add_argument(
    "-project_id",
    dest="project_id",
    help="airbrake project ID"
)
parser.add_argument(
    "-project_key",
    dest="project_key",
    help="airbrake project key"
)
args = parser.parse_args()

app = Flask(__name__)

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:////tmp/test.db"
db = SQLAlchemy(app)

app.config["PYBRAKE"] = dict(
    project_id=args.project_id, project_key=args.project_key,
    environment="test"
)

app = init_app(app)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)

    def __repr__(self):
        return "<User %r>" % self.username


db.create_all()


@app.route("/ping", methods=["GET"])
def ping():
    return "Pong"


@app.route("/hello/<name>", methods=["GET"])
def hello(name):
    sleep(randrange(0, 3))
    print(User.query.all())
    return render_template("hello.html", name=name)


app.run(debug=True)
