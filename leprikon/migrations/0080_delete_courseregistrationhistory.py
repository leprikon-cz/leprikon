# Generated by Django 3.2.20 on 2023-08-16 20:04

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("leprikon", "0079_mandatory_subject_variants"),
    ]

    operations = [
        migrations.DeleteModel(
            name="CourseRegistrationHistory",
        ),
    ]
