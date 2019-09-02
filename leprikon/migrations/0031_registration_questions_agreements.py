# -*- coding: utf-8 -*-
# Generated by Django 1.11.23 on 2019-09-01 22:42
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def set_registration_questions_agreements(apps, schema_editor):
    leprikon_site = apps.get_model('leprikon', 'LeprikonSite').objects.filter(id=settings.SITE_ID).first()
    site_agreements = set(leprikon_site.registration_agreements.all()) if leprikon_site else set()
    for subject_type in apps.get_model('leprikon', 'SubjectType').objects.all():
        subject_type_questions = set(subject_type.questions.all())
        subject_type_agreements = site_agreements.union(subject_type.registration_agreements.all())
        for subject in subject_type.subjects.prefetch_related('questions', 'registration_agreements'):
            questions = subject_type_questions.union(subject.questions.all())
            agreements = subject_type_agreements.union(subject.registration_agreements.all())
            for registration in subject.registrations.all():
                registration.questions.set(questions)
                registration.agreements.set(agreements)


class Migration(migrations.Migration):

    dependencies = [
        ('leprikon', '0030_agreements'),
    ]

    operations = [
        migrations.AddField(
            model_name='agreement',
            name='active',
            field=models.BooleanField(default=True, verbose_name='active'),
        ),
        migrations.AddField(
            model_name='question',
            name='active',
            field=models.BooleanField(default=True, verbose_name='active'),
        ),
        migrations.AddField(
            model_name='subjectregistration',
            name='agreements',
            field=models.ManyToManyField(editable=False, related_name='registrations', to='leprikon.Agreement'),
        ),
        migrations.AddField(
            model_name='subjectregistration',
            name='questions',
            field=models.ManyToManyField(editable=False, related_name='registrations', to='leprikon.Question'),
        ),
        migrations.RunPython(set_registration_questions_agreements),
    ]
