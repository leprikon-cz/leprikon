from datetime import date, datetime, time, timedelta

import pytest

from leprikon.models.fields import DayOfWeek, DaysOfWeek
from leprikon.utils.calendar import (
    SimpleEvent,
    TimeSlot,
    TimeSlots,
    WeeklyTime,
    WeeklyTimes,
    apply_preparation_and_recovery_times,
    flatten_events,
    get_time_slots_by_weekly_times,
    get_unavailable_time_slots,
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


def hour_to_slot(hour_start: int, hour_end: int, day_start: int = 1, day_end: int = 1) -> TimeSlot:
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
        hour_to_slot(9, 12, 1, 1),
        hour_to_slot(9, 0, 2, 3),
        hour_to_slot(10, 0, 3, 4),
        hour_to_slot(9, 12, 7, 7),
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
    ) == [hour_to_slot(0, 0, 1, 3)]


def test_time_slot_sub() -> None:
    # overlapping start
    assert hour_to_slot(4, 10) - hour_to_slot(2, 8) == TimeSlots([hour_to_slot(8, 10)])
    # overlapping end
    assert hour_to_slot(2, 8) - hour_to_slot(4, 10) == TimeSlots([hour_to_slot(2, 4)])
    # split
    assert hour_to_slot(1, 10) - hour_to_slot(2, 8) == TimeSlots([hour_to_slot(1, 2), hour_to_slot(8, 10)])
    # remove
    assert hour_to_slot(2, 8) - hour_to_slot(1, 10) == TimeSlots()
    # keep
    assert hour_to_slot(2, 8) - hour_to_slot(10, 12) == TimeSlots([hour_to_slot(2, 8)])
    # touching
    assert hour_to_slot(2, 8) - hour_to_slot(8, 10) == TimeSlots([hour_to_slot(2, 8)])
    assert hour_to_slot(8, 10) - hour_to_slot(2, 8) == TimeSlots([hour_to_slot(8, 10)])

    # timeslots
    assert TimeSlots([hour_to_slot(1, 3), hour_to_slot(4, 6)]) - hour_to_slot(2, 5) == TimeSlots(
        [hour_to_slot(1, 2), hour_to_slot(5, 6)]
    )
    assert hour_to_slot(2, 8) - TimeSlots([hour_to_slot(1, 3), hour_to_slot(4, 6), hour_to_slot(7, 10)]) == TimeSlots(
        [hour_to_slot(3, 4), hour_to_slot(6, 7)]
    )
    assert TimeSlots([hour_to_slot(1, 4), hour_to_slot(6, 10)]) - TimeSlots(
        [hour_to_slot(2, 3), hour_to_slot(5, 6), hour_to_slot(7, 10)]
    ) == TimeSlots([hour_to_slot(1, 2), hour_to_slot(3, 4), hour_to_slot(6, 7)])


def test_get_unavailable_time_slots() -> None:
    assert get_unavailable_time_slots(
        available_time_slots=TimeSlots(
            [
                hour_to_slot(8, 20, 1),
                hour_to_slot(9, 12, 2, 2),
                hour_to_slot(20, 9, 2, 3),
            ]
        ),
        start_date=date(2025, 7, 1),
        end_date=date(2025, 7, 3),
    ) == [
        hour_to_slot(0, 8, 1, 1),
        hour_to_slot(20, 9, 1, 2),
        hour_to_slot(12, 20, 2, 2),
        hour_to_slot(9, 0, 3, 4),
    ]


def test_time_slots_init() -> None:
    # one inside another
    assert TimeSlots([hour_to_slot(1, 10), hour_to_slot(5, 6)]) == TimeSlots([hour_to_slot(1, 10)])
    assert TimeSlots([hour_to_slot(5, 6), hour_to_slot(1, 10)]) == TimeSlots([hour_to_slot(1, 10)])
    # touching
    assert TimeSlots([hour_to_slot(1, 5), hour_to_slot(5, 10)]) == TimeSlots([hour_to_slot(1, 10)])
    # overlapping with wrong order
    assert TimeSlots([hour_to_slot(4, 10), hour_to_slot(1, 6)]) == TimeSlots([hour_to_slot(1, 10)])
    # not ordered
    assert TimeSlots([hour_to_slot(6, 10), hour_to_slot(1, 4)]) == TimeSlots([hour_to_slot(1, 4), hour_to_slot(6, 10)])
    # duplicate
    assert TimeSlots([hour_to_slot(2, 8), hour_to_slot(2, 8)]) == TimeSlots([hour_to_slot(2, 8)])


@pytest.mark.parametrize(
    "tss_a, tss_b, expected_result",
    [
        (
            TimeSlots([hour_to_slot(9, 12), hour_to_slot(13, 15)]),
            TimeSlots([hour_to_slot(10, 14)]),
            TimeSlots([hour_to_slot(10, 12), hour_to_slot(13, 14)]),
        )
    ],
)
def test_time_slots_and(tss_a: TimeSlots, tss_b: TimeSlots, expected_result: TimeSlots) -> None:
    assert tss_a & tss_b == expected_result


@pytest.mark.parametrize(
    "tss_a, tss_b, expected_result",
    [
        (
            TimeSlots([hour_to_slot(9, 12), hour_to_slot(13, 15)]),
            TimeSlots([hour_to_slot(10, 14), hour_to_slot(16, 18)]),
            TimeSlots([hour_to_slot(9, 15), hour_to_slot(16, 18)]),
        )
    ],
)
def test_time_slots_or(tss_a, tss_b, expected_result) -> None:
    assert tss_a | tss_b == expected_result


def test_flatten_events() -> None:
    events: list[SimpleEvent] = [
        # first
        SimpleEvent(
            timeslot=hour_to_slot(9, 12),
            resource_groups=[{1}],
        ),
        # same start
        SimpleEvent(
            timeslot=hour_to_slot(9, 13),
            resource_groups=[{2}],
        ),
        # inside other
        SimpleEvent(
            timeslot=hour_to_slot(10, 11),
            resource_groups=[{3}],
        ),
        # touching other, same end
        SimpleEvent(
            timeslot=hour_to_slot(11, 13),
            resource_groups=[{4}],
        ),
        # not overlaping
        SimpleEvent(
            timeslot=hour_to_slot(14, 15),
            resource_groups=[{5}],
        ),
    ]
    flattened_events = list(flatten_events(events))
    assert flattened_events == [
        SimpleEvent(
            timeslot=hour_to_slot(9, 10),
            resource_groups=[{1}, {2}],
        ),
        SimpleEvent(
            timeslot=hour_to_slot(10, 11),
            resource_groups=[{1}, {2}, {3}],
        ),
        SimpleEvent(
            timeslot=hour_to_slot(11, 12),
            resource_groups=[{1}, {2}, {4}],
        ),
        SimpleEvent(
            timeslot=hour_to_slot(12, 13),
            resource_groups=[{2}, {4}],
        ),
        SimpleEvent(
            timeslot=hour_to_slot(14, 15),
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
            timeslot=hour_to_slot(9, 10),
            resource_groups=resource_groups,
        ).has_resolvable_resource_groups()
        == expected_result
    )


def test_apply_preparation_and_recovery_time():
    assert apply_preparation_and_recovery_times(
        TimeSlots([hour_to_slot(9, 10), hour_to_slot(12, 13)]),
        timedelta(hours=1),
        timedelta(hours=1),
    ) == [hour_to_slot(8, 14)]
