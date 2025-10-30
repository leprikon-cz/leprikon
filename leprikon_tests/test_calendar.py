from datetime import date, datetime, time, timedelta

import pytest
from django.utils.timezone import is_aware, make_aware

from leprikon.models.fields import DayOfWeek, DaysOfWeek
from leprikon.utils.calendar import (
    SimpleEvent,
    TimeSlot,
    TimeSlots,
    WeeklyTime,
    WeeklyTimes,
    extend_timeslots,
    flatten_events,
    get_reverse_time_slots,
    get_time_slots_by_weekly_times,
)


@pytest.mark.parametrize(
    "wt_a, wt_b, expected_result",
    [
        # overlapping cases with no date
        (
            WeeklyTime(
                start_date=None,
                end_date=None,
                start_time=time(9),
                end_time=time(12),
                days_of_week=DaysOfWeek([DayOfWeek.MONDAY, DayOfWeek.TUESDAY]),
            ),
            WeeklyTime(
                start_date=None,
                end_date=None,
                start_time=time(10),
                end_time=time(13),
                days_of_week=DaysOfWeek([DayOfWeek.MONDAY, DayOfWeek.WEDNESDAY]),
            ),
            WeeklyTime(
                start_date=None,
                end_date=None,
                start_time=time(10),
                end_time=time(12),
                days_of_week=DaysOfWeek([DayOfWeek.MONDAY]),
            ),
        ),
        # overlapping cases with date
        (
            WeeklyTime(
                start_date=date(2025, 7, 1),
                end_date=date(2025, 7, 10),
                start_time=time(9),
                end_time=time(12),
                days_of_week=DaysOfWeek([DayOfWeek.MONDAY, DayOfWeek.TUESDAY]),
            ),
            WeeklyTime(
                start_date=date(2025, 7, 5),
                end_date=date(2025, 7, 15),
                start_time=time(9),
                end_time=time(11),
                days_of_week=DaysOfWeek([DayOfWeek.MONDAY, DayOfWeek.WEDNESDAY]),
            ),
            WeeklyTime(
                start_date=date(2025, 7, 5),
                end_date=date(2025, 7, 10),
                start_time=time(9),
                end_time=time(11),
                days_of_week=DaysOfWeek([DayOfWeek.MONDAY]),
            ),
        ),
        # overlaping cases just with some dates
        (
            WeeklyTime(
                start_date=date(2025, 7, 1),
                end_date=None,
                start_time=time(10),
                end_time=time(12),
                days_of_week=DaysOfWeek([DayOfWeek.MONDAY, DayOfWeek.TUESDAY]),
            ),
            WeeklyTime(
                start_date=None,
                end_date=date(2025, 7, 20),
                start_time=time(9),
                end_time=time(11),
                days_of_week=DaysOfWeek([DayOfWeek.MONDAY, DayOfWeek.WEDNESDAY]),
            ),
            WeeklyTime(
                start_date=date(2025, 7, 1),
                end_date=date(2025, 7, 20),
                start_time=time(10),
                end_time=time(11),
                days_of_week=DaysOfWeek([DayOfWeek.MONDAY]),
            ),
        ),
        # non-overlapping times
        (
            WeeklyTime(
                start_date=None,
                end_date=None,
                start_time=time(9),
                end_time=time(12),
                days_of_week=DaysOfWeek([DayOfWeek.MONDAY]),
            ),
            WeeklyTime(
                start_date=None,
                end_date=None,
                start_time=time(13),
                end_time=time(15),
                days_of_week=DaysOfWeek([DayOfWeek.MONDAY]),
            ),
            None,
        ),
        # non-overlaping days
        (
            WeeklyTime(
                start_date=None,
                end_date=None,
                start_time=time(9),
                end_time=time(12),
                days_of_week=DaysOfWeek([DayOfWeek.MONDAY, DayOfWeek.TUESDAY]),
            ),
            WeeklyTime(
                start_date=None,
                end_date=None,
                start_time=time(9),
                end_time=time(12),
                days_of_week=DaysOfWeek([DayOfWeek.WEDNESDAY]),
            ),
            None,
        ),
        # non-overlaping dates
        (
            WeeklyTime(
                start_date=date(2025, 7, 1),
                end_date=date(2025, 7, 10),
                start_time=time(9),
                end_time=time(12),
                days_of_week=DaysOfWeek([DayOfWeek.MONDAY]),
            ),
            WeeklyTime(
                start_date=date(2025, 7, 15),
                end_date=date(2025, 7, 20),
                start_time=time(9),
                end_time=time(12),
                days_of_week=DaysOfWeek([DayOfWeek.MONDAY]),
            ),
            None,
        ),
        (
            WeeklyTime(
                start_date=None,
                end_date=date(2025, 7, 10),
                start_time=time(9),
                end_time=time(12),
                days_of_week=DaysOfWeek([DayOfWeek.MONDAY]),
            ),
            WeeklyTime(
                start_date=date(2025, 7, 15),
                end_date=None,
                start_time=time(9),
                end_time=time(12),
                days_of_week=DaysOfWeek([DayOfWeek.MONDAY]),
            ),
            None,
        ),
    ],
)
def test_weekly_time_and(wt_a: WeeklyTime, wt_b: WeeklyTime, expected_result: WeeklyTime | None) -> None:
    assert wt_a & wt_b == expected_result


