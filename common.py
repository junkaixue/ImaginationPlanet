import ctypes
import platform
import time
from datetime import datetime

import cv2
import numpy as np
import pyautogui
from platform_config import get_image_path
from collections import namedtuple

DEBUG = False

Point = namedtuple('Point', ['x', 'y'])

# Platform-specific imports
if platform.system() == "Windows":
    import ctypes
else:
    import Quartz

from click import click_at

coor_dict = {}

# Load the button templates (for multiple buttons)
main_map = {
    # Main Run
    "RunButton": get_image_path("throwbutton.png"),
    "Replace": get_image_path("replace.png"),
    "NoMore": get_image_path("no_more.png"),
    "Gift": get_image_path("gift.png"),
    "Confirm": get_image_path("confirm.png"),

    # Guess
    "Guess": get_image_path("guess.png"),
    # Temp hard code
    # "GuessL": get_image_path("guess_left.png"),
    # "GuessR": get_image_path("guess_right.png"),
    "RobotDetect": get_image_path("robot_detect.png"),

    # Visit Main
    "VisitMain": get_image_path("visiting_main.png"),
    "ChessMan": get_image_path("chessman.png"),
    "ChessManInner": get_image_path("chessman_inner.png"),
}

visit_map = {
    # Visit
    "VisitComplete": get_image_path("visiting_complete.png"),
    "Roll": get_image_path("rolling.png"),
    "Timeout": get_image_path("timeout.png"),
    "VisitBusy": get_image_path("visit_busy.png"),
    "AdsSkip": get_image_path("ads_skip.png"),
    "RobotDetect": get_image_path("robot_detect.png"),
}

fight_map = {
    # Fight
    "FightButton": get_image_path("fight_button.png"),
}

common_map = {
    # Common
    "CancelBuy": get_image_path("cancel_button.png"),
    "Exit": get_image_path("exit.png"),
    "Confirm": get_image_path("confirm.png"),
}

