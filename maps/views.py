from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseBadRequest
from accounts.spotify import get_user_playlists, get_playlist_tracks, get_top_charts_for_country, get_available_chart_countries
from typing import Dict, List, Set


@login_required
def map_view(request):
    context = {
        'mapbox_access_token': 'pk.eyJ1Ijoic2FtdWVsZ2FseXNoIiwiYSI6ImNtZnp1aXlhbzA2amIybG9yaGp4dGVjODIifQ.jrTDRV67UtvzllABcKqVOA'
    }
    return render(request, 'maps/map.html', context)


@login_required
def api_playlists(request):
    """Return user's Spotify playlists (id + name) as JSON for the map UI."""
    try:
        data = get_user_playlists(request.user)
    except Exception as e:
        return JsonResponse({"error": "Failed to fetch playlists"}, status=400)

    items = data.get('items', [])
    playlists = [
        {"id": p.get("id"), "name": p.get("name")}
        for p in items if p.get("id") and p.get("name")
    ]
    return JsonResponse({"playlists": playlists})


SPOTIFY_MARKETS: Set[str] = set([
    # Spotify supported market codes as of 2024/2025 (ISO 3166-1 alpha-2)
    'AD','AE','AF','AG','AL','AM','AO','AR','AT','AU','AZ','BA','BB','BD','BE','BF','BG','BH','BI','BJ','BN','BO','BR','BS','BT','BW','BY','BZ',
    'CA','CD','CG','CH','CI','CL','CM','CO','CR','CV','CW','CY','CZ',
    'DE','DJ','DK','DM','DO','DZ',
    'EC','EE','EG','ES','ET',
    'FI','FJ','FM','FR',
    'GA','GB','GD','GE','GH','GM','GN','GQ','GR','GT','GW','GY',
    'HK','HN','HR','HT','HU',
    'ID','IE','IL','IN','IQ','IS','IT',
    'JM','JO','JP',
    'KE','KG','KH','KI','KM','KN','KR','KW','KZ',
    'LA','LB','LC','LI','LK','LR','LS','LT','LU','LV','LY',
    'MA','MC','MD','ME','MG','MH','MK','ML','MM','MN','MO','MR','MT','MU','MV','MW','MX','MY','MZ',
    'NA','NE','NG','NI','NL','NO','NP','NR','NZ',
    'OM',
    'PA','PE','PG','PH','PK','PL','PS','PT','PW','PY',
    'QA',
    'RO','RS','RU','RW',
    'SA','SB','SC','SE','SG','SI','SK','SL','SM','SN','SO','SR','ST','SV','SZ',
    'TD','TG','TH','TJ','TL','TN','TO','TR','TT','TV','TW','TZ',
    'UA','UG','US','UY','UZ',
    'VC','VE','VN','VU',
    'WS',
    'XK',
    'ZA','ZM','ZW'
])


@login_required
def api_playlist_geo(request):
    """
    Compute per-country presence for a given playlist based on track available_markets
    and aggregate top artists per country (from the user's playlist content).
    Returns JSON with ISO2 codes and top artists mapping.
    """
    playlist_id = request.GET.get('playlist_id')
    if not playlist_id:
        return HttpResponseBadRequest('playlist_id is required')

    try:
        items = get_playlist_tracks(request.user, playlist_id)
    except Exception as e:
        return JsonResponse({"error": "Failed to fetch playlist tracks"}, status=400)

    presence: Set[str] = set()
    top_artists_by_country: Dict[str, Dict[str, int]] = {}

    for item in items:
        track = (item or {}).get('track') or {}
        if not track:
            continue
        markets: List[str] = track.get('available_markets') or []
        artists = track.get('artists') or []
        artist_names = [a.get('name') for a in artists if a.get('name')]
        if not artist_names:
            continue
        for m in markets:
            if not m:
                continue
            presence.add(m)
            bucket = top_artists_by_country.setdefault(m, {})
            for name in artist_names:
                bucket[name] = bucket.get(name, 0) + 1

    presence_iso2 = sorted(presence)
    absence_iso2 = sorted(list(SPOTIFY_MARKETS - presence))

    # Collapse top artists to top 5 per country
    top_artists = {
        iso2: sorted(artists.items(), key=lambda kv: kv[1], reverse=True)[:5]
        for iso2, artists in top_artists_by_country.items()
    }

    # Convert tuples to objects for JSON
    top_artists = {
        iso2: [{"name": name, "count": count} for name, count in pairs]
        for iso2, pairs in top_artists.items()
    }

    return JsonResponse({
        "presence_iso2": presence_iso2,
        "absence_iso2": absence_iso2,
        "top_artists": top_artists,
    })


@login_required
def api_country_charts(request):
    """
    Fetch top artists from Spotify's Top 50 charts for a specific country.
    Returns the top artists currently charting in that country.
    """
    country_code = request.GET.get('country')
    if not country_code:
        return HttpResponseBadRequest('country parameter is required')
    
    try:
        chart_data = get_top_charts_for_country(request.user, country_code)
        return JsonResponse(chart_data)
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"Error fetching charts for {country_code}: {e}")
        print(error_trace)
        return JsonResponse({
            "error": str(e),
            "traceback": error_trace,
            "country_code": country_code.upper(),
            "has_chart": False,
            "artists": []
        }, status=400)


@login_required
def api_chart_countries(request):
    """Return list of countries that have Spotify Top 50 charts available."""
    countries = get_available_chart_countries()
    return JsonResponse({"countries": countries})
