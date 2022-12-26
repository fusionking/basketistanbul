import re
from datetime import datetime, timedelta

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


def create_reservation_job(selection_preference):
    selection = selection_preference.selection
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
        execution_time = slot_date_time - timedelta(days=3, hours=3)
        execution_type = ReservationJob.ETA
    return ReservationJob.objects.create(
        execution_time=execution_time,
        selection=selection,
        user=selection_preference.preference.user,
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


def show_slots(browser):
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

    for pinfo in panel_infos:
        h3 = pinfo.find("h3").text
        day = r.match(h3).group()
        date = re.search(r"(\d+\.\d+\.\d+)", h3).group()

        wells = pinfo.find_all("div", {"class": "well wellPlus"})

        day_info = {"day": day, "date": date, "slots": []}
        day_slots = day_info["slots"]

        for well in wells:
            status = well.find("div").text
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

            day_slots.append(
                {
                    "slot": slot,
                    "status": status,
                    "is_reservable": is_reservable,
                    "event_target": eventtarget,
                }
            )

        if not day_slots:
            [
                day_slots.append(
                    {
                        "slot": sl,
                        "status": "Added by our application",
                        "is_reservable": True,
                        "event_target": None,
                    }
                )
                for sl in sls
            ]

        slots.append(day_info)
    data["slots"] = slots
    return data