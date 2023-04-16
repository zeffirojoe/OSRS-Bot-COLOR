from enum import Enum

class mining_status(Enum):
    IDLE = "IDLE"
    MINING = "MINING"
    RUNNING_TO_BANK = "RUNNING_TO_BANK"
    BANKING = "BANKING"
    RUNNING_TO_MINE = "RUNNING_TO_MINE"
    