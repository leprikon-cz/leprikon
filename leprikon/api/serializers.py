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


class GetUnavailableDatesSerializer(serializers.Serializer):
    start = serializers.DateTimeField()
    end = serializers.DateTimeField()


class UnavailableDateSerializer(serializers.Serializer):
    id = serializers.CharField()
    start = serializers.DateField()
    color = serializers.CharField()
    display = serializers.CharField()


class GetBusinessHoursSerializer(serializers.Serializer):
    start = serializers.DateField()
    end = serializers.DateField()


class BusinessHoursSerializer(serializers.Serializer):
    days_of_week = serializers.ListField()
    start_time = serializers.CharField()
    end_time = serializers.CharField()


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
