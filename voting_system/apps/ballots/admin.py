from django.contrib import admin

from voting_system.apps.ballots.models import Ballot, BallotChoice


@admin.register(Ballot)
class BallotAdmin(admin.ModelAdmin):
    list_display = ("election", "receipt_code", "submitted_at")
    search_fields = ("election__title", "election__slug", "receipt_code", "token__token_hint")


@admin.register(BallotChoice)
class BallotChoiceAdmin(admin.ModelAdmin):
    list_display = ("ballot", "post", "candidate", "abstained")
    search_fields = ("ballot__receipt_code", "post__title", "candidate__name")
