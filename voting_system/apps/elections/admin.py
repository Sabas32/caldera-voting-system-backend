from django.contrib import admin

from voting_system.apps.elections.models import Candidate, Election, Post


@admin.register(Election)
class ElectionAdmin(admin.ModelAdmin):
    list_display = ("title", "organization", "status", "opens_at", "closes_at", "publish_results")
    list_filter = ("status", "organization")
    search_fields = ("title", "slug", "organization__name")


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ("title", "election", "max_selections", "allow_abstain", "sort_order")
    list_filter = ("election__organization",)
    search_fields = ("title", "election__title")


@admin.register(Candidate)
class CandidateAdmin(admin.ModelAdmin):
    list_display = ("name", "post", "status", "sort_order")
    list_filter = ("status", "post__election__organization")
    search_fields = ("name", "post__title", "post__election__title")
