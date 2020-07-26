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
        message = f"Expected environment variable '{name}' not set."
        raise Exception(message)

# get env vars OR ELSE
POSTGRES_URL = get_env_variable("POSTGRES_URL")
POSTGRES_USER = get_env_variable("POSTGRES_USER")
POSTGRES_PW = get_env_variable("POSTGRES_PW")
POSTGRES_DB = get_env_variable("POSTGRES_DB")
SECRET_KEY = get_env_variable("SECRET_KEY")
SPOTIFY_CLIENTID = get_env_variable("SPOTIFY_CLIENTID")
SPOTIFY_CLIENTSECRET = get_env_variable("SPOTIFY_CLIENTSECRET")

# Spotify clientauth
CLIENT_CREDS = f"{SPOTIFY_CLIENTID}:{SPOTIFY_CLIENTSECRET}"
CLIENT_CREDS_B64 = base64.b64encode(CLIENT_CREDS.encode())
SCOPES = "user-read-private user-read-email user-read-playback-state user-read-currently-playing user-library-read user-top-read user-read-recently-played"

class SpotifyAPI(object):
    access_token = None
    access_token_expires = datetime.datetime.now()
    access_token_did_expire = True
    client_id = None
    client_secret = None
    token_url = "https://accounts.spotify.com/api/token"
    
    def __init__(self, client_id, client_secret, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.client_id = client_id
        self.client_secret = client_secret
        
    def get_client_credentials(self):
        """Returns a base64 encoded string"""
        SPOTIFY_CLIENTID = self.client_id
        SPOTIFY_CLIENTSECRET = self.client_secret
        if SPOTIFY_CLIENTID == None or SPOTIFY_CLIENTSECRET == None:
            raise Exception("You must raise SPOTIFY_CLIENTID and SPOTIFY_CLIENTSECRET.")

        CLIENT_CREDS = f"{SPOTIFY_CLIENTID}:{SPOTIFY_CLIENTSECRET}"
        CLIENT_CREDS_B64 = base64.b64encode(CLIENT_CREDS.encode())
        return CLIENT_CREDS_B64.decode()
        
    def get_token_data(self):
        return {
            "grant_type": "client_credentials"
        }
    
    def get_token_headers(self):
        CLIENT_CREDS_B64 = self.get_client_credentials()
        return {
            "Authorization": f"Basic {CLIENT_CREDS_B64}"
        }

    def perform_auth(self):
        token_url = self.token_url
        token_data=self.get_token_data()
        token_headers = self.get_token_headers()
        r = requests.post(token_url, data=token_data, headers=token_headers)
        if r.status_code not in range(200, 299):
            return False
        data = r.json()
        now = datetime.datetime.now()
        access_token = data['access_token']
        expires_in = data['expires_in']
        expires = now + datetime.timedelta(seconds=expires_in)
        self.access_token = access_token
        self.access_token_expires = expires
        self.access_token_did_expire = expires < now
        return True

# Spotify client auth
request_type = "GET"
endpoint = "https://accounts.spotify.com/authorize"
client_id = SPOTIFY_CLIENTID
response_type = "code"
redirect_uri = "http://127.0.0.1:5000/"
example_redirect_uri = "https%3A%2F%2Fexample.com%2Fcallback"
scope = "user-library-read"
auth_url = f"{endpoint}?client_id={client_id}&response_type={response_type}&redirect_uri={example_redirect_uri}&scope={scope}"


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

@app.route("/clientAuth")
def spoti():
    client = SpotifyAPI(SPOTIFY_CLIENTID, SPOTIFY_CLIENTSECRET)
    client.perform_auth()
    return client.access_token

@app.route("/userAuth")
def userAuth():
    return auth_url


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