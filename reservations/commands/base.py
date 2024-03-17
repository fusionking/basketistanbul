import abc
import re
import time

import mechanicalsoup

from reservations.enums import StatusCode
from reservations.helpers import show_slots
from reservations.models import Reservation
from reservations.utils import get_legacy_session
from selections.constants import BRANCH_TENNIS_ID


class ReservationCommandRunner:
    def __init__(
        self,
        user,
        selection,
        sport_selection,
        event_target=None,
        commands=None,
        is_max_retry=False,
        court_selection=None,
    ):
        # Browser
        self.browser = mechanicalsoup.StatefulBrowser(session=get_legacy_session())
        # User
        self.user = user
        self.tckn = user.tckn
        self.password = user.third_party_app_password
        self.cookie = None

        # Pitch
        self.selection = selection
        self.sport_selection = sport_selection
        self.court_selection = (
            self.sport_selection.pitch_id if selection else court_selection
        )

        # One of these must be set
        self.event_target = event_target
        self.slot_date_time = selection.slot.date_time if selection else None

        # Response
        self.response = None

        # Credentials
        self.base_headers = {
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "en-US,en;q=0.9",
            "Connection": "keep-alive",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Host": "online.spor.istanbul",
            "Origin": "https://online.spor.istanbul",
            "Referer": "https://online.spor.istanbul/satiskiralik",
            "Sec-Fetch-Site": "same-origin",
            "Sec-GPC": "1",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/105.0.0.0 Safari/537.36",
        }
        self.base_data = {
            "__EVENTARGUMENT": None,
            "__LASTFOCUS": None,
            "ctl00$pageContent$ddlBransFiltre": BRANCH_TENNIS_ID,
            "ctl00$pageContent$ddlTesisFiltre": self.sport_selection.complex_id,
            "ctl00$pageContent$ddlSalonFiltre": self.court_selection,
            "__VIEWSTATEGENERATOR": "BA851843",
        }
        self.current_command = self.build(commands)

        self.is_failure = False
        self.is_no_slot = False
        self.is_max_retry = is_max_retry

    @staticmethod
    def build(commands=None):
        if not commands:
            base_command = LoginCommand()
            base_command.set_next(FillFormCommand()).set_next(
                ResolveEventTargetCommand()
            ).set_next(ReservationClickCommand()).set_next(
                ReservationChoiceCommand()
            ).set_next(
                AddToCartCommand()
            ).set_next(
                CreateReservationCommand()
            )
        else:
            base_command = commands[0]
            command = commands[0]
            for com in commands[1:]:
                command = command.set_next(com)

        return base_command

    def __call__(self, *args, **kwargs):
        command = self.current_command
        while getattr(command, "next", None):
            command = command(self)
        # Execute last command if no early return
        if command:
            result = command(self)
            print("Chain finished")
            return result


class BaseReservationCommand(metaclass=abc.ABCMeta):
    URL_PATH = None

    def __init__(self):
        self.base_url = "https://online.spor.istanbul"
        # Next Command to execute
        self.next = None

    def __call__(self, *args, **kwargs):
        runner_instance = args[0]
        return self.execute(runner_instance)

    @abc.abstractmethod
    def execute(self, runner_instance):
        raise NotImplementedError

    def set_next(self, CommandClass):
        self.next = CommandClass
        return self.next

    def has_next(self):
        return self.next


class LoginCommand(BaseReservationCommand):
    URL_PATH = "uyegiris"

    def execute(self, runner_instance):
        if not runner_instance.password:
            runner_instance.is_failure = True
            return self.next

        if runner_instance.is_failure:
            return self.next
        browser = runner_instance.browser
        browser.open(f"{self.base_url}/{self.URL_PATH}", verify=False)
        browser.select_form()
        browser["txtTCPasaport"] = runner_instance.tckn
        browser["txtSifre"] = runner_instance.password
        response = browser.submit_selected()
        runner_instance.cookie = response.request.headers["Cookie"]
        return self.next


class FillFormCommand(BaseReservationCommand):
    def execute(self, runner_instance):
        if runner_instance.is_failure:
            return self.next
        # Satis Kiralik Form Doldurma
        browser = runner_instance.browser

        browser.follow_link("satiskiralik")
        browser.select_form()
        browser[
            "ctl00$pageContent$ddlBransFiltre"
        ] = "59b7bd71-1aab-4751-8248-7af4a7790f8c"
        browser.submit_selected()
        time.sleep(0.5)

        browser.select_form()
        browser[
            "ctl00$pageContent$ddlTesisFiltre"
        ] = runner_instance.sport_selection.complex_id
        browser.submit_selected()
        time.sleep(0.8)

        browser.select_form()
        browser["ctl00$pageContent$ddlSalonFiltre"] = runner_instance.court_selection.strip()
        browser.submit_selected()
        time.sleep(0.5)

        return self.next


