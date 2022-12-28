from enum import Enum


class StatusCode(Enum):
    ANOTHER_RESERVATION = "AR"
    ANOTHER_BASKET = "AB"
    NO_SLOTS = "NS"
    WILL_BE_AVAILABLE = "WBA"
    RESERVABLE = "RV"
