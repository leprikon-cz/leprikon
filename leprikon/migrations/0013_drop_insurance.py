# Generated by Django 1.11.12 on 2018-07-31 16:53

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('leprikon', '0012_subject_variants'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='participant',
            name='insurance',
        ),
        migrations.RemoveField(
            model_name='subjectregistration',
            name='participant_insurance',
        ),
        migrations.DeleteModel(
            name='Insurance',
        ),
    ]
