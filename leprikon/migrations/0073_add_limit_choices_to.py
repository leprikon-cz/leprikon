# Generated by Django 3.2.16 on 2023-01-08 18:45

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("django_pays", "0001_initial"),
        ("leprikon", "0072_prices"),
    ]

    operations = [
        migrations.AlterField(
            model_name="courselistplugin",
            name="course_types",
            field=models.ManyToManyField(
                blank=True,
                help_text="Keep empty to skip searching by course types.",
                limit_choices_to={"subject_type": "course"},
                related_name="+",
                to="leprikon.SubjectType",
                verbose_name="course types",
            ),
        ),
        migrations.AlterField(
            model_name="eventlistplugin",
            name="event_types",
            field=models.ManyToManyField(
                blank=True,
                help_text="Keep empty to skip searching by event types.",
                limit_choices_to={"subject_type": "event"},
                related_name="+",
                to="leprikon.SubjectType",
                verbose_name="event types",
            ),
        ),
        migrations.AlterField(
            model_name="filteredcourselistplugin",
            name="course_types",
            field=models.ManyToManyField(
                limit_choices_to={"subject_type": "course"},
                related_name="+",
                to="leprikon.SubjectType",
                verbose_name="course types",
            ),
        ),
        migrations.AlterField(
            model_name="filteredeventlistplugin",
            name="event_types",
            field=models.ManyToManyField(
                limit_choices_to={"subject_type": "event"},
                related_name="+",
                to="leprikon.SubjectType",
                verbose_name="event types",
            ),
        ),
        migrations.AlterField(
            model_name="filteredorderablelistplugin",
            name="event_types",
            field=models.ManyToManyField(
                limit_choices_to={"subject_type": "orderable"},
                related_name="+",
                to="leprikon.SubjectType",
                verbose_name="event types",
            ),
        ),
        migrations.AlterField(
            model_name="message",
            name="sender",
            field=models.ForeignKey(
                limit_choices_to={"is_staff": True},
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="+",
                to=settings.AUTH_USER_MODEL,
                verbose_name="sender",
            ),
        ),
        migrations.AlterField(
            model_name="orderablelistplugin",
            name="event_types",
            field=models.ManyToManyField(
                blank=True,
                help_text="Keep empty to skip searching by event types.",
                limit_choices_to={"subject_type": "orderable"},
                related_name="+",
                to="leprikon.SubjectType",
                verbose_name="event types",
            ),
        ),
    ]