class ResolveEventTargetCommand(BaseReservationCommand):
    def execute(self, runner_instance):
        if runner_instance.is_failure:
            return self.next

        if not runner_instance.event_target:
            slots_data = show_slots(runner_instance.browser)
            slots = slots_data["slots"]
            all_reservables_for_selected_date = [
                s1
                for s in slots
                for s1 in s["slots"]
                if s1["is_reservable"] is True
                and s1["status_code"] != StatusCode.WILL_BE_AVAILABLE.value
                and s["date"] == runner_instance.slot_date_time.strftime("%d.%m.%Y")
            ]

            hour = str(runner_instance.slot_date_time.hour)
            hour_to_match = ("0" + hour) if len(hour) == 1 else hour
            reservable_slots = [
                slot
                for slot in all_reservables_for_selected_date
                if slot["slot"].startswith(hour_to_match)
            ]
            if not reservable_slots:
                print("No reservable field found! Returning")
                runner_instance.is_failure = True
                runner_instance.is_no_slot = True
                return self.next

            event_target = reservable_slots[0]["event_target"]
            runner_instance.event_target = event_target

        return self.next


class ReservationClickCommand(BaseReservationCommand):
    def execute(self, runner_instance):
        if runner_instance.is_failure:
            return self.next

        time.sleep(1)
        browser = runner_instance.browser
        # Satis Kiralik Rezervasyon

        page_content_script = (
            f"ctl00$pageContent$UpdatePanel1|{runner_instance.event_target}"
        )
        inp = browser.page.find("input", id="__VIEWSTATE")
        view_state = inp.get("value")

        headers = {
            "Accept": "*/*",
            "Cookie": runner_instance.cookie,
            "Cache-Control": "no-cache",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "X-MicrosoftAjax": "Delta=true",
            "X-Requested-With": "XMLHttpRequest",
            **runner_instance.base_headers,
        }
        data = {
            "ctl00$pageContent$script1": page_content_script,
            "__VIEWSTATE": view_state,
            "__ASYNCPOST": True,
            "__EVENTTARGET": runner_instance.event_target,
            **runner_instance.base_data,
        }

        runner_instance.response = browser.post(browser.url, data=data, headers=headers)
        return self.next


class ReservationChoiceCommand(BaseReservationCommand):
    def execute(self, runner_instance):
        if runner_instance.is_failure:
            return self.next

        time.sleep(1)
        # Kiralama Secimi
        browser = runner_instance.browser

        rc = runner_instance.response.content.decode("utf8")
        viewstate = rc[rc.find("__VIEWSTATE") : rc.find("|8|")]
        view_state = viewstate.replace("__VIEWSTATE|", "")
        event_target = (
            "ctl00$pageContent$rblKiralikTenisSatisTuru$rblKiralikTenisSatisTuru_2"
        )

        headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Cache-Control": "max-age=0",
            "Cookie": runner_instance.cookie,
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1",
            **runner_instance.base_headers,
        }
        data = {
            "ctl00$pageContent$rblKiralikTenisSatisTuru": "3",
            "__VIEWSTATE": view_state,
            "__EVENTTARGET": event_target,
            **runner_instance.base_data,
        }
        runner_instance.response = browser.post(browser.url, data=data, headers=headers)
        return self.next


class AddToCartCommand(BaseReservationCommand):
    def execute(self, runner_instance):
        from bs4 import BeautifulSoup as bs

        if runner_instance.is_failure:
            return self.next

        time.sleep(1)
        response = runner_instance.response
        browser = runner_instance.browser

        # add "lxml"
        soup = bs(
            response.content.decode("utf8"), parser="html.parser", features="lxml"
        )
        anchor = soup.find("a", id="pageContent_lbtnSepeteEkle")
        href = anchor.get("href")
        event_target = href[
            href.find("ctl") : href.find("SepeteEkle") + len("SepeteEkle")
        ]
        page_content_script = f"ctl00$pageContent$UpdatePanel1|{event_target}"
        inp = browser.page.find("input", id="__VIEWSTATE")
        view_state = inp.get("value")

        headers = {
            "Accept": "*/*",
            "Cookie": runner_instance.cookie,
            "Cache-Control": "no-cache",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "X-MicrosoftAjax": "Delta=true",
            "X-Requested-With": "XMLHttpRequest",
            **runner_instance.base_headers,
        }
        data = {
            "ctl00$pageContent$script1:": page_content_script,
            "ctl00$pageContent$rblKiralikTenisSatisTuru": "3",
            "__VIEWSTATE": view_state,
            "__EVENTTARGET": event_target,
            "ctl00$pageContent$ddlAdet": "2",
            "ctl00$pageContent$cboxKiralikSatisSozlesmesi": "on",
            "__ASYNCPOST": True,
            **runner_instance.base_data,
        }
        response = browser.post(browser.url, data=data, headers=headers)
        runner_instance.is_failure = True if not response.ok else False
        return self.next


