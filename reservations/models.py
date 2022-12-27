from django.contrib.auth import get_user_model
from django.db import models

from reservations.tasks import execute_reservation_job

User = get_user_model()


class TimestampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class ReservationJob(TimestampedModel):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

    STATUS_CHOICES = (
        (PENDING, "PENDING"),
        (COMPLETED, "COMPLETED"),
        (FAILED, "FAILED"),
    )

    ETA = "ETA"
    IMMEDIATE = "IMMEDIATE"

    EXECUTION_TYPE_CHOICES = ((ETA, "ETA"), (IMMEDIATE, "IMMEDIATE"))

    execution_time = models.DateTimeField()
    execution_type = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        choices=EXECUTION_TYPE_CHOICES,
        default=ETA,
    )
    status = models.CharField(
        max_length=255, null=True, blank=True, choices=STATUS_CHOICES, default=PENDING
    )
    selection = models.ForeignKey("selections.Selection", on_delete=models.CASCADE)
    user = models.ForeignKey(
        User,
        related_name="reservation_jobs",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )

    def __str__(self):
        return f"<ReservationJob> {self.execution_time.strftime('%Y-%m-%d %H:%M')} {self.status}"

    class Meta:
        ordering = ("id",)

    def save(
        self, force_insert=False, force_update=False, using=None, update_fields=None
    ):
        super().save(force_insert, force_update, using, update_fields)
        if self.execution_type == self.IMMEDIATE:
            execute_reservation_job.delay(self.id)
        else:
            execute_reservation_job.apply_async((self.id,), eta=self.execution_time)


class Reservation(TimestampedModel):
    PENDING = "PENDING"
    IN_CART = "IN_CART"
    FAILED = "FAILED"

    STATUS_CHOICES = (
        (IN_CART, "IN_CART"),
        (FAILED, "FAILED"),
        (PENDING, "PENDING"),
    )

    user = models.ForeignKey(
        User, related_name="reservations", on_delete=models.CASCADE
    )
    selection = models.ForeignKey("selections.Selection", on_delete=models.CASCADE)
    status = models.CharField(
        max_length=255, null=True, blank=True, choices=STATUS_CHOICES, default=PENDING
    )

    def __str__(self):
        return f"<Reservation> {self.user} {self.status} {self.selection}"

    class Meta:
        ordering = ("selection__slot__date_time",)

    @property
    def is_success(self):
        return self.status == Reservation.IN_CART

    def save(
        self, force_insert=False, force_update=False, using=None, update_fields=None
    ):
        from reservations.helpers import send_reservation_email

        super().save(force_insert, force_update, using, update_fields)

        send_reservation_email(self)

        status = ReservationJob.COMPLETED if self.is_success else ReservationJob.FAILED
        ReservationJob.objects.filter(user=self.user, selection=self.selection).update(
            status=status
        )
