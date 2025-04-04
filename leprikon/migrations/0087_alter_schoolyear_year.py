# Generated by Django 3.2.25 on 2025-04-04 06:41

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('leprikon', '0086_attachment_events'),
    ]

    operations = [
        migrations.AlterField(
            model_name='schoolyear',
            name='year',
            field=models.IntegerField(help_text='Only the first of the two years.', unique=True, validators=[django.core.validators.MinValueValidator(2000), django.core.validators.MaxValueValidator(3000)], verbose_name='year'),
        ),
    ]