single_find_map = {
    # Main
    "RunButton": get_image_path("throwbutton.png"),
    "ThankGift": get_image_path("thank_gift.png"),
    "PKG": get_image_path("package.png"),
    "TW": get_image_path("twenty_throw.png"),
    "TWB": get_image_path("twenty_throw_on_bar.png"),
    "ONE": get_image_path("one_throw.png"),
    "ONEB": get_image_path("one_throw_on_bar.png"),
    "FACE_UP_LEFT": get_image_path("face_up_left.png"),
    "VISIT_FACE_UP_LEFT": get_image_path("visit_face_up_left.png"),

    # Visit
    "CardButton": get_image_path("card_button.png"),
    "CardMode": get_image_path("card_mode.png"),
    "CatCard": get_image_path("cat_card.png"),
    "AgainCard": get_image_path("again_card.png"),
    "CatHouse": get_image_path("cat_house.png"),
    "CatHouseNiu": get_image_path("cat_house_niu.png"),
    "VisitBack": get_image_path("visit_back.png"),
    "Confirm": get_image_path("confirm.png"),
    "HConfirm": get_image_path("hconfirm.png"),
    "RollComplete": get_image_path("roll_complete.png"),
    "BackVisit": get_image_path("back_normal_visit.png"),
    "VisitFriend": get_image_path("friend_list.png"),
    "VisitButton": get_image_path("visiting_button.png"),
    "FightSkip": get_image_path("fight_skip.png"),
    "CancelBuy": get_image_path("cancel_button.png"),
    "UseTicket": get_image_path("use_ticket.png"),
    "VisitBusy": get_image_path("visit_busy.png"),
    "OneMore": get_image_path("one_more.png"),
    "VisitGoHome": get_image_path("visit_go_home.png"),
    "33": get_image_path("33.png"),
    "ChessMan": get_image_path("chessman.png"),
    "ChessManInner": get_image_path("chessman_inner.png"),

    # Repair
    "Repair": get_image_path("repair.png"),
    "RepairTop": get_image_path("repair_top.png"),

    # Fight
    "TaskMain": get_image_path("task_main.png"),
    "FightMain": get_image_path("fight_main.png"),
    "FightEntry": get_image_path("fight_entry.png"),
    "Exit": get_image_path("exit.png"),
    "TicketRunout": get_image_path("ticket_runout.png"),
    "FightButton": get_image_path("fight_button.png"),

    # Red Pack
    "Chat": get_image_path("chat.png"),
    "RollRed": get_image_path("roll_red_pack.png"),
    "TakeRed": get_image_path("take_red_pack.png"),
    "RedBack": get_image_path("red_pack_back.png"),
    "DiamRed": get_image_path("diamond_red_pack.png"),
    "ChatBar": get_image_path("chat_bar.png"),
    "SendText": get_image_path("send_text.png"),
    "MainBack": get_image_path("main_back.png"),

    "TooManyRequest": get_image_path("too_many_request.png"),

    # Robot check
    "RobotDetected": get_image_path("robot_detect.png"),
    "Plus": get_image_path("plus_sign.png"),
    "Equal": get_image_path("equal_sign.png"),
    "QWD": get_image_path("question_wide.png"),
    "QConfirm": get_image_path("question_confirm.png"),
    "QReward": get_image_path("answer_reward.png"),

    # Boss fight
    "BossDiam": get_image_path("boss_diamond.png"),
    "BossFree": get_image_path("boss_free.png"),
    "BossEnd": get_image_path("boss_no_ticket.png"),
    "BossWorld": get_image_path("boss_world.png"),
    "Group": get_image_path("group.png"),
    "BossGroup": get_image_path("group_boss.png"),
    "Challenge": get_image_path("challenge.png"),
    "GoHome": get_image_path("go_home.png"),
    "BossBack": get_image_path("boss_back.png"),
    "WGoHome": get_image_path("world_go_home.png"),
    "BGift": get_image_path("boss_gift.png"),
    "GBossMain": get_image_path("group_boss_main.png"),

    # Star Pick
    "StarPick": get_image_path("star/pick_up.png"),
    "Ship1": get_image_path("star/ship_1.png"),
    "Ship2": get_image_path("star/ship_2.png"),
    "Ship3": get_image_path("star/ship_3.png"),
    "Ship4": get_image_path("star/ship_4.png"),
    "S1V": get_image_path("star/ship1_verify.png"),
    "S2V": get_image_path("star/ship2_verify.png"),
    "S3V": get_image_path("star/ship3_verify.png"),
    "S4V": get_image_path("star/ship4_verify.png"),
    "ShipFree": get_image_path("star/ship_free.png"),
    "ShipList": get_image_path("star/ship_list.png"),
    "Star": get_image_path("star/star.png"),
    "ShipPage": get_image_path("star/ship_list_page.png"),
    "CloseList": get_image_path("star/close_ship_list.png"),
    "Shop": get_image_path("star/shop.png"),
    "Details": get_image_path("star/details.png"),
    "SConfirm": get_image_path("star/ship_confirm.png"),
    "SSConfirm": get_image_path("star/s_confirm.png"),
    "Disconnected": get_image_path("star/disconnected.png"),
    "SChat": get_image_path("star/ship_chat.png"),
    "Bag": get_image_path("star/bag.png"),
    "Acc": get_image_path("star/acc.png"),
    "PPT": get_image_path("star/property.png"),
    "SendShip": get_image_path("star/send_ship.png"),
    "SBack": get_image_path("star/go_back.png"),
    "SEntry": get_image_path("star/star_entry.png"),
    "75": get_image_path("star/75.png"),
    "75V": get_image_path("star/75_verify.png"),

    # Tower Fight
    "TEntry": get_image_path("tower/entry.png"),
    "TFight": get_image_path("tower/fight_button.png"),
    "TNext": get_image_path("tower/next_page.png"),
    "TSN": get_image_path("tower/shanliu.png"),
    "TConfirm": get_image_path("tower/tconfirm.png"),
    "TTicket": get_image_path("tower/ticket.png"),
    "TClick": get_image_path("tower/tclick.png"),
    "TComplete": get_image_path("tower/tcomplete.png"),
    "TBuy": get_image_path("tower/tbuy.png"),
    "TExit": get_image_path("tower/texit.png"),
    
    # Black Market (part of star feature)
    "BlackMarket": get_image_path("star/black_market.png"),

    # Zone Explore (zone_explore.py) - page screenshots in pics/mac/zone/pages, crops in pics/mac/zone
    # map page
    "ZBase": get_image_path("zone/base.png"),
    "ZIdle": get_image_path("zone/idle.png"),
    "ZBuilding": get_image_path("zone/building.png"),
    "ZReturning": get_image_path("zone/returning.png"),
    "ZSailing": get_image_path("zone/sailing.png"),
    "ZRepairing": get_image_path("zone/repairing.png"),
    "ZCrossSailing": get_image_path("zone/cross_sailing.png"),
    "ZExplore": get_image_path("zone/explore.png"),
    "ZTeam": get_image_path("zone/team.png"),
    "ZZoom50": get_image_path("zone/zoom50.png"),
    "ZZoom75": get_image_path("zone/zoom75.png"),
    "ZMyBase": get_image_path("zone/my_base.png"),
    "ZSelectZone": get_image_path("zone/select_zone.png"),
    # map resources
    "ZFactory1": get_image_path("zone/factory1.png"),
    "ZFactory2": get_image_path("zone/factory2.png"),   # green factory
    "ZFactory3": get_image_path("zone/factory3.png"),   # pink/orange factory
    "ZFactory4": get_image_path("zone/factory4.png"),   # blue factory with an ore symbol (04区)
    "ZFactory5": get_image_path("zone/factory5.png"),   # fifth factory kind: template not captured yet
    "ZBigBattle": get_image_path("zone/big_battle.png"),
    "ZYellowBoss": get_image_path("zone/yellow_boss.png"),
    "ZBox": get_image_path("zone/box.png"),
    "ZSmallBattle": get_image_path("zone/small_battle.png"),
    "ZGreenShip": get_image_path("zone/green_ship.png"),
    "ZRedVehicle": get_image_path("zone/red_vehicle.png"),
    "ZYellowBox": get_image_path("zone/yellow_box.png"),          # golden treasure chest, 4 score (capture at 75%)
    "ZRedBigBattle": get_image_path("zone/red_big_battle.png"),   # red big battle ship with star badge (capture at 75%)
    # dialogs
    "ZGo": get_image_path("zone/go.png"),
    "ZShareCoord": get_image_path("zone/share_coord.png"),
    "ZBuyPrompt": get_image_path("zone/buy_prompt.png"),
    "ZBuyOk": get_image_path("zone/buy_ok.png"),
    "ZBuyCancel": get_image_path("zone/buy_cancel.png"),
    "ZContinueHint": get_image_path("zone/continue_hint.png"),
    "ZTargetPage": get_image_path("zone/target_page.png"),
    "ZAttackPage": get_image_path("zone/attack_page.png"),
    "ZAllyExchange": get_image_path("zone/ally_exchange.png"),
    "ZDispatchTitle": get_image_path("zone/dispatch_title.png"),
    "ZFleetDetail": get_image_path("zone/fleet_detail.png"),
    "ZEnergy": get_image_path("zone/energy.png"),
    "ZEstimateLabel": get_image_path("zone/estimate_label.png"),
    "ZBigWin": get_image_path("zone/big_win.png"),
    "ZSmallWin": get_image_path("zone/small_win.png"),
    "ZDraw": get_image_path("zone/draw.png"),
    "ZBigLoss": get_image_path("zone/big_loss.png"),
    "ZSmallLoss": get_image_path("zone/small_loss.png"),
    "ZAttack": get_image_path("zone/attack.png"),
    "ZCancel": get_image_path("zone/cancel.png"),
    "ZCloseHint": get_image_path("zone/close_hint.png"),
    "ZBackArrow": get_image_path("zone/back_arrow.png"),
    # factory page
    "ZFactoryPage": get_image_path("zone/factory_page.png"),
    "ZOccupied": get_image_path("zone/occupied.png"),
    "ZSlotPower": get_image_path("zone/slot_power.png"),
    "ZSlotFree": get_image_path("zone/slot_free.png"),      # "可派舰队" under the + of a free factory slot
    "ZOurGoing": get_image_path("zone/our_going.png"),      # "你的舰队正在前往中" in a factory slot
    # fleet page
    "ZMyFleet": get_image_path("zone/my_fleet.png"),
    "ZRepair": get_image_path("zone/repair.png"),
    "ZRepairPrompt": get_image_path("zone/repair_prompt.png"),
    "ZRepairOk": get_image_path("zone/repair_ok.png"),
    "ZFleetRepairing": get_image_path("zone/fleet_repairing.png"),   # "舰队修理中..." on a fleet tab under repair
    # zone map
    "ZZoneList": get_image_path("zone/zone_list_title.png"),       # "远古深寒区" title of the zone chooser
    # Fleet panel (click a sailing ship in the top bar) and the boost dialog
    "ZRivalPanel": get_image_path("zone/rival_panel.png"),          # "同目标点舰队" panel on a target popup
    "ZFleetSpeed": get_image_path("zone/fleet_speed.png"),          # "当前速度:" = fleet panel open
    "ZAccelerate": get_image_path("zone/accelerate.png"),           # "加速" button on the fleet panel
    "ZReturnHome": get_image_path("zone/return_home.png"),          # "返航" button on the fleet panel
    "ZBoostPage": get_image_path("zone/boost_page.png"),            # "当前航行速度:" = boost dialog open
    "ZQuantumBoost": get_image_path("zone/quantum_boost.png"),      # "量子型舰队加速器" row label
    "ZSuperBoost": get_image_path("zone/super_boost.png"),          # "超级型舰队加速器" row label
    "ZLargeBoost": get_image_path("zone/large_boost.png"),          # "大型舰队加速器" row label
    "ZUseButton": get_image_path("zone/use_button.png"),            # "使用"
    # Fortress (铸械要塞) boss fight and the equipment pages
    "ZFortressMap": get_image_path("zone/fortress_map.png"),          # 铸械要塞 icon on the map
    "ZFortressTitle": get_image_path("zone/fortress_title.png"),      # "深寒铸械要塞" page title
    "ZFortressBack": get_image_path("zone/fortress_back.png"),        # "<" bottom-left of the fortress page
    "ZGuardBright": get_image_path("zone/guard_bright.png"),          # guard rocket cell
    "ZGuardAttack": get_image_path("zone/guard_attack.png"),          # "袭击" under a selected guard
    "ZShopLabel": get_image_path("zone/shop_label.png"),              # 商店
    "ZDepotLabel": get_image_path("zone/depot_label.png"),            # 委托站
    "ZCommandLabel": get_image_path("zone/command_label.png"),        # 指挥所
    "ZAutoEquip": get_image_path("zone/auto_equip.png"),              # "一键配队"
    "ZEditFleetTitle": get_image_path("zone/edit_fleet_title.png"),   # "编辑舰队"
    "ZEditArtifactTitle": get_image_path("zone/edit_artifact_title.png"),  # "编辑低级神器"
    "ZArtifactTarget": get_image_path("zone/artifact_target.png"),    # 残骸本源 (boss artifact)
    "ZArtifactCheck": get_image_path("zone/artifact_check.png"),      # check mark on the equipped artifact
    "ZArtifactSlot": get_image_path("zone/artifact_slot.png"),        # 残骸本源 as shown in the fleet page slot
    "ZLoadoutStandard": get_image_path("zone/loadout_standard.png"),  # the complete best loadout (我的舰队 grid)
    "ZPlusSlot": get_image_path("zone/plus_slot.png"),                # "+" empty slot in 编辑舰队
    "ZEditGearTitle": get_image_path("zone/edit_gear_title.png"),     # "编辑装备" (bottom-row artifacts)
    "ZEditCatTitle": get_image_path("zone/edit_cat_title.png"),       # "编辑猫护法"
    # 金秋赏月 festival (sit in a pavilion seat)
    "ZFestMainBtn": get_image_path("zone/fest_main_btn.png"),   # 金秋赏月 button label on the game main screen (right side)
    "ZFestTitle": get_image_path("zone/fest_title.png"),        # 金秋赏月 banner on the activity page
    "ZFestGo": get_image_path("zone/fest_go.png"),              # 前往>> buttons on the activity page
    "ZFestMe": get_image_path("zone/fest_me.png"),              # yellow "我" bubble = already seated
    "ZFestPav1": get_image_path("zone/fest_pav1.png"),          # 巅峰I号赏月亭 label
    "ZFestPavilion": get_image_path("zone/fest_pavilion.png"),  # "赏月亭" suffix of every pavilion label
    "ZFestBack": get_image_path("zone/fest_back.png"),          # back arrow bottom-left
    "ZFestOccupy": get_image_path("zone/fest_occupy.png"),      # 占据 (free seat)
    "ZFestEmpty": get_image_path("zone/fest_empty.png"),        # 无人占领
    "ZFestRow": get_image_path("zone/fest_row.png"),            # "观赏位" part of a row label
    "ZFestChallenge": get_image_path("zone/fest_challenge.png"),  # 挑战 (never clicked)
    # Run (dice) mode, used by the monitor to switch into zone explore when the dice run out
    "ZStarExplore": get_image_path("zone/star_explore.png"),        # "星际探险" button, main page bottom right
    "ZAutoThrowing": get_image_path("zone/auto_throwing.png"),      # "自动投掷中..." overlay
    "ZMoreDice": get_image_path("zone/more_dice.png"),              # "更多骰子" popup title = dice ran out
    "ZLongPressAuto": get_image_path("zone/long_press_auto.png"),   # "长按自动" on the dice button = not running

    # Restart Game
    "DingHao": get_image_path("dinghao.png"),
    "ClickGame": get_image_path("click_game.png"),
    "StartGame": get_image_path("start_game.png"),
    "AutoPick": get_image_path("auto_pick.png"),
    "Announcement": get_image_path("announcement.png"),
    "CloseTab": get_image_path("close_tab.png"),
}

