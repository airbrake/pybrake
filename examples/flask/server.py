import json
from datetime import datetime
from random import randrange
from time import sleep

from flask import Flask, render_template, jsonify
from flask_sqlalchemy import SQLAlchemy
from pybrake.middleware.flask import init_app

app = Flask(__name__)

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:////tmp/test.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

app.config["PYBRAKE"] = dict(
    project_id="XXXXXXXXXXXX",
    project_key="XXXXXXXXXXXX",
    environment="test",
    error_notifications=True,  # False to disable error notification
    performance_stats=True,  # False to disable APM
    query_stats=True,  # False to disable query monitoring
    queue_stats=True  # False to disable queue monitoring
)

app = init_app(app)

city_list = ["austin", "pune", "santabarbara"]


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


@app.route('/')
def index():
    return "Hello, Welcome to the Weather App!"


@app.route('/date')
def getdate():
    return jsonify({
        "date": "Current date and time is: %s" % datetime.now()
    })


@app.route('/locations')
def get_location_details():
    return jsonify({
        'cities': city_list
    })


# API for weather details for a location
@app.route('/weather/<location_name>')
def get_weather_details(location_name):
    file_name = location_name + ".json"
    if location_name not in city_list:
        return app.response_class(
            status=400,
            response=json.dumps({
                'error': 'Not found: Location not found!'
            }),
            mimetype='application/json'
        )
    try:
        with open('static/' + file_name) as f:
            data = json.load(f)
            return app.response_class(
                status=200,
                response=json.dumps(data),
                mimetype='application/json'
            )
    except Exception as e:
        return app.response_class(
            status=500,
            response=json.dumps({
                'error': str(e)
            }),
            mimetype='application/json'
        )


if __name__ == '__main__':
    app.debug = True
    app.run()
