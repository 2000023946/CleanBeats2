from django.contrib import admin
from django.http import HttpResponse
import csv
from .models import KeptSong


@admin.register(KeptSong)
class KeptSongAdmin(admin.ModelAdmin):
    list_display = ('user', 'playlist_id', 'name', 'get_artists', 'kept', 'created_at')
    list_filter = ('kept', 'created_at', 'user')
    search_fields = ('user__username', 'playlist_id', 'name', 'artists')
    list_per_page = 25
    ordering = ('-created_at',)
    actions = ['export_as_csv']
    
    def get_artists(self, obj):
        """Display artists in a readable format"""
        if not obj.artists:
            return 'Unknown Artist'
        
        try:
            # Handle different possible formats
            if isinstance(obj.artists, list):
                # If it's a list of dictionaries with 'name' field
                if all(isinstance(artist, dict) and 'name' in artist for artist in obj.artists):
                    return ', '.join([artist['name'] for artist in obj.artists])
                # If it's a list of strings
                elif all(isinstance(artist, str) for artist in obj.artists):
                    return ', '.join(obj.artists)
                # If it's a mixed list, convert all to strings
                else:
                    return ', '.join([str(artist) for artist in obj.artists])
            
            elif isinstance(obj.artists, dict):
                # If it's a single artist dictionary
                if 'name' in obj.artists:
                    return obj.artists['name']
                else:
                    return str(obj.artists)
            
            elif isinstance(obj.artists, str):
                # If it's already a string
                return obj.artists
            
            else:
                # Fallback for any other format
                return str(obj.artists)
                
        except (TypeError, KeyError, AttributeError) as e:
            # If there's any error parsing, show the raw data for debugging
            return f"Error parsing: {str(obj.artists)[:50]}..."
            
    get_artists.short_description = 'Artists'
    
    def export_as_csv(self, request, queryset):
        """Export selected songs as CSV"""
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename=songs_export.csv'
        writer = csv.writer(response)
        
        # Write header with only the requested fields
        writer.writerow(['User', 'Song Name', 'Artists', 'Kept', 'Spotify URL'])
        
        # Write data rows
        for obj in queryset:
            artists_str = self.get_artists(obj)
            
            row = [
                obj.user.username,
                obj.name,
                artists_str,
                'Yes' if obj.kept else 'No',
                obj.spotify_url or ''
            ]
            writer.writerow(row)
        
        return response
    
    export_as_csv.short_description = "Export selected songs as CSV"
    
    fieldsets = (
        ('User & Playlist Info', {
            'fields': ('user', 'playlist_id')
        }),
        ('Track Details', {
            'fields': ('track_uri', 'name', 'artists', 'kept')
        }),
        ('URLs', {
            'fields': ('image_url', 'preview_url', 'spotify_url'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ('created_at',)


# Register your models here.
