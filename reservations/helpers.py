import re
from datetime import datetime, timedelta

from reservations.enums import StatusCode
from reservations.models import ReservationJob

sls = [
    "07:00 - 08:00",
    "08:00 - 09:00",
    "09:00 - 10:00",
    "10:00 - 11:00",
    "11:00 - 12:00",
    "12:00 - 13:00",
    "13:00 - 14:00",
    "14:00 - 15:00",
    "16:00 - 17:00",
    "17:00 - 18:00",
    "18:00 - 19:00",
    "19:00 - 20:00",
]
RESERVED = "Rezervasyonu"
SEPET = "Sepetinde"


def create_reservation_job(selection, user):
    # In UTC
    # slot_date_time = 29.12.2022 07:00
    # in UTC this will be 29.12.2022 04:00
    slot_date_time = selection.slot.date_time.replace(tzinfo=None)
    now = datetime.now().replace(tzinfo=None)
    now_in_turkish_timezone = now + timedelta(hours=3)
    reservation_hours_range = range(0, 72)
    time_diff_in_hours = (
        (slot_date_time - now_in_turkish_timezone).total_seconds() // 60 // 60
    )
    if time_diff_in_hours in reservation_hours_range:
        execution_time = now
        execution_type = ReservationJob.IMMEDIATE
    else:
        # To be able to convert to UTC
        # Slots are open 3 days before, however there is a buffer of 10 seconds before the slot is opened
        execution_time = slot_date_time - timedelta(days=3, hours=3, seconds=10)
        execution_type = ReservationJob.ETA
    return ReservationJob.objects.create(
        execution_time=execution_time,
        selection=selection,
        user=user,
        execution_type=execution_type,
    )


def send_reservation_email(reservation):
    from reservations.mail.client import mail_client

    user = reservation.user
    selection = reservation.selection

    context = {
        "email": user.email,
        "first_name": user.first_name,
        "slot": selection.slot.formatted_date,
        "info": selection.sport_selection.info,
        "status": reservation.status,
    }

    mail_client.send(context)


def show_slots(browser, show_future_slots=True):
    data = {}
    slots = []

    r = re.compile(r"(Pazartesi|Salı|Çarşamba|Perşembe|\bCuma\b|Cumartesi|Pazar)")

    page = browser.page

    panel_infos = page.find_all("div", {"class": "panel panel-info"})
    court_data = page.find("select", {"id": "ddlSalonFiltre"}).find(
        "option", {"selected": "selected"}
    )
    data["court"] = court_data.text
    data["court_id"] = court_data["value"]

    reservation_hours_range = range(0, 72)
    now = datetime.now().replace(tzinfo=None)
    now_in_turkish_timezone = now + timedelta(hours=3)

    for pinfo in panel_infos:
        h3 = pinfo.find("h3").text
        day = r.match(h3).group()
        date = re.search(r"(\d+\.\d+\.\d+)", h3).group()

        wells = pinfo.find_all("div", {"class": "well wellPlus"})

        day_info = {"day": day, "date": date, "slots": []}
        day_slots = day_info["slots"]

        for well in wells:
            status = well.find("div").text
            if RESERVED in status:
                continue
            slot = well.find("span").text
            anchor = well.select('a[href^="javascript:__doPostBack"]')
            if anchor:
                is_reservable = True
                href = anchor[0].get("href")
                eventtarget = href[
                    href.find("ctl") : href.find("Rezervasyon") + len("Rezervasyon")
                ]
            else:
                eventtarget = None
                is_reservable = False

            if is_reservable:
                status_code = StatusCode.RESERVABLE.value
                status = "Reservable"
            else:
                status_code = (
                    StatusCode.ANOTHER_BASKET.value
                    if SEPET in status
                    else StatusCode.NO_SLOTS.value
                )

            day_slots.append(
                {
                    "slot": slot,
                    "status": status,
                    "status_code": status_code,
                    "is_reservable": is_reservable,
                    "event_target": eventtarget,
                }
            )

        if not day_slots and show_future_slots:
            date_obj = datetime.strptime(date, "%d.%m.%Y")
            time_diff_in_hours = (
                (date_obj - now_in_turkish_timezone).total_seconds() // 60 // 60
            )
            if (time_diff_in_hours not in reservation_hours_range) and (
                date_obj > now_in_turkish_timezone
            ):
                [
                    day_slots.append(
                        {
                            "slot": sl,
                            "status": "Reservable ETA",
                            "status_code": StatusCode.WILL_BE_AVAILABLE.value,
                            "is_reservable": True,
                            "event_target": None,
                        }
                    )
                    for sl in sls
                ]

        slots.append(day_info)
    data["slots"] = slots
    return data
