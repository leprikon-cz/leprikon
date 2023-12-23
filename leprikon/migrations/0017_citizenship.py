# Generated by Django 1.11.12 on 2018-08-29 13:30

from django.db import migrations, models
from django.utils import translation
from django.utils.translation import gettext as _
from django_countries.data import COUNTRIES
import django.db.models.deletion
from leprikon.conf import settings


_("Czechia")  # we want Czechia to be translated
all_EU_countries = [
    "AT",
    "BE",
    "BG",
    "CY",
    "CZ",
    "DK",
    "EE",
    "FI",
    "FR",
    "DE",
    "GR",
    "HU",
    "IE",
    "IT",
    "LV",
    "LT",
    "LU",
    "MT",
    "NL",
    "PL",
    "PT",
    "RO",
    "SK",
    "SI",
    "ES",
    "SE",
    "GB",
]
other_EU_countries = [country for country in all_EU_countries if country != settings.LEPRIKON_COUNTRY]


def create_default_citizenships(apps, schema_editor):
    Citizenship = apps.get_model("leprikon", "Citizenship")
    translation.activate(settings.LEPRIKON_COUNTRY)
    Citizenship.objects.bulk_create(
        (
            Citizenship(order=0, name=COUNTRIES[settings.LEPRIKON_COUNTRY], require_birth_num=True),
            Citizenship(order=1, name=_("other country in EU"), require_birth_num=False),
            Citizenship(order=2, name=_("country outside EU"), require_birth_num=False),
        )
    )


def update_registration_citizenships(apps, schema_editor):
    Citizenship = apps.get_model("leprikon", "Citizenship")
    SubjectRegistration = apps.get_model("leprikon", "SubjectRegistration")
    SubjectRegistration.objects.filter(
        participant_citizenship_old=settings.LEPRIKON_COUNTRY,
    ).update(participant_citizenship_id=1)
    SubjectRegistration.objects.filter(
        participant_citizenship_old__in=other_EU_countries,
    ).update(participant_citizenship_id=2)


def update_participant_citizenships(apps, schema_editor):
    Citizenship = apps.get_model("leprikon", "Citizenship")
    Participant = apps.get_model("leprikon", "Participant")
    Participant.objects.filter(
        citizenship_old=settings.LEPRIKON_COUNTRY,
    ).update(citizenship_id=1)
    Participant.objects.filter(
        citizenship_old__in=other_EU_countries,
    ).update(citizenship_id=2)


class Migration(migrations.Migration):
    dependencies = [
        ("leprikon", "0016_school_year_divisions_cleanup"),
    ]

    operations = [
        migrations.CreateModel(
            name="Citizenship",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=50, verbose_name="name")),
                ("require_birth_num", models.BooleanField(default=True, verbose_name="require birth number")),
                ("order", models.IntegerField(blank=True, default=0, verbose_name="order")),
            ],
            options={
                "ordering": ("order",),
                "verbose_name": "citizenship",
                "verbose_name_plural": "citizenships",
            },
        ),
        migrations.RunPython(create_default_citizenships),
        migrations.RenameField(
            model_name="subjectregistration",
            old_name="participant_citizenship",
            new_name="participant_citizenship_old",
        ),
        migrations.AddField(
            model_name="subjectregistration",
            name="participant_citizenship",
            field=models.ForeignKey(
                default=3,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="+",
                to="leprikon.Citizenship",
                verbose_name="citizenship",
            ),
            preserve_default=False,
        ),
        migrations.RunPython(update_registration_citizenships),
        migrations.RenameField(
            model_name="participant",
            old_name="citizenship",
            new_name="citizenship_old",
        ),
        migrations.AddField(
            model_name="participant",
            name="citizenship",
            field=models.ForeignKey(
                default=3,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="+",
                to="leprikon.Citizenship",
                verbose_name="citizenship",
            ),
            preserve_default=False,
        ),
        migrations.RunPython(update_participant_citizenships),
    ]
