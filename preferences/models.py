from django.contrib.auth import get_user_model
from django.db import models

from reservations.helpers import create_reservation_job

User = get_user_model()


class TimestampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Preference(TimestampedModel):
    user = models.OneToOneField(
        User, related_name="preferences", on_delete=models.CASCADE
    )
    selections = models.ManyToManyField(
        "selections.Selection", through="SelectionPreference"
    )

    def __str__(self):
        return f"<Preference> {self.user} Selections: {self.selections.count()}"

    class Meta:
        ordering = ("id",)


class SelectionPreference(TimestampedModel):
    preference = models.ForeignKey(Preference, on_delete=models.CASCADE)
    selection = models.ForeignKey("selections.Selection", on_delete=models.CASCADE)

    def save(
        self, force_insert=False, force_update=False, using=None, update_fields=None
    ):
        super().save(force_insert, force_update, using, update_fields)
        create_reservation_job(selection=self.selection, user=self.preference.user)
