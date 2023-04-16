from django.contrib.auth import get_user_model
from rest_framework import serializers

from leprikon.models.schoolyear import SchoolYear
from leprikon.models.subjects import SubjectRegistrationParticipant


class SubjectRegistrationParticipantSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubjectRegistrationParticipant
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
