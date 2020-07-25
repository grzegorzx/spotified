import os
import json
import requests
import base64
import datetime

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
SPOTIFY_CLIENTID = get_env_variable("SPOTIFY_CLIENTID")
SPOTIFY_CLIENTSECRET = get_env_variable("SPOTIFY_CLIENTSECRET")

# Spotify auth
CLIENT_CREDS = f"{SPOTIFY_CLIENTID}:{SPOTIFY_CLIENTSECRET}"
CLIENT_CREDS_B64 = base64.b64encode(CLIENT_CREDS.encode())

TOKEN_URL = "https://accounts.spotify.com/api/token"
METHOD = "POST"
TOKEN_DATA = {
        "grant_type": "client_credentials"
}
TOKEN_HEADERS = {
        "Authorization": f"Basic {CLIENT_CREDS_B64.decode()}"
}
SCOPES = "user-read-private user-read-email user-read-playback-state user-read-currently-playing user-library-read user-top-read user-read-recently-played"

# Spotify token respon se
r = requests.post(url=TOKEN_URL, data=TOKEN_DATA, headers=TOKEN_HEADERS)
token_response_data = r.json()
valid_request = r.status_code in range(200, 299)

if valid_request:
    now = datetime.datetime.now()
    access_token = token_response_data['access_token']
    expires_in = token_response_data['expires_in']
    expires = now + datetime.timedelta(seconds=expires_in)
    did_expire = expires < now

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

@app.route("/spoti")
def spoti():
    return r.json()

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
    app.run(debug=True)