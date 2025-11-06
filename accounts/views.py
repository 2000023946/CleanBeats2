from django.shortcuts import render, redirect
from django.contrib.auth import login as auth_login, authenticate, logout as auth_logout
from .forms import CustomUserCreationForm, CustomErrorList
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
import requests
from .models import SpotifyToken
from .spotify import get_spotify_user_profile
from urllib.parse import urlencode
import secrets
import string


@login_required
def logout(request):
    auth_logout(request)
    return redirect('home.index')
def login(request):
    template_data = {}
    template_data['title'] = 'Login'
    if request.method == 'GET':
        return render(request, 'accounts/login.html',
            {'template_data': template_data})
    elif request.method == 'POST':
        user = authenticate(
            request,
            username = request.POST['username'],
            password = request.POST['password']
        )
        if user is None:
            template_data['error'] = 'The username or password is incorrect.'
            return render(request, 'accounts/login.html',
                {'template_data': template_data})
        else:
            auth_login(request, user)
            return redirect('home.index')
def signup(request):
    template_data = {}
    template_data['title'] = 'Sign Up'
    if request.method == 'GET':
        template_data['form'] = CustomUserCreationForm()
        return render(request, 'accounts/signup.html',
            {'template_data': template_data})
    elif request.method == 'POST':
        form = CustomUserCreationForm(request.POST, error_class=CustomErrorList)
        if form.is_valid():
            form.save()
            return redirect('accounts.login')
        else:
            template_data['form'] = form
            return render(request, 'accounts/signup.html',
                {'template_data': template_data})


@login_required
def connect_spotify(request):
    """Redirect the logged-in user to Spotify's authorization page."""
    scopes = "playlist-read-private playlist-read-collaborative"

    # CSRF protection via state parameter
    state = secrets.token_urlsafe(16)
    request.session['spotify_auth_state'] = state

    # Build absolute redirect URI from current request and named route
    # This must EXACTLY match one of the Redirect URIs configured in the Spotify Dev Dashboard
    redirect_uri = request.build_absolute_uri(
        reverse('accounts.spotify_callback')
    )

    params = {
        'client_id': settings.SPOTIFY_CLIENT_ID,
        'response_type': 'code',
        'redirect_uri': redirect_uri,
        'scope': scopes,
        'state': state,
        'show_dialog': 'true',  # force re-consent on dev for easier testing
    }
    auth_url = 'https://accounts.spotify.com/authorize?' + urlencode(params)
    return redirect(auth_url)


def spotify_callback(request):
    """Handle Spotify redirect with a code and exchange it for tokens."""
    error = request.GET.get('error')
    code = request.GET.get('code')
    returned_state = request.GET.get('state')
    expected_state = request.session.pop('spotify_auth_state', None)

    if error:
        # Could render an error template; for now redirect home
        return redirect('home.index')
    if not code:
        return redirect('home.index')
    if not expected_state or returned_state != expected_state:
        # Potential CSRF or stale callback; do not attempt token exchange
        return redirect('home.index')

    token_url = 'https://accounts.spotify.com/api/token'
    # Must be identical to the redirect_uri used in the authorize request
    redirect_uri = request.build_absolute_uri(
        reverse('accounts.spotify_callback')
    )
    data = {
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': redirect_uri,
        'client_id': settings.SPOTIFY_CLIENT_ID,
        'client_secret': settings.SPOTIFY_CLIENT_SECRET,
    }
    try:
        r = requests.post(token_url, data=data, timeout=10)
        r.raise_for_status()
    except requests.RequestException:
        return redirect('home.index')
    token_data = r.json()
    access_token = token_data.get('access_token')
    refresh_token = token_data.get('refresh_token')
    expires_in = token_data.get('expires_in')  # seconds
    scope = token_data.get('scope', '')

    # If user is authenticated, save tokens to DB; otherwise store in session
    if request.user.is_authenticated:
        expires_at = timezone.now() + timedelta(seconds=expires_in) if expires_in else None
        SpotifyToken.objects.update_or_create(
            user=request.user,
            defaults={
                'access_token': access_token,
                'refresh_token': refresh_token,
                'scope': scope,
                'expires_at': expires_at,
            }
        )
        return redirect('home.index')
    else:
        # Not logged in: store token data in session and prompt user to login/signup
        request.session['spotify_oauth'] = token_data
        return redirect('accounts.login')


@login_required
def account(request):
    """Display user account information including Spotify connection status."""
    template_data = {'title': 'Account'}
    
    # Check if user has Spotify token
    spotify_connected = False
    spotify_profile = None
    
    try:
        spotify_token = SpotifyToken.objects.get(user=request.user)
        spotify_connected = True
        # Get Spotify profile info
        try:
            spotify_profile = get_spotify_user_profile(request.user)
        except Exception as e:
            # If we can't get profile (token expired, etc), still show as connected
            spotify_profile = None
    except SpotifyToken.DoesNotExist:
        spotify_connected = False
    
    template_data.update({
        'spotify_connected': spotify_connected,
        'spotify_profile': spotify_profile,
    })
    
    return render(request, 'accounts/account.html', {'template_data': template_data})


@login_required
def disconnect_spotify(request):
    """Disconnect user's Spotify account by deleting the token."""
    try:
        spotify_token = SpotifyToken.objects.get(user=request.user)
        spotify_token.delete()
    except SpotifyToken.DoesNotExist:
        pass  # Already disconnected
    
    return redirect('accounts.account')


# Create your views here.
