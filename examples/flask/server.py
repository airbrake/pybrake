from flask import Flask, request
from time import sleep
from random import randrange
from argparse import ArgumentParser
import pybrake
from pybrake.flask import init_app

parser = ArgumentParser()
parser.add_argument("-project_id", dest="project_id", help="airbrake project ID")
parser.add_argument("-project_key", dest="project_key", help="airbrake project key")
parser.add_argument("-host", dest="host", help="airbrake host")
args = parser.parse_args()

app = Flask(__name__)
app.config["PYBRAKE"] = dict(
    project_id=args.project_id,
    project_key=args.project_key,
    host=args.host,
    environment="test",
)

app = init_app(app)


@app.route("/ping", methods=["GET"])
def ping():
    return "Pong"


@app.route("/hello/<name>", methods=["GET"])
def hello(name):
    sleep(randrange(0, 3))

    return "Hello {}".format(name)


app.run(debug=True)
