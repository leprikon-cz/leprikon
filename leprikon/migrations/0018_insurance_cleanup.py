# -*- coding: utf-8 -*-
# Generated by Django 1.9.9 on 2016-11-26 09:43
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('leprikon', '0017_insurance'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='participant',
            name='insurance_old',
        ),
        migrations.RemoveField(
            model_name='clubregistration',
            name='insurance_old',
        ),
        migrations.RemoveField(
            model_name='eventregistration',
            name='insurance_old',
        ),
    ]
