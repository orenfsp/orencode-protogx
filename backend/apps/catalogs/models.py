from django.db import models


class Organization(models.Model):
    """Minimal organization identity; affiliation history belongs to the future registry."""

    code = models.SlugField(max_length=100, unique=True)
    name = models.CharField(max_length=300)
    organization_type = models.CharField(max_length=100, blank=True)
    municipality = models.CharField(max_length=200, blank=True)
    is_active = models.BooleanField(default=True)
    contact = models.CharField(max_length=300, blank=True)

    def __str__(self):
        return self.name


class Discipline(models.Model):
    code = models.SlugField(max_length=64, unique=True)
    name = models.CharField(max_length=200)
    is_active = models.BooleanField(default=True)
    config = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ("name",)

    def __str__(self):
        return self.name
