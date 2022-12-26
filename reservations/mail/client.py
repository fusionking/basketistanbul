from django.conf import settings
from django.template.loader import get_template
from mailjet_rest import Client


class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class MailJetClient(metaclass=Singleton):
    def __init__(self):
        self.api_key = settings.MAILJET_API_KEY
        self.secret_key = settings.MAILJET_SECRET_KEY
        self.client = Client(auth=(self.api_key, self.secret_key), version="v3.1")

        self.html = get_template("reservations/reservation.html")
        self.txt = get_template("reservations/reservation.txt")

        self.subject = "About Your Reservation"

    def send(self, context):
        if not settings.MAIL_ENABLED:
            return False

        data = {
            "Messages": [
                {
                    "From": {
                        "Email": "basket.stanbul@gmail.com",
                        "Name": "Basket Istanbul",
                    },
                    "To": [
                        {"Email": context.pop("email"), "Name": context["first_name"]}
                    ],
                    "Subject": self.subject,
                    "TextPart": self.txt.render(context),
                    "HTMLPart": self.html.render(context),
                }
            ]
        }
        result = self.client.send.create(data=data)
        return result.status_code == 200


mail_client = MailJetClient()
