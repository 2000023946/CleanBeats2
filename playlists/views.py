from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from accounts.spotify import get_user_playlists, get_playlist_tracks, get_track_info, get_playlist, remove_tracks_from_playlist
import requests
import requests
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import json
from .models import KeptSong
from django.views.decorators.http import require_POST
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from typing import Any, List


def _decode_unicode_escapes(value: Any) -> Any:
    """Decode strings that contain unicode escape sequences like \u002D.

    Uses json.loads on a quoted string to safely decode common escape sequences
    without over-decoding regular text. Non-strings are returned unchanged.
    """
    if isinstance(value, str) and "\\" in value:
        try:
            # Quote and escape for JSON string literal
            s = value.replace("\\", "\\\\").replace('"', '\\"')
            return json.loads(f'"{s}"')
        except Exception:
            return value
    return value


def _decode_list(lst: Any) -> Any:
    if isinstance(lst, list):
        return [_decode_unicode_escapes(x) for x in lst]
    return lst


@login_required
def playlist_dashboard(request):
    """Fetch the user's playlists from Spotify and render them."""
    try:
        data = get_user_playlists(request.user)
        playlists = data.get("items", [])
        
        # Only fetch fresh count for recently modified playlist (stored in session)
        modified_playlist_id = request.session.get('modified_playlist_id')
        if modified_playlist_id:
            for playlist in playlists:
                if playlist['id'] == modified_playlist_id:
                    try:
                        fresh_data = get_playlist(request.user, playlist['id'])
                        if fresh_data and 'tracks' in fresh_data:
                            playlist['tracks']['total'] = fresh_data['tracks']['total']
                    except Exception:
                        pass
                    break
            # Clear the session flag after refreshing
            del request.session['modified_playlist_id']
                
    except requests.RequestException as e:
        playlists = []
        error_message = f"Failed to fetch playlists: {e}"
        return render(
            request,
            "playlists/dashboard.html",
            {"error_message": error_message, "playlists": playlists},
        )
    return render(request, "playlists/dashboard.html", {"playlists": playlists})


@login_required
def render_edit(request, playlist_id=None):
    """Render the edit UI for a specific playlist.

    If playlist_id is provided we load that playlist; otherwise fall back to the user's
    first playlist (legacy behaviour).
    """
    data = get_user_playlists(request.user)
    playlists = data.get("items", [])

    # find requested playlist by id if given (fetch directly to avoid first-page issues)
    playlist = None
    if playlist_id:
        try:
            playlist = get_playlist(request.user, playlist_id)
        except requests.RequestException:
            # Fallback to scanning the first page, in case of transient error
            for p in playlists:
                if str(p.get("id")) == str(playlist_id):
                    playlist = p
                    break

    # default to first playlist
    if not playlist:
        if playlists:
            playlist = playlists[0]
        else:
            return render(request, "playlists/edit.html", {"songs": [], "playlist_name": "", "playlist_id": ""})

    # Check if user wants to reset progress
    show_all = request.GET.get('show_all', 'false').lower() == 'true'
    
    if show_all:
        # Reset mode: delete all kept songs from database (make them unprocessed)
        try:
            KeptSong.objects.filter(
                user=request.user, 
                playlist_id=playlist["id"], 
                kept=True
            ).delete()
        except Exception:
            pass
        # Redirect to same page without show_all parameter to show fresh start
        from django.urls import reverse
        return redirect(reverse('playlists.edit_by_id', kwargs={'playlist_id': playlist["id"]}))

    songs = get_playlist_tracks_with_previews(request.user, playlist["id"])

    # Always exclude removed songs (kept==False)
    try:
        removed_uris = set(
            KeptSong.objects.filter(user=request.user, playlist_id=playlist["id"], kept=False)
            .values_list("track_uri", flat=True)
        )
    except Exception:
        removed_uris = set()

    # Exclude kept songs by default so user progresses through playlist
    try:
        kept_uris = set(
            KeptSong.objects.filter(user=request.user, playlist_id=playlist["id"], kept=True)
            .values_list("track_uri", flat=True)
        )
        excluded_uris = removed_uris | kept_uris
    except Exception:
        excluded_uris = removed_uris

    filtered_songs = [s for s in songs if s.get("track_uri") not in excluded_uris]

    # Calculate progress
    # Total = all songs in playlist minus permanently removed songs
    total_count = len(songs) - len(removed_uris)
    # Processed = current position (how many songs have been processed in this session)
    # This is: total songs that should be shown minus songs still remaining to process
    processed_count = total_count - len(filtered_songs)
    
    # Check if playlist had any songs to begin with
    has_songs_in_playlist = len(songs) > 0

    # send playlist id and name to the template
    return render(
        request,
        "playlists/edit.html",
        {
            "songs": filtered_songs, 
            "playlist_name": playlist.get("name", ""), 
            "playlist_id": playlist["id"],
            "total_count": total_count,
            "processed_count": processed_count,
            "has_songs_in_playlist": has_songs_in_playlist,
        },
    )


