from django.urls import path
from . import views

urlpatterns = [
    path("", views.playlist_dashboard, name="playlists.dashboard"),
    path("analytics/", views.analytics_dashboard, name="playlists.analytics"),
    path("analytics/export/<str:section>/", views.export_analytics_csv, name="playlists.export_csv"),
    path("edit/", views.render_edit, name="playlists.edit"),
    path("<str:playlist_id>/edit/", views.render_edit, name="playlists.edit_by_id"),
    path("save_decision/", views.save_decision, name="playlists.save_decision"),
    path("<str:playlist_id>/choices/", views.kept_view, name="playlists.kept"),
    path("<str:playlist_id>/apply-changes/", views.apply_playlist_changes, name="playlists.apply_changes"),
    path("reconsider/", views.reconsider_decision, name="playlists.reconsider_decision"),
]
