from django.contrib.auth import get_user_model
from rest_framework import serializers

from leprikon.models.activities import Activity, CalendarEvent, RegistrationParticipant
from leprikon.models.calendar import CalendarExport
from leprikon.models.schoolyear import SchoolYear


class RegistrationParticipantSerializer(serializers.ModelSerializer):
    class Meta:
        model = RegistrationParticipant
        fields = ["id", "label"]


class SchoolYearSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = SchoolYear
        fields = ["id", "name", "year", "active"]


class SetSchoolYearSerializer(serializers.Serializer):
    id = serializers.IntegerField()


class CredentialsSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField()


class UserSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = get_user_model()
        fields = ["username", "first_name", "last_name", "email"]


class ActivitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Activity
        fields = ["id", "name"]


class GetResourceConflictSerializer(serializers.Serializer):
    start = serializers.DateTimeField()
    end = serializers.DateTimeField()


class ResourceConflictSerializer(serializers.Serializer):
    id = serializers.CharField()
    start = serializers.DateTimeField()
    end = serializers.DateTimeField()
    title = serializers.CharField()
    allDay = serializers.BooleanField()
    color = serializers.CharField()


class CalendarEventSerializer(serializers.ModelSerializer):

    class Meta:
        model = CalendarEvent
        fields = [
            "id",
            "name",
            "start",
            "end",
        ]


class CalendarExportSerializer(serializers.ModelSerializer):
    class Meta:
        model = CalendarExport
        fields = "__all__"
