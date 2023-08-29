import time

import utilities.api.item_ids as ids
import utilities.color as clr
from model.osrs.osrs_bot import OSRSBot
from utilities.api.morg_http_client import MorgHTTPSocket
from utilities.api.status_socket import StatusSocket
from utilities.geometry import RuneLiteObject
from model.bot import BotStatus


class OSRSCoxScavFarm(OSRSBot):
    
    scav_items_per_player = {
        ids.ENDARKENED_JUICE: 8,
        ids.STINKHORN_MUSHROOM: 3,
        ids.CICELY: 1,
        ids.MALLIGNUM_ROOT_PLANK: 2
    }
    
    item_id_to_string = {
        ids.ENDARKENED_JUICE: "Endarkened juice",
        ids.STINKHORN_MUSHROOM: "Stinkhorn mushroom",
        ids.CICELY: "Cicely",
        ids.MALLIGNUM_ROOT_PLANK: "Mallignum root plank"
    }
    
    def __init__(self):
        bot_title = "COX Scav + Farmer"
        description = '''
        Kills and loots Scavs (Done), Does farming (TODO)\n
        Shift Mark the Scavs and add all the necessary items to the ground items plugin\n
        Don't change any other of the plugin settings besides the filtered items\n
        '''
        super().__init__(bot_title=bot_title, description=description)
        self.player_count = 1

    def create_options(self):
        self.options_builder.add_slider_option("player_count", "Amount of players to loot for", 1, 6)

    def save_options(self, options: dict):
        for option in options:
            if option == "player_count":
                self.player_count = options[option]
            else:
                self.log_msg(f"Unknown option: {option}")
                print("Developer: ensure that the option keys are correct, and that options are being unpacked correctly.")
                self.options_set = False
                return
        if self.player_count:
            self.log_msg(f"player_count = {self.player_count}")
        self.log_msg("Options set successfully.")
        self.options_set = True
        
    def main_loop(self):
        # Setup APIs
        api_m = MorgHTTPSocket()
        api_s = StatusSocket()
        self.set_compass_north()
        self.toggle_run(True)
        self.toggle_auto_retaliate(False)
        self.log_msg("Selecting inventory...")
        self.mouse.move_to(self.win.cp_tabs[3].random_point())
        self.mouse.click()
        
        # Main loop
        while self.status != BotStatus.STOPPED:
            # -- Perform bot actions here --
            # Code within this block will LOOP until the bot is stopped.

            self.update_progress(time.time())
            if api_s.get_is_inv_full():
                self.log_msg("Inventory is full. Idk what to do.")
                self.set_status(BotStatus.STOPPED)
                return
            
            if self.check_inv_scav(api_m):
                self.log_msg("Have everything we need...")
                self.type_chat_message("Finished...")
                self.set_status(BotStatus.STOPPED)
                return
            
            # While not in combat
            while not api_m.get_is_in_combat():
                # Find a target
                target = self.get_nearest_tagged_NPC()
                if target is None:
                    break
                    # failed_searches += 1
                    # if failed_searches % 10 == 0:
                    #     self.log_msg("Searching for targets...")
                    # if failed_searches > 60:
                    #     # If we've been searching for a whole minute...
                    #     self.__logout("No tagged targets found. Logging out.")
                    #     return
                    # time.sleep(1)
                    # continue
                # failed_searches = 0

                # Click target if mouse is actually hovering over it, else recalculate
                self.mouse.move_to(target.random_point())
                if not self.mouseover_text(contains="Attack", color=clr.OFF_WHITE):
                    continue
                self.mouse.click()
                time.sleep(0.5)
                
            # While in combat
            while api_m.get_is_in_combat():
                time.sleep(.01)

            # Loot all highlighted items on the ground
            self.__loot(api_s)
        
        self.update_progress(1)
        self.__logout("Finished.")
                    
        
    def __move_mouse_to_nearest_tagged(self, next_nearest=False):
        options = self.get_all_tagged_in_rect(self.win.game_view, clr.PINK)
        option = None
        if not options:
            return False
        # If we are looking for the next nearest option, we need to make sure options has at least 2 elements
        if next_nearest and len(options) < 2:
            return False
        options = sorted(options, key=RuneLiteObject.distance_from_rect_center)
        option = options[1] if next_nearest else options[0]
        if next_nearest:
            self.mouse.move_to(option.random_point(), knotsCount=2)
        else:
            self.mouse.move_to(option.random_point())
        return True
    
    def __loot(self, api: StatusSocket):
        """Picks up loot while there is loot on the ground"""
        while self.pick_up_loot(list(self.item_id_to_string.values())):
            if api.get_is_inv_full():
                self.__logout("Inventory full. Cannot loot.")
                return
            curr_inv = len(api.get_inv())
            self.log_msg("Picking up loot...")
            for _ in range(5):  # give the bot 5 seconds to pick up the loot
                if len(api.get_inv()) != curr_inv:
                    self.log_msg("Loot picked up.")
                    time.sleep(1)
                    break
                time.sleep(1)
    
    def check_inv_scav(self, api: MorgHTTPSocket):
        for item, amount in self.scav_items_per_player.items():
            if item == ids.MALLIGNUM_ROOT_PLANK:
                current_count = api.get_inv_item_indices(item)
                if (current_count is None or 
                    len(current_count) * self.player_count < amount * self.player_count):
                    return False
            
            current_count = api.get_inv_item_stack_amount(item)
            if (current_count is None or 
                current_count * self.player_count < amount * self.player_count):
                return False
        return True
        
