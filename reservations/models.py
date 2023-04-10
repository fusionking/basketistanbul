from datetime import timedelta

from celery.task.control import inspect, revoke
from dateutil.relativedelta import relativedelta
from django.contrib.auth import get_user_model
from django.db import models

from reservations.tasks import check_basket, execute_reservation_job

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
    CANCELLED = "CANCELLED"
    APPROVED = "APPROVED"

    STATUS_CHOICES = (
        (PENDING, "PENDING"),
        (COMPLETED, "COMPLETED"),
        (FAILED, "FAILED"),
        (CANCELLED, "CANCELLED"),
        (APPROVED, "APPROVED"),
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
        ordering = ("selection__slot__date_time",)

    def revoke(self):
        i = inspect()
        scheduled_tasks = i.scheduled()
        for _, tasks in scheduled_tasks.items():
            rj_task = [task for task in tasks if task["request"]["args"][0] == self.id]
            if rj_task:
                revoke(rj_task[0]["request"]["id"])

    def execute(self):
        if self.status == self.CANCELLED:
            return

        if self.execution_type == self.IMMEDIATE:
            execute_reservation_job.delay(self.id)
        else:
            execute_reservation_job.apply_async((self.id,), eta=self.execution_time)

    def save(
        self, force_insert=False, force_update=False, using=None, update_fields=None
    ):
        if self.status == self.CANCELLED:
            self.revoke()

        super().save(force_insert, force_update, using, update_fields)
        self.execute()


class Reservation(TimestampedModel):
    PENDING = "PENDING"
    IN_CART = "IN_CART"
    FAILED = "FAILED"
    REMOVED_FROM_BASKET = "REMOVED_FROM_BASKET"
    PAID = "PAID"
    EXPIRED = "EXPIRED"

    STATUS_CHOICES = (
        (IN_CART, "IN_CART"),
        (FAILED, "FAILED"),
        (PENDING, "PENDING"),
        (REMOVED_FROM_BASKET, "REMOVED_FROM_BASKET"),
        (PAID, "PAID"),
        (EXPIRED, "EXPIRED"),
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

        if self.status in (Reservation.IN_CART, Reservation.FAILED):
            send_reservation_email(self)

            status = (
                ReservationJob.COMPLETED if self.is_success else ReservationJob.FAILED
            )
            ReservationJob.objects.filter(
                user=self.user, selection=self.selection
            ).update(status=status)

        if self.status == Reservation.IN_CART:
            check_basket.apply_async(
                (self.id,), eta=self.created_at + relativedelta(minutes=30)
            )