def make_slot(hour_start: int, hour_end: int, day_start: int = 1, day_end: int = 1) -> TimeSlot:
    return TimeSlot(datetime(2025, 7, day_start, hour_start, 0), datetime(2025, 7, day_end, hour_end, 0))


def test_get_time_slots_by_weekly_times() -> None:
    assert get_time_slots_by_weekly_times(
        WeeklyTimes(
            [
                WeeklyTime(
                    start_date=None,
                    end_date=None,
                    start_time=time(9),
                    end_time=time(12),
                    days_of_week=DaysOfWeek([DayOfWeek.MONDAY, DayOfWeek.TUESDAY, DayOfWeek.WEDNESDAY]),
                ),
                WeeklyTime(
                    start_date=date(2025, 7, 2),
                    end_date=date(2025, 7, 3),
                    start_time=time(10),
                    end_time=time(0),  # test EOD
                    days_of_week=DaysOfWeek([DayOfWeek.WEDNESDAY, DayOfWeek.THURSDAY]),
                ),
            ]
        ),
        date(2025, 7, 1),  # Tuesday
        date(2025, 7, 7),  # Monday
    ) == [
        make_slot(9, 12, 1, 1),
        make_slot(9, 0, 2, 3),
        make_slot(10, 0, 3, 4),
        make_slot(9, 12, 7, 7),
    ]
    assert (
        get_time_slots_by_weekly_times(
            WeeklyTimes(
                [
                    WeeklyTime(
                        start_date=date(2025, 7, 2),
                        end_date=date(2025, 7, 3),
                        start_time=time(10),
                        end_time=time(13),
                        days_of_week=DaysOfWeek([DayOfWeek.WEDNESDAY, DayOfWeek.THURSDAY]),
                    ),
                ]
            ),
            date(2025, 7, 10),
            date(2025, 7, 20),
        )
        == []
    )
    assert get_time_slots_by_weekly_times(
        WeeklyTimes.unlimited(),
        date(2025, 7, 1),
        date(2025, 7, 2),
    ) == [make_slot(0, 0, 1, 3)]


def test_timeslot_init() -> None:
    ts = TimeSlot(datetime(2025, 1, 1, 0, 0), datetime(2025, 1, 2, 0, 0))
    assert is_aware(ts.start)
    assert is_aware(ts.end)


@pytest.mark.parametrize(
    "ts, expected_result",
    [
        (TimeSlot.from_date_range(date(2025, 1, 1), date(2025, 1, 1)), "01.01.2025"),
        (TimeSlot.from_date_range(date(2025, 1, 1), date(2025, 1, 2)), "01.01.2025 - 02.01.2025"),
        (make_slot(9, 12), "01.07.2025 9:00 - 12:00"),
        (make_slot(12, 9, 1, 2), "01.07.2025 12:00 - 02.07.2025 9:00"),
    ],
)
def test_time_slot_str(ts: TimeSlot, expected_result: str, locale_cs_CZ: None) -> None:
    assert str(ts) == expected_result


def test_time_slot_from_date_range() -> None:
    ts = TimeSlot.from_date_range(date(2025, 1, 1), date(2025, 1, 2))
    assert ts.start == make_aware(datetime(2025, 1, 1, 0, 0))
    assert ts.end == make_aware(datetime(2025, 1, 3, 0, 0))


def test_time_slot_sub() -> None:
    # overlapping start
    assert make_slot(4, 10) - make_slot(2, 8) == TimeSlots([make_slot(8, 10)])
    # overlapping end
    assert make_slot(2, 8) - make_slot(4, 10) == TimeSlots([make_slot(2, 4)])
    # split
    assert make_slot(1, 10) - make_slot(2, 8) == TimeSlots([make_slot(1, 2), make_slot(8, 10)])
    # remove
    assert make_slot(2, 8) - make_slot(1, 10) == TimeSlots()
    # keep
    assert make_slot(2, 8) - make_slot(10, 12) == TimeSlots([make_slot(2, 8)])
    # touching
    assert make_slot(2, 8) - make_slot(8, 10) == TimeSlots([make_slot(2, 8)])
    assert make_slot(8, 10) - make_slot(2, 8) == TimeSlots([make_slot(8, 10)])

    # timeslots
    assert TimeSlots([make_slot(1, 3), make_slot(4, 6)]) - make_slot(2, 5) == TimeSlots(
        [make_slot(1, 2), make_slot(5, 6)]
    )
    assert make_slot(2, 8) - TimeSlots([make_slot(1, 3), make_slot(4, 6), make_slot(7, 10)]) == TimeSlots(
        [make_slot(3, 4), make_slot(6, 7)]
    )
    assert TimeSlots([make_slot(1, 4), make_slot(6, 10)]) - TimeSlots(
        [make_slot(2, 3), make_slot(5, 6), make_slot(7, 10)]
    ) == TimeSlots([make_slot(1, 2), make_slot(3, 4), make_slot(6, 7)])