resource_map = {
    "Main": main_map,
    "Fight": fight_map,
    "Visit": visit_map,
    "Common": common_map,
    "Single": single_find_map,
}

but_list = {}

no_cache_list = ["CatHouse", "Exit", "Replace", "Chat", "RollRed", "DiamRed", "Confirm", "Challenge", "StarPick",
                 "ShipFree", "Star", "BlackMarket", "CloseTab",
                 "ZBase", "ZGo", "ZEnergy", "ZAttack", "ZCancel", "ZCloseHint", "ZBackArrow", "ZSlotPower",
                 "ZFactoryPage", "ZZoom50", "ZTeam", "ZMyFleet", "ZRepair", "ZDispatchTitle", "ZEstimateLabel",
                 "ZBuyOk", "ZBuyCancel", "ZContinueHint", "ZAttackPage", "ZRepairOk", "ZFleetRepairing", "ZSlotFree", "ZOurGoing",
                 "ZStarExplore", "ZAutoThrowing", "ZMoreDice", "ZLongPressAuto",
                 "ZFleetSpeed", "ZAccelerate", "ZReturnHome", "ZBoostPage", "ZQuantumBoost", "ZSuperBoost", "ZLargeBoost", "ZUseButton",
                 "ZZoneList", "ZSelectZone", "ZRivalPanel",
                 "ZFortressTitle", "ZFortressBack", "ZGuardAttack", "ZAutoEquip", "ZEditFleetTitle", "ZEditArtifactTitle",
                 "ZArtifactTarget", "ZArtifactCheck", "ZArtifactSlot", "ZLoadoutStandard", "ZPlusSlot",
                 "ZFestMainBtn", "ZFestTitle", "ZFestGo", "ZFestMe", "ZFestPav1", "ZFestPavilion", "ZFestBack", "ZFestOccupy", "ZFestEmpty", "ZFestRow", "ZEditGearTitle", "ZEditCatTitle", "ZShopLabel", "ZDepotLabel", "ZCommandLabel"]

