from itertools import chain
from django.db import migrations, models
import django.db.models.deletion
import leprikon.models.fields


from leprikon import migrations as leprikon_migrations


def migrate_cms_apps(apps, schema_editor):
    Page = apps.get_model("cms", "Page")

    Page.objects.filter(application_urls="LeprikonSubjectTypeApp").update(application_urls="LeprikonActivityTypeApp")


class Migration(migrations.Migration):

    dependencies = [
        ("cms", "0022_auto_20180620_1551"),
        ("leprikon", "0087_alter_schoolyear_year"),
    ]

    operations = (
        [
            migrations.RunPython(migrate_cms_apps, migrations.RunPython.noop),
            migrations.RenameModel(old_name="SubjectType", new_name="ActivityType"),
            migrations.AlterModelOptions(
                name="activitytype",
                options={
                    "ordering": ("order",),
                    "verbose_name": "activity type",
                    "verbose_name_plural": "activity types",
                },
            ),
            migrations.RenameField(
                model_name="activitytype",
                old_name="subject_type",
                new_name="model",
            ),
            migrations.AlterField(
                model_name="activitytype",
                name="model",
                field=models.CharField(
                    choices=[("course", "course"), ("event", "fixed time event"), ("orderable", "orderable event")],
                    max_length=10,
                    verbose_name="data model",
                ),
            ),
            migrations.CreateModel(
                name="ActivityTypeTexts",
                fields=[],
                options={
                    "verbose_name": "texts",
                    "verbose_name_plural": "texts",
                    "proxy": True,
                    "indexes": [],
                    "constraints": [],
                },
                bases=("leprikon.activitytype",),
            ),
            migrations.CreateModel(
                name="ActivityTypePrintSetups",
                fields=[],
                options={
                    "verbose_name": "print setups",
                    "verbose_name_plural": "print setups",
                    "proxy": True,
                    "indexes": [],
                    "constraints": [],
                },
                bases=("leprikon.activitytype",),
            ),
            migrations.AlterField(
                model_name="courselistplugin",
                name="course_types",
                field=models.ManyToManyField(
                    blank=True,
                    help_text="Keep empty to skip searching by course types.",
                    limit_choices_to={"activity_type": "course"},
                    related_name="+",
                    to="leprikon.ActivityType",
                    verbose_name="course types",
                ),
            ),
            migrations.AlterField(
                model_name="eventlistplugin",
                name="event_types",
                field=models.ManyToManyField(
                    blank=True,
                    help_text="Keep empty to skip searching by event types.",
                    limit_choices_to={"activity_type": "event"},
                    related_name="+",
                    to="leprikon.ActivityType",
                    verbose_name="event types",
                ),
            ),
            migrations.AlterField(
                model_name="filteredcourselistplugin",
                name="course_types",
                field=models.ManyToManyField(
                    limit_choices_to={"activity_type": "course"},
                    related_name="+",
                    to="leprikon.ActivityType",
                    verbose_name="course types",
                ),
            ),
            migrations.AlterField(
                model_name="filteredeventlistplugin",
                name="event_types",
                field=models.ManyToManyField(
                    limit_choices_to={"activity_type": "event"},
                    related_name="+",
                    to="leprikon.ActivityType",
                    verbose_name="event types",
                ),
            ),
            migrations.AlterField(
                model_name="filteredorderablelistplugin",
                name="event_types",
                field=models.ManyToManyField(
                    limit_choices_to={"activity_type": "orderable"},
                    related_name="+",
                    to="leprikon.ActivityType",
                    verbose_name="event types",
                ),
            ),
            migrations.AlterField(
                model_name="orderablelistplugin",
                name="event_types",
                field=models.ManyToManyField(
                    blank=True,
                    help_text="Keep empty to skip searching by event types.",
                    limit_choices_to={"activity_type": "orderable"},
                    related_name="+",
                    to="leprikon.ActivityType",
                    verbose_name="event types",
                ),
            ),
        ]
        + [
            migrations.RenameField(model_name=model_name, old_name="subject_type", new_name="activity_type")
            for model_name in ["registrationlink", "subject", "subjecttypeattachment"]
        ]
        + [
            migrations.RenameModel(old_name="SubjectTypeAttachment", new_name="ActivityTypeAttachment"),
            migrations.RenameModel(old_name="SubjectGroup", new_name="ActivityGroup"),
            migrations.RenameField(model_name="activitygroup", old_name="subject_types", new_name="activity_types"),
        ]
        + [
            migrations.RenameField(model_name=model_name, old_name="subject_ptr", new_name="activity_ptr")
            for model_name in ["course", "event", "orderable"]
        ]
        + [
            leprikon_migrations.AlterModelBases(name=model_name, bases=(models.Model,))
            for model_name in ["course", "event", "orderable"]
        ]
        + [
            migrations.RenameModel(old_name="Subject", new_name="Activity"),
        ]
        + [
            leprikon_migrations.AlterModelBases(name=model_name, bases=("leprikon.activity",))
            for model_name in ["course", "event", "orderable"]
        ]
        + [
            migrations.AlterModelOptions(
                name="activity",
                options={"ordering": ("code", "name"), "verbose_name": "activity", "verbose_name_plural": "activities"},
            ),
            migrations.RenameModel(old_name="SubjectAttachment", new_name="ActivityAttachment"),
            migrations.RenameModel(old_name="SubjectTime", new_name="ActivityTime"),
            migrations.AlterModelOptions(
                name="activitytime",
                options={"ordering": ("days_of_week", "start"), "verbose_name": "time", "verbose_name_plural": "times"},
            ),
            migrations.RenameModel(old_name="SubjectVariant", new_name="ActivityVariant"),
            migrations.AlterModelOptions(
                name="activityvariant",
                options={
                    "ordering": ("activity", "order"),
                    "verbose_name": "price and registering variant",
                    "verbose_name_plural": "price and registering variants",
                },
            ),
            migrations.RenameField(
                model_name="subjectregistration",
                old_name="subject_variant",
                new_name="activity_variant",
            ),
            migrations.RenameModel(old_name="SubjectRegistrationParticipant", new_name="RegistrationParticipant"),
            migrations.RenameModel(old_name="SubjectRegistrationGroup", new_name="RegistrationGroup"),
            migrations.RenameModel(old_name="SubjectRegistrationGroupMember", new_name="RegistrationGroupMember"),
            migrations.RenameModel(old_name="SubjectRegistrationBillingInfo", new_name="RegistrationBillingInfo"),
            migrations.RenameModel(old_name="SubjectPayment", new_name="Payment"),
            migrations.RenameModel(old_name="SubjectReceivedPayment", new_name="ReceivedPayment"),
            migrations.RenameModel(old_name="SubjectReturnedPayment", new_name="ReturnedPayment"),
        ]
        + [
            migrations.RenameField(
                model_name=model_name, old_name="subjectregistration_ptr", new_name="registration_ptr"
            )
            for model_name in ["courseregistration", "eventregistration", "orderableregistration"]
        ]
        + [
            leprikon_migrations.AlterModelBases(name=model_name, bases=(models.Model,))
            for model_name in ["courseregistration", "eventregistration", "orderableregistration"]
        ]
        + [
            migrations.RenameModel(old_name="SubjectRegistration", new_name="Registration"),
        ]
        + [
            leprikon_migrations.AlterModelBases(name=model_name, bases=("leprikon.registration",))
            for model_name in ["courseregistration", "eventregistration", "orderableregistration"]
        ]
        + [
            migrations.RenameField(model_name=model_name, old_name="subject", new_name="activity")
            for model_name in [
                "activityvariant",
                "activityattachment",
                "activitytime",
                "journal",
                "leaderlistplugin",
                "registration",
            ]
        ]
        + [
            migrations.RenameField(
                model_name="registrationlink", old_name="subject_variants", new_name="activity_variants"
            ),
            migrations.AlterModelOptions(
                name="activitygroup",
                options={
                    "ordering": ("order",),
                    "verbose_name": "activity group",
                    "verbose_name_plural": "activity groups",
                },
            ),
            migrations.AlterField(
                model_name="activity",
                name="activity_type",
                field=models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="activities",
                    to="leprikon.activitytype",
                    verbose_name="activity type",
                ),
            ),
            migrations.AlterField(
                model_name="activity",
                name="age_groups",
                field=models.ManyToManyField(
                    related_name="activities", to="leprikon.AgeGroup", verbose_name="age groups"
                ),
            ),
            migrations.AlterField(
                model_name="activity",
                name="bill_print_setup",
                field=models.ForeignKey(
                    blank=True,
                    help_text="Only use to set value specific for this activity.",
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="+",
                    to="leprikon.printsetup",
                    verbose_name="payment print setup",
                ),
            ),
            migrations.AlterField(
                model_name="activity",
                name="decision_print_setup",
                field=models.ForeignKey(
                    blank=True,
                    help_text="Only use to set value specific for this activity.",
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="+",
                    to="leprikon.printsetup",
                    verbose_name="registration print setup",
                ),
            ),
            migrations.AlterField(
                model_name="activity",
                name="department",
                field=models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="activities",
                    to="leprikon.department",
                    verbose_name="department",
                ),
            ),
            migrations.AlterField(
                model_name="activity",
                name="groups",
                field=models.ManyToManyField(
                    blank=True, related_name="activities", to="leprikon.ActivityGroup", verbose_name="groups"
                ),
            ),
            migrations.AlterField(
                model_name="activity",
                name="leaders",
                field=models.ManyToManyField(
                    blank=True, related_name="activities", to="leprikon.Leader", verbose_name="leaders"
                ),
            ),
            migrations.AlterField(
                model_name="activity",
                name="organization",
                field=models.ForeignKey(
                    blank=True,
                    help_text="Only use to set value specific for this activity.",
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="+",
                    to="leprikon.organization",
                    verbose_name="organization",
                ),
            ),
            migrations.AlterField(
                model_name="activity",
                name="place",
                field=models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="activities",
                    to="leprikon.place",
                    verbose_name="place",
                ),
            ),
            migrations.AlterField(
                model_name="activity",
                name="pr_print_setup",
                field=models.ForeignKey(
                    blank=True,
                    help_text="Only use to set value specific for this activity.",
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="+",
                    to="leprikon.printsetup",
                    verbose_name="payment request print setup",
                ),
            ),
            migrations.AlterField(
                model_name="activity",
                name="reg_print_setup",
                field=models.ForeignKey(
                    blank=True,
                    help_text="Only use to set value specific for this activity.",
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="+",
                    to="leprikon.printsetup",
                    verbose_name="registration print setup",
                ),
            ),
            migrations.AlterField(
                model_name="activity",
                name="registration_agreements",
                field=models.ManyToManyField(
                    blank=True,
                    help_text="Add additional legal agreements specific for this activity.",
                    related_name="_leprikon_activity_registration_agreements_+",
                    to="leprikon.Agreement",
                    verbose_name="additional legal agreements",
                ),
            ),
            migrations.AlterField(
                model_name="activity",
                name="school_year",
                field=models.ForeignKey(
                    editable=False,
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="activities",
                    to="leprikon.schoolyear",
                    verbose_name="school year",
                ),
            ),
            migrations.AlterField(
                model_name="activity",
                name="target_groups",
                field=models.ManyToManyField(
                    related_name="activities", to="leprikon.TargetGroup", verbose_name="target groups"
                ),
            ),
            migrations.AlterField(
                model_name="activityattachment",
                name="activity",
                field=models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="attachments",
                    to="leprikon.activity",
                    verbose_name="activity",
                ),
            ),
            migrations.AlterField(
                model_name="activitygroup",
                name="activity_types",
                field=models.ManyToManyField(
                    related_name="groups", to="leprikon.ActivityType", verbose_name="activity type"
                ),
            ),
            migrations.AlterField(
                model_name="activitytypeattachment",
                name="activity_type",
                field=models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="attachments",
                    to="leprikon.activitytype",
                    verbose_name="activity type",
                ),
            ),
            migrations.AlterField(
                model_name="activityvariant",
                name="activity",
                field=models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="variants",
                    to="leprikon.activity",
                    verbose_name="activity",
                ),
            ),
            migrations.AlterField(
                model_name="activityvariant",
                name="age_groups",
                field=models.ManyToManyField(
                    related_name="activity_variants", to="leprikon.AgeGroup", verbose_name="age groups"
                ),
            ),
            migrations.AlterField(
                model_name="activityvariant",
                name="target_groups",
                field=models.ManyToManyField(
                    related_name="activity_variants", to="leprikon.TargetGroup", verbose_name="target groups"
                ),
            ),
            migrations.AlterField(
                model_name="journal",
                name="activity",
                field=models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="journals",
                    to="leprikon.activity",
                    verbose_name="activity",
                ),
            ),
            migrations.AlterField(
                model_name="leaderlistplugin",
                name="activity",
                field=models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="+",
                    to="leprikon.activity",
                    verbose_name="activity",
                ),
            ),
            migrations.AlterField(
                model_name="registration",
                name="activity",
                field=models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="registrations",
                    to="leprikon.activity",
                    verbose_name="activity",
                ),
            ),
            migrations.AlterField(
                model_name="registrationlink",
                name="activity_variants",
                field=models.ManyToManyField(
                    related_name="registration_links", to="leprikon.ActivityVariant", verbose_name="activities"
                ),
            ),
        ]
    )