@login_required
@csrf_exempt
@require_POST
def save_decision(request):
    """API endpoint to save a user's keep/remove decision for a track in a playlist.

    Expects JSON body with: playlist_id, track_uri, name, artists (list), image_url, preview_url, spotify_url, kept (bool)
    """
    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "invalid_json"}, status=400)

    user = request.user
    playlist_id = payload.get("playlist_id")
    track_uri = payload.get("track_uri")
    name = payload.get("name")
    artists = payload.get("artists")
    image_url = payload.get("image_url")
    preview_url = payload.get("preview_url")
    spotify_url = payload.get("spotify_url")
    kept = payload.get("kept")

    if not all([playlist_id, track_uri]) or kept is None:
        return JsonResponse({"error": "missing_fields"}, status=400)

    # Normalize any escaped unicode sequences that may have come from data-* attributes
    name = _decode_unicode_escapes(name or "")
    artists = _decode_list(artists or [])

    # Upsert the decision
    obj, created = KeptSong.objects.update_or_create(
        user=user, playlist_id=playlist_id, track_uri=track_uri,
        defaults={
            "name": name,
            "artists": artists,
            "image_url": image_url,
            "preview_url": preview_url,
            "spotify_url": spotify_url,
            "kept": bool(kept),
        },
    )

    return JsonResponse({"status": "saved", "created": created})


@login_required
def kept_view(request, playlist_id):
    """Render a page showing kept and removed songs for given playlist id."""
    # Query the KeptSong objects for this user+playlist
    qs = KeptSong.objects.filter(user=request.user, playlist_id=playlist_id).order_by('-created_at')
    kept = [
        {
            "name": _decode_unicode_escapes(s.name),
            "artists": _decode_list(s.artists or []),
            "image_url": s.image_url,
            "preview_url": s.preview_url,
            "spotify_url": s.spotify_url,
            "track_uri": s.track_uri,
        }
        for s in qs.filter(kept=True)
    ]

    removed = [
        {
            "name": _decode_unicode_escapes(s.name),
            "artists": _decode_list(s.artists or []),
            "image_url": s.image_url,
            "preview_url": s.preview_url,
            "spotify_url": s.spotify_url,
            "track_uri": s.track_uri,
        }
        for s in qs.filter(kept=False)
    ]

    return render(request, "playlists/kept.html", {"kept": kept, "removed": removed, "playlist_id": playlist_id})


@login_required
@require_POST
def apply_playlist_changes(request, playlist_id):
    """Remove all 'removed' songs from the actual Spotify playlist and clear them from database."""
    try:
        # Get all removed songs for this user and playlist
        removed_songs = KeptSong.objects.filter(
            user=request.user,
            playlist_id=playlist_id,
            kept=False
        )
        
        if not removed_songs.exists():
            return JsonResponse({
                'status': 'success',
                'message': 'No songs to remove.',
                'count': 0
            })
        
        # Extract track URIs
        track_uris = [song.track_uri for song in removed_songs]
        count = len(track_uris)
        
        # Remove tracks from Spotify playlist
        remove_tracks_from_playlist(request.user, playlist_id, track_uris)
        
        # Delete removed songs from database
        removed_songs.delete()
        
        # Mark this playlist as modified so dashboard refreshes its count
        request.session['modified_playlist_id'] = playlist_id
        
        return JsonResponse({
            'status': 'success',
            'message': f'Successfully removed {count} song{"s" if count != 1 else ""} from your Spotify playlist!',
            'count': count
        })
        
    except requests.RequestException as e:
        return JsonResponse({
            'status': 'error',
            'message': f'Failed to update Spotify playlist: {str(e)}'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'An error occurred: {str(e)}'
        }, status=500)


@login_required
@require_POST
def reconsider_decision(request):
    """Reconsider a previously saved decision: remove the KeptSong entry so the track
    returns to the unedited pool.

    Expects JSON body with: playlist_id, track_uri
    """
    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "invalid_json"}, status=400)

    playlist_id = payload.get("playlist_id")
    track_uri = payload.get("track_uri")

    if not playlist_id or not track_uri:
        return JsonResponse({"error": "missing_fields"}, status=400)

    # Flip an existing removed decision back to kept=True
    obj = KeptSong.objects.filter(user=request.user, playlist_id=playlist_id, track_uri=track_uri).first()
    if not obj:
        return JsonResponse({"error": "not_found"}, status=404)

    obj.kept = True
    obj.save(update_fields=["kept"])

    return JsonResponse({"status": "updated", "kept": True})