# Define a new print function with a timestamp
# Save the original built-in print function
original_print = print


def print(*args, **kwargs):
    """
    Custom print function with a timestamp.
    """
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    # Call the original print function
    original_print(f'[{timestamp}]', *args, **kwargs)


def get_scaling_factor():
    """
    Get the display scaling factor.
    """
    if platform.system() == "Windows":
        hdc = ctypes.windll.user32.GetDC(0)
        dpi = ctypes.windll.gdi32.GetDeviceCaps(hdc, 88)  # LOGPIXELSX
        ctypes.windll.user32.ReleaseDC(0, hdc)
        return dpi / 96  # Standard DPI is 96
    elif platform.system() == "Darwin":
        # If macOS support is needed, implement Quartz-based scaling factor logic
        # Get the main display ID
        main_display_id = Quartz.CGMainDisplayID()

        # Get the display mode
        display_mode = Quartz.CGDisplayCopyDisplayMode(main_display_id)

        # Retrieve the pixel dimensions
        pixel_width = Quartz.CGDisplayModeGetPixelWidth(display_mode)
        pixel_height = Quartz.CGDisplayModeGetPixelHeight(display_mode)

        # Retrieve the point dimensions
        point_width = Quartz.CGDisplayModeGetWidth(display_mode)
        point_height = Quartz.CGDisplayModeGetHeight(display_mode)

        # Calculate the scaling factor
        scaling_factor = pixel_width / point_width

        return scaling_factor
    else:
        return 1  # Default scaling factor for other systems


