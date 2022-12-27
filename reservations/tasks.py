from celery.task import task
from django.conf import settings


@task(
    bind=True,
    max_retries=3,
    default_retry_delay=settings.DEFAULT_TASK_COUNTDOWN_MINUTES * 60,
)
def execute_reservation_job(self, reservation_job_id, retry_count=0):
    from .commands.base import ReservationCommandRunner
    from .models import ReservationJob

    reservation_job = ReservationJob.objects.get(id=reservation_job_id)
    runner = ReservationCommandRunner(
        reservation_job.user,
        reservation_job.selection,
        is_max_retry=self.max_retries == retry_count,
    )
    runner()

    if runner.is_failure:
        raise self.retry(kwargs={"retry_count": retry_count + 1})
