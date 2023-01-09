from django.db import migrations, models
import django.db.models.deletion


def set_journalentry_period(apps, schema_editor):
    SchoolYearDivision = apps.get_model("leprikon", "SchoolYearDivision")
    SchoolYearPeriod = apps.get_model("leprikon", "SchoolYearPeriod")
    JournalEntry = apps.get_model("leprikon", "JournalEntry")
    for school_year_period in SchoolYearPeriod.objects.filter(start__isnull=False, end__isnull=False):
        JournalEntry.objects.filter(
            journal__school_year_division=school_year_period.school_year_division,
            date__gte=school_year_period.start,
            date__lte=school_year_period.end,
        ).update(period=school_year_period)
    for school_year_division in SchoolYearDivision.objects.all():
        JournalEntry.objects.filter(
            journal__school_year_division=school_year_division,
            period__isnull=True,
        ).update(period=SchoolYearPeriod.objects.filter(school_year_division=school_year_division).first())


class Migration(migrations.Migration):

    dependencies = [
        ("leprikon", "0075_journal_school_year_division"),
    ]

    operations = [
        migrations.AddField(
            model_name="journalentry",
            name="period",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="journal_entries",
                to="leprikon.schoolyearperiod",
                verbose_name="school year period",
            ),
        ),
        migrations.RunPython(set_journalentry_period),
    ]
