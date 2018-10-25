from flask import Flask, request
from time import sleep
from random import randrange
from argparse import ArgumentParser
from airbrake_middleware import setup_airbrake_middleware
import pybrake

parser = ArgumentParser()
parser.add_argument("-project_id", dest="project_id", help="airbrake project ID")
parser.add_argument("-project_key", dest="project_key", help="airbrake project key")
parser.add_argument("-host", dest="host", help="airbrake host")
args = parser.parse_args()

notifier = pybrake.Notifier(
	args.project_id, args.project_key, args.host, environment='test')

app = Flask(__name__)
setup_airbrake_middleware(app, notifier)

@app.route('/ping',methods=['GET'])
def ping():
    return 'Pong'

@app.route('/hello/<name>',methods=['GET'])
def hello(name):
  sleep(randrange(0, 3))

  return "Hello {}".format(name)

app.run(debug=True)
