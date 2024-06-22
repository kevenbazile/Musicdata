from flask import Flask, render_template, request, jsonify
import requests
import base64
import json
import plotly
import plotly.express as px
import pandas as pd
from models import db, Artist, Track

app = Flask(__name__)

# Spotify API credentials
client_id = '7a86df422bb14e88b5b425cb187fea8e'
client_secret = '74f5143c2671441aa19676af4cded978'

# Configuration for SQLAlchemy
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///musicdata.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

# List of Brooklyn artist names
brooklyn_artist_names = [
    'Ice Spice',
    'Sleepy Hallow',
    'Pop Smoke',
    'Joey Bada$$',
    'Fivio Foreign',
    'Sheff G',
    'Smoove\'L',
    'Desiigner',
    'Bobby Shmurda',
    'Young M.A'
]

def get_spotify_token():
    token_url = "https://accounts.spotify.com/api/token"
    client_creds = f"{client_id}:{client_secret}"
    client_creds_b64 = base64.b64encode(client_creds.encode()).decode()

    token_data = {
        "grant_type": "client_credentials"
    }

    token_headers = {
        "Authorization": f"Basic {client_creds_b64}",
        "Content-Type": "application/x-www-form-urlencoded"
    }

    r = requests.post(token_url, data=token_data, headers=token_headers)
    token_response_data = r.json()

    if 'access_token' not in token_response_data:
        raise Exception('Failed to retrieve access token')

    return token_response_data['access_token']

def search_artist_id(artist_name, headers):
    search_url = f"https://api.spotify.com/v1/search?q={artist_name}&type=artist&limit=1"
    response = requests.get(search_url, headers=headers)
    search_results = response.json()
    if response.status_code != 200 or not search_results['artists']['items']:
        print(f"Failed to find artist {artist_name}")
        return None

    return search_results['artists']['items'][0]['id']

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/get_data', methods=['POST'])
def get_data():
    try:
        access_token = get_spotify_token()
        headers = {
            "Authorization": f"Bearer {access_token}"
        }

        artists_data = []
        top_tracks_data = []

        for artist_name in brooklyn_artist_names:
            artist_id = search_artist_id(artist_name, headers)
            if not artist_id:
                continue  # Skip if the artist ID couldn't be found

            artist_url = f'https://api.spotify.com/v1/artists/{artist_id}'
            response = requests.get(artist_url, headers=headers)
            artist_data = response.json()

            if response.status_code != 200:
                print(f"Failed to fetch artist data for {artist_id}: {artist_data}")
                continue  # Skip if the artist data couldn't be fetched

            # Log the artist data for debugging
            print('Artist data:', artist_data)

            artists_data.append(artist_data)

            # Check if the artist already exists
            artist = Artist.query.get(artist_data['id'])
            if artist is None:
                artist = Artist(
                    id=artist_data['id'],
                    name=artist_data['name'],
                    followers=artist_data['followers']['total'],
                    genres=','.join(artist_data['genres']),
                    popularity=artist_data['popularity']
                )
                db.session.add(artist)
            else:
                # Update existing artist
                artist.name = artist_data['name']
                artist.followers = artist_data['followers']['total']
                artist.genres = ','.join(artist_data['genres'])
                artist.popularity = artist_data['popularity']
            db.session.commit()

            top_tracks_url = f'https://api.spotify.com/v1/artists/{artist_id}/top-tracks?market=US'
            response = requests.get(top_tracks_url, headers=headers)
            tracks_data = response.json().get('tracks', [])

            if response.status_code != 200:
                print(f"Failed to fetch top tracks for {artist_id}: {tracks_data}")
                continue  # Skip if the tracks data couldn't be fetched

            # Log the tracks data for debugging
            print('Tracks data:', tracks_data)

            # Fetch detailed track information to check release date
            for track in tracks_data:
                track_id = track['id']
                track_url = f'https://api.spotify.com/v1/tracks/{track_id}'
                track_response = requests.get(track_url, headers=headers)
                track_detail = track_response.json()

                # Check if the track was released in 2024
                if track_detail['album']['release_date'].startswith('2024'):
                    top_tracks_data.append({
                        'artist_name': artist_data['name'],
                        'track_name': track['name'],
                        'popularity': track['popularity'],
                        'release_date': track_detail['album']['release_date']
                    })

                    track_record = Track.query.get(track['id'])
                    if track_record is None:
                        track_record = Track(
                            id=track['id'],
                            name=track['name'],
                            popularity=track['popularity'],
                            artist_id=artist.id,
                            streams=track.get('playcount', 0),  # Assuming Spotify API provides playcount
                            downloads=0  # Placeholder, need to find actual data source
                        )
                        db.session.add(track_record)
                    else:
                        # Update existing track
                        track_record.name = track['name']
                        track_record.popularity = track['popularity']
                        track_record.streams = track.get('playcount', 0)
                db.session.commit()

        return render_template('data.html', artists=artists_data, top_tracks=top_tracks_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/visualization')
def visualization():
    try:
        # Retrieve data from database
        artists = Artist.query.all()

        # Create a DataFrame
        data = {
            'name': [artist.name for artist in artists],
            'followers': [artist.followers for artist in artists],
            'popularity': [artist.popularity for artist in artists]
        }
        df = pd.DataFrame(data)

        # Create a bar chart for artist popularity
        fig = px.bar(df, x='name', y='popularity', title='Popularity of Brooklyn Artists', labels={'popularity': 'Popularity (0-100)'})
        graphJSON = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)

        return render_template('visualization.html', graphJSON=graphJSON)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