def get_center(but, map_scope):
    return get_center_h(but, map_scope, 0.6)


def simple_single_find(but, map_scope, th):
    """
    Find a button on screen using template matching.
    Mac-compatible - uses cv2.matchTemplate instead of pyautogui.locateOnScreen.
    """
    try:
        template_path = resource_map[map_scope][but]
        if DEBUG:
            print(f"[DEBUG] Looking for '{but}' in scope '{map_scope}'")
            print(f"[DEBUG] Template path: {template_path}")
        result = single_find_with_path(template_path, None, th)
        if DEBUG:
            print(f"[DEBUG] Result: {result}")
        return result
    except Exception as e:
        if DEBUG:
            print(f"[DEBUG] Error in simple_single_find: {e}")
        return False


def get_center_h(but, map_scope, th):
    """
    Get the center coordinates of a button on the screen.
    Mac-compatible - uses cv2.matchTemplate instead of pyautogui.locateOnScreen.
    """
    if but in no_cache_list or but not in coor_dict:  # Sometimes scroll can change the position
        try:
            template_path = resource_map[map_scope][but]
            center = get_center_with_path(template_path, None, th)
            if center is not None:
                coor_dict[but] = center
            else:
                print(f"Warning: Button '{but}' not found on screen.")
                return None
        except Exception as e:
            print(f"Error finding button '{but}': {e}")
            return None
    return coor_dict.get(but)


