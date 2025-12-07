from django.urls import path
from . import views

urlpatterns = [
    path('', views.map_view, name='maps.view'),
    path('api/playlists/', views.api_playlists, name='maps.api_playlists'),
    path('api/playlist-geo/', views.api_playlist_geo, name='maps.api_playlist_geo'),
    path('api/country-charts/', views.api_country_charts, name='maps.api_country_charts'),
    path('api/chart-countries/', views.api_chart_countries, name='maps.api_chart_countries'),
]
