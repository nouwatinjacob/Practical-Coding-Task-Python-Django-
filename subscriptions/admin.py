# subscriptions/admin.py
from django.contrib import admin
from .models import Feature, Plan


@admin.register(Feature)
class FeatureAdmin(admin.ModelAdmin):
    pass


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    filter_horizontal = ('features',)