def test_get_reverse_time_slots() -> None:
    assert get_reverse_time_slots(
        time_slots=TimeSlots(
            [
                make_slot(8, 20, 1),
                make_slot(9, 12, 2, 2),
                make_slot(20, 9, 2, 3),
            ]
        ),
        start_date=date(2025, 7, 1),
        end_date=date(2025, 7, 3),
    ) == [
        make_slot(0, 8, 1, 1),
        make_slot(20, 9, 1, 2),
        make_slot(12, 20, 2, 2),
        make_slot(9, 0, 3, 4),
    ]


def test_time_slots_init() -> None:
    # one inside another
    assert TimeSlots([make_slot(1, 10), make_slot(5, 6)]) == TimeSlots([make_slot(1, 10)])
    assert TimeSlots([make_slot(5, 6), make_slot(1, 10)]) == TimeSlots([make_slot(1, 10)])
    # touching
    assert TimeSlots([make_slot(1, 5), make_slot(5, 10)]) == TimeSlots([make_slot(1, 10)])
    # overlapping with wrong order
    assert TimeSlots([make_slot(4, 10), make_slot(1, 6)]) == TimeSlots([make_slot(1, 10)])
    # not ordered
    assert TimeSlots([make_slot(6, 10), make_slot(1, 4)]) == TimeSlots([make_slot(1, 4), make_slot(6, 10)])
    # duplicate
    assert TimeSlots([make_slot(2, 8), make_slot(2, 8)]) == TimeSlots([make_slot(2, 8)])


@pytest.mark.parametrize(
    "tss_a, tss_b, expected_result",
    [
        (
            TimeSlots([make_slot(9, 12), make_slot(13, 15)]),
            TimeSlots([make_slot(10, 14)]),
            TimeSlots([make_slot(10, 12), make_slot(13, 14)]),
        )
    ],
)
def test_time_slots_and(tss_a: TimeSlots, tss_b: TimeSlots, expected_result: TimeSlots) -> None:
    assert tss_a & tss_b == expected_result


@pytest.mark.parametrize(
    "tss_a, tss_b, expected_result",
    [
        (
            TimeSlots([make_slot(9, 12), make_slot(13, 15)]),
            TimeSlots([make_slot(10, 14), make_slot(16, 18)]),
            TimeSlots([make_slot(9, 15), make_slot(16, 18)]),
        )
    ],
)
def test_time_slots_or(tss_a, tss_b, expected_result) -> None:
    assert tss_a | tss_b == expected_result


def test_flatten_events() -> None:
    events: list[SimpleEvent] = [
        # first
        SimpleEvent(
            timeslot=make_slot(9, 12),
            resource_groups=[{1}],
        ),
        # same start
        SimpleEvent(
            timeslot=make_slot(9, 13),
            resource_groups=[{2}],
        ),
        # inside other
        SimpleEvent(
            timeslot=make_slot(10, 11),
            resource_groups=[{3}],
        ),
        # touching other, same end
        SimpleEvent(
            timeslot=make_slot(11, 13),
            resource_groups=[{4}],
        ),
        # not overlaping
        SimpleEvent(
            timeslot=make_slot(14, 15),
            resource_groups=[{5}],
        ),
    ]
    flattened_events = list(flatten_events(events))
    assert flattened_events == [
        SimpleEvent(
            timeslot=make_slot(9, 10),
            resource_groups=[{1}, {2}],
        ),
        SimpleEvent(
            timeslot=make_slot(10, 11),
            resource_groups=[{1}, {2}, {3}],
        ),
        SimpleEvent(
            timeslot=make_slot(11, 12),
            resource_groups=[{1}, {2}, {4}],
        ),
        SimpleEvent(
            timeslot=make_slot(12, 13),
            resource_groups=[{2}, {4}],
        ),
        SimpleEvent(
            timeslot=make_slot(14, 15),
            resource_groups=[{5}],
        ),
    ]


@pytest.mark.parametrize(
    "resource_groups, expected_result",
    [
        ([], True),
        ([{1}], True),
        ([{1}, {1}], False),
        ([{1, 2, 3}], True),
        ([{1}, {2}, {3}], True),
        ([{1, 2}, {1, 2}, {3}], True),
        ([{1, 2}, {1, 2}, {1, 2}], False),
        ([{1, 2, 3}, {1, 2}, {1}], True),
    ],
)
def test_has_resolvable_resource_groups(resource_groups: list[set[int]], expected_result: bool) -> None:
    assert (
        SimpleEvent(
            timeslot=make_slot(9, 10),
            resource_groups=resource_groups,
        ).has_resolvable_resource_groups()
        == expected_result
    )


def test_apply_preparation_and_recovery_time():
    assert extend_timeslots(
        TimeSlots([make_slot(9, 10), make_slot(14, 15)]),
        timedelta(hours=1),
        timedelta(hours=3),
    ) == [make_slot(8, 18)]
    assert extend_timeslots(
        TimeSlots([make_slot(9, 10), make_slot(15, 16)]),
        timedelta(hours=1),
        timedelta(hours=3),
    ) == [make_slot(8, 13), make_slot(14, 19)]
