from django.db import models


class TimestampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class SportSelection(TimestampedModel):
    TENNIS = "Tennis"
    FOOTBALL = "Football"

    BRANCH_CHOICES = (
        (TENNIS, "Tennis"),
        (FOOTBALL, "Football"),
    )

    MALTEPE = "Maltepe Sports Complex"
    LOS_ANGELES = "LA Sports Complex"

    COMPLEX_CHOICES = (
        (MALTEPE, "Maltepe Sports Complex"),
        (LOS_ANGELES, "LA Sports Complex"),
    )

    OPEN_COURT = "Open Court"
    CLOSED_COURT_A = "Closed Court 1"
    CLOSED_COURT_B = "Closed Court 2"
    CLOSED_COURT_C = "Closed Court 3"
    CLOSED_COURT_D = "Closed Court 4"

    PITCH_CHOICES = (
        (OPEN_COURT, "Open Court"),
        (CLOSED_COURT_A, "Closed Court 1"),
        (CLOSED_COURT_B, "Closed Court 2"),
        (CLOSED_COURT_C, "Closed Court 3"),
        (CLOSED_COURT_D, "Closed Court 4"),
    )

    branch_name = models.CharField(max_length=255, choices=BRANCH_CHOICES)
    branch_id = models.CharField(max_length=255)
    complex_name = models.CharField(max_length=255, choices=COMPLEX_CHOICES)
    complex_id = models.CharField(max_length=255)
    pitch_name = models.CharField(max_length=255, choices=PITCH_CHOICES)
    pitch_id = models.CharField(max_length=255)

    def __str__(self):
        return f"<SportSelection> {self.branch_name} - {self.complex_name} - {self.pitch_name}"

    class Meta:
        unique_together = ["branch_id", "complex_id", "pitch_id"]
        ordering = ("id",)

    @property
    def info(self):
        return f"{self.branch_name} - {self.complex_name} - {self.pitch_name}"


class Slot(TimestampedModel):
    date_time = models.DateTimeField()
    event_target = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return f"<Slot> {self.date_time.strftime('%Y-%m-%d %H:%M')}"

    class Meta:
        ordering = ("-date_time",)

    @property
    def formatted_date(self):
        return self.date_time.strftime("%Y-%m-%d %H:%M")


class Selection(TimestampedModel):
    sport_selection = models.ForeignKey(SportSelection, on_delete=models.CASCADE)
    slot = models.ForeignKey(Slot, on_delete=models.CASCADE)

    def __str__(self):
        return f"<Selection> {self.sport_selection} {self.slot}"

    class Meta:
        ordering = ("id",)
