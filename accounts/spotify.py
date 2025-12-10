from django.conf import settings
from datetime import timedelta
from django.utils import timezone
import requests #type: ignore
from .models import SpotifyToken

TOKEN_URL = "https://accounts.spotify.com/api/token"
API_BASE = "https://api.spotify.com/v1"

# Spotify's official "Top 50" playlist IDs by country code
# These are Spotify's curated chart playlists
SPOTIFY_TOP50_PLAYLISTS = {
    'US': '37i9dQZEVXbLRQDuF5jeBp',  # Top 50 - USA
    'GB': '37i9dQZEVXbLnolsZ8PSNw',  # Top 50 - UK
    'CA': '37i9dQZEVXbKj23U1GF4IR',  # Top 50 - Canada
    'AU': '37i9dQZEVXbJPcfkRz0wJ0',  # Top 50 - Australia
    'DE': '37i9dQZEVXbJiZcmkrIHGU',  # Top 50 - Germany
    'FR': '37i9dQZEVXbIPWwFssbupI',  # Top 50 - France
    'ES': '37i9dQZEVXbNFJfN1Vw8d9',  # Top 50 - Spain
    'IT': '37i9dQZEVXbIQnj7RRhdSX',  # Top 50 - Italy
    'BR': '37i9dQZEVXbMXbN3EUUhlg',  # Top 50 - Brazil
    'MX': '37i9dQZEVXbO3qyFxbkOE1',  # Top 50 - Mexico
    'JP': '37i9dQZEVXbKXQ4mDTEBXq',  # Top 50 - Japan
    'KR': '37i9dQZEVXbNxXF4SkHj9F',  # Top 50 - South Korea
    'IN': '37i9dQZEVXbLZ52XmnySJg',  # Top 50 - India
    'AR': '37i9dQZEVXbMMy2roB9myp',  # Top 50 - Argentina
    'CL': '37i9dQZEVXbL0GavIqMTeb',  # Top 50 - Chile
    'CO': '37i9dQZEVXbOa2lmxNORXQ',  # Top 50 - Colombia
    'NL': '37i9dQZEVXbKCF6dqVpDkS',  # Top 50 - Netherlands
    'BE': '37i9dQZEVXbJNSeeHswcKB',  # Top 50 - Belgium
    'AT': '37i9dQZEVXbKNHh6NIXu36',  # Top 50 - Austria
    'CH': '37i9dQZEVXbJiyhoAPEfMK',  # Top 50 - Switzerland
    'SE': '37i9dQZEVXbLoATJ81JYXz',  # Top 50 - Sweden
    'NO': '37i9dQZEVXbJvfa0Yxg7E7',  # Top 50 - Norway
    'DK': '37i9dQZEVXbL3J0k32lWnN',  # Top 50 - Denmark
    'FI': '37i9dQZEVXbMxcczTSoGwZ',  # Top 50 - Finland
    'PL': '37i9dQZEVXbN6itCcaL3Tt',  # Top 50 - Poland
    'PT': '37i9dQZEVXbKyJS56d1pgi',  # Top 50 - Portugal
    'IE': '37i9dQZEVXbKM896FDX8L1',  # Top 50 - Ireland
    'NZ': '37i9dQZEVXbM8SIrkERIYl',  # Top 50 - New Zealand
    'ZA': '37i9dQZEVXbMH2jvi6jvjk',  # Top 50 - South Africa
    'PH': '37i9dQZEVXbNBz9cRCSFkY',  # Top 50 - Philippines
    'ID': '37i9dQZEVXbObFQZ3JLcXt',  # Top 50 - Indonesia
    'MY': '37i9dQZEVXbJlfUljuZExa',  # Top 50 - Malaysia
    'SG': '37i9dQZEVXbK4gjvS1FjPY',  # Top 50 - Singapore
    'TH': '37i9dQZEVXbMnz8KIWsvf9',  # Top 50 - Thailand
    'VN': '37i9dQZEVXbLdGSmz6xilI',  # Top 50 - Vietnam
    'TW': '37i9dQZEVXbMnZEatlMSiu',  # Top 50 - Taiwan
    'HK': '37i9dQZEVXbLwpL8TjsxOG',  # Top 50 - Hong Kong
    'TR': '37i9dQZEVXbIVYVBNw9D5K',  # Top 50 - Turkey
    'EG': '37i9dQZEVXbLn7RQmT5Xv2',  # Top 50 - Egypt
    'SA': '37i9dQZEVXbLrQBcXqUtaC',  # Top 50 - Saudi Arabia
    'AE': '37i9dQZEVXbM4UZuIrvHvA',  # Top 50 - UAE
    'IL': '37i9dQZEVXbJ6IpvNlYifZ',  # Top 50 - Israel
    'RO': '37i9dQZEVXbNZbJ6TZelCq',  # Top 50 - Romania
    'HU': '37i9dQZEVXbNHwMxAkvmF8',  # Top 50 - Hungary
    'CZ': '37i9dQZEVXbIP3c3fqVrJY',  # Top 50 - Czech Republic
    'GR': '37i9dQZEVXbJqdarpmTJDL',  # Top 50 - Greece
    'UA': '37i9dQZEVXbKkidEfWYRuD',  # Top 50 - Ukraine
    'PE': '37i9dQZEVXbJfdy5b0KP7W',  # Top 50 - Peru
    'EC': '37i9dQZEVXbJlM6nvL1nD1',  # Top 50 - Ecuador
    'VE': '37i9dQZEVXbNLrliB8ZovC',  # Top 50 - Venezuela
    'CR': '37i9dQZEVXbMZAjGMynsQX',  # Top 50 - Costa Rica
    'PA': '37i9dQZEVXbKypXHVwk1f0',  # Top 50 - Panama
    'DO': '37i9dQZEVXbKAbrMR8uuf7',  # Top 50 - Dominican Republic
    'GT': '37i9dQZEVXbLy5tBFyQvd4',  # Top 50 - Guatemala
    'HN': '37i9dQZEVXbJp9wcIM9Eo5',  # Top 50 - Honduras
    'SV': '37i9dQZEVXbLxoIml4MYkT',  # Top 50 - El Salvador
    'NI': '37i9dQZEVXbISk8kxnzfCq',  # Top 50 - Nicaragua
    'PY': '37i9dQZEVXbNOUPGj7tW6T',  # Top 50 - Paraguay
    'UY': '37i9dQZEVXbMJJi3wgRbAy',  # Top 50 - Uruguay
    'BO': '37i9dQZEVXbJqfMFK4d691',  # Top 50 - Bolivia
    'GLOBAL': '37i9dQZEVXbMDoHDwVN2tF',  # Top 50 - Global
}


