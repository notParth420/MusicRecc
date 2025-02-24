from flask import Flask, render_template, request, session, redirect, url_for, jsonify
import requests, base64

app = Flask(__name__)
app.secret_key = "some_random_secret_key"

# ---------------------
# Last.fm API Details
# ---------------------
LASTFM_API_KEY = "2f7532344ba8617f42910ab364c0ae49"
LASTFM_API_URL = "http://ws.audioscrobbler.com/2.0/"
HEADERS = {"User-Agent": "MyMusicRecommender/1.0"}

# ---------------------
# Spotify API Credentials
# ---------------------
SPOTIFY_CLIENT_ID = "d6b3ce067dc44c48ae4f46dda01c5c38"
SPOTIFY_CLIENT_SECRET = "86c0296678b841ebb826bf99a3f022a2"
SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"
SPOTIFY_SEARCH_URL = "https://api.spotify.com/v1/search"

def get_spotify_token():
    """
    Obtain a Spotify access token using Client Credentials Flow.
    """
    auth_str = f"{SPOTIFY_CLIENT_ID}:{SPOTIFY_CLIENT_SECRET}"
    b64_auth_str = base64.b64encode(auth_str.encode()).decode()
    headers = {
        "Authorization": f"Basic {b64_auth_str}",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    data = {"grant_type": "client_credentials"}
    response = requests.post(SPOTIFY_TOKEN_URL, data=data, headers=headers)
    if response.status_code != 200:
        print("Error getting Spotify token:", response.text)
        return None
    return response.json().get("access_token")

def search_spotify_track(track_name, artist):
    """
    Search for a track on Spotify using the client token.
    Returns track data including album art and popularity.
    """
    token = get_spotify_token()
    if not token:
        return None
    headers = {"Authorization": f"Bearer {token}"}
    query = f"track:{track_name} artist:{artist}"
    params = {"q": query, "type": "track", "limit": 1}
    response = requests.get(SPOTIFY_SEARCH_URL, headers=headers, params=params)
    if response.status_code != 200:
        print("Error searching track on Spotify:", response.text)
        return None
    results = response.json()
    tracks = results.get("tracks", {}).get("items", [])
    return tracks[0] if tracks else None

@app.route("/", methods=["GET", "POST"])
def index():
    """Homepage where users enter their Last.fm username."""
    if request.method == "POST":
        username = request.form.get("username")
        if not username:
            return "Error: Please enter a Last.fm username!", 400
        session["username"] = username
        return redirect(url_for("recent"))
    return render_template("index.html")

@app.route("/recent")
def recent():
    """Fetch and display the user's recent tracks from Last.fm."""
    username = session.get("username")
    if not username:
        return redirect(url_for("index"))

    params = {
        "method": "user.getRecentTracks",
        "user": username,
        "api_key": LASTFM_API_KEY,
        "format": "json",
        "limit": 10
    }
    response = requests.get(LASTFM_API_URL, params=params, headers=HEADERS)
    if response.status_code != 200:
        return "Error fetching recent tracks!", 500
    data = response.json()

    recent_tracks = []
    for t in data.get("recenttracks", {}).get("track", []):
        track_name = t.get("name", "Unknown")
        artist_name = t.get("artist", {}).get("#text", "Unknown")
        album_art = t.get("image", [])[-1].get("#text") if t.get("image") else None

        recent_tracks.append({
            "track_name": track_name,
            "artist_name": artist_name,
            "album_art": album_art if album_art else "static/default_album.png"
        })
    
    return render_template("recent.html", username=username, recent_tracks=recent_tracks)

@app.route("/tracks")
def tracks():
    """
    Fetch and display the user's top tracks from Last.fm,
    then enrich each track with metadata from Spotify.
    """
    username = session.get("username")
    if not username:
        return redirect(url_for("index"))

    params = {
        "method": "user.getTopTracks",
        "user": username,
        "api_key": LASTFM_API_KEY,
        "format": "json",
        "limit": 5
    }
    response = requests.get(LASTFM_API_URL, params=params, headers=HEADERS)
    if response.status_code != 200:
        return "Error fetching top tracks!", 500
    data = response.json()

    user_top_tracks = []
    for t in data.get("toptracks", {}).get("track", []):
        track_name = t.get("name")
        artist_name = t.get("artist", {}).get("name")

        spotify_track = search_spotify_track(track_name, artist_name)
        album_art = None

        if spotify_track:
            album_images = spotify_track.get("album", {}).get("images", [])
            album_art = album_images[0]["url"] if album_images else None

        user_top_tracks.append({
            "track_name": track_name,
            "artist_name": artist_name,
            "album_art": album_art if album_art else "static/default_album.png"
        })

    return render_template("tracks.html", username=username, tracks=user_top_tracks)

@app.route("/recommend")
def recommend():
    """
    Generate recommendations based on the user's top tracks using Last.fm similar tracks.
    """
    username = session.get("username")
    if not username:
        return redirect(url_for("index"))

    params = {
        "method": "user.getTopTracks",
        "user": username,
        "api_key": LASTFM_API_KEY,
        "format": "json",
        "limit": 5
    }
    response = requests.get(LASTFM_API_URL, params=params, headers=HEADERS)
    if response.status_code != 200:
        return "Error fetching top tracks!", 500
    data = response.json()

    recommendations = []
    for t in data.get("toptracks", {}).get("track", []):
        track_name = t.get("name")
        artist_name = t.get("artist", {}).get("name")

        spotify_track = search_spotify_track(track_name, artist_name)
        album_art = None

        if spotify_track:
            album_images = spotify_track.get("album", {}).get("images", [])
            album_art = album_images[0]["url"] if album_images else None

        recommendations.append({
            "track_name": track_name,
            "artist_name": artist_name,
            "album_art": album_art if album_art else "static/default_album.png"
        })

    return render_template("recommend.html", username=username, recommendations=recommendations)

if __name__ == "__main__":
    app.run(debug=True)
