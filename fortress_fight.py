"""
Fortress fight (星炽要塞 or 铸械要塞, -f xz|zx) - attack the fortress guards with the one fleet
that carries the best equipment, moving that equipment to a fresh full-hp fleet before every attack.

Cycle (user rules):
    1. The fleet holding the best gear = the one with the highest 战力 on the 我的舰队 tabs.
    2. Pick another fleet that is idle at 100% hp.
    3. On the holder's tab: remove everything (编辑舰队: 飞行器, 主题皮肤, 骰子皮肤, 棋子; the cats;
       both right-column artifacts, 残骸本源 among them; the bottom-row artifacts; the lv.6
       shield at the bottom right is never touched), confirming each edit page.
    4. On the fresh fleet's tab: 一键配队 (it also takes the loose 残骸本源 into the top-right
       artifact slot; not checked).
    5. Back on the old holder's tab: 一键配队 (a fleet without a loadout cannot be repaired),
       then 修理舰队, confirm.
    6. Map -> the fortress icon -> all five buildings are checked first, from the top of the page
       down (bright = ready: the guards around it are cleared and it has recovered; a broken
       one wears a 已损坏 badge, a guarded one is dim); only without a ready one the first
       bright guard (dim ones are not attackable yet). The scroll gesture must stay above
       指挥所 (the area below does not drag) -> 袭击 -> 派遣舰队 list: pick the fresh
       fleet's card (it also has the highest 战力) -> battle estimate: always attack. A target
       that shows no 袭击 when tapped is left alone for FAILED_TARGET_TTL.
    7. Wait for the fleet to come back, then repeat with the next full-hp fleet.

Only one fleet fights at a time (there is one set of best gear). No zoom or map dragging.

Ordered mode (-oxz / -ozx ORDER, e.g. 41032: five fleet digits from 0, big ship first, then two
middle, two small): no gear swaps; each idle fleet below full energy is repaired (修理舰队 only),
each idle full one attacks, biggest first, while the others may still be out. A guard's rank
label (I / II bars) caps who fights it: big II/I/none and the buildings, middle I/none, small
unlabelled only; a ship takes the highest level it may. No two fleets fight the same target:
a target is claimed for its fleet before the final 袭击 until that fleet is back (BUSY_MIN).

Usage:
    python fortress_fight.py -f zx      # 铸械要塞 instead of 星炽要塞 (default -f xz)
    python fortress_fight.py -oxz 41032 # ordered mode on 星炽要塞: fleet 5 big, 2/1 middle, 4/3 small
    python fortress_fight.py --dry      # does the gear swap and repair for real, cancels at the attack
    python fortress_fight.py            # full loop (started on the zone map)
    python fortress_fight.py -m         # monitor: wait on the dice board until the dice run out
                                        # (更多骰子 popup / 长按自动 idle), enter 星际探险, then fight
"""

import argparse
import json
import os
import time
from collections import namedtuple

import cv2
import numpy as np
import pyautogui

from common import single_find, get_center, get_all, single_find_map
from log_helper import log
from zone_explore import (ZoneExplore, match_all, Point, FLEET_PAGE_LAYOUT, SHIP_LAYOUT, MATCH_TH, DRAG_LAYOUT,
                          MONITOR_POLL, RUN_IDLE_SECONDS, CONTINUE_TAP_DY, _code_version)

# ---- 我的舰队 page, logical px relative to the "我的舰队" title center (ZMyFleet)
EQUIP_LAYOUT = {
    "slot_dx": (-151, -76, 0, 76.5, 152.5),          # five columns of equipment slots
    "row_dy": (132.5, 207.5, 305, 380, 475),         # two gear rows, two chess rows, artifact row
    "shield_slot": (152.5, 475),                     # bottom right lv.6 shield: never touched
    "power_dx": 0, "power_dy": 618, "power_half_w": 95, "power_half_h": 15,   # "战力:835.26万"
    "close_dx": 0, "close_dy": -60,                  # tap the dimmed top bar above the title to close
    "loadout_dx": 3, "loadout_dy": 305,              # center of the loadout grid (ZLoadoutStandard)
    "loadout_th": 0.9,                               # the holder's grid matches the standard >= this ...
    "loadout_margin": 0.05,                          # ... and clearly better than every other tab
}
# ---- 编辑舰队 page, relative to its title center. The equipped items sit in the bottom area;
# clicking one removes it and the rest shift left, an empty place shows a "+" placeholder.
EDIT_LAYOUT = {
    "tab_dy": 64,
    # (tab dx, [(click dx, click dy, times)]) -- user's recipe: keep tapping the leftmost item,
    # the rest shift left; chess: leftmost twice clears the first column, then the second
    # position eight times clears the remaining ones.
    "tabs": [
        ("飞行器", -151, [(-40, 500, 6)]),
        ("主题皮肤", -51, [(-40, 500, 6)]),
        ("骰子皮肤", 49, [(0, 500, 4), (-40, 500, 4)]),
        ("棋子", 149, [(-152.5, 465, 6), (-76.5, 465, 30)]),
    ],
    "burst_gap": 0.1,          # seconds between taps of a burst
    "tab_underline_dy": 82,    # the selected tab has a bright underline this far below the title (mean ~209 vs ~36)
    "tab_half_w": 40,
    "tab_retries": 4,
}
# ---- 编辑装备 page (bottom-row artifacts 炬团令牌/烙印/战旗/密契), relative to its title center
GEAR_LAYOUT = {"tab_dx": (-150, -50, 50, 150), "tab_dy": 62, "preview": (0, 470)}   # 令牌/烙印/战旗/密契
# ---- 编辑猫护法 page (opened from the cat slot left of the artifact), relative to its title
CAT_LAYOUT = {"slot": (76.5, 132.5), "item": (-76, 511), "count": 3}
# ---- right-column artifact slots (row 1 = 高级, holds 残骸本源; row 2 = 顶级, lv.14): on the page the equipped
# artifact is shown in the preview area above the buttons; tapping it removes it.
ARTIFACT_SLOTS = {"rows": (0, 1), "preview_from_confirm": (-92, -147)}
UNEQUIP_BOTTOM_ARTIFACTS = True     # the four bottom slots (not the lv.6 shield); flow unverified
# ---- 派遣舰队 list, card centers relative to the "派遣舰队" title
DISPATCH_CARDS = {"dx": -15, "dy0": 105, "spacing": 125}
# ---- fortress page
FORTRESS = {
    "guard_th": 0.8,          # template match for a guard cell (dim ones match too)
    "grid_top_dy": 200,       # guard grid lies below the title by at least this (logical px)
    "scroll_x_dxs": (-150, -100),   # scroll gesture columns relative to the title (guard columns, not 指挥所);
                              # the second is tried when a gesture in the first opened a dialog
    "scroll_y0_dy": 450,      # gesture from title+y0 up to title+y1 (content moves up by y0-y1 = 220, less
    "scroll_y1_dy": 230,      # than the measured content area so that the move can be matched). Both ends
                              # stay above 指挥所's lower edge (~title+500): the page does not drag below it
    "max_scrolls": 10,
    "blank_dy": 45,           # the description line under the title: tapping it closes popups
    "cell_half": 10,          # guard brightness: half size of the sampled square (logical px)
    "building_patch": (45, 5, 20),   # building brightness: from 45 to 5 px above the label, +-20 wide
    "dim_ratio": 0.7,         # the content area this much darker after a drag: a dialog may be on top
    "move_diff": 12,          # mean frame change above this without a strip match is a real move; a glow is ~5
    "shop_label_dy": (324, 15),     # 商店's label sits this far below the title on the unscrolled page (+- tolerance,
                                    # tighter than spot_radius so that remembered guard spots still line up)
    "spot_radius": 20,        # a guard this close to a tried spot (screen position) is the same guard; cells are ~33 apart
    "press": 0.2,             # press-before-move of the scroll gesture: the guard cells react to taps
    "min_step": 100,          # a measured move shorter than this (of the 220 px gesture) is not a screen step
    "grid_half_w": 230,       # the page content spans this far left/right of the title (shift measurement)
    "content_bottom_dy": 530, # the page content measured for scrolling ends this far below the title (above 停机坪)
    "tap_timeout": 5.0,       # seconds a tap on a target gets to open something
    "icon_timeout": 2.0,      # the map icon's popup shows within a second
    "want_grace": 2.0,        # seconds 袭击 still gets after another part of its popup showed
    "tap_settle": 1.0,        # a popup draws its parts over a few frames: look once more after this
    "building_tap_dy": 35,    # tap point above a building's label
}
# the fortresses: their own map icon, page title and guard cell templates; the page layout,
# buildings and buttons are the same. bright_min: mean grey of an attackable guard cell (铸械
# 85-98 vs dim 37-56, pages/boss/fortress_page.png; 星炽 31-33 vs dim 17-19,
# pages/xingzhi/command_attack_cut.png). building_bright_min: mean grey above a ready building's
# label (铸械 ~118 vs guarded ~50); not measured on 星炽 yet (no ready building captured; its
# raided 指挥所 measures ~93, the dim 商店/委托站 ~40), so 铸械's value is used
FORTRESS_KINDS = {
    "xz": {"name": "星炽要塞", "map": "ZXingzhiMap", "title": "ZXingzhiTitle", "guard": "ZXingzhiGuard",
           "bright_min": 24, "building_bright_min": 75},
    "zx": {"name": "铸械要塞", "map": "ZFortressMap", "title": "ZFortressTitle", "guard": "ZGuardBright",
           "bright_min": 75, "building_bright_min": 75},
}
# 袭击 under a target, matched by the top 70% of its template: under 指挥所 on the unscrolled
# page the button is cut off by 停机坪 (full template 0.61 there). The real button scores >= 0.95
# on every screenshot, other pages <= 0.76 (the top half alone reached 0.81 on map pages)
ATTACK = "ZGuardAttackTop"
# the fortress page's title counts only with the page's "<" (ZFortressBack) this far from it
# (logical px; pages/boss/fortress_page.png, guard_clicked.png, pages/xingzhi: dy 764-767): the
# fortress's map popup shows the same name mid-screen, and the map's own "<" also scores ~0.83
TITLE_TO_BACK = (-208, 765, 25)     # dx, dy, tolerance
FULL_HP = 100
TAP_BURST = 3                # taps per burst on idempotent buttons (tabs, 一键配队): a dropped tap is harmless
PENDING_REPAIR_TRIES = 3     # passes a failed repair is retried from pending_repair before giving up
DEFERRED_EQUIP_TRIES = 3     # passes a stripped fleet's deferred 一键配队 is retried before giving up
SWAP_FINISH_TRIES = 3        # passes an unfinished gear swap is resumed before it is abandoned
BAD_TARGET_TTL = 30 * 60     # seconds a fleet whose 一键配队 kept failing in a swap is not picked again
HOLDER_LOOKUP_TRIES = 3      # consecutive failures to find the gear holder before the run stops
HOLDER_OK_HP = 90            # the gear holder attacks again by itself above this hp (no swap)
DEBUG_DIR = None             # --debug-shots: save the OCR crops here
RETURN_TIMEOUT = 40 * 60     # seconds to wait for the fighting fleet to come back
POLL = 30
BUILDINGS_FRESH = 60         # seconds a walk that saw all five buildings without a ready one is trusted
                             # (retries within one attack_with look for guards from the screen in front)
