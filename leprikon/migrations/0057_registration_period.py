# -*- coding: utf-8 -*-
# Generated by Django 1.11.29 on 2020-10-10 21:11
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('leprikon', '0056_registration_period'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='coursediscount',
            name='period',
        ),
        migrations.AlterField(
            model_name='coursediscount',
            name='registration_period',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='discounts', to='leprikon.CourseRegistrationPeriod', verbose_name='period'),
        ),
    ]
