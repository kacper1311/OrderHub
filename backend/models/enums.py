from enum import Enum


class UserRole(str, Enum):
    ADMIN = "ADMIN"
    OPERATOR = "OPERATOR"


class OrderStatus(str, Enum):
    NOWE = "NOWE"
    W_REALIZACJI = "W_REALIZACJI"
    WYSLANE = "WYSLANE"
    ANULOWANE = "ANULOWANE"
    WSTRZYMANE = "WSTRZYMANE"


class MovementType(str, Enum):
    ORDER = "ORDER"
    CANCEL = "CANCEL"
    MANUAL = "MANUAL"