FAILED_TARGET_TTL = 15 * 60  # seconds a building is skipped after FAILED_TARGET_MISSES taps showed no 袭击
FAILED_TARGET_MISSES = 2     # taps on a building in one go that showed no 袭击: the first may be dropped
# a guard cell's rank label: one ("I") or two ("II") short bars at the cell's top left, none on
# the weakest guards (grey on dim cells, white on bright ones). Box in logical px from the guard
# match center (dx0, dy0, dx1, dy1); a bar rises >= 40 grey above the darkest column within
# bar_reach on pages/boss/fortress_page.png and fortress_page_bottom.png (51 labels), other
# detail <= 14. Not checked on 星炽 yet (no labelled guard captured)
GUARD_LABEL = {"box": (-15, -15, -5, -7), "bar_reach": 2, "contrast": 25}
# -oxz/-ozx ORDER: five fleets (0-based digits) by size, one big, two middle, two small. A ship
# fights guards up to its rank (big: II, I and none; middle: I and none; small: none only), the
# highest it may; only the big one attacks buildings. No gear swaps, several fleets out at once
SHIP_RANKS = (2, 1, 1, 0, 0)
BIG = max(SHIP_RANKS)
# ordered mode: a target a fleet was sent to stays that fleet's until the ship bar shows the fleet
# idle again (at least BUSY_MIN after the send: the bar may lag), BUSY_MAX at most. Guards are
# remembered by page position (x exact: the page scrolls vertically only; y with the measured
# scroll, so a wider BUSY_DY); without a proven page position no guard is attacked while one is
# out. Saved in BUSY_FILE so that a restart keeps them
BUSY_MIN = 90
BUSY_MAX = 2 * 60 * 60
BUSY_DY = 50                 # (cells are ~33 apart: the guards right above and below are left out too)
BUSY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fortress_busy.json")
NO_TARGET_WAIT = 3 * 60      # seconds a rank waits after its search found nothing (ordered mode)
FLEET_FAIL_WAIT = 3 * 60     # seconds a fleet whose attack or repair failed is left out (ordered mode)
# the fleet number of each 派遣舰队 card ("舰队N", ZFleetNo<N>), relative to the title + the card
# spacing: its own template scores 1.0 there, the other numbers <= 0.82 (dispatch_list_fortress.png)
DISPATCH_NO = {"dx": -160, "dy": 75, "search": 15, "th": 0.9}

# result sentinels


class _Sentinel:
    """A result marker. Compared with `is`; a truth test is a bug and raises."""
    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return self.name

    def __bool__(self):
        raise TypeError(f"compare {self.name} with `is`, not by truth value")


UNCLEAR = _Sentinel("UNCLEAR")          # scroll_fortress: an end decided on an unexplained change

# something to attack on the fortress page: kind "building" (name 商店/委托站/...) or "guard"
# (name None); x, y in the reference frame; level: a guard's rank label (0 none, 1 "I", 2 "II")
class Target(namedtuple("Target", "kind name x y level", defaults=(0,))):
    __slots__ = ()
    label = property(lambda t: t.name or (f"guard {'I' * t.level}" if t.level else t.kind))


# the scroll gesture must leave an overlap that measure_shift can match (strip inset + a margin)
assert (FORTRESS["scroll_y0_dy"] - FORTRESS["scroll_y1_dy"] + 2 * DRAG_LAYOUT["strip_inset"] + 40
        < FORTRESS["content_bottom_dy"] - FORTRESS["grid_top_dy"]), "fortress scroll step too long to measure"


DIGIT_DIR = os.path.join(os.path.dirname(single_find_map["ZBase"]), "digits")
DIGIT_H = 40
_DIGITS = None


def _digit_templates():
    """Glyph templates of the yellow 战力 font, cut from screenshots with known values
    (pics/<platform>/zone/digits/<d>.png, '.' is dot.png). Tesseract read 5 as 9 on this font."""
    global _DIGITS
    if _DIGITS is None:
        _DIGITS = {}
        for fn in os.listdir(DIGIT_DIR) if os.path.isdir(DIGIT_DIR) else []:
            if fn.endswith(".png"):
                lab = "." if fn[:-4] == "dot" else fn[:-4]
                _DIGITS[lab] = cv2.imread(os.path.join(DIGIT_DIR, fn), 0)
    return _DIGITS


def read_yellow_number(rgb):
    """'513.10' from a crop of the yellow number ('万' and anything unknown are dropped)."""
    a = rgb.astype(int)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    m = ((r > 170) & (g > 140) & (b < 130)).astype(np.uint8)
    if m.sum() == 0:
        return ""
    runs, start = [], None
    for x in range(m.shape[1]):
        on = m[:, x].sum() > 0
        if on and start is None:
            start = x
        if not on and start is not None:
            runs.append((start, x))
            start = None
    if start is not None:
        runs.append((start, m.shape[1]))
    ys = np.where(m.sum(axis=1) > 0)[0]
    y0, y1 = ys.min(), ys.max() + 1
    out = ""
    for x0, x1 in runs:
        gl = (m[y0:y1, x0:x1] * 255).astype(np.uint8)
        gl = cv2.resize(gl, (max(1, int(gl.shape[1] * DIGIT_H / gl.shape[0])), DIGIT_H), interpolation=cv2.INTER_AREA)
        best, lab = -1.0, "?"
        for cand, t in _digit_templates().items():
            w = max(t.shape[1], gl.shape[1])
            if abs(t.shape[1] - gl.shape[1]) > 6:
                continue
            p = cv2.copyMakeBorder(gl, 0, 0, 0, w - gl.shape[1], cv2.BORDER_CONSTANT, value=0)
            q = cv2.copyMakeBorder(t, 0, 0, 0, w - t.shape[1], cv2.BORDER_CONSTANT, value=0)
            s = 1 - ZoneExplore.frame_diff(p, q) / 255
            if s > best:
                best, lab = s, cand
        if best >= 0.75 and lab != "?":
            out += lab
    return out


