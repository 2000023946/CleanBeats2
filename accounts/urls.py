from django.urls import path
from . import views
from .spotify import play_track

urlpatterns = [
    path("signup", views.signup, name="accounts.signup"),
    path("login/", views.login, name="accounts.login"),
    path("logout/", views.logout, name="accounts.logout"),
    path("spotify/connect/", views.connect_spotify, name="accounts.spotify_connect"),
    path("spotify/callback/", views.spotify_callback, name="accounts.spotify_callback"),
    path("spotify/play-track/", play_track, name="spotify_play_track"),
]
