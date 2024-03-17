from celery.task import task
from django.conf import settings


def try_to_reserve(current_selection, user):
    from selections.constants import CLOSED_COURT_IDS
    from selections.models import Selection, Slot, SportSelection

    from .commands.base import ReservationCommandRunner

    current_pitch_id = current_selection.sport_selection.pitch_id
    other_pitch_ids = [
        court_id for court_id in CLOSED_COURT_IDS if court_id != current_pitch_id
    ]

    current_slot_date_obj = current_selection.slot.date_time

    for pitch_id in other_pitch_ids:
        print(
            f"***** Trying to reserve {pitch_id} now for slot {current_slot_date_obj.date()} ******"
        )
        slot, _ = Slot.objects.get_or_create(
            date_time__date=current_slot_date_obj,
            date_time__hour=current_slot_date_obj.hour,
            defaults={"date_time": current_slot_date_obj},
        )
        # Get or create Sport Selection
        sport_selection, _ = SportSelection.objects.get_or_create(pitch_id=pitch_id)
        # Get or create Selection
        selection, _ = Selection.objects.get_or_create(
            sport_selection=sport_selection, slot=slot
        )

        runner = ReservationCommandRunner(user, selection, selection.sport_selection)
        runner()

        if not runner.is_failure:
            return True
    return False


@task(
    bind=True,
    max_retries=4,
    default_retry_delay=settings.DEFAULT_TASK_COUNTDOWN_SECONDS,
)
def execute_reservation_job(self, reservation_job_id, retry_count=0):
    from .commands.base import ReservationCommandRunner
    from .models import ReservationJob

    reservation_job = ReservationJob.objects.get(id=reservation_job_id)

    if reservation_job.status == ReservationJob.CANCELLED:
        return

    runner = ReservationCommandRunner(
        reservation_job.user,
        reservation_job.selection,
        reservation_job.selection.sport_selection,
        is_max_retry=self.max_retries == retry_count,
    )
    runner()

    if runner.is_failure:
        if runner.is_no_slot and try_to_reserve(
            reservation_job.selection, reservation_job.user
        ):
            return
        raise self.retry(kwargs={"retry_count": retry_count + 1})


@task
def check_basket(reservation_id):
    from reservations.commands.base import (CheckReservationCommand,
                                            LoginCommand)

    from .commands.base import ReservationCommandRunner
    from .models import Reservation

    reservation = Reservation.objects.get(id=reservation_id)

    selection = reservation.selection
    runner = ReservationCommandRunner(
        reservation.user,
        selection,
        selection.sport_selection,
        commands=[LoginCommand(), CheckReservationCommand()],
        court_selection=selection.sport_selection.pitch_id,
    )
    is_paid = runner()
    if is_paid:
        reservation.status = Reservation.PAID
    else:
        reservation.status = Reservation.EXPIRED
    reservation.save()
