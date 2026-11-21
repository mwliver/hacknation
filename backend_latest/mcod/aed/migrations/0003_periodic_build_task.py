from django.db import migrations

TASK_NAME = "AED – budowa krajowego zbioru defibrylatorów"
TASK = "mcod.aed.tasks.build_aed_national_dataset_task"


def create_periodic_task(apps, schema_editor):
    CrontabSchedule = apps.get_model("django_celery_beat", "CrontabSchedule")
    PeriodicTask = apps.get_model("django_celery_beat", "PeriodicTask")
    schedule, _ = CrontabSchedule.objects.get_or_create(
        minute="30", hour="3", day_of_week="*", day_of_month="*", month_of_year="*", timezone="Europe/Warsaw"
    )
    # The task itself is a no-op while AED_ENABLED is False.
    PeriodicTask.objects.get_or_create(
        name=TASK_NAME, defaults={"task": TASK, "crontab": schedule, "queue": "periodic", "enabled": True}
    )


def delete_periodic_task(apps, schema_editor):
    apps.get_model("django_celery_beat", "PeriodicTask").objects.filter(name=TASK_NAME).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("aed", "0002_national_dataset"),
        ("django_celery_beat", "0015_edit_solarschedule_events_choices"),
    ]

    operations = [migrations.RunPython(create_periodic_task, delete_periodic_task)]
