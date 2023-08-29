import random
import time

import utilities.api.item_ids as ids
import utilities.color as clr
from model.bot import BotStatus
from model.osrs.amethyst.mining_status import mining_status
from model.osrs.osrs_bot import OSRSBot
from utilities.api.morg_http_client import MorgHTTPSocket
from utilities.api.status_socket import StatusSocket


class OSRSAmethystMiner(OSRSBot):
    def __init__(self):
        bot_title = "Amethyst miner/banker"
        description = """Mines Amethyst in the mining guild and banks it.\n
        Mark ALL the amethyst spots you want to mine from AND the bank chest.\n
        Zoom out the minimap enough where you can always see the poll booth or bank icon\n
        Mark a tile at the entrace of the amethyst room visible from the bank
        """
        super().__init__(bot_title=bot_title, description=description)
        self.mining_status = mining_status.IDLE
        self.drop_items = False
        self.deposit_items = [ids.UNCUT_DIAMOND, ids.UNCUT_EMERALD, ids.UNCUT_RUBY, ids.UNCUT_SAPPHIRE, ids.AMETHYST]

    def create_options(self):
        self.options_builder.add_checkbox_option("drop_items", "Drop instead of Bank, (TODO)", [" "])

    def save_options(self, options: dict):
        for option in options:
            if option == "drop_items":
                self.drop_items = options[option] != []
            else:
                self.log_msg(f"Unknown option: {option}")
                print("Developer: ensure that the option keys are correct, and that options are being unpacked correctly.")
                self.options_set = False
                return
        if self.drop_items:
            self.log_msg(f"drop_items = {self.drop_items}")
        self.log_msg("Options set successfully.")
        self.options_set = True

    def main_loop(self):
        # Setup APIs
        api_m = MorgHTTPSocket()
        api_s = StatusSocket()

        self.log_msg("Selecting inventory...")
        self.mouse.move_to(self.win.cp_tabs[3].random_point())
        self.mouse.click()
        self.set_compass_south()
        self.toggle_run(True)
        self.keypress("up", 2)
        self.mining_status = mining_status.IDLE

        # Main loop
        while self.status != BotStatus.STOPPED:
            # -- Perform bot actions here --
            # Code within this block will LOOP until the bot is stopped.

            self.update_progress(time.time())

            match self.mining_status:
                case mining_status.IDLE:
                    while not api_m.get_is_player_idle():
                        time.sleep(0.1)

                    self.log_msg("Idle...")

                    if api_m.get_is_inv_full():
                        self.mining_status = mining_status.RUNNING_TO_BANK
                        continue

                    self.__move_mouse_to_nearest_tagged()
                    self.mouse.click()
                    self.mining_status = mining_status.MINING

                case mining_status.MINING:
                    self.log_msg("Mining...")
                    time.sleep(2.5)
                    while not api_m.get_is_player_idle():
                        time.sleep(0.1)
                    self.mining_status = mining_status.IDLE

                case mining_status.RUNNING_TO_BANK:
                    self.log_msg("Clicking mini-map...")
                    while not self.click_poll_booth_icon():
                        time.sleep(0.1)

                    self.log_msg("Running to bank...")
                    time.sleep(0.5)
                    while not api_m.get_is_player_idle():
                        time.sleep(0.1)

                    self.mining_status = mining_status.BANKING

                case mining_status.BANKING:
                    self.log_msg("Starting to bank...")
                    self.__move_mouse_to_nearest_tagged()
                    self.mouse.click()

                    time.sleep(random.uniform(2, 2.75))
                    for item in self.deposit_items:
                        indices = api_m.get_inv_item_indices(item)
                        if indices is None or len(indices) <= 0:
                            continue
                        self.drop([random.choice(indices)])
                        time.sleep(random.uniform(0.25, 0.60))

                    self.mining_status = mining_status.RUNNING_TO_MINE

                case mining_status.RUNNING_TO_MINE:
                    self.log_msg("Running to mine...")
                    while not self.click_poll_booth_icon():
                        time.sleep(0.1)
                    self.__move_mouse_to_nearest_tagged(color=clr.GREEN)
                    self.mouse.click()
                    self.mining_status = mining_status.IDLE

        self.update_progress(1)
        self.__logout("Finished.")