def get_all(but, map_scope):
    """
    Get all matching locations of a button on the screen.
    Mac-compatible - uses cv2.matchTemplate and adjusts for scaling factor.
    """
    try:
        template_path = resource_map[map_scope][but]
        matches = find_all_with_path(template_path, None, 0.8)
        
        # Get scaling factor for coordinate conversion
        sft = get_scaling_factor()
        
        # Filter out matches that are too close vertically (same as before)
        coors = []
        prev_y = None
        for cx, cy, confidence in matches:
            if prev_y is None or abs(prev_y - cy) > 20:
                prev_y = cy
                # Convert to logical coordinates for clicking
                coors.append(Point(cx / sft, cy / sft))
        return coors
    except Exception as e:
        print(f"Error finding all instances of '{but}': {e}")
        return []


def get_all_with_cache(but, map_scope):
    """
    Get all cached locations of a button on the screen.
    """
    if but not in but_list:
        but_list[but] = get_all(but, map_scope)
    return but_list[but]


def find_button(map_scope):
    """
    Find buttons on the screen by matching templates.
    """
    gray_screen = screen_shot()
    bts = []
    for button_name, template_path in resource_map[map_scope].items():
        if single_find_with_path(template_path, gray_screen, 0.8):
            bts.append(button_name)
    return bts


def single_find(but):
    """
    Find a single button using its pre-defined template path.
    Mac-compatible - uses cv2.matchTemplate via single_find_with_path.
    """
    return single_find_with_path(single_find_map[but], None, 0.8)


