from datetime import date, datetime, time, timedelta
from itertools import chain
from typing import Iterator

from django.contrib.auth import authenticate, login, logout
from django.http import HttpResponse
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import AuthenticationFailed, NotFound
from rest_framework.permissions import DjangoModelPermissions, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from leprikon.conf import settings
from leprikon.models.calendar import CalendarExport
from leprikon.utils.calendar import TimeSlot, end_time_format, start_time_format

from ..models.activities import ActivityVariant, CalendarEvent
from ..models.journals import Journal
from ..models.schoolyear import SchoolYear
from .serializers import (
    ActivitySerializer,
    BusinessHoursSerializer,
    CalendarEventSerializer,
    CalendarExportSerializer,
    CredentialsSerializer,
    GetBusinessHoursSerializer,
    GetUnavailableDatesSerializer,
    RegistrationParticipantSerializer,
    SchoolYearSerializer,
    SetSchoolYearSerializer,
    UnavailableDateSerializer,
    UserSerializer,
)


class JournalViewSet(viewsets.GenericViewSet):
    def get_queryset(self):
        if self.request.user.is_staff:
            return Journal.objects.all()
        return Journal.objects.filter(leaders=self.request.leader)

    @extend_schema(
        responses={200: RegistrationParticipantSerializer(many=True)},
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

        return Response(RegistrationParticipantSerializer(participants, many=True).data)


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


class ActivityViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ActivitySerializer
    permission_classes = [IsAuthenticated]
    queryset = ActivityVariant.objects.all()

    def get_queryset(self):
        queryset = self.queryset.filter(activity__school_year=self.request.school_year)
        if not self.request.user.is_staff:
            queryset = queryset.filter(activity__public=True)
        return queryset

    def get_object(self) -> ActivityVariant:
        """Override get_object() type, which is guessed to be Never"""
        return super().get_object()

    @extend_schema(
        operation_id="unavailable_dates",
        request=None,
        responses={200: UnavailableDateSerializer(many=True)},
        methods=["get"],
        parameters=[
            OpenApiParameter(name="start", type=OpenApiTypes.DATETIME),
            OpenApiParameter(name="end", type=OpenApiTypes.DATETIME),
        ],
    )
    @action(detail=True, permission_classes=[IsAuthenticated])
    def unavailable_dates(self, request: Request, pk: str):
        """
        Returns a list of full day calendar events for days when the activity variant is not available.
        """
        activity_variant: ActivityVariant = self.get_object()
        input_serializer = GetUnavailableDatesSerializer(data=request.query_params)
        input_serializer.is_valid(raise_exception=True)
        start_date: date = input_serializer.validated_data["start"].date()
        end_date: date = input_serializer.validated_data["end"].date() - timedelta(days=1)
        available_timeslots = activity_variant.get_available_timeslots(
            start_date=start_date,
            end_date=end_date,
        )

        def date_range(start_date: date, end_date: date) -> Iterator[date]:
            while start_date <= end_date:
                yield start_date
                start_date += timedelta(days=1)

        available_dates = set(
            chain.from_iterable(
                date_range(time_slot.start.date(), time_slot.end.date())
                for time_slot in available_timeslots
                if time_slot.duration >= activity_variant.activity.orderable.duration
            )
        )

        unavailable_timeslots = [
            dict(
                id=str(d),
                start=d,
                allDay=True,
                color=settings.LEPRIKON_API_UNAVAILABLE_DATE_COLOR,
                display="background",
            )
            for d in date_range(start_date, end_date)
            if d not in available_dates
        ]

        return Response(
            UnavailableDateSerializer(
                unavailable_timeslots,
                many=True,
            ).data
        )

    @extend_schema(
        operation_id="business_hours",
        request=None,
        responses={200: BusinessHoursSerializer(many=True)},
        methods=["get"],
        parameters=[OpenApiParameter(name="date", type=OpenApiTypes.DATE)],
    )
    @action(
        detail=True,
        permission_classes=[IsAuthenticated],
    )
    def business_hours(self, request: Request, pk: str):
        """
        Returns a list of calendar events that use the same resources as the activity variant.
        """
        activity_variant: ActivityVariant = self.get_object()
        input_serializer = GetBusinessHoursSerializer(data=request.query_params)
        input_serializer.is_valid(raise_exception=True)

        def split_multidate_timeslot(timeslot: TimeSlot) -> Iterator[TimeSlot]:
            while timeslot.start.date() != timeslot.end.date():
                next_date = timeslot.start.date() + timedelta(days=1)
                midnight = datetime.combine(next_date, time(0))
                yield TimeSlot(start=timeslot.start, end=midnight)
                timeslot.start = midnight
            if timeslot.start < timeslot.end:
                yield timeslot

        business_hours = [
            dict(
                days_of_week=[timeslot.start.isoweekday() % 7],
                start_time=start_time_format(timeslot.start.time()),
                end_time=end_time_format(timeslot.end.time()),
            )
            for raw_timeslot in activity_variant.get_available_timeslots(
                input_serializer.validated_data["start"],
                input_serializer.validated_data["end"] - timedelta(days=1),
            )
            for timeslot in split_multidate_timeslot(raw_timeslot)
        ]

        return Response(
            BusinessHoursSerializer(
                business_hours
                or [
                    dict(
                        days_of_week=[],
                        start_time=time(0),
                        end_time=time(0),
                    )
                ],
                many=True,
            ).data
        )


class CalendarEventViewSet(viewsets.ModelViewSet):
    serializer_class = CalendarEventSerializer
    permission_classes = [DjangoModelPermissions]

    def get_queryset(self):
        return CalendarEvent.objects.all()


class CalendarExportViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CalendarExportSerializer
    permission_classes = [DjangoModelPermissions]

    def get_queryset(self):
        return CalendarExport.objects.all()

    @extend_schema(operation_id="calendar_export_ical", responses={200: str})
    @action(detail=True, methods=["get"], permission_classes=[])
    def ical(self, request: Request, pk: str):
        calendar_export: CalendarExport = self.get_object()
        return HttpResponse(
            calendar_export.get_ical(),
            content_type="text/calendar",
            headers={"Content-Disposition": f'inline; filename="calendar-{calendar_export.id}.ics"'},
        )
