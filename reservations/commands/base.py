import abc
import time

import mechanicalsoup

from reservations.helpers import show_slots
from reservations.models import Reservation


class ReservationCommandRunner:
    def __init__(
        self,
        user,
        selection,
        event_target=None,
        commands=None,
        is_max_retry=False,
        court_selection=None,
    ):
        # Browser
        self.browser = mechanicalsoup.StatefulBrowser()
        # User
        self.user = user
        self.tckn = user.tckn
        self.password = user.third_party_app_password
        self.cookie = None

        # Pitch
        self.selection = selection
        self.court_selection = (
            selection.sport_selection.pitch_id if selection else court_selection
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
            "ctl00$pageContent$ddlBransFiltre": "59b7bd71-1aab-4751-8248-7af4a7790f8c",
            "ctl00$pageContent$ddlTesisFiltre": "6989b491-bb85-414a-b470-293b190ebb44",
            "ctl00$pageContent$ddlSalonFiltre": self.court_selection,
            "__VIEWSTATEGENERATOR": "BA851843",
        }
        self.current_command = self.build(commands)

        self.is_failure = False
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
            command(self)
        print("Chain finished")


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
        time.sleep(2)

        browser.select_form()
        browser[
            "ctl00$pageContent$ddlTesisFiltre"
        ] = "6989b491-bb85-414a-b470-293b190ebb44"
        browser.submit_selected()
        time.sleep(2)

        browser.select_form()
        browser["ctl00$pageContent$ddlSalonFiltre"] = runner_instance.court_selection
        browser.submit_selected()
        time.sleep(2)

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
                and s1["status"] != "Added by our application"
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
                return self.next

            event_target = reservable_slots[0]["event_target"]
            runner_instance.event_target = event_target

        return self.next


class ReservationClickCommand(BaseReservationCommand):
    def execute(self, runner_instance):
        if runner_instance.is_failure:
            return self.next

        time.sleep(2)
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

        time.sleep(5)
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

        time.sleep(5)
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