def get_top_charts_for_country(user, country_code: str):
    """
    Fetch top artists from Spotify's Top 50 playlist for a given country.
    Uses Spotify's search API to find the official chart playlist.
    Returns a list of top artists with their track counts.
    """
    country_code = country_code.upper()
    
    st = SpotifyToken.objects.get(user=user)
    if st.is_expired():
        st = refresh_spotify_token_for_user(user)
    
    headers = {"Authorization": f"Bearer {st.access_token}"}
    
    # First, try to find the Top 50 playlist by searching
    # Spotify's official chart playlists are owned by 'spotify'
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
    
    print(f"[Charts] Looking for charts for {country_code} ({country_name})")
    
    # If we have a known playlist ID, try it first
    if playlist_id:
        url = f"{API_BASE}/playlists/{playlist_id}/tracks?limit=50"
        r = requests.get(url, headers=headers)
        print(f"[Charts] Hardcoded playlist {playlist_id}: status {r.status_code}")
        if r.status_code == 200:
            data = r.json()
            items = data.get('items', [])
            print(f"[Charts] Got {len(items)} tracks from hardcoded playlist")
            if items:
                return _parse_playlist_artists(data, country_code, True)
    
    # Fallback: Search for the playlist
    if country_name:
        search_query = f"Top 50 {country_name}"
        search_url = f"{API_BASE}/search?q={requests.utils.quote(search_query)}&type=playlist&limit=10"
        r = requests.get(search_url, headers=headers)
        print(f"[Charts] Search for '{search_query}': status {r.status_code}")
        
        if r.status_code == 200:
            search_data = r.json()
            playlists = search_data.get('playlists', {}).get('items', [])
            print(f"[Charts] Found {len(playlists)} playlists in search")
            
            # Look for any playlist with "top" in the name that has tracks
            for pl in playlists:
                if pl is None:
                    continue
                owner = pl.get('owner', {}) or {}
                pl_name = (pl.get('name', '') or '').lower()
                owner_id = owner.get('id', '')
                track_count = pl.get('tracks', {}).get('total', 0) if pl.get('tracks') else 0
                print(f"[Charts]   - '{pl.get('name')}' by {owner_id} ({track_count} tracks)")
                
                # Accept any playlist with "top" in name and at least 20 tracks
                if ('top' in pl_name or 'chart' in pl_name or 'hits' in pl_name) and track_count >= 20:
                    found_playlist_id = pl.get('id')
                    print(f"[Charts] Using playlist: {found_playlist_id}")
                    break
            
            if found_playlist_id:
                url = f"{API_BASE}/playlists/{found_playlist_id}/tracks?limit=50"
                r = requests.get(url, headers=headers)
                print(f"[Charts] Fetching playlist tracks: status {r.status_code}")
                if r.status_code == 200:
                    data = r.json()
                    return _parse_playlist_artists(data, country_code, True)
    
    # Try searching for "top hits" or "charts" for the country
    if country_name:
        for search_term in [f"{country_name} top hits", f"{country_name} charts 2024", f"top songs {country_name}"]:
            search_url = f"{API_BASE}/search?q={requests.utils.quote(search_term)}&type=playlist&limit=5"
            r = requests.get(search_url, headers=headers)
            print(f"[Charts] Search for '{search_term}': status {r.status_code}")
            
            if r.status_code == 200:
                search_data = r.json()
                playlists = search_data.get('playlists', {}).get('items', [])
                
                for pl in playlists:
                    if pl is None:
                        continue
                    track_count = pl.get('tracks', {}).get('total', 0) if pl.get('tracks') else 0
                    if track_count >= 20:
                        found_playlist_id = pl.get('id')
                        print(f"[Charts] Using fallback playlist: {found_playlist_id} - {pl.get('name')}")
                        break
                
                if found_playlist_id:
                    url = f"{API_BASE}/playlists/{found_playlist_id}/tracks?limit=50"
                    r = requests.get(url, headers=headers)
                    if r.status_code == 200:
                        data = r.json()
                        return _parse_playlist_artists(data, country_code, True)
                    break
    
    # Final fallback: Global Top 50
    print(f"[Charts] Trying Global Top 50 fallback")
    global_id = SPOTIFY_TOP50_PLAYLISTS.get('GLOBAL', '37i9dQZEVXbMDoHDwVN2tF')
    url = f"{API_BASE}/playlists/{global_id}/tracks?limit=50"
    r = requests.get(url, headers=headers)
    print(f"[Charts] Global playlist: status {r.status_code}")
    
    if r.status_code == 200:
        data = r.json()
        items = data.get('items', [])
        print(f"[Charts] Got {len(items)} tracks from Global playlist")
        if items:
            return _parse_playlist_artists(data, country_code, False)
    
    # Try "Today's Top Hits" as ultimate fallback
    print(f"[Charts] Trying Today's Top Hits fallback")
    todays_top_hits = '37i9dQZF1DXcBWIGoYBM5M'
    url = f"{API_BASE}/playlists/{todays_top_hits}/tracks?limit=50"
    r = requests.get(url, headers=headers)
    print(f"[Charts] Today's Top Hits: status {r.status_code}")
    
    if r.status_code == 200:
        data = r.json()
        items = data.get('items', [])
        print(f"[Charts] Got {len(items)} tracks from Today's Top Hits")
        if items:
            return _parse_playlist_artists(data, country_code, False)
    
    # If all else fails
    print(f"[Charts] All fallbacks failed for {country_code}")
    return {
        'country_code': country_code,
        'has_chart': False,
        'artists': [],
        'error': f"Could not fetch charts"
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
    
    # Sort by count and take top 10
    top_artists = sorted(artist_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    
    return {
        'country_code': country_code,
        'has_chart': has_chart,
        'artists': [{'name': name, 'count': count} for name, count in top_artists]
    }


def get_available_chart_countries():
    """Return list of country codes that have Top 50 charts available."""
    return list(SPOTIFY_TOP50_PLAYLISTS.keys())


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


def _format_retry_after(seconds):
    """Format retry_after seconds into a human-readable string."""
    try:
        seconds = int(seconds)
    except (ValueError, TypeError):
        return "unknown time"
    
    if seconds >= 3600:  # 1 hour or more
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        return f"{hours}h {minutes}m {secs}s"
    elif seconds >= 60:  # 1 minute or more
        minutes = seconds // 60
        secs = seconds % 60
        return f"{minutes}m {secs}s"
    else:  # less than 1 minute
        return f"{seconds}s"


def get_user_playlists(user):
    st = SpotifyToken.objects.get(user=user)
    if st.is_expired():
        st = refresh_spotify_token_for_user(user)
    headers = {"Authorization": f"Bearer {st.access_token}"}
    url = f"{API_BASE}/me/playlists"
    r = requests.get(url, headers=headers)
    
    if r.status_code == 429:
        retry_after = r.headers.get('Retry-After', 'unknown')
        wait_time = _format_retry_after(retry_after)
        raise requests.exceptions.HTTPError(
            f"Rate limited. Please wait {wait_time} before trying again.",
            response=r
        )
    
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
        
        if r.status_code == 429:
            retry_after = r.headers.get('Retry-After', 'unknown')
            wait_time = _format_retry_after(retry_after)
            raise requests.exceptions.HTTPError(
                f"Rate limited. Please wait {wait_time} before trying again.",
                response=r
            )
        
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
    
    if r.status_code == 429:
        retry_after = r.headers.get('Retry-After', 'unknown')
        wait_time = _format_retry_after(retry_after)
        raise requests.exceptions.HTTPError(
            f"Rate limited. Please wait {wait_time} before trying again.",
            response=r
        )
    
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
