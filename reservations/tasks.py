from celery import shared_task


@shared_task
def execute_reservation_job(reservation_job_id):
    from .commands.base import ReservationCommandRunner
    from .models import ReservationJob

    reservation_job = ReservationJob.objects.get(id=reservation_job_id)
    runner = ReservationCommandRunner(reservation_job.user, reservation_job.selection)
    runner()
