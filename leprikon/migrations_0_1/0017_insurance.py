# -*- coding: utf-8 -*-
# Generated by Django 1.9.9 on 2016-11-20 22:33
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('leprikon', '0016_countries'),
    ]

    operations = [
        migrations.CreateModel(
            name='Insurance',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.CharField(max_length=10, unique=True, verbose_name='code')),
                ('name', models.CharField(max_length=150, verbose_name='name')),
            ],
            options={
                'ordering': ('code',),
                'verbose_name': 'insurance company',
                'verbose_name_plural': 'insurance companies',
            },
        ),
    ]
    for model_name in ['participant', 'clubregistration', 'eventregistration']:
        operations += [
            migrations.RenameField(
                model_name=model_name,
                old_name='insurance',
                new_name='insurance_old',
            ),
            migrations.AddField(
                model_name=model_name,
                name='insurance',
                field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='+', to='leprikon.Insurance', verbose_name='insurance'),
            ),
        ]