class RemoveFromBasketCommand(BaseReservationCommand):
    URL_PATH = "uyesepet"

    def execute(self, runner_instance):
        browser = runner_instance.browser
        browser.open(f"{self.base_url}/{self.URL_PATH}")
        event_target = None
        table = browser.page.find("table", id="dataTable1")
        tbody = table.find("tbody")
        trs = tbody.findAll("tr")
        for tr in trs:
            tds = tr.findAll("td")
            td_time = tds[1]
            time_match = re.search(r"(\d{1}\d{1}):\d{1}\d{1}", td_time.text).groups()
            slot_start_hour = time_match[0] if time_match else None
            slot_start_hour = (
                slot_start_hour[1]
                if slot_start_hour.startswith("0")
                else slot_start_hour[:]
            )

            td_date = tds[2]
            td_date_match = re.search(
                r"(\d+\.\d+\.\d+)\s-\s(\d+\.\d+\.\d+)", td_date.text
            ).groups()
            slot_date = td_date_match[0] if td_date_match else None

            if all(
                (
                    (slot_start_hour is not None),
                    (runner_instance.selection is not None),
                    (
                        str(runner_instance.selection.slot.date_time.hour)
                        == slot_start_hour
                    ),
                    (
                        str(
                            runner_instance.selection.slot.date_time.strftime(
                                "%d.%m.%Y"
                            )
                        )
                        == slot_date
                    ),
                )
            ):
                event_target = tds[-1].find("a").get("href")[25:63]
                break

        if event_target:
            inp = browser.page.find("input", id="__VIEWSTATE")
            view_state = inp.get("value")
            headers = {
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
                "Cache-Control": "max-age=0",
                "Cookie": runner_instance.cookie,
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-User": "?1",
                "Upgrade-Insecure-Requests": "1",
                **runner_instance.base_headers,
            }
            data = {
                "__VIEWSTATE": view_state,
                "__EVENTTARGET": event_target,
                "__VIEWSTATEGENERATOR": "2730706D",
                "__EVENT_ARGUMENT": None,
            }
            response = browser.post(browser.url, data=data, headers=headers)
            runner_instance.is_failure = True if not response.ok else False
            return self.next


class CheckReservationCommand(BaseReservationCommand):
    URL_PATH = "uyespor"

    def execute(self, runner_instance):
        from bs4 import BeautifulSoup as bs

        browser = runner_instance.browser
        browser.open(f"{self.base_url}/{self.URL_PATH}")
        event_target = None
        table = browser.page.find("table", id="dtUyeSpor")
        tbody = table.find("tbody")
        trs = tbody.findAll("tr")
        for tr in trs:
            tds = tr.findAll("td")
            td_time = tds[2]
            time_match = re.search(
                r"(\d{1}\d{1}):\d{1}\d{1}:\d{1}\d{1}\s-\s(\d{1}\d{1})", td_time.text
            ).groups()
            slot_start_hour = time_match[0] if time_match else None
            slot_start_hour = (
                slot_start_hour[1]
                if slot_start_hour.startswith("0")
                else slot_start_hour[:]
            )

            td_date = tds[3]
            td_date_match = re.search(
                r"(\d+\.\d+\.\d+)\s-\s(\d+\.\d+\.\d+)", td_date.text
            ).groups()
            slot_date = td_date_match[0] if td_date_match else None

            if all(
                (
                    (slot_start_hour is not None),
                    (runner_instance.selection is not None),
                    (
                        str(runner_instance.selection.slot.date_time.hour)
                        == slot_start_hour
                    ),
                    (
                        str(
                            runner_instance.selection.slot.date_time.strftime(
                                "%d.%m.%Y"
                            )
                        )
                        == slot_date
                    ),
                )
            ):
                event_target = tds[-1].find("a").get("href")[25:73]
                break

        if event_target:
            inp = browser.page.find("input", id="__VIEWSTATE")
            view_state = inp.get("value")
            headers = {
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
                "Cache-Control": "max-age=0",
                "Cookie": runner_instance.cookie,
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-User": "?1",
                "Upgrade-Insecure-Requests": "1",
                **runner_instance.base_headers,
            }
            data = {
                "__VIEWSTATE": view_state,
                "__EVENTTARGET": event_target,
                "__VIEWSTATEGENERATOR": "76CD4AB0",
                "__EVENT_ARGUMENT": None,
            }
            response = browser.post(browser.url, data=data, headers=headers)
            runner_instance.is_failure = True if not response.ok else False
            soup = bs(
                response.content.decode("utf8"), parser="html.parser", features="lxml"
            )
            table = soup.find("table", id="dtUyeSpor")
            tbody = table.find("tbody")
            tr = tbody.findAll("tr")[2]
            td = tr.findAll("td")[4]
            status_text = td.text
            if status_text == "Satış Yapıldı":
                return True
            else:
                return False
        return False


class CreateReservationCommand(BaseReservationCommand):
    def execute(self, runner_instance):
        can_create_reservation = (
            runner_instance.is_max_retry or not runner_instance.is_failure
        )
        if not can_create_reservation:
            return

        status = (
            Reservation.FAILED if runner_instance.is_failure else Reservation.IN_CART
        )
        Reservation.objects.create(
            user=runner_instance.user,
            selection=runner_instance.selection,
            status=status,
        )
