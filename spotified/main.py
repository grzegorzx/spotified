import os
import json
import requests

from flask import Flask
from flask_sqlalchemy import SQLAlchemy


def get_env_variable(name):
    try:
        return os.environ[name]
    except KeyError:
        message = "Expected environment variable '{}' not set.".format(name)
        raise Exception(message)

# get env vars OR ELSE
POSTGRES_URL = get_env_variable("POSTGRES_URL")
POSTGRES_USER = get_env_variable("POSTGRES_USER")
POSTGRES_PW = get_env_variable("POSTGRES_PW")
POSTGRES_DB = get_env_variable("POSTGRES_DB")
SECRET_KEY = get_env_variable("SECRET_KEY")

SPOTIFY_SCOPES = "user-read-private user-read-email user-read-playback-state user-read-currently-playing user-library-read user-top-read user-read-recently-played"


app = Flask(__name__)
app.secret_key = SECRET_KEY

DB_URL = 'postgresql+psycopg2://{user}:{pw}@{url}/{db}'.format(user=POSTGRES_USER,pw=POSTGRES_PW,url=POSTGRES_URL,db=POSTGRES_DB)

app.config['SQLALCHEMY_DATABASE_URI'] = DB_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False # silence the deprecation warning

db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    spotify_id = db.Column(db.String(200), unique=False, nullable=True)
    spotify_token = db.Column(db.String(200), unique=False, nullable=True)

@app.route("/")
def hello():
    return "Hello World!"

@app.cli.command('resetdb')
def resetdb_command():
    """Destroys and creates the database + tables."""

    from sqlalchemy_utils import database_exists, create_database, drop_database
    if database_exists(DB_URL):
        print('Deleting database.')
        drop_database(DB_URL)
    if not database_exists(DB_URL):
        print('Creating database.')
        create_database(DB_URL)

    #db.drop_all()
    print('Creating tables.')
    db.create_all()
    print('Shiny!')


if __name__ == "__main__":
    app.debug = True
    app.run()