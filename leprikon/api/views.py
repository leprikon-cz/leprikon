from datetime import date

from django.contrib.auth import authenticate, login, logout
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import AuthenticationFailed, NotFound
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from ..models.journals import Journal
from ..models.schoolyear import SchoolYear
from .serializers import (
    CredentialsSerializer,
    SchoolYearSerializer,
    SetSchoolYearSerializer,
    SubjectRegistrationParticipantSerializer,
    UserSerializer,
)


class JournalViewSet(viewsets.GenericViewSet):
    def get_queryset(self):
        if self.request.user.is_staff:
            return Journal.objects.all()
        return Journal.objects.filter(leaders=self.request.leader)

    @extend_schema(
        responses={200: SubjectRegistrationParticipantSerializer(many=True)},
        methods=["get"],
        parameters=[OpenApiParameter(name="date", type=OpenApiTypes.DATE)],
    )
    @action(detail=True, methods=["get"], permission_classes=[IsAuthenticated])
    def participants(self, request, pk: str):
        journal: Journal = self.get_object()
        try:
            d = date.fromisoformat(request.GET["date"])
        except (KeyError, ValueError):
            d = date.today()

        participants = journal.get_valid_participants(d)

        return Response(SubjectRegistrationParticipantSerializer(participants, many=True).data)


class SchoolYearViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = SchoolYearSerializer

    def get_queryset(self):
        if self.request.user and self.request.user.is_staff:
            return SchoolYear.objects.all()
        return SchoolYear.objects.filter(active=True)

    @extend_schema(request=None, responses={200: SchoolYearSerializer}, methods=["get"])
    @extend_schema(request=SetSchoolYearSerializer, responses={204: None}, methods=["post"])
    @action(detail=False, methods=["get", "post"])
    def current(self, request):
        if request.method == "GET":
            return Response(SchoolYearSerializer(request.school_year).data)

        if request.method == "POST":
            serializer = SetSchoolYearSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            try:
                request._request.school_year = self.get_queryset().get(pk=serializer.validated_data["id"])
                return Response(status=status.HTTP_204_NO_CONTENT)
            except SchoolYear.DoesNotExist:
                raise NotFound


class UserViewSet(viewsets.ViewSet):
    @extend_schema(operation_id="user_login", request=CredentialsSerializer, responses={200: UserSerializer})
    @action(detail=False, methods=["post"])
    def login(self, request):
        serializer = CredentialsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if user := authenticate(request, **serializer.validated_data):
            login(request, user)
            return Response(UserSerializer(user).data)
        else:
            raise AuthenticationFailed()

    @extend_schema(responses={200: UserSerializer})
    @action(detail=False, methods=["get"], permission_classes=[IsAuthenticated])
    def me(self, request: Request) -> Response:
        return Response(UserSerializer(request.user).data)

    @extend_schema(operation_id="user_logout", responses={204: None})
    @action(
        detail=False,
        methods=["post"],
        permission_classes=[IsAuthenticated],
    )
    def logout(self, request: Request) -> Response:
        logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)
