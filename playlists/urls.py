from django.urls import path
from . import views

urlpatterns = [
    path("", views.playlist_dashboard, name="playlists.dashboard"),
    path("edit/", views.render_edit, name="playlists.edit"),
    path("<str:playlist_id>/edit/", views.render_edit, name="playlists.edit_by_id"),
    path("save_decision/", views.save_decision, name="playlists.save_decision"),
    path("<str:playlist_id>/kept/", views.kept_view, name="playlists.kept"),
    path("reconsider/", views.reconsider_decision, name="playlists.reconsider_decision"),
]
