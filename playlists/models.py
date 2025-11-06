from django.db import models
from django.conf import settings
from django.utils import timezone
from django.db.models import JSONField


class KeptSong(models.Model):
	"""Stores user's decision for a track in a specific Spotify playlist.

	Fields saved to avoid extra Spotify API calls when reviewing kept/removed songs.
	"""
	user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
	playlist_id = models.CharField(max_length=255)  # Spotify playlist id
	track_uri = models.CharField(max_length=255)
	name = models.CharField(max_length=512)
	artists = JSONField(blank=True, null=True)
	image_url = models.URLField(blank=True, null=True)
	preview_url = models.URLField(blank=True, null=True)
	spotify_url = models.URLField(blank=True, null=True)
	kept = models.BooleanField()  # True = kept, False = removed
	created_at = models.DateTimeField(default=timezone.now)

	class Meta:
		unique_together = ("user", "playlist_id", "track_uri")
		verbose_name_plural = "Songs"

	def __str__(self):
		return f"{self.user} - {self.playlist_id} - {self.name} ({'kept' if self.kept else 'removed'})"
