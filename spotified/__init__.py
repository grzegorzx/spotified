import os
import json
import requests
import base64
import datetime
from urllib.parse import quote, urlencode

from flask import Flask, redirect, request, url_for
from flask_sqlalchemy import SQLAlchemy


def get_env_variable(name):
    try:
        return os.environ[name]
    except KeyError:
        message = f"Expected environment variable '{name}' not set."
        raise Exception(message)

# get env vars OR ELSE
POSTGRES_HOST = get_env_variable("POSTGRES_HOST")
POSTGRES_PORT = get_env_variable("POSTGRES_PORT")
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
endpoint = "https://accounts.spotify.com/authorize"
client_id = SPOTIFY_CLIENTID
response_type = "code"
redirect_uri = "http://127.0.0.1:5000/callback/"
example_redirect_uri = "https%3A%2F%2Fexample.com%2Fcallback"
scope = "user-library-read"
auth_url = f"{endpoint}?client_id={client_id}&response_type={response_type}&redirect_uri={quote(redirect_uri)}&scope={scope}"

# table
tracks_db = []

app = Flask(__name__)
app.secret_key = SECRET_KEY
#
DB_URL = f'postgresql+psycopg2://{POSTGRES_USER}:{POSTGRES_PW}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}'
# DB_URL='sqlite:///mockup_db.db'

app.config['SQLALCHEMY_DATABASE_URI'] = DB_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False # silence the deprecation warning
app.config['FLASK_APP']='spotified'
app.config['FLASK_ENV']='development'

db = SQLAlchemy(app)
# db.session.commit()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    spotify_id = db.Column(db.String(200), unique=False, nullable=True)
    spotify_token = db.Column(db.String(200), unique=False, nullable=True)

    def __repr__(self):
        return f"User('{self.id}, '{self.spotify_id}, {self.spotify_token}"

class Track(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), unique=False, nullable=True)
    popularity = db.Column(db.Integer, unique=False, nullable=True)
    album = db.Column(db.String(200), unique=False, nullable=True)
    artist = db.Column(db.String(200), unique=False, nullable=True)

    def __repr__(self):
        return f"Track('{self.id}, '{self.name}, {self.popularity}, {self.album}, {self.artist}"

@app.route("/")
def hello():
    return "Hello World2!"

@app.route("/clientAuth")
def spoti():
    client = SpotifyAPI(SPOTIFY_CLIENTID, SPOTIFY_CLIENTSECRET)
    client.perform_auth()
    return client.access_token

@app.route("/auth")
def auth():
    return redirect(auth_url)


AUTH = { 
  'spotify': None,
  'access_token': None
}

@app.route("/callback/")
def callback_code():
    AUTH['spotify'] = request.args.get('code')
    return redirect(url_for('api_token'))

@app.route("/api_token")
def api_token():
    auth_body = {
        "grant_type":"authorization_code",
        "code":AUTH['spotify'],
        "redirect_uri":redirect_uri,
    }    
    auth_headers = {
        "Authorization":f"Basic {CLIENT_CREDS_B64.decode()}"
    }
    r = requests.post("https://accounts.spotify.com/api/token", data=auth_body, headers=auth_headers)
    r = r.json()
    AUTH['access_token'] = r['access_token']
    return redirect(url_for('tracks'))

@app.route("/tracks")
def tracks():
    tracks_endpoint = "https://api.spotify.com/v1/me/tracks"
    tracks_parameters = {
        'limit':'50'
    }
    tracks_auth = {
      "Authorization":f"Bearer {AUTH['access_token']}"
    }
    tracks = requests.get(tracks_endpoint, headers=tracks_auth, params=tracks_parameters)

    tracks_data = tracks.json()

    for i in tracks_data['items']:
        temp_tracks = {
            'name': None,
            'popularity': None,
            'album': None,
            'artist': None
            }
        temp_tracks['name'] = i['track']['name']
        temp_tracks['popularity'] = i['track']['popularity']
        temp_tracks['album'] = i['track']['album']['name']
        temp_artist = []
        for x in i['track']['artists']:
            temp_artist.append(x['name'])
        temp_tracks['artist'] = str(temp_artist)
        tracks_db.append(temp_tracks)

        # # track = Track(**tracks_db)
        # db.session.add(track)
        # db.session.commit()

        for i in tracks_db:
            track = Track(**i)
            db.session.add(track)
        db.session.commit()
    return 'Success!'

@app.route('/query')
def query_tracks():
    result = Track.query.all()
    print(result)
    return str(result)

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

    print('Creating tables.')
    db.create_all()
    print('Shiny!')

if __name__ == "__main__":
    app.run(debug=True)