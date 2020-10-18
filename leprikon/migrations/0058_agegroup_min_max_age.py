# -*- coding: utf-8 -*-
# Generated by Django 1.11.29 on 2020-10-14 09:31
from __future__ import unicode_literals

from django.db import migrations, models
import re
import django.db.models.deletion


def set_agegroup_age_limits(apps, schema_editor):
    AgeGroup = apps.get_model('leprikon', 'AgeGroup')
    for age_group in AgeGroup.objects.all():
        match = re.match('([0-9]+)[^0-9]+([0-9]+)', age_group.name)
        if match:
            min_age, max_age = match.groups()
            age_group.min_age = int(min_age)
            age_group.max_age = int(max_age)
            age_group.save()


class Migration(migrations.Migration):

    dependencies = [
        ('leprikon', '0057_registration_period'),
    ]

    operations = [
        migrations.AddField(
            model_name='agegroup',
            name='max_age',
            field=models.PositiveSmallIntegerField(blank=True, null=True, verbose_name='maximal age'),
        ),
        migrations.AddField(
            model_name='agegroup',
            name='min_age',
            field=models.PositiveSmallIntegerField(blank=True, null=True, verbose_name='minimal age'),
        ),
        migrations.RunPython(set_agegroup_age_limits),
    ]