def get_playlist_tracks_with_previews(user, playlist_id):
    raw_tracks = get_playlist_tracks(user, playlist_id)
    tracks_with_preview = []

    for item in raw_tracks:
        track = item["track"]
        if not track:  # Skip if track is None (deleted/unavailable)
            continue
            
        tracks_with_preview.append(
            {
                "name": track.get("name"),
                "image_url": (
                    track["album"]["images"][0]["url"]
                    if track.get("album") and track["album"].get("images")
                    else None
                ),
                "preview_url": track.get("preview_url"),
                "spotify_url": track.get("external_urls", {}).get("spotify"),
                "artists": [artist["name"] for artist in track.get("artists", [])],
                "track_uri": track.get("uri"),
            }
        )

    return tracks_with_preview


[
    {
        "added_at": "2025-11-04T19:13:45Z",
        "added_by": {
            "external_urls": {
                "spotify": "https://open.spotify.com/user/31bruxgr2pyas6a72hpa7oeyjkwu"
            },
            "href": "https://api.spotify.com/v1/users/31bruxgr2pyas6a72hpa7oeyjkwu",
            "id": "31bruxgr2pyas6a72hpa7oeyjkwu",
            "type": "user",
            "uri": "spotify:user:31bruxgr2pyas6a72hpa7oeyjkwu",
        },
        "is_local": False,
        "primary_color": None,
        "track": {
            "preview_url": None,
            "available_markets": [
                "AR",
                "AU",
                "AT",
                "BE",
                "BO",
                "BR",
                "BG",
                "CA",
                "CL",
                "CO",
                "CR",
                "CY",
                "CZ",
                "DK",
                "DO",
                "DE",
                "EC",
                "EE",
                "SV",
                "FI",
                "FR",
                "GR",
                "GT",
                "HN",
                "HK",
                "HU",
                "IS",
                "IE",
                "IT",
                "LV",
                "LT",
                "LU",
                "MY",
                "MT",
                "MX",
                "NL",
                "NZ",
                "NI",
                "NO",
                "PA",
                "PY",
                "PE",
                "PH",
                "PL",
                "PT",
                "SG",
                "SK",
                "ES",
                "SE",
                "CH",
                "TW",
                "TR",
                "UY",
                "US",
                "GB",
                "AD",
                "LI",
                "MC",
                "ID",
                "JP",
                "TH",
                "VN",
                "RO",
                "IL",
                "ZA",
                "SA",
                "AE",
                "BH",
                "QA",
                "OM",
                "KW",
                "EG",
                "MA",
                "DZ",
                "TN",
                "LB",
                "JO",
                "PS",
                "IN",
                "BY",
                "KZ",
                "MD",
                "UA",
                "AL",
                "BA",
                "HR",
                "ME",
                "MK",
                "RS",
                "SI",
                "KR",
                "BD",
                "PK",
                "LK",
                "GH",
                "KE",
                "NG",
                "TZ",
                "UG",
                "AG",
                "AM",
                "BS",
                "BB",
                "BZ",
                "BT",
                "BW",
                "BF",
                "CV",
                "CW",
                "DM",
                "FJ",
                "GM",
                "GE",
                "GD",
                "GW",
                "GY",
                "HT",
                "JM",
                "KI",
                "LS",
                "LR",
                "MW",
                "MV",
                "ML",
                "MH",
                "FM",
                "NA",
                "NR",
                "NE",
                "PW",
                "PG",
                "PR",
                "WS",
                "SM",
                "ST",
                "SN",
                "SC",
                "SL",
                "SB",
                "KN",
                "LC",
                "VC",
                "SR",
                "TL",
                "TO",
                "TT",
                "TV",
                "VU",
                "AZ",
                "BN",
                "BI",
                "KH",
                "CM",
                "TD",
                "KM",
                "GQ",
                "SZ",
                "GA",
                "GN",
                "KG",
                "LA",
                "MO",
                "MR",
                "MN",
                "NP",
                "RW",
                "TG",
                "UZ",
                "ZW",
                "BJ",
                "MG",
                "MU",
                "MZ",
                "AO",
                "CI",
                "DJ",
                "ZM",
                "CD",
                "CG",
                "IQ",
                "LY",
                "TJ",
                "VE",
                "ET",
                "XK",
            ],
            "explicit": False,
            "type": "track",
            "episode": False,
            "track": True,
            "album": {
                "available_markets": [
                    "AR",
                    "AU",
                    "AT",
                    "BE",
                    "BO",
                    "BR",
                    "BG",
                    "CA",
                    "CL",
                    "CO",
                    "CR",
                    "CY",
                    "CZ",
                    "DK",
                    "DO",
                    "DE",
                    "EC",
                    "EE",
                    "SV",
                    "FI",
                    "FR",
                    "GR",
                    "GT",
                    "HN",
                    "HK",
                    "HU",
                    "IS",
                    "IE",
                    "IT",
                    "LV",
                    "LT",
                    "LU",
                    "MY",
                    "MT",
                    "MX",
                    "NL",
                    "NZ",
                    "NI",
                    "NO",
                    "PA",
                    "PY",
                    "PE",
                    "PH",
                    "PL",
                    "PT",
                    "SG",
                    "SK",
                    "ES",
                    "SE",
                    "CH",
                    "TW",
                    "TR",
                    "UY",
                    "US",
                    "GB",
                    "AD",
                    "LI",
                    "MC",
                    "ID",
                    "JP",
                    "TH",
                    "VN",
                    "RO",
                    "IL",
                    "ZA",
                    "SA",
                    "AE",
                    "BH",
                    "QA",
                    "OM",
                    "KW",
                    "EG",
                    "MA",
                    "DZ",
                    "TN",
                    "LB",
                    "JO",
                    "PS",
                    "IN",
                    "BY",
                    "KZ",
                    "MD",
                    "UA",
                    "AL",
                    "BA",
                    "HR",
                    "ME",
                    "MK",
                    "RS",
                    "SI",
                    "KR",
                    "BD",
                    "PK",
                    "LK",
                    "GH",
                    "KE",
                    "NG",
                    "TZ",
                    "UG",
                    "AG",
                    "AM",
                    "BS",
                    "BB",
                    "BZ",
                    "BT",
                    "BW",
                    "BF",
                    "CV",
                    "CW",
                    "DM",
                    "FJ",
                    "GM",
                    "GE",
                    "GD",
                    "GW",
                    "GY",
                    "HT",
                    "JM",
                    "KI",
                    "LS",
                    "LR",
                    "MW",
                    "MV",
                    "ML",
                    "MH",
                    "FM",
                    "NA",
                    "NR",
                    "NE",
                    "PW",
                    "PG",
                    "PR",
                    "WS",
                    "SM",
                    "ST",
                    "SN",
                    "SC",
                    "SL",
                    "SB",
                    "KN",
                    "LC",
                    "VC",
                    "SR",
                    "TL",
                    "TO",
                    "TT",
                    "TV",
                    "VU",
                    "AZ",
                    "BN",
                    "BI",
                    "KH",
                    "CM",
                    "TD",
                    "KM",
                    "GQ",
                    "SZ",
                    "GA",
                    "GN",
                    "KG",
                    "LA",
                    "MO",
                    "MR",
                    "MN",
                    "NP",
                    "RW",
                    "TG",
                    "UZ",
                    "ZW",
                    "BJ",
                    "MG",
                    "MU",
                    "MZ",
                    "AO",
                    "CI",
                    "DJ",
                    "ZM",
                    "CD",
                    "CG",
                    "IQ",
                    "LY",
                    "TJ",
                    "VE",
                    "ET",
                    "XK",
                ],
                "type": "album",
                "album_type": "album",
                "href": "https://api.spotify.com/v1/albums/3XH1loQu2ohrMnmGCJMPYa",
                "id": "3XH1loQu2ohrMnmGCJMPYa",
                "images": [
                    {
                        "height": 640,
                        "url": "https://i.scdn.co/image/ab67616d0000b273f17110b67858552d3f18e1e0",
                        "width": 640,
                    },
                    {
                        "height": 300,
                        "url": "https://i.scdn.co/image/ab67616d00001e02f17110b67858552d3f18e1e0",
                        "width": 300,
                    },
                    {
                        "height": 64,
                        "url": "https://i.scdn.co/image/ab67616d00004851f17110b67858552d3f18e1e0",
                        "width": 64,
                    },
                ],
                "name": "Duotones",
                "release_date": "1986-09-01",
                "release_date_precision": "day",
                "uri": "spotify:album:3XH1loQu2ohrMnmGCJMPYa",
                "artists": [
                    {
                        "external_urls": {
                            "spotify": "https://open.spotify.com/artist/6I3M904Y9IwgDjrQ9pANiB"
                        },
                        "href": "https://api.spotify.com/v1/artists/6I3M904Y9IwgDjrQ9pANiB",
                        "id": "6I3M904Y9IwgDjrQ9pANiB",
                        "name": "Kenny G",
                        "type": "artist",
                        "uri": "spotify:artist:6I3M904Y9IwgDjrQ9pANiB",
                    }
                ],
                "external_urls": {
                    "spotify": "https://open.spotify.com/album/3XH1loQu2ohrMnmGCJMPYa"
                },
                "total_tracks": 10,
            },
            "artists": [
                {
                    "external_urls": {
                        "spotify": "https://open.spotify.com/artist/6I3M904Y9IwgDjrQ9pANiB"
                    },
                    "href": "https://api.spotify.com/v1/artists/6I3M904Y9IwgDjrQ9pANiB",
                    "id": "6I3M904Y9IwgDjrQ9pANiB",
                    "name": "Kenny G",
                    "type": "artist",
                    "uri": "spotify:artist:6I3M904Y9IwgDjrQ9pANiB",
                }
            ],
            "disc_number": 1,
            "track_number": 1,
            "duration_ms": 303333,
            "external_ids": {"isrc": "USAR18600113"},
            "external_urls": {
                "spotify": "https://open.spotify.com/track/3Yx4nbYHdmHQdnYAukyHJR"
            },
            "href": "https://api.spotify.com/v1/tracks/3Yx4nbYHdmHQdnYAukyHJR",
            "id": "3Yx4nbYHdmHQdnYAukyHJR",
            "name": "Songbird",
            "popularity": 49,
            "uri": "spotify:track:3Yx4nbYHdmHQdnYAukyHJR",
            "is_local": False,
        },
        "video_thumbnail": {"url": None},
    },
    {
        "added_at": "2025-11-04T19:13:46Z",
        "added_by": {
            "external_urls": {
                "spotify": "https://open.spotify.com/user/31bruxgr2pyas6a72hpa7oeyjkwu"
            },
            "href": "https://api.spotify.com/v1/users/31bruxgr2pyas6a72hpa7oeyjkwu",
            "id": "31bruxgr2pyas6a72hpa7oeyjkwu",
            "type": "user",
            "uri": "spotify:user:31bruxgr2pyas6a72hpa7oeyjkwu",
        },
        "is_local": False,
        "primary_color": None,
        "track": {
            "preview_url": None,
            "available_markets": [
                "AR",
                "AU",
                "AT",
                "BE",
                "BO",
                "BR",
                "BG",
                "CA",
                "CL",
                "CO",
                "CR",
                "CY",
                "CZ",
                "DK",
                "DO",
                "DE",
                "EC",
                "EE",
                "SV",
                "FI",
                "FR",
                "GR",
                "GT",
                "HN",
                "HK",
                "HU",
                "IS",
                "IE",
                "IT",
                "LV",
                "LT",
                "LU",
                "MY",
                "MT",
                "MX",
                "NL",
                "NZ",
                "NI",
                "NO",
                "PA",
                "PY",
                "PE",
                "PH",
                "PL",
                "PT",
                "SG",
                "SK",
                "ES",
                "SE",
                "CH",
                "TW",
                "TR",
                "UY",
                "US",
                "GB",
                "AD",
                "LI",
                "MC",
                "ID",
                "JP",
                "TH",
                "VN",
                "RO",
                "IL",
                "ZA",
                "SA",
                "AE",
                "BH",
                "QA",
                "OM",
                "KW",
                "EG",
                "MA",
                "DZ",
                "TN",
                "LB",
                "JO",
                "PS",
                "IN",
                "KZ",
                "MD",
                "UA",
                "AL",
                "BA",
                "HR",
                "ME",
                "MK",
                "RS",
                "SI",
                "KR",
                "BD",
                "PK",
                "LK",
                "GH",
                "KE",
                "NG",
                "TZ",
                "UG",
                "AG",
                "AM",
                "BS",
                "BB",
                "BZ",
                "BT",
                "BW",
                "BF",
                "CV",
                "CW",
                "DM",
                "FJ",
                "GM",
                "GE",
                "GD",
                "GW",
                "GY",
                "HT",
                "JM",
                "KI",
                "LS",
                "LR",
                "MW",
                "MV",
                "ML",
                "MH",
                "FM",
                "NA",
                "NR",
                "NE",
                "PW",
                "PG",
                "WS",
                "SM",
                "ST",
                "SN",
                "SC",
                "SL",
                "SB",
                "KN",
                "LC",
                "VC",
                "SR",
                "TL",
                "TO",
                "TT",
                "TV",
                "VU",
                "AZ",
                "BN",
                "BI",
                "KH",
                "CM",
                "TD",
                "KM",
                "GQ",
                "SZ",
                "GA",
                "GN",
                "KG",
                "LA",
                "MO",
                "MR",
                "MN",
                "NP",
                "RW",
                "TG",
                "UZ",
                "ZW",
                "BJ",
                "MG",
                "MU",
                "MZ",
                "AO",
                "CI",
                "DJ",
                "ZM",
                "CD",
                "CG",
                "IQ",
                "LY",
                "TJ",
                "VE",
                "ET",
                "XK",
            ],
            "explicit": False,
            "type": "track",
            "episode": False,
            "track": True,
            "album": {
                "available_markets": [
                    "AR",
                    "AU",
                    "AT",
                    "BE",
                    "BO",
                    "BR",
                    "BG",
                    "CA",
                    "CL",
                    "CO",
                    "CR",
                    "CY",
                    "CZ",
                    "DK",
                    "DO",
                    "DE",
                    "EC",
                    "EE",
                    "SV",
                    "FI",
                    "FR",
                    "GR",
                    "GT",
                    "HN",
                    "HK",
                    "HU",
                    "IS",
                    "IE",
                    "IT",
                    "LV",
                    "LT",
                    "LU",
                    "MY",
                    "MT",
                    "MX",
                    "NL",
                    "NZ",
                    "NI",
                    "NO",
                    "PA",
                    "PY",
                    "PE",
                    "PH",
                    "PL",
                    "PT",
                    "SG",
                    "SK",
                    "ES",
                    "SE",
                    "CH",
                    "TW",
                    "TR",
                    "UY",
                    "US",
                    "GB",
                    "AD",
                    "LI",
                    "MC",
                    "ID",
                    "JP",
                    "TH",
                    "VN",
                    "RO",
                    "IL",
                    "ZA",
                    "SA",
                    "AE",
                    "BH",
                    "QA",
                    "OM",
                    "KW",
                    "EG",
                    "MA",
                    "DZ",
                    "TN",
                    "LB",
                    "JO",
                    "PS",
                    "IN",
                    "KZ",
                    "MD",
                    "UA",
                    "AL",
                    "BA",
                    "HR",
                    "ME",
                    "MK",
                    "RS",
                    "SI",
                    "KR",
                    "BD",
                    "PK",
                    "LK",
                    "GH",
                    "KE",
                    "NG",
                    "TZ",
                    "UG",
                    "AG",
                    "AM",
                    "BS",
                    "BB",
                    "BZ",
                    "BT",
                    "BW",
                    "BF",
                    "CV",
                    "CW",
                    "DM",
                    "FJ",
                    "GM",
                    "GE",
                    "GD",
                    "GW",
                    "GY",
                    "HT",
                    "JM",
                    "KI",
                    "LS",
                    "LR",
                    "MW",
                    "MV",
                    "ML",
                    "MH",
                    "FM",
                    "NA",
                    "NR",
                    "NE",
                    "PW",
                    "PG",
                    "WS",
                    "SM",
                    "ST",
                    "SN",
                    "SC",
                    "SL",
                    "SB",
                    "KN",
                    "LC",
                    "VC",
                    "SR",
                    "TL",
                    "TO",
                    "TT",
                    "TV",
                    "VU",
                    "AZ",
                    "BN",
                    "BI",
                    "KH",
                    "CM",
                    "TD",
                    "KM",
                    "GQ",
                    "SZ",
                    "GA",
                    "GN",
                    "KG",
                    "LA",
                    "MO",
                    "MR",
                    "MN",
                    "NP",
                    "RW",
                    "TG",
                    "UZ",
                    "ZW",
                    "BJ",
                    "MG",
                    "MU",
                    "MZ",
                    "AO",
                    "CI",
                    "DJ",
                    "ZM",
                    "CD",
                    "CG",
                    "IQ",
                    "LY",
                    "TJ",
                    "VE",
                    "ET",
                    "XK",
                ],
                "type": "album",
                "album_type": "single",
                "href": "https://api.spotify.com/v1/albums/68CN2LzY8MoxO2udy2C22e",
                "id": "68CN2LzY8MoxO2udy2C22e",
                "images": [
                    {
                        "height": 640,
                        "url": "https://i.scdn.co/image/ab67616d0000b273e6065f209e0a01986206bd53",
                        "width": 640,
                    },
                    {
                        "height": 300,
                        "url": "https://i.scdn.co/image/ab67616d00001e02e6065f209e0a01986206bd53",
                        "width": 300,
                    },
                    {
                        "height": 64,
                        "url": "https://i.scdn.co/image/ab67616d00004851e6065f209e0a01986206bd53",
                        "width": 64,
                    },
                ],
                "name": "Sailor Song",
                "release_date": "2024-07-26",
                "release_date_precision": "day",
                "uri": "spotify:album:68CN2LzY8MoxO2udy2C22e",
                "artists": [
                    {
                        "external_urls": {
                            "spotify": "https://open.spotify.com/artist/1iCnM8foFssWlPRLfAbIwo"
                        },
                        "href": "https://api.spotify.com/v1/artists/1iCnM8foFssWlPRLfAbIwo",
                        "id": "1iCnM8foFssWlPRLfAbIwo",
                        "name": "Gigi Perez",
                        "type": "artist",
                        "uri": "spotify:artist:1iCnM8foFssWlPRLfAbIwo",
                    }
                ],
                "external_urls": {
                    "spotify": "https://open.spotify.com/album/68CN2LzY8MoxO2udy2C22e"
                },
                "total_tracks": 1,
            },
            "artists": [
                {
                    "external_urls": {
                        "spotify": "https://open.spotify.com/artist/1iCnM8foFssWlPRLfAbIwo"
                    },
                    "href": "https://api.spotify.com/v1/artists/1iCnM8foFssWlPRLfAbIwo",
                    "id": "1iCnM8foFssWlPRLfAbIwo",
                    "name": "Gigi Perez",
                    "type": "artist",
                    "uri": "spotify:artist:1iCnM8foFssWlPRLfAbIwo",
                }
            ],
            "disc_number": 1,
            "track_number": 1,
            "duration_ms": 211978,
            "external_ids": {"isrc": "USHM92438095"},
            "external_urls": {
                "spotify": "https://open.spotify.com/track/2262bWmqomIaJXwCRHr13j"
            },
            "href": "https://api.spotify.com/v1/tracks/2262bWmqomIaJXwCRHr13j",
            "id": "2262bWmqomIaJXwCRHr13j",
            "name": "Sailor Song",
            "popularity": 87,
            "uri": "spotify:track:2262bWmqomIaJXwCRHr13j",
            "is_local": False,
        },
        "video_thumbnail": {"url": None},
    },
    {
        "added_at": "2025-11-04T19:13:48Z",
        "added_by": {
            "external_urls": {
                "spotify": "https://open.spotify.com/user/31bruxgr2pyas6a72hpa7oeyjkwu"
            },
            "href": "https://api.spotify.com/v1/users/31bruxgr2pyas6a72hpa7oeyjkwu",
            "id": "31bruxgr2pyas6a72hpa7oeyjkwu",
            "type": "user",
            "uri": "spotify:user:31bruxgr2pyas6a72hpa7oeyjkwu",
        },
        "is_local": False,
        "primary_color": None,
        "track": {
            "preview_url": None,
            "available_markets": [
                "AR",
                "AU",
                "AT",
                "BE",
                "BO",
                "BR",
                "BG",
                "CA",
                "CL",
                "CO",
                "CR",
                "CY",
                "CZ",
                "DK",
                "DO",
                "DE",
                "EC",
                "EE",
                "SV",
                "FI",
                "FR",
                "GR",
                "GT",
                "HN",
                "HK",
                "HU",
                "IS",
                "IE",
                "IT",
                "LV",
                "LT",
                "LU",
                "MY",
                "MT",
                "MX",
                "NL",
                "NZ",
                "NI",
                "NO",
                "PA",
                "PY",
                "PE",
                "PH",
                "PL",
                "PT",
                "SG",
                "SK",
                "ES",
                "SE",
                "CH",
                "TW",
                "TR",
                "UY",
                "US",
                "GB",
                "AD",
                "LI",
                "MC",
                "ID",
                "JP",
                "TH",
                "VN",
                "RO",
                "IL",
                "ZA",
                "SA",
                "AE",
                "BH",
                "QA",
                "OM",
                "KW",
                "EG",
                "MA",
                "DZ",
                "TN",
                "LB",
                "JO",
                "PS",
                "IN",
                "KZ",
                "MD",
                "UA",
                "AL",
                "BA",
                "HR",
                "ME",
                "MK",
                "RS",
                "SI",
                "KR",
                "BD",
                "PK",
                "LK",
                "GH",
                "KE",
                "NG",
                "TZ",
                "UG",
                "AG",
                "AM",
                "BS",
                "BB",
                "BZ",
                "BT",
                "BW",
                "BF",
                "CV",
                "CW",
                "DM",
                "FJ",
                "GM",
                "GE",
                "GD",
                "GW",
                "GY",
                "HT",
                "JM",
                "KI",
                "LS",
                "LR",
                "MW",
                "MV",
                "ML",
                "MH",
                "FM",
                "NA",
                "NR",
                "NE",
                "PW",
                "PG",
                "WS",
                "SM",
                "ST",
                "SN",
                "SC",
                "SL",
                "SB",
                "KN",
                "LC",
                "VC",
                "SR",
                "TL",
                "TO",
                "TT",
                "TV",
                "VU",
                "AZ",
                "BN",
                "BI",
                "KH",
                "CM",
                "TD",
                "KM",
                "GQ",
                "SZ",
                "GA",
                "GN",
                "KG",
                "LA",
                "MO",
                "MR",
                "MN",
                "NP",
                "RW",
                "TG",
                "UZ",
                "ZW",
                "BJ",
                "MG",
                "MU",
                "MZ",
                "AO",
                "CI",
                "DJ",
                "ZM",
                "CD",
                "CG",
                "IQ",
                "LY",
                "TJ",
                "VE",
                "ET",
                "XK",
            ],
            "explicit": False,
            "type": "track",
            "episode": False,
            "track": True,
            "album": {
                "available_markets": [
                    "AR",
                    "AU",
                    "AT",
                    "BE",
                    "BO",
                    "BR",
                    "BG",
                    "CA",
                    "CL",
                    "CO",
                    "CR",
                    "CY",
                    "CZ",
                    "DK",
                    "DO",
                    "DE",
                    "EC",
                    "EE",
                    "SV",
                    "FI",
                    "FR",
                    "GR",
                    "GT",
                    "HN",
                    "HK",
                    "HU",
                    "IS",
                    "IE",
                    "IT",
                    "LV",
                    "LT",
                    "LU",
                    "MY",
                    "MT",
                    "MX",
                    "NL",
                    "NZ",
                    "NI",
                    "NO",
                    "PA",
                    "PY",
                    "PE",
                    "PH",
                    "PL",
                    "PT",
                    "SG",
                    "SK",
                    "ES",
                    "SE",
                    "CH",
                    "TW",
                    "TR",
                    "UY",
                    "US",
                    "GB",
                    "AD",
                    "LI",
                    "MC",
                    "ID",
                    "JP",
                    "TH",
                    "VN",
                    "RO",
                    "IL",
                    "ZA",
                    "SA",
                    "AE",
                    "BH",
                    "QA",
                    "OM",
                    "KW",
                    "EG",
                    "MA",
                    "DZ",
                    "TN",
                    "LB",
                    "JO",
                    "PS",
                    "IN",
                    "KZ",
                    "MD",
                    "UA",
                    "AL",
                    "BA",
                    "HR",
                    "ME",
                    "MK",
                    "RS",
                    "SI",
                    "KR",
                    "BD",
                    "PK",
                    "LK",
                    "GH",
                    "KE",
                    "NG",
                    "TZ",
                    "UG",
                    "AG",
                    "AM",
                    "BS",
                    "BB",
                    "BZ",
                    "BT",
                    "BW",
                    "BF",
                    "CV",
                    "CW",
                    "DM",
                    "FJ",
                    "GM",
                    "GE",
                    "GD",
                    "GW",
                    "GY",
                    "HT",
                    "JM",
                    "KI",
                    "LS",
                    "LR",
                    "MW",
                    "MV",
                    "ML",
                    "MH",
                    "FM",
                    "NA",
                    "NR",
                    "NE",
                    "PW",
                    "PG",
                    "WS",
                    "SM",
                    "ST",
                    "SN",
                    "SC",
                    "SL",
                    "SB",
                    "KN",
                    "LC",
                    "VC",
                    "SR",
                    "TL",
                    "TO",
                    "TT",
                    "TV",
                    "VU",
                    "AZ",
                    "BN",
                    "BI",
                    "KH",
                    "CM",
                    "TD",
                    "KM",
                    "GQ",
                    "SZ",
                    "GA",
                    "GN",
                    "KG",
                    "LA",
                    "MO",
                    "MR",
                    "MN",
                    "NP",
                    "RW",
                    "TG",
                    "UZ",
                    "ZW",
                    "BJ",
                    "MG",
                    "MU",
                    "MZ",
                    "AO",
                    "CI",
                    "DJ",
                    "ZM",
                    "CD",
                    "CG",
                    "IQ",
                    "LY",
                    "TJ",
                    "VE",
                    "ET",
                    "XK",
                ],
                "type": "album",
                "album_type": "single",
                "href": "https://api.spotify.com/v1/albums/68CN2LzY8MoxO2udy2C22e",
                "id": "68CN2LzY8MoxO2udy2C22e",
                "images": [
                    {
                        "height": 640,
                        "url": "https://i.scdn.co/image/ab67616d0000b273e6065f209e0a01986206bd53",
                        "width": 640,
                    },
                    {
                        "height": 300,
                        "url": "https://i.scdn.co/image/ab67616d00001e02e6065f209e0a01986206bd53",
                        "width": 300,
                    },
                    {
                        "height": 64,
                        "url": "https://i.scdn.co/image/ab67616d00004851e6065f209e0a01986206bd53",
                        "width": 64,
                    },
                ],
                "name": "Sailor Song",
                "release_date": "2024-07-26",
                "release_date_precision": "day",
                "uri": "spotify:album:68CN2LzY8MoxO2udy2C22e",
                "artists": [
                    {
                        "external_urls": {
                            "spotify": "https://open.spotify.com/artist/1iCnM8foFssWlPRLfAbIwo"
                        },
                        "href": "https://api.spotify.com/v1/artists/1iCnM8foFssWlPRLfAbIwo",
                        "id": "1iCnM8foFssWlPRLfAbIwo",
                        "name": "Gigi Perez",
                        "type": "artist",
                        "uri": "spotify:artist:1iCnM8foFssWlPRLfAbIwo",
                    }
                ],
                "external_urls": {
                    "spotify": "https://open.spotify.com/album/68CN2LzY8MoxO2udy2C22e"
                },
                "total_tracks": 1,
            },
            "artists": [
                {
                    "external_urls": {
                        "spotify": "https://open.spotify.com/artist/1iCnM8foFssWlPRLfAbIwo"
                    },
                    "href": "https://api.spotify.com/v1/artists/1iCnM8foFssWlPRLfAbIwo",
                    "id": "1iCnM8foFssWlPRLfAbIwo",
                    "name": "Gigi Perez",
                    "type": "artist",
                    "uri": "spotify:artist:1iCnM8foFssWlPRLfAbIwo",
                }
            ],
            "disc_number": 1,
            "track_number": 1,
            "duration_ms": 211978,
            "external_ids": {"isrc": "USHM92438095"},
            "external_urls": {
                "spotify": "https://open.spotify.com/track/2262bWmqomIaJXwCRHr13j"
            },
            "href": "https://api.spotify.com/v1/tracks/2262bWmqomIaJXwCRHr13j",
            "id": "2262bWmqomIaJXwCRHr13j",
            "name": "Sailor Song",
            "popularity": 87,
            "uri": "spotify:track:2262bWmqomIaJXwCRHr13j",
            "is_local": False,
        },
        "video_thumbnail": {"url": None},
    },
]
