# -*- coding: utf-8 -*-
# Generated by Django 1.11.24 on 2019-12-01 19:04
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion
import leprikon.models.fields
import localflavor.generic.models


def migrate_organization(apps, schema_editor):
    Organization = apps.get_model("leprikon", "Organization")
    LeprikonSite = apps.get_model("leprikon", "LeprikonSite")

    for leprikon_site in LeprikonSite.objects.all():
        leprikon_site.organization = Organization.objects.create(
            name=leprikon_site.company_name or leprikon_site.name,
            street=leprikon_site.street,
            city=leprikon_site.city,
            postal_code=leprikon_site.postal_code,
            email=leprikon_site.email,
            phone=leprikon_site.phone,
            company_num=leprikon_site.company_num,
            vat_number=leprikon_site.vat_number,
            iban=leprikon_site.iban,
            bic=leprikon_site.bic,
        )
        leprikon_site.save()


class Migration(migrations.Migration):

    dependencies = [
        ("leprikon", "0037_message_sender"),
    ]

    operations = [
        migrations.CreateModel(
            name="Organization",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=150, verbose_name="organization name")),
                ("street", models.CharField(blank=True, max_length=150, null=True, verbose_name="street")),
                ("city", models.CharField(blank=True, max_length=150, null=True, verbose_name="city")),
                (
                    "postal_code",
                    leprikon.models.fields.PostalCodeField(blank=True, null=True, verbose_name="postal code"),
                ),
                (
                    "email",
                    leprikon.models.fields.EmailField(
                        blank=True, max_length=254, null=True, verbose_name="email address"
                    ),
                ),
                ("phone", models.CharField(blank=True, max_length=30, null=True, verbose_name="phone")),
                ("company_num", models.CharField(blank=True, max_length=8, null=True, verbose_name="company number")),
                ("vat_number", models.CharField(blank=True, max_length=10, null=True, verbose_name="VAT number")),
                (
                    "iban",
                    localflavor.generic.models.IBANField(
                        blank=True,
                        include_countries=None,
                        max_length=34,
                        null=True,
                        use_nordea_extensions=False,
                        verbose_name="IBAN",
                    ),
                ),
                (
                    "bic",
                    localflavor.generic.models.BICField(
                        blank=True, max_length=11, null=True, verbose_name="BIC (SWIFT)"
                    ),
                ),
            ],
            options={
                "verbose_name": "organization",
                "verbose_name_plural": "organizations",
            },
        ),
        migrations.AddField(
            model_name="leprikonsite",
            name="organization",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="+",
                to="leprikon.Organization",
                verbose_name="default organization",
            ),
        ),
        migrations.AddField(
            model_name="subject",
            name="organization",
            field=models.ForeignKey(
                blank=True,
                help_text="Only use to set value specific for this subject.",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="+",
                to="leprikon.Organization",
                verbose_name="organization",
            ),
        ),
        migrations.AddField(
            model_name="subjecttype",
            name="organization",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="+",
                to="leprikon.Organization",
                verbose_name="organization",
            ),
        ),
        migrations.RunPython(migrate_organization),
        migrations.RemoveField(
            model_name="leprikonsite",
            name="bic",
        ),
        migrations.RemoveField(
            model_name="leprikonsite",
            name="city",
        ),
        migrations.RemoveField(
            model_name="leprikonsite",
            name="company_name",
        ),
        migrations.RemoveField(
            model_name="leprikonsite",
            name="company_num",
        ),
        migrations.RemoveField(
            model_name="leprikonsite",
            name="email",
        ),
        migrations.RemoveField(
            model_name="leprikonsite",
            name="iban",
        ),
        migrations.RemoveField(
            model_name="leprikonsite",
            name="phone",
        ),
        migrations.RemoveField(
            model_name="leprikonsite",
            name="postal_code",
        ),
        migrations.RemoveField(
            model_name="leprikonsite",
            name="street",
        ),
        migrations.RemoveField(
            model_name="leprikonsite",
            name="vat_number",
        ),
        migrations.AlterField(
            model_name="leprikonsite",
            name="bill_print_setup",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="+",
                to="leprikon.PrintSetup",
                verbose_name="default bill print setup",
            ),
        ),
        migrations.AlterField(
            model_name="leprikonsite",
            name="reg_print_setup",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="+",
                to="leprikon.PrintSetup",
                verbose_name="default registration print setup",
            ),
        ),
        migrations.AlterField(
            model_name="leprikonsite",
            name="registration_agreements",
            field=models.ManyToManyField(
                blank=True,
                help_text="Add legal agreements for the registration form.",
                related_name="+",
                to="leprikon.Agreement",
                verbose_name="default registration agreements",
            ),
        ),
        migrations.AlterField(
            model_name="subject",
            name="bill_print_setup",
            field=models.ForeignKey(
                blank=True,
                help_text="Only use to set value specific for this subject.",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="+",
                to="leprikon.PrintSetup",
                verbose_name="payment print setup",
            ),
        ),
        migrations.AlterField(
            model_name="subject",
            name="reg_print_setup",
            field=models.ForeignKey(
                blank=True,
                help_text="Only use to set value specific for this subject.",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="+",
                to="leprikon.PrintSetup",
                verbose_name="registration print setup",
            ),
        ),
    ]
