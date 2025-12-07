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


# Spotify's official "Top 50" playlist IDs by country code (some may be outdated)
SPOTIFY_TOP50_PLAYLISTS = {
    'US': '37i9dQZEVXbLRQDuF5jeBp',
    'GB': '37i9dQZEVXbLnolsZ8PSNw',
    'CA': '37i9dQZEVXbKj23U1GF4IR',
    'AU': '37i9dQZEVXbJPcfkRz0wJ0',
    'DE': '37i9dQZEVXbJiZcmkrIHGU',
    'FR': '37i9dQZEVXbIPWwFssbupI',
    'ES': '37i9dQZEVXbNFJfN1Vw8d9',
    'IT': '37i9dQZEVXbIQnj7RRhdSX',
    'BR': '37i9dQZEVXbMXbN3EUUhlg',
    'MX': '37i9dQZEVXbO3qyFxbkOE1',
    'JP': '37i9dQZEVXbKXQ4mDTEBXq',
    'GLOBAL': '37i9dQZEVXbMDoHDwVN2tF',
}


def get_top_charts_for_country(user, country_code: str):
    """
    Fetch top artists from Spotify's Top 50 playlist for a given country.
    Uses Spotify's search API to find chart playlists.
    Returns a list of top artists with their track counts.
    """
    country_code = country_code.upper()
    
    st = SpotifyToken.objects.get(user=user)
    if st.is_expired():
        st = refresh_spotify_token_for_user(user)
    
    headers = {"Authorization": f"Bearer {st.access_token}"}
    
    country_names = {
        'US': 'USA', 'GB': 'UK', 'CA': 'Canada', 'AU': 'Australia',
        'DE': 'Germany', 'FR': 'France', 'ES': 'Spain', 'IT': 'Italy',
        'BR': 'Brazil', 'MX': 'Mexico', 'JP': 'Japan', 'KR': 'South Korea',
        'IN': 'India', 'AR': 'Argentina', 'NL': 'Netherlands', 'SE': 'Sweden',
        'NO': 'Norway', 'DK': 'Denmark', 'FI': 'Finland', 'PL': 'Poland',
        'PT': 'Portugal', 'IE': 'Ireland', 'NZ': 'New Zealand', 'ZA': 'South Africa',
        'PH': 'Philippines', 'ID': 'Indonesia', 'TH': 'Thailand', 'TR': 'Turkey',
        'UA': 'Ukraine', 'RO': 'Romania', 'HU': 'Hungary', 'CZ': 'Czechia',
        'GR': 'Greece', 'IL': 'Israel', 'EG': 'Egypt', 'SA': 'Saudi Arabia',
        'AE': 'UAE', 'CH': 'Switzerland', 'AT': 'Austria', 'BE': 'Belgium',
        'CL': 'Chile', 'CO': 'Colombia', 'PE': 'Peru', 'VE': 'Venezuela',
    }
    
    country_name = country_names.get(country_code, '')
    playlist_id = SPOTIFY_TOP50_PLAYLISTS.get(country_code)
    found_playlist_id = None
    
    # If we have a known playlist ID, try it first
    if playlist_id:
        url = f"{API_BASE}/playlists/{playlist_id}/tracks?limit=50"
        r = requests.get(url, headers=headers)
        if r.status_code == 200:
            data = r.json()
            items = data.get('items', [])
            if items:
                return _parse_playlist_artists(data, country_code, True)
    
    # Fallback: Search for the playlist
    if country_name:
        search_query = f"Top 50 {country_name}"
        search_url = f"{API_BASE}/search?q={requests.utils.quote(search_query)}&type=playlist&limit=10"
        r = requests.get(search_url, headers=headers)
        
        if r.status_code == 200:
            search_data = r.json()
            playlists = search_data.get('playlists', {}).get('items', [])
            
            for pl in playlists:
                if pl is None:
                    continue
                pl_name = (pl.get('name', '') or '').lower()
                track_count = pl.get('tracks', {}).get('total', 0) if pl.get('tracks') else 0
                
                if ('top' in pl_name or 'chart' in pl_name or 'hits' in pl_name) and track_count >= 20:
                    found_playlist_id = pl.get('id')
                    break
            
            if found_playlist_id:
                url = f"{API_BASE}/playlists/{found_playlist_id}/tracks?limit=50"
                r = requests.get(url, headers=headers)
                if r.status_code == 200:
                    data = r.json()
                    return _parse_playlist_artists(data, country_code, True)
    
    # Try additional search terms
    if country_name:
        for search_term in [f"{country_name} top hits", f"{country_name} charts 2024", f"top songs {country_name}"]:
            search_url = f"{API_BASE}/search?q={requests.utils.quote(search_term)}&type=playlist&limit=5"
            r = requests.get(search_url, headers=headers)
            
            if r.status_code == 200:
                search_data = r.json()
                playlists = search_data.get('playlists', {}).get('items', [])
                
                for pl in playlists:
                    if pl is None:
                        continue
                    track_count = pl.get('tracks', {}).get('total', 0) if pl.get('tracks') else 0
                    if track_count >= 20:
                        found_playlist_id = pl.get('id')
                        break
                
                if found_playlist_id:
                    url = f"{API_BASE}/playlists/{found_playlist_id}/tracks?limit=50"
                    r = requests.get(url, headers=headers)
                    if r.status_code == 200:
                        data = r.json()
                        return _parse_playlist_artists(data, country_code, True)
                    break
    
    # Final fallback: Global Top 50
    global_id = SPOTIFY_TOP50_PLAYLISTS.get('GLOBAL', '37i9dQZEVXbMDoHDwVN2tF')
    url = f"{API_BASE}/playlists/{global_id}/tracks?limit=50"
    r = requests.get(url, headers=headers)
    
    if r.status_code == 200:
        data = r.json()
        items = data.get('items', [])
        if items:
            return _parse_playlist_artists(data, country_code, False)
    
    return {
        'country_code': country_code,
        'has_chart': False,
        'artists': [],
        'error': 'Could not fetch charts'
    }


def _parse_playlist_artists(data, country_code, has_chart):
    """Parse playlist tracks and count artist appearances."""
    artist_counts = {}
    
    for item in data.get('items', []):
        track = item.get('track')
        if not track:
            continue
        
        for artist in track.get('artists', []):
            name = artist.get('name')
            if name:
                artist_counts[name] = artist_counts.get(name, 0) + 1
    
    top_artists = sorted(artist_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    
    return {
        'country_code': country_code,
        'has_chart': has_chart,
        'artists': [{'name': name, 'count': count} for name, count in top_artists]
    }


def get_available_chart_countries():
    """Return list of country codes that have Top 50 charts available."""
    return list(SPOTIFY_TOP50_PLAYLISTS.keys())


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
