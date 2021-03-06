# -*- coding: utf-8 -*-
# Generated by Django 1.11.23 on 2019-09-09 08:31
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion
import leprikon.models.fields


class Migration(migrations.Migration):

    dependencies = [
        ('leprikon', '0032_registration_participants_groups'),
    ]

    operations = [
        migrations.CreateModel(
            name='TargetGroup',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50, verbose_name='name')),
                ('order', models.IntegerField(blank=True, default=0, verbose_name='order')),
                ('require_school', models.BooleanField(default=True, verbose_name='require school')),
            ],
            options={
                'verbose_name': 'target group',
                'verbose_name_plural': 'target groups',
                'ordering': ('order',),
            },
        ),
        migrations.AddField(
            model_name='subjectregistration',
            name='group_leader_city',
            field=models.CharField(blank=True, default='', max_length=150, verbose_name='city'),
        ),
        migrations.AddField(
            model_name='subjectregistration',
            name='group_leader_email',
            field=leprikon.models.fields.EmailField(blank=True, default='', max_length=254, verbose_name='email address'),
        ),
        migrations.AddField(
            model_name='subjectregistration',
            name='group_leader_first_name',
            field=models.CharField(blank=True, default='', max_length=30, verbose_name='first name'),
        ),
        migrations.AddField(
            model_name='subjectregistration',
            name='group_leader_last_name',
            field=models.CharField(blank=True, default='', max_length=30, verbose_name='last name'),
        ),
        migrations.AddField(
            model_name='subjectregistration',
            name='group_leader_phone',
            field=models.CharField(blank=True, default='', max_length=30, verbose_name='phone'),
        ),
        migrations.AddField(
            model_name='subjectregistration',
            name='group_leader_postal_code',
            field=leprikon.models.fields.PostalCodeField(blank=True, default='', verbose_name='postal code'),
        ),
        migrations.AddField(
            model_name='subjectregistration',
            name='group_leader_street',
            field=models.CharField(blank=True, default='', max_length=150, verbose_name='street'),
        ),
        migrations.AddField(
            model_name='subjectregistration',
            name='group_school',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='+', to='leprikon.School', verbose_name='school'),
        ),
        migrations.AddField(
            model_name='subjectregistration',
            name='group_school_class',
            field=models.CharField(blank=True, default='', max_length=30, verbose_name='class'),
        ),
        migrations.AddField(
            model_name='subjectregistration',
            name='group_school_other',
            field=models.CharField(blank=True, default='', max_length=150, verbose_name='other school'),
        ),
        migrations.AlterField(
            model_name='subject',
            name='age_groups',
            field=models.ManyToManyField(blank=True, related_name='subjects', to='leprikon.AgeGroup', verbose_name='age groups'),
        ),
        migrations.AddField(
            model_name='subject',
            name='target_groups',
            field=models.ManyToManyField(blank=True, related_name='subjects', to='leprikon.TargetGroup', verbose_name='target groups'),
        ),
        migrations.AddField(
            model_name='subjectregistration',
            name='target_group',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='+', to='leprikon.TargetGroup', verbose_name='target group'),
        ),
    ]