class FortressFight(ZoneExplore):
    TAB_DIM_LOOKS = 3                   # the fleet panel here is often still fading when a tab is read

    def __init__(self, dry_run=False, fortress="xz", order=None):
        super().__init__(dry_run=dry_run)
        # ordered mode (-oxz/-ozx): fleet -> rank (SHIP_RANKS), biggest first
        self.order = dict(zip(order, SHIP_RANKS)) if order else None
        self.no_target_until = {}     # rank -> time before which its search is not repeated
        self.fleet_wait = {}          # fleet -> time before which a failed attack / repair is not retried
        self.busy = self.load_busy() if order else {}   # fleet -> the target it was sent to (see BUSY_MIN)
        self.page_known = False       # page_off is measured from a proven page top
        self.attacking = None         # the fleet attack_with is sending (its own old claim does not count)
        self.screen_labels = {}       # building name -> (x, y) on the screen visible_targets read last
        self.sent_at = {}             # fleet -> time it was last sent (the ship bar may still read it idle)
        self.search_gave_up = False   # the last pick_target stopped on a page problem, not on "nothing"
        self.kind = FORTRESS_KINDS[fortress]
        self.map_key, self.title_key, self.guard_key = self.kind["map"], self.kind["title"], self.kind["guard"]
        self.holder = None        # fleet index currently carrying the best gear
        self.pending_repair = set()   # fleets whose repair could not be started yet
        self.repair_tries = {}        # fleet -> attempts made from pending_repair
        self.holder_misses = 0        # consecutive starts that could not find the gear holder
        self.lookup_unreadable = False  # the last find_gear_holder failed to read the fleet page (not: no match)
        self.swap_fails = 0           # consecutive swap_gear failures before the holder is looked for again
        self.calibrated = False       # the window scale was measured on the map
        self.swap = None              # an unfinished gear swap (see finish_swap)
        self.deferred_repair = set()  # fleets to repair once the gear has a known owner again
        self.deferred_equip = set()   # full-hp stripped fleets to 一键配队 once the gear has an owner
        self.equip_tries = {}         # fleet -> deferred 一键配队 attempts
        self.no_direct_attack = set() # holders whose check swap failed: they attack only after a swap
        self.bad_targets = {}         # fleet -> time a swap to it was abandoned at its 一键配队
        self.failed_targets = {}      # building name -> time until which it is skipped (no 袭击 / busy)
        self.tried_spots = []         # (x, page y, until) of guards skipped (no 袭击 / busy)
        self.page_off = 0.0           # how far the content is scrolled from the top (measured px)
        self.page_step = 0            # up-scrolls from the top of the fortress page (screens are 220 px apart)
        self.buildings_checked_at = 0.0   # time pick_target last saw all five buildings, none ready
        self.fortress_title = None    # title position on the open fortress page (the header does not scroll)
        mode = (" ordered: " + ", ".join(f"fleet {f} {'big' if r == BIG else 'middle' if r else 'small'}"
                                         for f, r in self.order.items())) if self.order else ""
        log(f"FortressFight ready: {self.kind['name']}{mode} (code={_code_version()})")

    # ------------------------------------------------------------------ fleet page
    EDIT_PAGES = ("ZEditFleetTitle", "ZEditCatTitle", "ZEditGearTitle", "ZEditArtifactTitle")

    # dialogs that can sit on top of 我的舰队 without dimming its tabs; the slot must not be
    # re-tapped into them
    FLEET_DIALOGS = ("ZBuyPrompt", "ZRepairPrompt", "ZContinueHint", "ZCancel")

    def edit_page_open(self, gs=None):
        """Which edit sub-page is on top, or None. One capture for all the templates."""
        if gs is None:
            self.invalidate_shot()
            gs = self.shot()[1]
        k = self.seen(*self.EDIT_PAGES, gs=gs)
        # 确认 is matched at get_center's 0.6: its template comes from the repair dialog and the
        # artifact pages' button scores lower
        if (k is None and self.seen("ZCloseHint", gs=gs) and not self.seen("ZMyFleet", gs=gs)
                and self.seen("ZRepairOk", gs=gs, th=0.6)):
            k = "ZCloseHint"        # an edit page without a learned title (e.g. 编辑高级/顶级神器)
        return k

    def confirm_edit(self, what="edit page"):
        """Press 确认 on an edit sub-page and wait until it is gone. Never 取消: that would undo
        every removal made on the page."""
        for attempt in range(3):
            page = self.edit_page_open()
            if page is None:
                return True
            ok = get_center("ZRepairOk", "Single")
            if ok is None:
                log(f"确认 not found on {page}")
                self.save_debug("no_confirm")
                return False
            self.click(ok.x, ok.y, 2, f"确认 ({what})", force=True)
            for _ in range(8):
                if not single_find(page):
                    return True
                time.sleep(0.5)
            log(f"{page} still open after 确认 (attempt {attempt + 1})")
        self.save_debug("confirm_stuck")
        return False

    def close_popup(self, tries=6):
        """Edit sub-pages are confirmed, not cancelled; the fortress page is left through its
        bottom-left "<"; then the generic popup handling."""
        if self.edit_page_open():
            self.confirm_edit("close_popup")
        if self.on_fortress_page():
            self.leave_fortress()
        return super().close_popup(tries)

    def leave_fortress(self):
        """Fortress page -> zone map through the "<" button at the bottom left. Dialogs on top
        are closed first: the dispatch list covers the "<" that page_title needs."""
        for _ in range(4):
            self.invalidate_shot()
            gs = self.shot()[1]
            k = self.seen(*self.FORTRESS_DIALOGS, gs=gs)    # a guard popup / dialog / building panel on top
            if k is not None:
                self.clear_fortress_dialogs(k)
                continue
            if self.page_title(gs) is None:
                self.fortress_title = None
                return True
            if not self.press("ZFortressBack", "< (leave fortress)", appears="ZExplore"):
                break
        self.fortress_title = None
        return self.wait_for("ZExplore", 5)

    def open_fleet_page(self):
        self.invalidate_shot()
        gs = self.shot()[1]
        if self.seen("ZMyFleet", gs=gs):
            return True
        if self.edit_page_open(gs):
            self.confirm_edit("open_fleet_page")
            if self.seen("ZMyFleet", fresh=True):
                return True
        if not self.on_map():
            log("Not on the map page, closing what is open")
            self.close_popup()
        team = self.ui("team")
        if team is None:
            team = get_center("ZTeam", "Single")        # fallback: the button's own template
        if team is None:
            log("队伍 button not found (base icon and button template both missing): is the map page open?")
            self.save_debug("no_team_button")
            return False
        log(f"Opening 队伍 at ({team.x:.0f},{team.y:.0f})")
        self.click(team.x, team.y, 2, "队伍", force=True)
        if self.wait_for("ZMyFleet", 8):
            self.wait_still()                   # the panel slides in: taps during the animation are lost
            return True
        log("我的舰队 did not appear after clicking 队伍")
        self.save_debug("fleet_page_missing")
        return False

    def save_debug(self, name):
        if not DEBUG_DIR:
            return
        self.invalidate_shot()
        color = self.shot()[0]
        path = os.path.join(DEBUG_DIR, f"{time.strftime('%H%M%S')}_{name}.png")
        cv2.imwrite(path, cv2.cvtColor(color, cv2.COLOR_RGB2BGR))
        log(f"Debug shot saved: {path}")

    def fleet_title(self):
        return self.anchor("ZMyFleet")

    def close_fleet_page(self):
        """Close 我的舰队 (and anything on top of it). The top bar is dimmed under the panel, so
        ship status and hp can only be read once it is closed."""
        for _ in range(4):
            if self.edit_page_open():
                self.confirm_edit("close_fleet_page")
                continue
            title = self.fleet_title()
            if title is None or not single_find("ZMyFleet"):
                break
            self.click(title.x + EQUIP_LAYOUT["close_dx"], title.y + EQUIP_LAYOUT["close_dy"], 1.5,
                       "dimmed top bar (close 我的舰队)", force=True)
        return self.close_popup()

    def read_power(self):
        """战力 of the fleet whose tab is open, as a float in 万, or None."""
        title = self.fleet_title()
        if title is None:
            return None
        color = np.array(pyautogui.screenshot())
        cx, cy = title.x + EQUIP_LAYOUT["power_dx"], title.y + EQUIP_LAYOUT["power_dy"]
        x1, x2 = int((cx - EQUIP_LAYOUT["power_half_w"]) * self.sft), int((cx + EQUIP_LAYOUT["power_half_w"]) * self.sft)
        y1, y2 = int((cy - EQUIP_LAYOUT["power_half_h"]) * self.sft), int((cy + EQUIP_LAYOUT["power_half_h"]) * self.sft)
        crop = color[y1:y2, x1:x2]
        if DEBUG_DIR:
            cv2.imwrite(os.path.join(DEBUG_DIR, f"power_{time.strftime('%H%M%S')}.png"), cv2.cvtColor(crop, cv2.COLOR_RGB2BGR))
        txt = read_yellow_number(crop)
        if not txt:
            return None
        whole, _, frac = txt.partition(".")
        try:
            return float(f"{whole}.{frac[:2]}") if frac else float(whole)
        except ValueError:
            return None

    def loadout_score(self):
        """How well the open tab's equipment grid matches the standard best loadout (0..1)."""
        title = self.fleet_title()
        if title is None:
            return 0.0
        self.invalidate_shot()
        gray = self.shot()[1]
        t = self.full_template("ZLoadoutStandard")
        if t is None:
            return 0.0
        cx, cy = title.x + EQUIP_LAYOUT["loadout_dx"], title.y + EQUIP_LAYOUT["loadout_dy"]
        h, w = t.shape
        x1, y1 = int(cx * self.sft - w / 2) - 30, int(cy * self.sft - h / 2) - 30
        x2, y2 = x1 + w + 60, y1 + h + 60
        sub = gray[max(0, y1):y2, max(0, x1):x2]
        if sub.shape[0] < h or sub.shape[1] < w:
            return 0.0
        return float(cv2.minMaxLoc(cv2.matchTemplate(sub, t, cv2.TM_CCOEFF_NORMED))[1])

    def find_gear_holder(self):
        """The fleet carrying the best equipment: all five tabs are compared against the
        standard loadout screenshot. 战力 is logged for reference only. lookup_unreadable tells
        a None from an unreadable page apart from one with no matching fleet."""
        self.lookup_unreadable = True
        if not self.open_fleet_page():
            return None
        self.lookup_unreadable = False
        powers, scores = {}, {}
        for i in range(1, SHIP_LAYOUT["slots"] + 1):
            if not self.select_tab(i):
                # a weaker copy of the same items also matches the screenshot: with the real
                # holder's tab possibly among the unseen ones no election is safe
                log(f"Fleet {i}: tab could not be shown; gear holder unknown")
                self.lookup_unreadable = True
                return None
            powers[i] = self.read_power()
            scores[i] = self.loadout_score()
        log("Fleet power: " + ", ".join(f"{i}:{p}" for i, p in powers.items())
            + " | loadout match: " + ", ".join(f"{i}:{s:.2f}" for i, s in scores.items()))
        matching = [i for i, s in scores.items() if s >= EQUIP_LAYOUT["loadout_th"]]
        if len(matching) == 1:
            log(f"Best gear is on fleet {matching[0]} (loadout match {scores[matching[0]]:.2f})")
            return matching[0]
        if len(matching) > 1:
            # several tabs look like the standard loadout: the one with the highest 战力 has the
            # real gear (the others carry weaker copies of the same items)
            best = max(matching, key=lambda i: powers.get(i) or 0.0)
            log(f"Fleets {matching} all match the standard loadout; fleet {best} has the highest 战力")
            return best
        log("No fleet matches the standard loadout (threshold "
            f"{EQUIP_LAYOUT['loadout_th']}); best match is fleet {max(scores, key=scores.get)} at {max(scores.values()):.2f}")
        return None

    # ------------------------------------------------------------------ equipment moves
    def unequip_all(self, index):
        """Remove every piece of gear from fleet `index` through the 编辑舰队 tabs."""
        if not self.open_slot_page(index, EQUIP_LAYOUT["slot_dx"][0], EQUIP_LAYOUT["row_dy"][0], "gear slot",
                                   lambda: single_find("ZEditFleetTitle")):
            log("编辑舰队 did not open")
            return False
        et = get_center("ZEditFleetTitle", "Single")
        if et is None:
            log("编辑舰队 title lost after opening")
            return False
        for name, tab_dx, clicks in EDIT_LAYOUT["tabs"]:
            if not self.select_edit_tab(et, name, tab_dx):
                log(f"  {name}: tab could not be selected, skipped")
                self.save_debug(f"tab_{name}")
                continue
            n = 0
            for dx, dy, times in clicks:
                n += self.burst(et.x + dx, et.y + dy, times)
            log(f"  {name}: {n} removal tap(s)")
            time.sleep(0.5)
        ok = self.confirm_edit("编辑舰队")
        log("Gear removed and confirmed" if ok else "编辑舰队 could not be confirmed")
        if ok:
            self.unequip_cats(index)
            # 残骸本源 is among the right-column artifacts: 一键配队 on the next fleet only takes it
            # once it is off, so a failure here fails the strip (repeated on the next try)
            ok = self.unequip_right_artifacts(index)
            if UNEQUIP_BOTTOM_ARTIFACTS:
                self.unequip_bottom_artifacts(index)
        return ok

    def unequip_right_artifacts(self, index):
        """The two artifact slots in the right column each open their own edit page; the
        equipped artifact sits in the preview area above 取消/确认, tapping it removes it. False
        when a page could not be opened or confirmed."""
        all_ok = True
        for row in ARTIFACT_SLOTS["rows"]:
            if not self.open_slot_page(index, EQUIP_LAYOUT["slot_dx"][4], EQUIP_LAYOUT["row_dy"][row],
                                       f"artifact slot row {row + 1}", self.artifact_page_open):
                all_ok = False
                continue
            ok = get_center("ZRepairOk", "Single")
            if ok is None:
                log("确认 not found on the artifact page")
                self.close_popup()
                all_ok = False
                continue
            px, py = ARTIFACT_SLOTS["preview_from_confirm"]
            self.burst(ok.x + px, ok.y + py, 3)
            if not self.confirm_edit(f"artifact row {row + 1}"):
                all_ok = False
        return all_ok

    def tab_selected(self, et, tab_dx):
        """The selected tab shows a bright underline below its label."""
        self.invalidate_shot()
        band = self.band(et.x + tab_dx, et.y + EDIT_LAYOUT["tab_underline_dy"], EDIT_LAYOUT["tab_half_w"], 5)
        if band.size == 0:
            return False
        rows = band.mean(axis=1)
        return float(rows.max()) > 110          # unselected tabs stay below ~45 here

    def select_edit_tab(self, et, name, tab_dx, tab_dy=None):
        """Tab of an edit page (编辑舰队 / 编辑装备): tapped until its underline shows."""
        dy = EDIT_LAYOUT["tab_dy"] if tab_dy is None else tab_dy
        return self.select_until(f"tab {name}", lambda: self.tab_selected(et, tab_dx),
                                 lambda: self.burst(et.x + tab_dx, et.y + dy, TAP_BURST),
                                 EDIT_LAYOUT["tab_retries"])

    def artifact_page_open(self):
        """An artifact edit page (编辑低级/高级/顶级神器): the fleet page is gone and the page has
        its confirm button. ZCloseHint alone is not enough, the fleet page shows it too."""
        # edit_page_open() reports "ZCloseHint" for an edit page without a learned title, which
        # is what the 高级/顶级 artifact pages are; the other titled pages are neighbours' slots
        return self.edit_page_open() in ("ZEditArtifactTitle", "ZCloseHint")

    def open_slot_page(self, index, dx, dy, what, opened, tries=3, wait=8.0):
        """Tap a slot on fleet `index`'s tab until `opened()` is true (the tap may be dropped or
        land during a transition). When the fleet page is still showing after a failed tap the
        slot is simply tapped again; the page is only closed and re-opened when something else
        is on top."""
        for attempt in range(tries):
            t0 = time.time()
            if not self.open_fleet_page() or not self.select_tab(index):
                log(f"{what}: fleet page not available (attempt {attempt + 1})")
                self.close_popup()
                continue
            title = self.fleet_title()
            if title is None:               # a transient miss (tab animation): look once more
                self.invalidate_shot()
                title = self.fleet_title()
            if title is None:
                log(f"{what}: 我的舰队 title lost (attempt {attempt + 1})")
                self.close_popup()
                continue
            self.click(title.x + dx, title.y + dy, 2, what, force=True)
            start = time.time()
            while time.time() - start < wait:
                if opened():
                    time.sleep(0.5)          # let the page settle before its anchors are read
                    return True
                time.sleep(0.5)
            self.save_debug(f"slot_{what}_try{attempt + 1}")
            # ZMyFleet last: it is also visible under a dialog; an edit page replaces it
            k = self.seen(*self.EDIT_PAGES, *self.FLEET_DIALOGS, "ZMyFleet", fresh=True)
            if k == "ZMyFleet":
                log(f"{what}: page did not open in {time.time() - t0:.0f} s, tapping again (attempt {attempt + 1})")
                continue
            log(f"{what}: page did not open in {time.time() - t0:.0f} s; closing what is on top (attempt {attempt + 1})")
            self.close_popup()
        self.save_debug(f"slot_{what}")
        return False

    def unequip_cats(self, index):
        """The cat slot (left of the artifact) opens 编辑猫护法; the three equipped cats sit at
        the bottom, tapping the leftmost one repeatedly removes them."""
        dx, dy = CAT_LAYOUT["slot"]
        if not self.open_slot_page(index, dx, dy, "cat slot", lambda: single_find("ZEditCatTitle")):
            log("编辑猫护法 did not open")
            return False
        ct = get_center("ZEditCatTitle", "Single")
        if ct is None:
            log("编辑猫护法 title lost after opening")
            return False
        ix, iy = CAT_LAYOUT["item"]
        self.burst(ct.x + ix, ct.y + iy, CAT_LAYOUT["count"] * 3)
        ok = self.confirm_edit("编辑猫护法")
        log("Cats removed" if ok else "编辑猫护法 could not be confirmed")
        return ok

    def unequip_bottom_artifacts(self, index):
        """The four bottom-row artifact slots open 编辑装备 (tabs 炬团令牌/烙印/战旗/密契); the
        equipped one is shown in the preview area. Clicking the preview is assumed to remove it."""
        if not self.open_slot_page(index, EQUIP_LAYOUT["slot_dx"][0], EQUIP_LAYOUT["row_dy"][4], "bottom artifact slot",
                                   lambda: single_find("ZEditGearTitle")):
            log("编辑装备 did not open")
            return False
        gt = get_center("ZEditGearTitle", "Single")
        if gt is None:
            log("编辑装备 title lost after opening")
            return False
        for tab_dx in GEAR_LAYOUT["tab_dx"]:
            if not self.select_edit_tab(gt, f"gear {tab_dx:+}", tab_dx, GEAR_LAYOUT["tab_dy"]):
                log(f"  gear tab {tab_dx:+} underline not seen; tapping its preview anyway")
            px, py = GEAR_LAYOUT["preview"]
            self.burst(gt.x + px, gt.y + py, 3)
        ok = self.confirm_edit("编辑装备")
        log("Bottom artifacts cleared" if ok else "编辑装备 could not be confirmed")
        return ok

    def auto_equip(self, index):
        if not self.open_fleet_page() or not self.select_tab(index):
            return False
        b = get_center("ZAutoEquip", "Single")
        if b is None:
            log("一键配队 not found")
            return False
        self.burst(b.x, b.y, TAP_BURST)             # idempotent: repeated taps re-apply the same loadout
        time.sleep(2)
        if self.wait_for("ZRepairOk", 3):           # a confirmation dialog, if any
            self.click_button("ZRepairOk", 2, force=True)
        return True

    def re_equip(self, fleets):
        """一键配队 on stripped full-hp fleets (no loadout left)."""
        for fleet in sorted(fleets):
            if self.retry_later(self.equip_tries, fleet, self.auto_equip(fleet), "一键配队", DEFERRED_EQUIP_TRIES):
                self.deferred_equip.add(fleet)

    def repair_fleet(self, index):
        """一键配队 first (a fleet without a loadout cannot be repaired), then the shared
        verified repair (修理舰队 -> 确认 -> "舰队修理中..." shown)."""
        if not self.auto_equip(index):
            return False
        ok = self.confirm_repair(index)
        if not ok:
            self.save_debug(f"repair_failed_{index}")
        return ok

    def swap_gear(self, holder, target, ships):
        """Strip the gear holder and give the gear to `target` (finish_swap does the equipping
        part; when it fails the swap is remembered and resumed on the next pass). The fleet
        handed in (it was due a swap because of its hp) and the actually stripped holder are
        repaired afterwards unless `ships` shows them at full hp; a stripped holder at full hp
        gets 一键配队 instead (a fleet without a loadout)."""
        log(f"Move the best gear from fleet {holder} to fleet {target}")
        not_full = lambda i: ships.get(i, {}).get("hp") != FULL_HP     # hp unknown counts as damaged
        damaged = {holder} if not_full(holder) else set()   # (repaired even when another fleet turns out
                                                            # to hold the gear: it was due a swap for its hp)
        # the fleet page is open now anyway: make sure the remembered holder really has the gear
        if not self.open_fleet_page() or not self.select_tab(holder):
            self.close_fleet_page()
            return False
        score = self.loadout_score()
        if score < EQUIP_LAYOUT["loadout_th"]:
            log(f"Fleet {holder} does not match the standard loadout ({score:.2f}); re-checking all tabs")
            found = self.find_gear_holder()
            if found is None:
                self.holder = None              # next pass looks for the gear afresh
                self.close_fleet_page()
                return False
            holder = self.holder = found
            if not_full(found):
                damaged.add(found)              # stripped below: repaired too
        # from here on the gear may be loose: the swap is remembered and resumed until it is done
        self.swap = self.make_swap(holder, target, to_repair=damaged, re_equip={holder} - damaged)
        if holder == target:                    # the gear is already on the fleet about to attack
            log(f"Fleet {target} already carries the best gear; nothing to move")
        return self.finish_swap()

    @staticmethod
    def make_swap(holder, target, to_repair=(), re_equip=()):
        """The record of a gear swap (holder == target: a check of the holder). Keys:
        unequipped (the holder was stripped), equipped (一键配队 on the target done and its loadout
        checked), tries, to_repair / re_equip (fleets for repair or 一键配队 when it ends),
        errored (a pass ended in an exception: abandoned at once, the gear must not stay loose)."""
        return {"holder": holder, "target": target, "unequipped": holder == target, "tries": 0,
                "to_repair": set(to_repair) - {target}, "re_equip": set(re_equip) - {target},
                "equipped": False, "errored": False}

    def finish_swap(self):
        """A gear swap from the stripping on, in a fixed order: unequip the holder (unless done),
        一键配队 on the target (it also takes 残骸本源), loadout check, then the holder is recorded
        and the fleets in to_repair (the stripped holder when damaged, the damaged fleet the swap
        was made for) are repaired. With holder == target it is a check of the holder itself.
        Returns True when done, False (keeping self.swap for the next pass) as soon as a step fails."""
        sw = self.swap
        try:
            r = self._finish_swap()
        except Exception:
            sw["errored"] = True                # run() restarts the pass; _run abandons the swap first
            raise
        if not r:
            sw["tries"] += 1
        return r

    def _finish_swap(self):
        sw = self.swap
        target = sw["target"]
        try:
            if not sw["unequipped"]:            # (again) strip the holder; a partial strip is completed
                if not self.unequip_all(sw["holder"]):
                    return False
                sw["unequipped"] = True
            if not sw["equipped"]:
                if not self.auto_equip(target):
                    return False
                score = self.loadout_score()
                log(f"Fleet {target} loadout vs standard: {score:.2f}")
                if score < EQUIP_LAYOUT["loadout_th"]:
                    if sw["holder"] == target:  # a check of the holder: it must really carry the gear
                        log("Loadout differs from the standard screenshot; this fleet does not hold the gear")
                        return False
                    log("Loadout differs from the standard screenshot; check the equipment by hand")
                sw["equipped"] = True
            self.holder = target
            self.no_direct_attack.discard(target)
            for fleet in sorted(sw["to_repair"]):
                if not self.repair_fleet(fleet):
                    self.pending_repair.add(fleet)  # retried at the start of every later pass
            self.re_equip(sw["re_equip"])
            self.swap = None
            return True
        finally:
            self.close_fleet_page()

    # ------------------------------------------------------------------ fortress page
    def page_title(self, gray=None):
        """The fortress page's title (logical px), or None: the best title match (MATCH_TH)
        with the page's "<" at TITLE_TO_BACK from it (window-independent)."""
        if gray is None:
            gray = self.shot()[1]
        t, back = self.full_template(self.title_key), self.full_template("ZFortressBack")
        if t is None or back is None:
            return None
        _, conf, _, loc = cv2.minMaxLoc(cv2.matchTemplate(gray, t, cv2.TM_CCOEFF_NORMED))
        if conf < MATCH_TH:
            return None
        title = Point((loc[0] + t.shape[1] / 2) / self.sft, (loc[1] + t.shape[0] / 2) / self.sft)
        dx, dy, tol = TITLE_TO_BACK
        bh, bw = back.shape
        cx, cy = (title.x + dx) * self.sft, (title.y + dy) * self.sft
        r = tol * self.sft
        x1, y1 = int(max(0, cx - bw / 2 - r)), int(max(0, cy - bh / 2 - r))
        x2, y2 = int(min(gray.shape[1], cx + bw / 2 + r)), int(min(gray.shape[0], cy + bh / 2 + r))
        if x2 - x1 < bw or y2 - y1 < bh:
            return None
        _, bconf, _, _ = cv2.minMaxLoc(cv2.matchTemplate(gray[y1:y2, x1:x2], back, cv2.TM_CCOEFF_NORMED))
        return title if bconf >= MATCH_TH else None

    def on_fortress_page(self):
        self.invalidate_shot()
        return self.page_title() is not None

    def wait_fortress_page(self, timeout):
        """Poll until the fortress page shows (one more look at the deadline, like wait_seen)."""
        start = time.time()
        while True:
            if self.on_fortress_page():
                return True
            if time.time() - start >= timeout:
                return False
            time.sleep(0.5)

    def open_fortress(self):
        """Zone map -> fortress icon -> info popup -> 袭击 -> fortress page. Each step is
        retried: taps on the map are sometimes dropped by the emulator."""
        if self.on_fortress_page():
            if self.fortress_title is None:     # first sight of the page this run
                self.settle_fresh_page()
            return True
        if not self.on_map():
            self.close_popup()
        # the fortress icon template was captured at 75%; the game may come up at 50%
        self.ensure_zoom()
        for attempt in range(3):
            if not self.on_map():
                self.close_popup()          # a leftover popup from the previous attempt hides the icon
            self.invalidate_shot()
            # the program is started in the central zone with the fortress on screen; no zone logic
            icon = get_center(self.map_key, "Single")
            if icon is None:
                log(f"{self.kind['name']} icon not on screen (attempt {attempt + 1})")
                self.save_debug("no_fortress_icon")
                continue
            log(f"{self.kind['name']} icon at ({icon.x:.0f},{icon.y:.0f})")
            # the icon opens an info popup (位置/坐标/距离/守卫等级) with a 袭击 button; a second
            # tap is only sent when nothing opened (the popup covers the icon with 前往 etc.)
            opened = self.tap_until(icon.x, icon.y, self.kind["name"], TAP_BURST, (ATTACK, "ZGo", self.title_key),
                                    want=None, timeout=FORTRESS["icon_timeout"])
            if opened is None:
                log(f"Fortress icon did not respond (attempt {attempt + 1})")
                continue
            if opened != self.title_key or not self.on_fortress_page():   # (the popup shows the name too)
                # 袭击 is drawn last: wait for it (or 前往) before pressing
                k = self.wait_seen((ATTACK, "ZGo"), FORTRESS["want_grace"]) if opened != ATTACK else ATTACK
                log(f"Fortress popup ({opened}) -> {k or 'no button'}")
                if k == ATTACK:
                    self.press(ATTACK, "袭击 (fortress popup)", gone=ATTACK)
                elif k == "ZGo":
                    log("No 袭击 on the popup, using 前往")
                    self.click_button("ZGo", 2.5, force=True)
            if self.wait_fortress_page(8):      # the page may take a few seconds to load
                self.fortress_title = None
                self.settle_fresh_page()
                return True
            log(f"Fortress page not seen after the popup (attempt {attempt + 1})")
            self.close_popup()
        self.save_debug("fortress_page_missing")
        return False

    def guard_cells(self, gray, title):
        """[(x, y, bright, level)] of every guard cell on the fortress page (logical px); the
        level (guard_level) is read on bright cells only (0 on dim ones)."""
        t = self.full_template(self.guard_key)
        h = int(FORTRESS["cell_half"] * self.sft)
        out = []
        for cx, cy, conf in match_all(gray, t, FORTRESS["guard_th"]):
            x, y = cx / self.sft, cy / self.sft
            if title is not None and y < title.y + FORTRESS["grid_top_dy"]:
                continue
            cell = gray[cy - h:cy + h, cx - h:cx + h]
            bright = float(cell.mean()) >= self.kind["bright_min"]
            out.append((x, y, bright, self.guard_level(gray, cx, cy) if bright else 0))
        return out

    def guard_level(self, gray, cx, cy):
        """The rank label of the guard cell matched at physical (cx, cy): the number of bright
        bars in GUARD_LABEL's box (0, 1 "I" or 2 "II"). Each column is judged by its brighter
        two thirds (a bar is shorter than the box), against the darkest column within
        bar_reach (a bar is narrow; a glow or the cell's edge brightens a whole side)."""
        x0, y0, x1, y1 = (int(v * self.sft) for v in GUARD_LABEL["box"])
        p = gray[max(0, cy + y0):max(0, cy + y1), max(0, cx + x0):max(0, cx + x1)].astype(int)
        if p.shape[0] < 3 or p.shape[1] < 3:
            return 0
        prof = np.sort(p, axis=0)[p.shape[0] // 3:].mean(axis=0)
        w = max(1, int(GUARD_LABEL["bar_reach"] * self.sft))
        pad = np.pad(prof, w, mode="edge")
        rise = prof - np.array([pad[i:i + 2 * w + 1].min() for i in range(len(prof))])
        if rise.max() < GUARD_LABEL["contrast"]:
            return 0
        bars = rise > rise.max() / 2
        return min(2, int(bars[0]) + int(np.count_nonzero(bars[1:] & ~bars[:-1])))

    # building name labels on the fortress page (商店/委托站/指挥所 on the first screen, 资源库/
    # 军事基地 further down). A ready building (guards around it cleared and recovered) is bright
    # above its label: pages/boss/building_ready.png 商店 ~118, the still guarded 委托站/指挥所
    # ~50. A raided one stays bright but wears a yellow 已损坏 badge over the building
    # (building_broken.png) until it recovers. A ready building's tap shows 袭击 below the label
    # (building_clicked.png), the same button and dispatch list as a guard.
    BUILDING_LABELS = (("ZShopLabel", "商店"), ("ZDepotLabel", "委托站"), ("ZCommandLabel", "指挥所"),
                       ("ZResourceLabel", "资源库"), ("ZMilitaryLabel", "军事基地"))
    BUILDING_LABEL_TH = 0.8     # real labels match >= 0.97 on every page screenshot, other labels <= 0.68
    # the 已损坏 badge is a yellow-framed box over the building (building_broken.png): its frame is
    # the largest yellow blob above the label, ~40x15 logical px with a low fill ratio. A selected
    # building's yellow-green corner brackets (building_clicked.png) are ~10x15 and the ready
    # 商店's yellow detail is a few px: both fall outside the size window.
    BADGE_BOX = (45, 70, 5)     # search area above the label: +-dx, from dy_top to dy_bottom above
    BADGE_W, BADGE_H = (30, 55), (11, 22)
    BADGE_RGB = (150, 110, 110, 80)     # r >, g >, b <, r - b >

    def badge_above(self, color, cx, cy):
        """Whether a 已损坏 badge frame sits above the label at physical (cx, cy)."""
        dx, top, bottom = (int(v * self.sft) for v in self.BADGE_BOX)
        p = color[max(0, cy - top):cy - bottom, max(0, cx - dx):cx + dx].astype(int)
        if p.size == 0:
            return False
        r, g, b = p[..., 0], p[..., 1], p[..., 2]
        rmin, gmin, bmax, rb = self.BADGE_RGB
        mask = ((r > rmin) & (g > gmin) & (b < bmax) & (r - b > rb)).astype(np.uint8)
        n, _, stats, _ = cv2.connectedComponentsWithStats(mask)
        for x, y, w, h, area in stats[1:]:
            if (self.BADGE_W[0] * self.sft <= w <= self.BADGE_W[1] * self.sft
                    and self.BADGE_H[0] * self.sft <= h <= self.BADGE_H[1] * self.sft):
                return True
        return False

    def buildings(self, color, gray, title, names=None):
        """[(name, x, y, state)] for every building label on screen, top to bottom; state is
        "ready", "dim" (guarded) or "broken" (已损坏 badge, see badge_above). Labels are matched
        below the header only (on the unscrolled page 商店's label sits ~324 px below the
        title, a label nearer than grid_top_dy has its building hidden under the header)."""
        top, bottom, half = (int(v * self.sft) for v in FORTRESS["building_patch"])
        # the patch above the label must lie below the header too
        y0 = int((title.y + FORTRESS["grid_top_dy"]) * self.sft) + top if title is not None else 0
        y0 = max(0, min(y0, gray.shape[0]))
        below = gray[y0:]
        found = []
        for key, name in self.BUILDING_LABELS:
            if names is not None and name not in names:
                continue
            hits = match_all(below, self.full_template(key), self.BUILDING_LABEL_TH)
            if not hits:
                continue
            cx, cy, _ = hits[0]                 # match_all yields the best match first
            cy += y0
            if cy - top < 0:
                continue
            patch = gray[cy - top:cy - bottom, max(0, cx - half):cx + half]      # the building above its label
            bright = float(patch.mean()) >= self.kind["building_bright_min"]
            state = "broken" if self.badge_above(color, cx, cy) else "ready" if bright else "dim"
            found.append((name, cx / self.sft, cy / self.sft - FORTRESS["building_tap_dy"], state))
        return sorted(found, key=lambda b: (b[2], b[1]))

    def visible_targets(self):
        """(ready building or None, bright guards top to bottom, names of the building labels
        on screen); one capture for all. Buildings whose taps showed no 袭击 recently and guard
        spots (screen position at this scroll step) that opened nothing are skipped, and so are
        the guards other fleets were sent to (self.busy; only the big ship attacks buildings)."""
        self.invalidate_shot()
        color, gray = self.shot()
        title = self.page_title(gray) or self.fortress_title   # the header does not scroll
        if title is not None:
            self.fortress_title = title
        blds = self.buildings(color, gray, title)
        now = time.time()
        for name, until in list(self.failed_targets.items()):
            if now > until:
                del self.failed_targets[name]
        log("Buildings: " + (", ".join(f"{n} {st}{' (skipped)' if n in self.failed_targets else ''}" for n, _, _, st in blds)
                             or "none on screen"))
        building = next((Target("building", n, x, y) for n, x, y, st in blds
                         if st == "ready" and n not in self.failed_targets), None)
        self.screen_labels = {n: (x, y) for n, x, y, _ in blds}
        cells = self.guard_cells(gray, title)
        r = FORTRESS["spot_radius"]
        self.tried_spots = [t for t in self.tried_spots if now <= t[2]]
        claims = [b for f, b in self.busy.items() if f != self.attacking and b["fortress"] == self.kind["name"]]
        if self.order and (title is None or not self.page_known):
            log("Page position not proven: no guard is attacked (it could not be kept from the other fleets)")
            self.search_gave_up = True          # (a page problem, not "nothing to attack")
            cells = []
        bright = sorted((c for c in cells if c[2]
                         and not any(abs(c[0] - sx) < r and abs(c[1] + self.page_off - sy) < r for sx, sy, _ in self.tried_spots)
                         and not any(self.claimed(b, c[0], c[1], title) for b in claims)),
                        key=lambda c: (c[1], c[0]))
        levels = [sum(1 for c in bright if c[3] == lv) for lv in (2, 1, 0)]
        log(f"Guards: {len(cells)} cells, {len(bright)} attackable (II {levels[0]}, I {levels[1]}, none {levels[2]})")
        guards = [Target("guard", None, x, y, lv) for x, y, _, lv in bright]
        return building, guards, {n for n, _, _, _ in blds}

    def scroll_fortress(self, up=True):
        """Scroll the fortress page (it is taller than the screen). True: moved; False: did not
        move, the end was reached; None: could not scroll (page not there, a dialog that did not
        close, or the gesture opening a dialog in both columns). The content area is compared
        before and after the gesture: a measured move is a real scroll; a small change (a glow)
        or none is the end; a large unmatched change or a darker page gets the one costly
        template check for a dialog the gesture may have opened (closed, then one more gesture
        in another column); without a dialog any other change counts as the end (closing
        what can be closed when the page got darker) and is returned as UNCLEAR (compare the
        result with `is`; scroll_to_top double-checks it)."""
        from zone_explore import drag as _drag
        if self.fortress_title is None:
            self.invalidate_shot()
        title = self.fortress_title or self.page_title()
        if title is None:
            return None                         # not on the fortress page (None, not "end")
        self.fortress_title = title             # the header does not scroll
        y0, y1 = title.y + FORTRESS["scroll_y0_dy"], title.y + FORTRESS["scroll_y1_dy"]
        if not up:
            y0, y1 = y1, y0
        region = None
        for attempt, x_dx in enumerate(FORTRESS["scroll_x_dxs"]):
            if attempt:
                self.wait_still()               # after a closed dialog: let the page settle
            self.invalidate_shot()              # a frame of a fade still running must not be `before`
            gray = self.shot()[1]
            if region is None:                  # the content between the header and 停机坪
                h, w = gray.shape
                region = (max(0, title.x - FORTRESS["grid_half_w"]), title.y + FORTRESS["grid_top_dy"],
                          min(w / self.sft, title.x + FORTRESS["grid_half_w"]),
                          min(h / self.sft, title.y + FORTRESS["content_bottom_dy"]))
            before = self.grab_region(region)
            if before.size == 0:
                log("Fortress page content area is off screen")
                return None
            if self.dry_run:
                log(f"[DRY] scrolling the fortress page {'up' if up else 'down'} (navigation)")
            rx0, ry0 = self.to_real(title.x + x_dx, y0)
            rx1, ry1 = self.to_real(title.x + x_dx, y1)
            _drag(rx0, ry0, rx1, ry1, press=FORTRESS["press"])
            self.invalidate_shot()
            time.sleep(0.6)
            self.wait_still()
            after = self.grab_region(region)
            diff = self.frame_diff(before, after)
            shift = self.measure_shift(before, after, 0, y1 - y0) if diff > DRAG_LAYOUT["static_diff"] else None
            # content moves up (dy < 0) for an up-scroll, down for a down-scroll; a move the other
            # way is the spring-back of an overscroll
            measured = shift is not None and abs(shift[1]) >= 2 and (shift[1] < 0) == up
            moved = measured and abs(shift[1]) >= FORTRESS["min_step"]
            if measured and not moved:          # a short move (the last bit before the end): look, no step
                log(f"Fortress page scroll {'up' if up else 'down'}: moved {abs(shift[1]):.0f} px only (step kept)")
                self.page_off = max(0.0, self.page_off - shift[1])     # (content up: further down the page)
                return True
            if not moved:
                # no measured scroll. A small change (a glow) is the end; a big one or a darker
                # page (a dialog dims the page evenly, which the strip match does not see, and
                # a popup may cover only a corner) gets the one costly template check
                dimmed = float(after.mean()) < float(before.mean()) * FORTRESS["dim_ratio"]
                if not dimmed and diff <= FORTRESS["move_diff"]:
                    break
                k = self.seen(*self.FORTRESS_DIALOGS)
                if k is not None:
                    log(f"Fortress scroll gesture opened a dialog ({k}); closing it (column {attempt + 1})")
                    if not self.clear_fortress_dialogs(k):
                        log("The dialog did not close")
                        return None
                    continue
                if dimmed:                      # darker and no known dialog: something unknown on top?
                    log("Fortress page got dark after the scroll gesture; closing what can be closed")
                    self.save_debug("scroll_dark")
                    self.clear_fortress_dialogs()
                    return UNCLEAR              # treated as the end; the next look decides
                # matched in place / spring-back, or a change the strip match could not place: no
                # evidence of a scroll (an animation, a cell cleared)
                log("Fortress page changed without a measurable scroll; treated as the end")
                return UNCLEAR
            self.page_step = max(0, self.page_step + (1 if up else -1))
            self.page_off = max(0.0, self.page_off - shift[1])
            log(f"Fortress page scroll {'up' if up else 'down'}: moved (step {self.page_step})")
            return True
        else:
            log("Fortress scroll gesture opened a dialog in both columns; the page did not move")
            return None
        log(f"Fortress page scroll {'up' if up else 'down'}: end")
        return False

    def settle_fresh_page(self):
        """A fortress page just opened or first seen: the game may restore the last scroll
        position, so the page is brought to the top unless its top layout already shows."""
        self.wait_still()                       # the page may still be loading
        at_top = self.page_at_top()
        if not at_top:                          # the labels draw after the header: look once more
            time.sleep(1.0)
            at_top = self.page_at_top()
        if at_top:
            self.page_step, self.page_off, self.page_known = 0, 0.0, True
        elif self.scroll_to_top() is None:
            log("Fortress page could not be brought to the top; its upper part may be missed this pass")
            self.page_step, self.page_off, self.tried_spots = 0, 0.0, []    # a re-opened page: position unknown
            self.page_known = False

    def page_at_top(self):
        """The unscrolled page: 商店's label at its place below the title (a restored scroll of
        a hundred px still shows the label, lower)."""
        self.invalidate_shot()
        color, gray = self.shot()
        title = self.page_title(gray)
        if title is None:
            return False
        self.fortress_title = title
        dy, tol = FORTRESS["shop_label_dy"]
        tap_dy = FORTRESS["building_tap_dy"]
        return any(abs(y + tap_dy - title.y - dy) <= tol
                   for n, _, y, _ in self.buildings(color, gray, title, names=("商店",)))

    def scroll_to_top(self):
        """Scroll down until the page stops moving. The number of moves (0: it was at the top
        already), or None when the page is not there / cannot be scrolled."""
        unclear_seen, moves = False, 0
        for _ in range(FORTRESS["max_scrolls"] + 1):
            moved = self.scroll_fortress(up=False)
            if moved is None:
                return None                     # the page did not move: its position is still known
            if moved is True:
                unclear_seen, moves = False, moves + 1
                continue
            if moved is UNCLEAR or unclear_seen:    # an end that needs the top layout as proof
                if not self.page_at_top():
                    if not unclear_seen:
                        log("The scroll stopped on an unexplained change, not at the top; trying again")
                        unclear_seen = True
                        continue
                    log("The page still does not show its top; taken as the top without proof")
                    self.tried_spots = []       # (the remembered guard spots may not fit)
                    self.page_step, self.page_off, self.page_known = 0, 0.0, False
                    return moves
            self.page_step, self.page_off, self.page_known = 0, 0.0, True
            return moves
        self.page_step, self.page_off, self.tried_spots = 0, 0.0, []    # position unknown
        self.page_known = False
        return None

    @staticmethod
    def choose(guards, rank):
        """The guard to attack from one screen's list (top to bottom): the topmost one (rank
        None), or the topmost of the highest level up to `rank`."""
        if rank is None:
            return guards[0] if guards else None
        ok = [g for g in guards if g.level <= rank]
        return max(ok, key=lambda g: (g.level, -g.y, -g.x)) if ok else None

    def pick_target(self, rank=None, buildings=True):
        """A ready building anywhere on the page first (all five: 商店/委托站/指挥所 on the first
        screen, 资源库/军事基地 further down), only then a bright guard. The page is walked from
        the top down until every label was seen (then a bright guard on that screen, or on the
        first screen that showed one, or further down) or the page ends. Every target comes
        from a reading of the screen it is tapped on. When all five were seen without a ready
        one less than BUILDINGS_FRESH ago (a retry within one attack), guards are looked for
        from the screen in front instead. The page is left where the search ended.
        Ordered mode: `rank` caps the guard level and the highest level seen on the walk wins
        (the first screen that showed it); without `buildings` they are not attacked, and the
        walk ends early on a guard of level `rank`."""
        self.search_gave_up = False
        if time.time() - self.buildings_checked_at < BUILDINGS_FRESH:
            return self.guard_search(rank, buildings)
        if self.page_at_top():
            self.page_step, self.page_off, self.page_known = 0, 0.0, True   # (the count may have drifted)
        elif self.scroll_to_top() is None:
            log("Fortress page could not be brought to the top; giving up this pass")
            self.search_gave_up = True
            return None
        names = {n for _, n in self.BUILDING_LABELS}
        best = 0 if rank is None else rank     # the level nothing further down can beat
        labels, guard_step, step_level = set(), None, -1
        last = FORTRESS["max_scrolls"]
        for i in range(last + 1):
            building, guards, seen = self.visible_targets()
            if building is not None and buildings:
                return building
            labels |= seen
            g = self.choose(guards, rank)
            level = -1 if g is None else 0 if rank is None else g.level
            if level > step_level:
                guard_step, step_level = self.page_step, level
            if labels >= names:
                self.buildings_checked_at = time.time()
                if g is not None and level == step_level:
                    return g
                if guard_step is not None:
                    break                       # back to the first screen that showed the best guard
            elif level == best and not buildings:
                return g                        # (no building to look for: nothing better comes)
            if i == last:
                break
            r = self.scroll_fortress(up=True)
            if r is None:
                log("Fortress page could not be scrolled; giving up this pass")
                self.search_gave_up = True
                return None
            if r is not True:                   # False / UNCLEAR: the end of the page
                break
        if buildings and not labels >= names:
            log(f"Buildings not found on the page: {', '.join(sorted(names - labels))}")
        if guard_step is None:
            return None
        for _ in range(FORTRESS["max_scrolls"]):
            if self.page_step <= guard_step or self.scroll_fortress(up=False) is not True:
                break
        _, guards, _ = self.visible_targets()   # (read again: the last scroll may have moved it)
        return self.choose(guards, rank)

    def guard_search(self, rank=None, buildings=True):
        """A bright guard (or a ready building after all): the screen in front, then down to
        the end, then from the top down to where the search began."""
        above = self.page_step
        for screens, start_top in ((FORTRESS["max_scrolls"] + 1, False), (above, True)):
            if start_top:
                if not screens:
                    return None
                if self.scroll_to_top() is None:
                    self.search_gave_up = True
                    return None
            for i in range(screens):
                building, guards, _ = self.visible_targets()
                if building is not None and buildings:
                    return building
                g = self.choose(guards, rank)
                if g is not None:
                    return g
                if i == screens - 1:
                    break
                r = self.scroll_fortress(up=True)
                if r is None:
                    log("Fortress page could not be scrolled; giving up this pass")
                    self.search_gave_up = True
                    return None
                if r is not True:
                    break
        return None

    def tap_until(self, x, y, what, taps, keys, want=ATTACK, timeout=None):
        """Tap (x, y) until one of `keys` shows (precedence in their order), at most `taps`
        times: the emulator drops taps now and then, but a tap must not be repeated while a
        slow popup is still drawing (it would land on the popup). After a tap the keys are
        polled for `timeout` seconds (tap_timeout); when another part of a popup shows before
        `want` (袭击, drawn last), `want` still gets the rest of the timeout and at least
        want_grace seconds. A modal dialog is returned at once: the tap went nowhere else.
        Returns the key seen, or None."""
        timeout = FORTRESS["tap_timeout"] if timeout is None else timeout
        for tap in range(taps):
            self.click(x, y, 1.5, what, force=True)
            deadline = time.time() + timeout
            k = self.wait_seen(keys, timeout)
            if k is None:                       # a very slow popup: look once more before re-tapping
                time.sleep(FORTRESS["tap_settle"])
                k = self.seen(*keys, fresh=True)
            if k is not None and want is not None and k != want and k not in self.MODAL_KEYS:
                until = max(deadline, time.time() + FORTRESS["want_grace"])
                while time.time() < until:
                    time.sleep(0.5)
                    if self.seen(want, fresh=True):
                        k = want
                        break
            if k is not None:
                return k
            log(f"  tap {tap + 1} on {what} opened nothing")
        return None

    # what a tap on the fortress page may leave on top (the fleet panel is a map thing); the
    # guard popup's 袭击 ahead of the close hint here
    FORTRESS_DIALOGS = ZoneExplore.MODAL_KEYS + (ATTACK,) + tuple(
        k for k in ZoneExplore.DIALOGS if k not in ZoneExplore.MODAL_KEYS + ("ZGuardAttack", "ZFleetSpeed"))

    def clear_fortress_dialogs(self, on_top=None, passes=3):
        """Dismiss what lies over the fortress page (purchase prompt, 点击任意处继续, estimate
        dialog, building panel, dispatch list, guard popup). `on_top` is the key already
        detected by the caller. Stops as soon as nothing is seen."""
        return self.dismiss_all(self.FORTRESS_DIALOGS, passes, first=on_top)

    def blank_spot(self):
        """On the fortress page: the description text under the title (the map's plain_spot
        needs the map anchors, which the fortress page does not show)."""
        title = self.page_title() or self.fortress_title   # the header may be dimmed by the popup
        if title is not None:
            return Point(title.x, title.y + FORTRESS["blank_dy"])
        return super().blank_spot()

    def select_and_raid(self, target):
        """Click a target on the fortress page and press its 袭击. Returns "raided", "buy"
        (the purchase prompt is up), "retry" (a dialog took the tap, the page moved or the
        target could not be located again: not the target's fault, pick again) or "no_attack"
        (the target opens no 袭击; a building is then skipped for FAILED_TARGET_TTL, a guard
        spot likewise). A tap may be dropped, so a target that shows nothing at all is
        located again and tapped up to FAILED_TARGET_MISSES times; a target that answers
        with its own panel is given up at once."""
        r = FORTRESS["spot_radius"]
        for tap in range(FAILED_TARGET_MISSES):
            on_top = self.tap_until(target.x, target.y, target.label, 1, self.FORTRESS_DIALOGS)
            if on_top == ATTACK:
                if self.press(ATTACK, f"袭击 ({target.label})", gone=ATTACK):
                    return "raided"
                if self.seen("ZBuyPrompt", fresh=True):
                    return "buy"
                self.clear_fortress_dialogs()   # the popup is still open: do not pick on a dimmed page
                return "retry"
            log(f"袭击 did not appear for {target.label} (tap {tap + 1}): {on_top or 'nothing opened'}")
            self.save_debug("no_guard_attack")
            if on_top == "ZBuyPrompt":
                return "buy"
            if on_top == "ZCloseHint":          # its own panel, no 袭击: not attackable
                self.clear_fortress_dialogs(on_top)
                break
            if on_top is not None:              # a dialog took the tap
                self.clear_fortress_dialogs(on_top)
                return "retry"
            if tap + 1 < FAILED_TARGET_MISSES:  # nothing opened: locate it again before the next tap
                building, guards, _ = self.visible_targets()
                if target.kind == "building":
                    again = building if building is not None and building.name == target.name else None
                else:
                    again = next((g for g in guards if abs(g.x - target.x) < r and abs(g.y - target.y) < r), None)
                if again is None:
                    log(f"{target.label} not found again; picking anew")
                    return "retry"
                target = again
        if target.kind == "building":
            log(f"{target.label} opens no 袭击; skipped for {FAILED_TARGET_TTL // 60} min")
            self.failed_targets[target.name] = time.time() + FAILED_TARGET_TTL
        else:
            log(f"This guard opens no 袭击; skipped for {FAILED_TARGET_TTL // 60} min")
            self.skip_spot(target, FAILED_TARGET_TTL)
        return "no_attack"

    def skip_spot(self, target, ttl):
        """Leave the guard `target` (screen position at the current scroll) alone for `ttl` s."""
        self.tried_spots.append((target.x, target.y + self.page_off, time.time() + ttl))

    # ---- ordered mode: who fights what
    @staticmethod
    def load_busy():
        """The saved claims; entries that do not look right are dropped (a broken file: none)."""
        try:
            with open(BUSY_FILE) as fh:
                data = json.load(fh)
        except (OSError, ValueError):
            return {}
        keys = {"fortress", "since", "dx", "dy", "labels"}
        if not isinstance(data, dict):
            return {}
        return {int(f): b for f, b in data.items()
                if str(f).isdigit() and isinstance(b, dict) and keys <= b.keys() and isinstance(b["labels"], dict)}

    def save_busy(self):
        """Write the claims (a temporary file, then renamed: a kill mid-write keeps the old one)."""
        tmp = BUSY_FILE + ".tmp"
        try:
            with open(tmp, "w") as fh:
                json.dump(self.busy, fh)
            os.replace(tmp, BUSY_FILE)
        except OSError as e:
            log(f"Could not save {BUSY_FILE}: {e}")

    def claimed(self, b, x, y, title):
        """Whether the guard at screen (x, y) is the one claim `b` keeps: by a building label
        both screens show (exact; any of them is enough), else by page position (BUSY_DY)."""
        r = FORTRESS["spot_radius"]
        shared = [n for n in b["labels"] if n in self.screen_labels]
        if shared:
            return any(abs(x - self.screen_labels[n][0] - b["labels"][n][0]) < r
                       and abs(y - self.screen_labels[n][1] - b["labels"][n][1]) < r for n in shared)
        return abs(x - title.x - b["dx"]) < r and abs(y + self.page_off - title.y - b["dy"]) < BUSY_DY

    def claim(self, fleet, target):
        """Fleet `fleet` is about to be sent at the guard `target`: the others leave it alone
        (saved before the final 袭击, so that no send goes unrecorded). The guard is kept by
        its offset from every building label on the screen it was read on (exact) and by its
        page position (dx from the title, dy with the measured scroll); False without a proven
        page position. Buildings need no claim: only the big ship attacks them."""
        title = self.fortress_title
        if target.kind == "guard" and (title is None or not self.page_known):
            return False
        self.sent_at[fleet] = time.time()
        if target.kind != "guard":
            return True
        self.busy[fleet] = {"fortress": self.kind["name"], "since": time.time(),
                            "dx": target.x - title.x, "dy": target.y + self.page_off - title.y,
                            "labels": {n: [target.x - lx, target.y - ly] for n, (lx, ly) in self.screen_labels.items()}}
        self.save_busy()
        return True

    def unclaim(self, fleet):
        self.sent_at.pop(fleet, None)
        if self.busy.pop(fleet, None) is not None:
            self.save_busy()

    def release_busy(self, ships):
        """Free the targets of fleets the ship bar shows idle again (after BUSY_MIN) and old ones."""
        now, freed = time.time(), []
        for fleet, b in list(self.busy.items()):
            age = now - b["since"]
            if age > BUSY_MAX or (age > BUSY_MIN and ships.get(fleet, {}).get("idle")):
                freed.append(fleet)
                del self.busy[fleet]
        if freed:
            log(f"Fleets back: their targets are free again ({', '.join(map(str, freed))})")
            self.save_busy()

    def card_number(self, gray, title, card, numbers):
        """Which of `numbers` the 派遣舰队 card `card` (from the top) shows, or None."""
        r = int(DISPATCH_NO["search"] * self.sft)
        cx = int((title.x + DISPATCH_NO["dx"]) * self.sft)
        cy = int((title.y + DISPATCH_NO["dy"] + card * DISPATCH_CARDS["spacing"]) * self.sft)
        area = gray[max(0, cy - 2 * r):cy + 2 * r, max(0, cx - r):cx + r]
        best, no = DISPATCH_NO["th"], None
        for n in numbers:
            t = self.full_template(f"ZFleetNo{n}")
            if t is None or area.shape[0] < t.shape[0] or area.shape[1] < t.shape[1]:
                continue
            score = float(cv2.matchTemplate(area, t, cv2.TM_CCOEFF_NORMED).max())
            if score >= best:
                best, no = score, n
        return no

    def pick_dispatch_card(self, index):
        """Tap fleet `index`'s card on the 派遣舰队 list, found by the number on it (a fleet
        that is out may be missing from the list): the card at the fleet's place first, else
        every card is read. None: the list is not readable yet (look again); False: the list
        shows numbers but not this one, or none at all in ordered mode (there the cards shift
        with fleets out; elsewhere the card at the fleet's place is tapped)."""
        title = get_center("ZDispatchTitle", "Single")
        if title is None:
            return None                         # (still drawing)
        self.invalidate_shot()
        gray = self.shot()[1]
        slots = SHIP_LAYOUT["slots"]
        if self.card_number(gray, title, index - 1, (index,)) == index:
            card = index - 1
        else:
            numbers = [self.card_number(gray, title, c, range(1, slots + 1)) for c in range(slots)]
            if index in numbers:
                card = numbers.index(index)
            elif any(n is not None for n in numbers):
                log(f"Fleet {index} is not on the 派遣舰队 list (cards: {numbers})")
                return False
            elif self.order:
                log("No fleet number read on the 派遣舰队 list; not dispatching blind")
                self.save_debug("dispatch_unread")
                return False
            else:
                log("No fleet number read on the 派遣舰队 list; tapping the card at the fleet's place")
                card = index - 1
        self.click(title.x + DISPATCH_CARDS["dx"], title.y + DISPATCH_CARDS["dy0"] + card * DISPATCH_CARDS["spacing"],
                   2, f"fleet card {index}", force=True)
        return True

    def attack_with(self, index, rank=None, buildings=True):
        """Select an attackable target on the fortress page and send fleet `index`. The action
        is spent at the final 袭击 of the estimate dialog: when the purchase prompt pops up there
        (or anywhere earlier), the actions are bought and the whole selection is redone.
        `rank` / `buildings`: what the fleet may attack (see pick_target). Returns True when
        launched, None when the search found nothing it may attack, else False."""
        self.buildings_checked_at = 0.0         # every attack looks at all five buildings first
        self.attacking = index
        if not self.open_fortress():
            log("Could not open the fortress page")
            return False
        target = self.pick_target(rank, buildings)
        if target is None:
            log("Nothing attackable on the fortress page" + ("" if rank is None else f" for fleet {index}"))
            self.leave_fortress()
            return False if self.search_gave_up else None
        for _ in range(5):
            log(f"Attack {target.label} at ({target.x:.0f},{target.y:.0f}) with fleet {index}")
            result = self.raid_once(index, target)
            if result in ("launched", "cancelled"):     # cancelled = dry run
                self.leave_fortress()                   # back to the map with the "<" button
                return True
            if result in ("retry", "no_attack"):
                # the page may have been left or re-opened: locate a target afresh (a target
                # that opened no 袭击 is already on the skip lists)
                if not self.open_fortress():
                    break
                target = self.pick_target(rank, buildings)
                if target is None:
                    break
                continue
            if result != "buy":
                break
            # out of actions: buy, then the target has to be selected and 袭击 pressed again
            if not self.handle_buy_prompt(True):
                log("Could not buy actions" if not self.dry_run else "[DRY] stopped at the purchase prompt")
                break
            time.sleep(1.5)
            # the estimate dialog or the guard popup may still be up under the dimmed title:
            # clear them, then make sure the fortress page is really in front
            self.clear_fortress_dialogs()
            if not self.open_fortress():                # returns at once when the page is in front
                break
            target = self.pick_target(rank, buildings)
            if target is None:
                break
            log("Actions bought -> selecting again")
        log("Attack not launched")
        self.leave_fortress()
        return False

    def raid_once(self, index, target):
        """One pass: target -> 袭击 -> fleet card -> estimate -> 袭击. Returns 'launched',
        'cancelled' (dry run), 'buy' (purchase prompt appeared), 'no_attack' (the target opens
        no 袭击), 'retry' (a dialog took the tap / the target was lost) or 'failed'."""
        picked = self.select_and_raid(target)
        if picked != "raided":
            return picked
        for _ in range(12):
            k = self.seen("ZBuyPrompt", "ZEstimateLabel", "ZDispatchTitle", "ZContinueHint", fresh=True)
            if k == "ZBuyPrompt":
                return "buy"
            if k == "ZEstimateLabel":
                if self.dry_run:
                    log("[DRY] estimate dialog reached -> would press 袭击; cancelling")
                    self.press("ZCancel", "取消 (dry run)", gone="ZEstimateLabel")
                    return "cancelled"
                if self.order and not self.claim(index, target):
                    log("Target position unknown: not sent (it could not be kept from the other fleets)")
                    self.press("ZCancel", "取消 (no claim)", gone="ZEstimateLabel")
                    return "failed"
                if not self.press("ZAttack", "袭击 (estimate)", gone="ZEstimateLabel"):   # estimates do not matter
                    if self.seen("ZBuyPrompt", fresh=True):
                        self.unclaim(index)     # out of actions: not sent
                        return "buy"
                    return "failed"             # (maybe sent: the claim stays until the fleet reads idle)
                # the action is charged here: give a purchase prompt a moment to show up
                if self.wait_seen(("ZBuyPrompt",), 6) is not None:
                    self.unclaim(index)
                    return "buy"
                log("Attack launched")
                return "launched"
            if k == "ZDispatchTitle":
                if self.pick_dispatch_card(index) is False:
                    self.clear_fortress_dialogs()
                    return "failed"
                continue
            if k == "ZContinueHint":
                self.press("ZContinueHint", "点击任意处继续", gone="ZContinueHint", dy=CONTINUE_TAP_DY, tries=1)
                continue
            time.sleep(1)
        log("Attack flow did not reach the estimate dialog")
        return "failed"

    # ------------------------------------------------------------------ cycle
    def full_hp_idle(self, exclude):
        if not self.on_map():
            self.close_fleet_page()
        ships = self.scan_ships()
        return [i for i, s in ships.items() if s["idle"] and s["hp"] == FULL_HP and i != exclude]

    def wait_back(self, index):
        start = time.time()
        while time.time() - start < RETURN_TIMEOUT:
            if not self.on_map():
                self.close_popup()
            ships = self.scan_ships()
            if ships.get(index, {}).get("idle"):
                return True
            time.sleep(POLL)
        return False

    def wait_for_dice_run(self):
        """Same watch as zone_explore's monitor: stay on the dice board while the game's own
        auto-throw runs; when the dice run out (更多骰子) or the button sits on 长按自动 for
        RUN_IDLE_SECONDS, enter 星际探险. Returns once the zone map is open."""
        log("Monitor: waiting for the dice run to end before the fortress fight")
        idle_since = None
        while True:
            if self.on_known_page():
                return True
            if single_find("ZMoreDice"):
                log("Dice ran out -> entering 星际探险")
                if self.enter_zone_explore():
                    return True
            elif single_find("ZAutoThrowing"):
                idle_since = None
                log("Run in progress")
            elif single_find("ZLongPressAuto"):
                idle_since = idle_since or time.time()
                waited = time.time() - idle_since
                log(f"Run button idle for {waited:.0f}s")
                if waited >= RUN_IDLE_SECONDS:
                    log("Run has been idle long enough -> entering 星际探险")
                    if self.enter_zone_explore():
                        return True
                    idle_since = None
            else:
                log("Unknown page, waiting")
            time.sleep(MONITOR_POLL)


    def on_known_page(self):
        self.invalidate_shot()
        gs = self.shot()[1]
        return self.seen("ZExplore", "ZMyFleet", gs=gs) is not None or self.page_title(gs) is not None

    def enter_map_from_main(self):
        """Started on the game main screen (dice board): go to 星际探险 first."""
        if self.on_known_page():
            return True
        if single_find("ZStarExplore"):
            log("Main screen -> 星际探险")
            return self.enter_zone_explore()
        log("Start the program on the zone map or on the game main screen")
        return False

    @staticmethod
    def retry_later(counter, fleet, ok, what, limit):
        """Book an attempt of `what` on `fleet` in `counter`: True when it failed and is to be
        tried again later, False when it is done or given up after `limit` failures."""
        if ok:
            counter.pop(fleet, None)
            return False
        counter[fleet] = counter.get(fleet, 0) + 1
        if counter[fleet] >= limit:
            log(f"Fleet {fleet}: giving up on the {what} after {limit} tries; check by hand")
            counter.pop(fleet)
            return False
        log(f"Fleet {fleet}: {what} not done; tried again next pass")
        return True

    def run_pending_repairs(self, ships):
        """Repair the idle fleets in pending_repair (dropping those repaired or at full hp);
        returns the ship scan, fresh when the fleet page was used."""
        opened = False
        for i in sorted(self.pending_repair):
            s = ships.get(i, {})
            if s.get("status") == "repairing" or s.get("hp") == FULL_HP:
                self.pending_repair.discard(i)  # nothing left to repair
            elif s.get("idle"):
                opened = True
                r = self.repair_fleet(i)
                if r:
                    self.deferred_equip.discard(i)  # (the repair began with 一键配队)
                if not self.retry_later(self.repair_tries, i, r, "repair", PENDING_REPAIR_TRIES):
                    self.pending_repair.discard(i)
        if not opened:
            return ships
        self.close_fleet_page()
        return self.scan_ships()

    def pause(self, msg):
        """Log `msg` and wait POLL seconds before the next pass; False in a dry run (one pass)."""
        log(msg)
        if self.dry_run:
            return False
        time.sleep(POLL)
        return True

    def abandon_swap(self):
        """A swap that could not be finished in SWAP_FINISH_TRIES passes: the gear must not
        stay loose. Whoever holds it now (the target, when 一键配队 worked) becomes the holder,
        else 一键配队 on the original holder takes the gear back; the fleets to repair wait
        until the owner is known (一键配队 during their repair would take loose gear). The new
        holder then gets one check swap (holder == target: 一键配队, loadout) before it attacks."""
        sw, self.swap = self.swap, None
        log(f"Giving up on the gear swap to fleet {sw['target']} after {SWAP_FINISH_TRIES} passes")
        self.deferred_repair |= sw["to_repair"]
        if sw["holder"] == sw["target"]:        # a check swap failed: this holder only attacks after a
            self.no_direct_attack.add(sw["target"])     # real swap
        elif sw["unequipped"] and not sw["equipped"]:
            # the strip was done, the target's 一键配队 kept failing: the next swaps pick another
            # fleet for a while instead of looping on this one
            log(f"Fleet {sw['target']} is not picked for a swap for {BAD_TARGET_TTL // 60} min")
            self.bad_targets[sw["target"]] = time.time()
        found = self.find_gear_holder()
        if found is None and not self.lookup_unreadable and sw["holder"] != sw["target"]:
            # the gear is loose (or split): 一键配队 on the original holder takes what is loose;
            # the next lookup says whether that made it the holder again
            log(f"Putting the gear back on fleet {sw['holder']}: {'done' if self.auto_equip(sw['holder']) else 'failed'}")
            found = self.find_gear_holder()
        # 一键配队 on the stripped fleets only once the gear has settled (the check swap below
        # finished, or the next holder lookup): it could take loose items
        self.deferred_equip |= sw["re_equip"]
        self.close_fleet_page()
        self.holder = found
        if found is not None and sw["holder"] != sw["target"]:
            self.swap = self.make_swap(found, found)    # a check swap

    def run(self, monitor=False):
        """The fight loop; an unexpected error in a pass is logged (with a debug shot), the
        dialogs are closed and the loop starts again with its state kept."""
        import traceback
        errors = []                             # times of recent errors
        while True:
            try:
                return self._run_ordered(monitor) if self.order else self._run(monitor)
            except Exception:
                log("Unexpected error in a pass:\n" + traceback.format_exc())
                errors = [t for t in errors if time.time() - t < 15 * 60] + [time.time()]
                try:
                    self.save_debug("pass_error")
                except Exception:
                    pass                        # (the screen itself may be the problem)
                if self.dry_run or len(errors) >= 3:    # the same bug again and again: stop for a fix
                    log("Stopping: errors keep coming" if not self.dry_run else "Dry run: stopping")
                    raise
                try:
                    self.close_fleet_page()
                    self.close_popup()
                except Exception:
                    pass
                monitor = False                 # (already on the map side; _run re-enters the map)
                time.sleep(POLL)

    def start(self, monitor):
        if monitor:
            self.wait_for_dice_run()
        else:
            self.enter_map_from_main()

    def map_ready(self):
        """Back on the zone map (calibrated once); False when no known page could be left."""
        if not self.on_map():
            if not self.close_popup() and not self.enter_map_from_main():
                self.save_debug("unknown_page")
                return False
        if not self.calibrated and self.on_map():
            self.calibrated = self.calibrate_scale()   # needs the map anchors; once per run (kept on a restart)
        return True

    def _run_ordered(self, monitor=False):
        """Ordered mode: every idle fleet of the order below full energy is repaired as it is
        (no 一键配队: the gear stays where it is); a full one attacks the highest target its
        rank allows, biggest first, while the others are still out."""
        self.start(monitor)
        while True:
            if not self.map_ready():
                if not self.pause("Not on the zone map and no known page to leave; waiting"):
                    return
                continue
            ships = self.scan_ships()
            self.release_busy(ships)
            now = time.time()
            waiting = {f for f in self.order if now < self.fleet_wait.get(f, 0)}
            # (a fleet sent less than BUSY_MIN ago may still read idle: the bar lags)
            waiting |= {f for f, t in self.sent_at.items() if now - t <= BUSY_MIN}
            # (unknown hp counts as damaged, as in the swap mode)
            damaged = [f for f in self.order if f not in waiting and ships.get(f, {}).get("idle")
                       and ships[f]["hp"] != FULL_HP]
            if damaged and self.open_fleet_page():
                for f in damaged:
                    if not self.confirm_repair(f):
                        self.save_debug(f"repair_failed_{f}")
                        log(f"Fleet {f}: repair failed; tried again in {FLEET_FAIL_WAIT // 60} min")
                        self.fleet_wait[f] = time.time() + FLEET_FAIL_WAIT
                self.close_fleet_page()
                ships = self.scan_ships()
            now = time.time()
            ready = [f for f, rank in self.order.items() if f not in waiting and ships.get(f, {}).get("idle")
                     and ships[f]["hp"] == FULL_HP and now >= self.no_target_until.get(rank, 0)]
            if not ready:
                if not self.pause("No fleet of the order is idle at full energy with something to attack; waiting"):
                    return
                continue
            fleet = ready[0]
            rank = self.order[fleet]
            r = self.attack_with(fleet, rank, buildings=rank == BIG)
            if self.dry_run:
                return
            if r is None:                       # nothing for this rank, so nothing for the smaller ones
                for lower in set(self.order.values()):
                    if lower <= rank:
                        self.no_target_until[lower] = time.time() + NO_TARGET_WAIT
                log(f"Ranks up to {'I' * rank or 'none'}: nothing to attack; looked for again in {NO_TARGET_WAIT // 60} min")
            elif not r:                         # the other fleets get their turn meanwhile
                log(f"Fleet {fleet}: attack not launched; tried again in {FLEET_FAIL_WAIT // 60} min")
                self.fleet_wait[fleet] = time.time() + FLEET_FAIL_WAIT

    def _run(self, monitor=False):
        self.start(monitor)
        while True:
            if not self.map_ready():
                if not self.pause("Not on the zone map and no known page to leave; waiting"):
                    return
                continue
            ships = self.scan_ships()
            if self.swap is not None and self.swap["errored"]:
                # the last pass broke off inside the swap with an error: the same error would
                # likely come again, so the gear is settled the abandon way (一键配队 fallback)
                log("The gear swap ended in an error; abandoning it")
                try:
                    self.abandon_swap()
                except Exception:
                    self.swap = None            # (abandon_swap itself failed: the holder lookup decides)
                    self.holder = None
                    raise
                continue
            if self.swap is not None:           # first: an interrupted swap, before anything repairs
                r = self.finish_swap()          # (一键配队 on the stripped fleet would take the loose gear back)
                if r:
                    self.swap_fails = 0
                    ships = self.scan_ships()
                elif self.swap["tries"] >= SWAP_FINISH_TRIES:
                    self.abandon_swap()
                    if not self.pause("Swap abandoned; the next pass checks the gear's owner first"):
                        return
                    continue                    # (the check swap, or the holder lookup, comes first)
                elif not self.pause(f"Gear swap to fleet {self.swap['target']} unfinished; resumed in {POLL} s"):
                    return
                else:
                    continue
            if self.holder is None:
                # every start looks for the gear afresh (it may have been moved by hand); inside
                # the loop the holder is remembered and only verified when swapping
                self.holder = self.find_gear_holder()
                self.close_fleet_page()
                log(f"Gear holder: fleet {self.holder}; map page back: {self.on_map()}")
                ships = self.scan_ships()           # the earlier scan may have seen the dimmed bar
            if self.holder is None:
                self.holder_misses += 1
                if self.dry_run or self.holder_misses >= HOLDER_LOOKUP_TRIES:
                    log(f"Could not tell which fleet has the best gear after {self.holder_misses} looks; "
                        "check the standard loadout screenshot (pages/boss/loadout_standard_user.png)")
                    return
                self.pause(f"Could not tell which fleet has the best gear; looking again in {POLL} s")
                continue
            self.holder_misses = 0
            if self.deferred_repair:            # (a full-hp fleet is dropped by the repair loop itself)
                self.pending_repair |= self.deferred_repair
                self.deferred_repair = set()
            repairs_now = {i for i in self.pending_repair    # (a repair starts with 一键配队)
                           if ships.get(i, {}).get("idle") and ships.get(i, {}).get("hp") != FULL_HP}
            self.deferred_equip -= {self.holder}
            self.equip_tries.pop(self.holder, None)
            ready = {i for i in self.deferred_equip - repairs_now if ships.get(i, {}).get("idle")}
            # (fleets repaired now stay queued: a repair that fails leaves them without a loadout)
            self.deferred_equip -= ready        # (fleets that are out wait)
            if ready:                           # stripped full-hp fleets: 一键配队 now the gear has an owner
                self.re_equip(ready)
                self.close_fleet_page()
                ships = self.scan_ships()
            ships = self.run_pending_repairs(ships)
            if not self.on_map():
                self.close_fleet_page()
                ships = self.scan_ships()
            h = ships.get(self.holder, {})
            if not h.get("idle"):
                # the gear is on a fleet that is still out (sailing / fighting / returning):
                # nothing can be swapped until it is back
                if not self.pause(f"Fleet {self.holder} (best gear) is {h.get('status', 'unknown')}; waiting for it to return"):
                    return
                continue
            if h.get("hp") is not None and h["hp"] > HOLDER_OK_HP and self.holder not in self.no_direct_attack:
                log(f"Fleet {self.holder} still has {h['hp']}% hp: attacking again without a gear swap")
                target = self.holder
            else:
                now = time.time()
                fresh = [i for i, s in ships.items()
                         if s["idle"] and s["hp"] == FULL_HP and i != self.holder
                         and now - self.bad_targets.get(i, 0) > BAD_TARGET_TTL]
                if not fresh:
                    if not self.pause("No idle fleet at 100% hp; waiting"):
                        return
                    continue
                target = fresh[0]
                r = self.swap_gear(self.holder, target, ships)
                if not r:
                    if self.swap is None:       # failed before the swap started: the holder's page/tab
                        self.swap_fails += 1    # (a started swap is resumed by the swap block)
                    if self.swap_fails >= SWAP_FINISH_TRIES:
                        self.holder, self.swap_fails = None, 0
                    if not self.pause("Gear swap failed"):
                        return
                    continue
                self.swap_fails = 0
            if not self.attack_with(target):
                if not self.pause("Attack not launched; next pass"):
                    return
                continue
            if self.dry_run:
                return
            log(f"Waiting for fleet {target} to return")
            self.wait_back(target)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry", action="store_true", help="Detect and log only")
    parser.add_argument("-f", "--fortress", choices=sorted(FORTRESS_KINDS),
                        help="Which fortress to fight: xz (星炽要塞, default) or zx (铸械要塞)")
    parser.add_argument("--delay", type=int, default=3)
    parser.add_argument("--debug-shots", action="store_true", help="Save OCR crops to pics/<platform>/zone/debug/")
    parser.add_argument("-m", "--monitor", action="store_true",
                        help="Wait on the dice board until the dice run out, enter 星际探险, then fight")
    for kind in sorted(FORTRESS_KINDS):
        parser.add_argument(f"-o{kind}", metavar="ORDER",
                            help=f"Ordered mode on {FORTRESS_KINDS[kind]['name']}: five fleet digits from 0, "
                                 "big ship first, then two middle, two small (e.g. 41032); no gear swaps")
    args = parser.parse_args()
    orders = [(kind, getattr(args, f"o{kind}")) for kind in sorted(FORTRESS_KINDS) if getattr(args, f"o{kind}")]
    order = None
    if len(orders) > 1:
        parser.error("give one of " + " / ".join(f"-o{k}" for k in sorted(FORTRESS_KINDS)))
    if orders:
        kind, digits = orders[0]
        if args.fortress not in (None, kind):
            parser.error(f"-o{kind} fights {FORTRESS_KINDS[kind]['name']}; it does not go with -f {args.fortress}")
        args.fortress = kind
        if sorted(digits) != [str(i) for i in range(SHIP_LAYOUT["slots"])]:
            parser.error(f"ORDER must use each digit 0-{SHIP_LAYOUT['slots'] - 1} once, e.g. 41032")
        order = [int(d) + 1 for d in digits]    # the ship bar counts fleets from 1
    if args.debug_shots:
        DEBUG_DIR = os.path.join(os.path.dirname(single_find_map["ZBase"]), "debug")
        os.makedirs(DEBUG_DIR, exist_ok=True)
    time.sleep(args.delay)
    FortressFight(dry_run=args.dry, fortress=args.fortress or "xz", order=order).run(monitor=args.monitor)
