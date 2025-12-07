from django.conf import settings
from datetime import timedelta
from django.utils import timezone
import requests
from .models import SpotifyToken

TOKEN_URL = "https://accounts.spotify.com/api/token"
API_BASE = "https://api.spotify.com/v1"


def refresh_spotify_token_for_user(user):
    try:
        st = SpotifyToken.objects.get(user=user)
    except SpotifyToken.DoesNotExist:
        raise RuntimeError("No Spotify token for user")
    if not st.refresh_token:
        raise RuntimeError("No refresh token available")
    data = {
        "grant_type": "refresh_token",
        "refresh_token": st.refresh_token,
        "client_id": settings.SPOTIFY_CLIENT_ID,
        "client_secret": settings.SPOTIFY_CLIENT_SECRET,
    }
    r = requests.post(TOKEN_URL, data=data)
    r.raise_for_status()
    token_data = r.json()
    st.access_token = token_data.get("access_token")
    expires_in = token_data.get("expires_in")
    st.expires_at = (
        timezone.now() + timedelta(seconds=expires_in) if expires_in else None
    )
    # Spotify may or may not return a new refresh_token
    if token_data.get("refresh_token"):
        st.refresh_token = token_data.get("refresh_token")
    st.save()
    return st


def get_user_playlists(user):
    st = SpotifyToken.objects.get(user=user)
    if st.is_expired():
        st = refresh_spotify_token_for_user(user)
    headers = {"Authorization": f"Bearer {st.access_token}"}
    url = f"{API_BASE}/me/playlists"
    r = requests.get(url, headers=headers)
    r.raise_for_status()
    return r.json()


def get_spotify_user_profile(user):
    """Get the current user's Spotify profile information."""
    st = SpotifyToken.objects.get(user=user)
    if st.is_expired():
        st = refresh_spotify_token_for_user(user)
    headers = {"Authorization": f"Bearer {st.access_token}"}
    url = f"{API_BASE}/me"
    r = requests.get(url, headers=headers)
    r.raise_for_status()
    return r.json()


def get_playlist_tracks(user, playlist_id):
    st = SpotifyToken.objects.get(user=user)
    if st.is_expired():
        st = refresh_spotify_token_for_user(user)
    headers = {"Authorization": f"Bearer {st.access_token}"}

    tracks = []
    url = f"{API_BASE}/playlists/{playlist_id}/tracks"

    while url:
        r = requests.get(url, headers=headers)
        r.raise_for_status()
        data = r.json()
        tracks.extend(data["items"])  # each item contains a track
        url = data["next"]  # Spotify paginates, so 'next' gives next page or None

    return tracks


def get_track_info(user, track_id):
    st = SpotifyToken.objects.get(user=user)
    if st.is_expired():
        st = refresh_spotify_token_for_user(user)
    headers = {"Authorization": f"Bearer {st.access_token}"}
    url = f"{API_BASE}/tracks/{track_id}"
    r = requests.get(url, headers=headers)
    r.raise_for_status()
    return r.json()


def get_playlist(user, playlist_id):
    """Fetch a single playlist object by id for the current user.

    Useful when we already know the id and don't want to rely on the first-page
    results of /me/playlists.
    """
    st = SpotifyToken.objects.get(user=user)
    if st.is_expired():
        st = refresh_spotify_token_for_user(user)
    headers = {"Authorization": f"Bearer {st.access_token}"}
    url = f"{API_BASE}/playlists/{playlist_id}"
    r = requests.get(url, headers=headers)
    r.raise_for_status()
    return r.json()


def remove_tracks_from_playlist(user, playlist_id, track_uris):
    """Remove tracks from a Spotify playlist.
    
    Args:
        user: The Django user object
        playlist_id: Spotify playlist ID
        track_uris: List of Spotify track URIs to remove
    
    Returns:
        Response from Spotify API
    """
    st = SpotifyToken.objects.get(user=user)
    if st.is_expired():
        st = refresh_spotify_token_for_user(user)
    
    headers = {
        "Authorization": f"Bearer {st.access_token}",
        "Content-Type": "application/json"
    }
    
    url = f"{API_BASE}/playlists/{playlist_id}/tracks"
    
    # Spotify expects tracks in this format
    tracks_payload = [{"uri": uri} for uri in track_uris]
    payload = {"tracks": tracks_payload}
    
    r = requests.delete(url, headers=headers, json=payload)
    r.raise_for_status()
    return r.json()


# views.py
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import json
from django.contrib.auth.decorators import login_required


@login_required
@csrf_exempt
def play_track(request):
    if request.method != "POST":
        return JsonResponse(
            {"status": "error", "message": "Invalid method"}, status=405
        )

    data = json.loads(request.body)
    track_uri = data.get("uri")

    try:
        st = SpotifyToken.objects.get(user=request.user)
    except SpotifyToken.DoesNotExist:
        return JsonResponse(
            {"status": "error", "message": "No Spotify token for user"}, status=400
        )

    # Refresh token if expired
    if st.is_expired():
        st = refresh_spotify_token_for_user(request.user)

    access_token = st.access_token

    # Play the track
    url = "https://api.spotify.com/v1/me/player/play"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    payload = {"uris": [track_uri]}

    r = requests.put(url, headers=headers, json=payload)

    if r.status_code in [204, 202]:
        return JsonResponse({"status": "success"})
    return JsonResponse({"status": "error", "message": r.text}, status=400)
