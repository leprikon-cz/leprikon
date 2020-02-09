# -*- coding: utf-8 -*-
# Generated by Django 1.11.27 on 2020-02-09 15:09
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion
import leprikon.models.fields


class Migration(migrations.Migration):

    dependencies = [
        ('leprikon', '0043_registration_links'),
    ]

    operations = [
        migrations.AddField(
            model_name='billinginfo',
            name='contact_person',
            field=models.CharField(blank=True, max_length=60, null=True, verbose_name='contact person'),
        ),
        migrations.AddField(
            model_name='billinginfo',
            name='email',
            field=leprikon.models.fields.EmailField(blank=True, default='', max_length=254, verbose_name='email address'),
        ),
        migrations.AddField(
            model_name='billinginfo',
            name='employee',
            field=models.CharField(blank=True, default='', max_length=150, verbose_name='employee ID'),
        ),
        migrations.AddField(
            model_name='billinginfo',
            name='phone',
            field=models.CharField(blank=True, default='', max_length=30, verbose_name='phone'),
        ),
        migrations.AddField(
            model_name='subjectregistrationbillinginfo',
            name='contact_person',
            field=models.CharField(blank=True, max_length=60, null=True, verbose_name='contact person'),
        ),
        migrations.AddField(
            model_name='subjectregistrationbillinginfo',
            name='email',
            field=leprikon.models.fields.EmailField(blank=True, default='', max_length=254, verbose_name='email address'),
        ),
        migrations.AddField(
            model_name='subjectregistrationbillinginfo',
            name='employee',
            field=models.CharField(blank=True, default='', max_length=150, verbose_name='employee ID'),
        ),
        migrations.AddField(
            model_name='subjectregistrationbillinginfo',
            name='phone',
            field=models.CharField(blank=True, default='', max_length=30, verbose_name='phone'),
        ),
    ]
