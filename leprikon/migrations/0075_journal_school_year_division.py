from django.db import migrations, models
import django.db.models.deletion
from leprikon.models.activities import ActivityModel, ActivityType


def set_journal_school_year_division(apps, schema_editor):
    SchoolYearDivision = apps.get_model("leprikon", "SchoolYearDivision")
    JournalEntry = apps.get_model("leprikon", "JournalEntry")
    Journal = apps.get_model("leprikon", "Journal")

    for journal in Journal.objects.filter(subject__subject_type__subject_type=ActivityModel.COURSE):
        school_year_divisions = list(
            SchoolYearDivision.objects.filter(
                course_registrations__participants__in=journal.participants.all()
            ).distinct()
        )

        if len(school_year_divisions) == 0:
            journal.school_year_division = journal.subject.course.school_year_division
            journal.save()
            continue

        if len(school_year_divisions) == 1:
            journal.school_year_division = school_year_divisions[0]
            journal.save()
            continue

        # split journals by school_year_divisions
        for school_year_division in school_year_divisions:
            new_journal = Journal.objects.create(
                subject=journal.subject,
                name=f"{journal.name}, {school_year_division.name}"[:150],
                school_year_division=school_year_division,
                risks=journal.risks,
                plan=journal.plan,
                evaluation=journal.evaluation,
            )
            new_journal.leaders.set(journal.leaders.all())
            new_journal.participants.set(
                journal.participants.filter(registration__courseregistration__school_year_division=school_year_division)
            )
            for entry in journal.journal_entries.all():
                new_entry = JournalEntry.objects.create(
                    journal=new_journal,
                    date=entry.date,
                    start=entry.start,
                    end=entry.end,
                    agenda=entry.agenda,
                )
                new_entry.participants.set(
                    entry.participants.filter(
                        registration__courseregistration__school_year_division=school_year_division
                    )
                )
                new_entry.participants_instructed.set(
                    entry.participants_instructed.filter(
                        registration__courseregistration__school_year_division=school_year_division
                    )
                )
                entry.leader_entries.update(journal_entry=new_entry)
            journal.journal_entries.all().delete()
        journal.delete()


class Migration(migrations.Migration):
    dependencies = [
        ("leprikon", "0074_schoolyear_period_order"),
    ]

    operations = [
        migrations.AddField(
            model_name="journal",
            name="school_year_division",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="journals",
                to="leprikon.schoolyeardivision",
                verbose_name="school year division",
            ),
        ),
        migrations.RunPython(set_journal_school_year_division),
    ]