def single_find_with_path(but_path, gs, th):
    """
    Perform template matching using a specified template path.
    Mac-compatible - uses cv2.matchTemplate with grayscale images.
    
    Args:
        but_path: Path to template image
        gs: Grayscale screenshot (or None to take new one)
        th: Confidence threshold
    
    Returns:
        True if found, False otherwise
    """
    gray_screen = screen_shot() if gs is None else gs
    template = cv2.imread(but_path, 0)
    if template is None:
        if DEBUG:
            print(f"[ERROR] Unable to load template from '{but_path}'.")
        return False

    if DEBUG:
        print(f"[DEBUG] Template size: {template.shape[1]}x{template.shape[0]}")
        print(f"[DEBUG] Screen size: {gray_screen.shape[1]}x{gray_screen.shape[0]}")
    
    # Perform template matching
    result = cv2.matchTemplate(gray_screen, template, cv2.TM_CCOEFF_NORMED)
    threshold = th
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
    
    if DEBUG:
        print(f"[DEBUG] Best match confidence: {max_val:.4f} (threshold: {threshold})")
        print(f"[DEBUG] Best match location: {max_loc}")
    
    if max_val >= threshold:
        if DEBUG:
            print(f"[DEBUG] ✅ FOUND (confidence {max_val:.4f} >= {threshold})")
        return True
    else:
        if DEBUG:
            print(f"[DEBUG] ❌ NOT FOUND (confidence {max_val:.4f} < {threshold})")
        return False


def find_all_with_path(but_path, gs, th):
    """
    Find all instances of a template and return their center coordinates.
    
    Args:
        but_path: Path to template image
        gs: Grayscale screenshot (or None to take new one)
        th: Confidence threshold
    
    Returns:
        List of (cx, cy, confidence) tuples for all matches, or empty list if none found
    """
    gray_screen = screen_shot() if gs is None else gs
    template = cv2.imread(but_path, 0)
    if template is None:
        print(f"Error: Unable to load template from '{but_path}'.")
        return []
    
    # Perform template matching
    result = cv2.matchTemplate(gray_screen, template, cv2.TM_CCOEFF_NORMED)
    h, w = template.shape[:2]
    
    matches = []
    temp_result = result.copy()
    
    # Find all matches by iterating and masking
    while True:
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(temp_result)
        
        if max_val < th:
            break
        
        # Found a match - calculate center
        x, y = max_loc
        cx = x + w // 2
        cy = y + h // 2
        matches.append((cx, cy, max_val))
        
        # Mask this region to find next match
        mask_size = int(max(w, h) * 1.2)
        y1 = max(0, y - mask_size // 2)
        y2 = min(temp_result.shape[0], y + mask_size // 2)
        x1 = max(0, x - mask_size // 2)
        x2 = min(temp_result.shape[1], x + mask_size // 2)
        temp_result[y1:y2, x1:x2] = 0
    
    return matches


def get_center_with_path(but_path, gs, th):
    """
    Find a template and return its center coordinates.
    Mac-compatible - uses cv2.matchTemplate and adjusts for scaling factor.
    
    Args:
        but_path: Path to template image
        gs: Grayscale screenshot (or None to take new one)
        th: Confidence threshold
    
    Returns:
        Tuple (cx, cy) in logical coordinates if found, None otherwise
    """
    matches = find_all_with_path(but_path, gs, th)
    if matches:
        cx, cy = matches[0][0], matches[0][1]
        
        # On Mac, cv2.matchTemplate returns physical pixel coordinates
        # but pyautogui.click expects logical coordinates
        # So we need to divide by scaling factor
        sft = get_scaling_factor()
        cx_logical = cx / sft
        cy_logical = cy / sft

        if DEBUG:
            print(f"[DEBUG] Physical pixels: ({cx}, {cy})")
            print(f"[DEBUG] Scaling factor: {sft}")
            print(f"[DEBUG] Logical coords: ({cx_logical:.1f}, {cy_logical:.1f})")
        
        return Point(cx_logical, cy_logical)
    return None


def screen_shot():
    """
    Take a screenshot and convert it to a grayscale image for template matching.
    """
    screenshot = pyautogui.screenshot()
    screen = np.array(screenshot)
    return cv2.cvtColor(screen, cv2.COLOR_RGB2GRAY)


def challenge_fight():
    count = 1
    while single_find("Challenge"):
        print("Chanllenge not pass, fight again!")
        center = get_center("Challenge", "Single")
        click_at(center.x, center.y)
        time.sleep(3)
        print("Start challenge fight " + str(count))
        count += 1

        while simple_single_find("FightSkip", "Single", 0.9):
            print("Found Skip Button")
            cc = get_center("FightSkip", "Single")
            click_at(cc.x, cc.y)
            time.sleep(3)
    print("Challenge fight " + str(count) + " then it succeeded!")


if __name__ == "__main__":
    challenge_fight()
