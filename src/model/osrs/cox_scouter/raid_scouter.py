import time

import utilities.api.item_ids as ids
import utilities.color as clr
import utilities.random_util as rd
from model.osrs.osrs_bot import OSRSBot
from utilities.api.morg_http_client import MorgHTTPSocket
from utilities.api.status_socket import StatusSocket
from model.osrs.cox_scouter.scouting_status import scouting_status
from model.osrs.cox_scouter.raid_rooms import raid_room
from utilities.geometry import RuneLiteObject


class OSRSCoxScouter(OSRSBot):
    def __init__(self):
        bot_title = "COX Raid Scouter"
        description = "Scouts raids until it finds a suitable layout. Order does NOT matter, (TODO)"
        super().__init__(bot_title=bot_title, description=description)
        self.allow_six = False
        self.lf_rope = False
        self.lf_crabs = False
        self.tek_muta = False
        self.v_t_v = False
        self.scouting_status = scouting_status.CLICKING_BOARD

    def create_options(self):
        self.options_builder.add_checkbox_option("allow_six", "Allow 6", [" "])
        self.options_builder.add_checkbox_option("lf_rope", "Looking for Rope", [" "])
        self.options_builder.add_checkbox_option("lf_crabs", "Looking for Crabs", [" "])
        self.options_builder.add_checkbox_option("tek_muta", "Tek Muta", [" "])
        self.options_builder.add_checkbox_option("v_t_v", "VTV", [" "])

    def save_options(self, options: dict):
        for option in options:
            if option == "allow_six":
                self.allow_six = options[option] != []
            elif option == "lf_rope":
                self.lf_rope = options[option] != []
            elif option == "lf_crabs":
                self.lf_crabs = options[option] != []
            elif option == "tek_muta":
                self.tek_muta = options[option] != []
            elif option == "v_t_v":
                self.v_t_v = options[option] != []
            else:
                self.log_msg(f"Unknown option: {option}")
                print("Developer: ensure that the option keys are correct, and that options are being unpacked correctly.")
                self.options_set = False
                return
        if self.allow_six:
            self.log_msg(f"allow_six = {self.allow_six}")
        if self.lf_rope:
            self.log_msg(f"lf_rope = {self.allow_six}")
        if self.lf_crabs:
            self.log_msg(f"lf_crabs = {self.lf_crabs}")
        if self.tek_muta:
            self.log_msg(f"tek_muta = {self.tek_muta}")
        if self.v_t_v:
            self.log_msg(f"v_t_v = {self.v_t_v}")
        self.log_msg("Options set successfully.")
        self.options_set = True
        
    def main_loop(self):
        # Setup APIs
        api_m = MorgHTTPSocket()
        api_s = StatusSocket()
        self.log_msg("Selecting inventory...")
        self.mouse.move_to(self.win.cp_tabs[3].random_point())
        self.mouse.click()
        self.toggle_run(True)
        self.set_compass_north()
        self.scouting_status = scouting_status.CLICKING_BOARD

        # Main loop
        while True:
            # -- Perform bot actions here --
            # Code within this block will LOOP until the bot is stopped.

            self.update_progress(time.time())
            
            match self.scouting_status:
                case scouting_status.CLICKING_BOARD:
                    self.log_msg("Looking for starting board")
                    while not self.get_all_tagged_in_rect(self.win.game_view, clr.PINK): continue
                    while self.gameview_runelite_text_white("Puzzle") or self.gameview_runelite_text_white("Combat"): continue
                    self.__move_mouse_to_nearest_tagged()
                    self.mouse.click()
                    time.sleep(.5)
                    self.scouting_status = scouting_status.MAKING_PARTY
                    
                case scouting_status.MAKING_PARTY:
                    self.log_msg("Waiting for idle")                    
                    while not api_m.get_is_player_idle():
                        time.sleep(.1)
                    self.log_msg("Looking for Make party button")
                    while not self.click_make_party_button(): 
                        time.sleep(.1)
                    self.scouting_status = scouting_status.ENTER_RAID
                    
                case scouting_status.ENTER_RAID:
                    self.log_msg("Looking for dungeon icon")
                    while not self.click_dungeon_icon(): 
                        time.sleep(.1)                    
                    time.sleep(.25)
                    self.mouse.move_to(self.win.chat.random_point())
                    self.log_msg("Waiting for idle")
                    while not api_m.get_is_player_idle():
                        time.sleep(.1)
                    self.__move_mouse_to_nearest_tagged()
                    self.mouse.click()
                    self.scouting_status = scouting_status.CHECKING_RAID
                    
                case scouting_status.CHECKING_RAID:
                    self.log_msg("Waiting for layout info")
                    while not self.gameview_runelite_text_white("Puzzle"):
                        time.sleep(.1)
                    time.sleep(1) #Just waiting in case of rendering problem
                    raid_layout = api_m.get_latest_chat_message()
                    raid_layout = raid_layout[raid_layout.find("]") + 2:].split(',')
                    raid_layout = [room.strip() for room in raid_layout]
                    self.log_msg(raid_layout)
                    if self.check_raid_layout(raid_layout):
                        self.log_msg("Approved Raid")
                        self.scouting_status = scouting_status.DONE
                    else:
                        self.log_msg("Bad Raid, restarting...")
                        self.scouting_status = scouting_status.RESTART
                        
                case scouting_status.RESTART:
                    self.__move_mouse_to_nearest_tagged()
                    self.mouse.click()
                    time.sleep(.63)
                    self.keypress("1", .43)
                    self.log_msg("waiting to leave raid")
                    while self.gameview_runelite_text_white("Puzzle"):
                        time.sleep(.1)
                    time.sleep(1.23)
                    self.scouting_status = scouting_status.CLICKING_BOARD
                    
                case scouting_status.DONE:
                    time.sleep(60)
                    self.mouse.move_to(self.win.chat.random_point())
                    self.mouse.click()
                case _:
                    self.update_progress(1)
                    self.log_msg("Failed. Need to restart")
                    self.stop()
                    
        
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
    
    def check_raid_layout(self, layout: list):
        if layout.count(raid_room.VANGUARDS.value) > 0:
            return False
        if layout.count(raid_room.CRABS.value) <= 0 and self.lf_crabs:
            return False
        if layout.count(raid_room.TIGHTROPE.value) <= 0 and self.lf_rope:
            return False
        if len(layout) > 5 and not self.allow_six:
            return False
        
        if (
            self.tek_muta and 
            layout.count(raid_room.TEKTON.value) > 0 and 
            layout.count(raid_room.MUTTADILES.value) > 0
        ):
            return True
        
        if (self.v_t_v and 
            layout.count(raid_room.VASA.value) > 0 and 
            layout.count(raid_room.TEKTON.value) > 0 and 
            layout.count(raid_room.VESPULA.value) > 0
        ):
            return True
        
        return False
        
        
