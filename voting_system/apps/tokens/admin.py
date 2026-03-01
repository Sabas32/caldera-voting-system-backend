from django.contrib import admin

from voting_system.apps.tokens.models import Token, TokenBatch


@admin.register(TokenBatch)
class TokenBatchAdmin(admin.ModelAdmin):
    list_display = ("election", "label", "quantity", "revoked", "created_at")
    list_filter = ("revoked", "election__organization")
    search_fields = ("label", "election__title", "election__slug")


@admin.register(Token)
class TokenAdmin(admin.ModelAdmin):
    list_display = ("election", "token_hint", "status", "created_at", "used_at")
    list_filter = ("status", "election__organization")
    search_fields = ("token_hint", "election__slug")
