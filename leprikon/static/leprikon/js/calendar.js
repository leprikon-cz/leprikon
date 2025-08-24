function initializeCalendar(
  {
    minStartDate,
    maxEndDate,
    duration,
    unavailableDatesUrl,
    businessHoursUrl,
    selectedEventTimeLabel,
    locale,
    buttonText,
  },
  selectedStart,
) {
  document.addEventListener("DOMContentLoaded", function () {
    var calendarElement = document.getElementById("event-time-calendar");
    var startDateInput = document.getElementById("id_start_date");
    var startTimeInput = document.getElementById("id_start_time");
    var selectedTimeInput = document.getElementById("selected-time-input");

    function dateToTimeString(date) {
      return date.toTimeString().slice(0, 8);
    }

    function dateToSeconds(date) {
      return timeStringToSeconds(dateToTimeString(date));
    }

    function secondsToTimeString(seconds) {
      var hours = Math.floor(seconds / 3600).toString().padStart(2, "0");
      var minutes = Math.floor((seconds % 3600) / 60).toString().padStart(2, "0");
      var seconds = Math.floor(seconds % 60).toString().padStart(2, "0");
      return `${hours}:${minutes}:${seconds}`;
    }

    function timeStringToSeconds(time) {
      var parts = time.split(":").map(Number);
      var hours = parts.shift() || 0;
      var minutes = parts.shift() || 0;
      var seconds = parts.shift() || 0;
      return hours * 3600 + minutes * 60 + seconds;
    }

    function getEndTime(start) {
      return new Date(start.getTime() + duration * 1000);
    }

    function setFormValues(start, end) {
      startDateInput.value = start.toISOString().slice(0, 10);
      startTimeInput.value = start.toTimeString().slice(0, 8);
      selectedTimeInput.value =
        start.toLocaleString("cs-CZ", {
          year: "numeric",
          month: "2-digit",
          day: "2-digit",
          hour: "2-digit",
          minute: "2-digit",
          hour12: false,
        }) +
        " - " +
        end.toLocaleString("cs-CZ", {
          hour: "2-digit",
          minute: "2-digit",
        });
    }

    function setSelectedTime(start, end) {
      // remove existing event
      var existingEvent = calendar.getEventById("selected-time");
      if (existingEvent) {
        existingEvent.remove();
      }

      // add new event
      calendar.addEvent({
        id: "selected-time",
        start: start,
        end: end,
        title: selectedEventTimeLabel,
        allDay: false,
        editable: true,
        resizableFromStart: false,
        durationEditable: false,
      });

      // set start date and time inputs
      setFormValues(start, end);
    }

    function isAvailableDate(dateStr) {
      return ! calendar.getEvents().some(e => e.display === 'background' && e.startStr === dateStr);
    }

    function isAvailableTime(start, end) {
      // find business hours that match the selection and duration
      var startSeconds = dateToSeconds(start);
      var endSeconds = dateToSeconds(end);
      var overlapingBusinessHours = calendar.getOption('businessHours').find(
        (bh) => {
          if (! bh.daysOfWeek.includes(start.getDay())) return false;
          var bhStartSec = timeStringToSeconds(bh.startTime);
          var bhEndSec = timeStringToSeconds(bh.endTime);
          if (bhEndSec - bhStartSec < duration) return false;
          return bhStartSec < endSeconds && bhEndSec > startSeconds;
        }
      );
      if (!overlapingBusinessHours) return false;

      // update selection to match business hours and duration
      var bhStartSeconds = timeStringToSeconds(overlapingBusinessHours.startTime);
      var bhEndSeconds = timeStringToSeconds(overlapingBusinessHours.endTime);

      // truncate selection to business hours
      if (startSeconds < bhStartSeconds) startSeconds = bhStartSeconds;
      if (endSeconds > bhEndSeconds) endSeconds = bhEndSeconds;
      
      // if the selection is longer than the duration, truncate it
      if (endSeconds - startSeconds > duration) endSeconds = startSeconds + duration;
      // if the selection is shorter than the duration, extend it
      else if (endSeconds - startSeconds < duration) {
        endSeconds = Math.min(startSeconds + duration, bhEndSeconds);
        if (endSeconds - startSeconds < duration) startSeconds = endSeconds - duration;
      }

      // convert seconds back to Date
      var startDelta = startSeconds - dateToSeconds(start);
      start = new Date(start.getTime() + startDelta * 1000);
      end = getEndTime(start);
      return {start, end};
    }

    var calendar = new FullCalendar.Calendar(calendarElement, {
      initialView: "dayGridMonth",
      initialDate: minStartDate,
      validRange: {
        start: minStartDate,
        end: maxEndDate,
      },
      locale,
      buttonText,
      firstDay: 1,
      allDaySlot: false,
      selectable: true,
      slotDuration: "0:15",
      slotLabelInterval: "1:00",
      slotMinTime: "8:00",
      slotMaxTime: "16:00",
      themeSystem: "bootstrap",
      headerToolbar: {
        left: 'title',
        right: 'dayGridMonth,timeGridWeek prev,next'
      },
      events: unavailableDatesUrl,
      datesSet: function(info) {
        if (info.view.type === 'timeGridWeek') {
          fetch(`${businessHoursUrl}?start=${info.startStr.substring(0, 10)}&end=${info.endStr.substring(0, 10)}`)
            .then(res => res.json())
            .then(data => {
              var businessHours = data.map(({daysOfWeek, startTime, endTime}) => ({
                daysOfWeek,
                startTime,
                endTime,
              }));
              calendar.setOption('businessHours', businessHours);
              if (businessHours.length === 0) {
                calendar.setOption('slotMinTime', "8:00:00");
                calendar.setOption('slotMaxTime', "16:00:00");
              } else {
                var minStartSeconds = businessHours.reduce((min, bh) => {
                  var bhStartSeconds = timeStringToSeconds(bh.startTime);
                  return Math.min(min, bhStartSeconds);
                }, timeStringToSeconds("9:00:00"));
                var maxEndSeconds = businessHours.reduce((max, bh) => {
                  var bhEndSeconds = timeStringToSeconds(bh.endTime);
                  return Math.max(max, bhEndSeconds);
                }, timeStringToSeconds("14:00:00"));

                // give some margin and round to nearest hour
                var quaterHourSeconds = timeStringToSeconds("00:15:00");
                if (minStartSeconds > quaterHourSeconds) {
                  minStartSeconds -= quaterHourSeconds;
                }
                minStartSeconds = Math.floor(minStartSeconds / 3600) * 3600;

                // give some margin and round to nearest hour + 15 minutes
                maxEndSeconds = Math.ceil(maxEndSeconds / 3600) * 3600;
                if (maxEndSeconds < timeStringToSeconds("24:00:00")) {
                  maxEndSeconds += quaterHourSeconds;
                }

                // set min and max time slot
                calendar.setOption('slotMinTime', secondsToTimeString(minStartSeconds));
                calendar.setOption('slotMaxTime', secondsToTimeString(maxEndSeconds));
              }
            });
        } else {
          calendar.setOption('businessHours', []);
        }
      },
      dateClick: function(info) {
        if (isAvailableDate(info.dateStr)) {
          calendar.changeView('timeGridWeek', info.date);
        }
      },
      selectAllow: function (selectInfo) {
        if (selectInfo.allDay) {
            return isAvailableDate(selectInfo.startStr);
        } else {
            return !!isAvailableTime(selectInfo.start, selectInfo.end);
        }
      },
      select: function (info) {
        if (info.allDay) return;
        calendar.unselect();
        var {start, end} = isAvailableTime(info.start, info.end);
        if (start && end) {
          setSelectedTime(start, end);
        }
      },
      eventDrop: function (info) {
        var start = info.event.start;
        var end = getEndTime(start);

        if (isAvailableTime(start, end)) {
          setFormValues(start, end);
        } else {
          info.revert();
        }
      },
    });
    calendar.render();

    if (selectedStart) {
      calendar.changeView('timeGridWeek', selectedStart);
      setSelectedTime(selectedStart, getEndTime(selectedStart));
    }
  });
}
