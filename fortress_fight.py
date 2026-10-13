"""
Fortress fight (铸械要塞) - attack the fortress guards with the one fleet that carries the best
equipment, moving that equipment to a fresh full-hp fleet before every attack.

Cycle (user rules):
    1. The fleet holding the best gear = the one with the highest 战力 on the 我的舰队 tabs.
    2. Pick another fleet that is idle at 100% hp.
    3. On the holder's tab: open 编辑舰队 and remove everything (飞行器, 主题皮肤, 骰子皮肤, 棋子;
       the lv.6 shield at the bottom right is never touched), confirm.
    4. On the fresh fleet's tab: 一键配队; then make sure the top-right artifact slot holds
       残骸本源 (一键配队 may pick another one): open it, select 残骸本源, confirm.
    5. Back on the old holder's tab: 一键配队 (a fleet without a loadout cannot be repaired),
       then 修理舰队, confirm.
    6. Map -> 铸械要塞 -> scroll through the whole page for a ready building (bright: the
       guards around it are cleared and it has recovered; a broken one, just raided, or one
       still guarded is dim) -> otherwise the first bright guard (dim ones are not attackable
       yet) -> 袭击 -> 派遣舰队 list: pick the fresh fleet's card (it also has the highest
       战力) -> battle estimate: always attack. A building that shows no 袭击 when tapped is
       left alone for FAILED_TARGET_TTL.
    7. Wait for the fleet to come back, then repeat with the next full-hp fleet.

Only one fleet fights at a time (there is one set of best gear). No zoom or map dragging.

Usage:
    python fortress_fight.py --dry      # does the gear swap and repair for real, cancels at the attack
    python fortress_fight.py            # full loop (started on the zone map)
    python fortress_fight.py -m         # monitor: wait on the dice board until the dice run out
                                        # (更多骰子 popup / 长按自动 idle), enter 星际探险, then fight
"""

import argparse
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
    "artifact_slot": (152.5, 132.5),                 # top right: the 神器 slot
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
    "bright_min": 75,         # mean grey of the cell: attackable guards ~86-104, dim ones ~46-65
    "building_bright_min": 75,
    "grid_top_dy": 200,       # guard grid lies below the title by at least this (logical px)
    "scroll_x_dx": 0,         # scroll gesture column, relative to the title
    "scroll_y0_dy": 650,      # gesture from title+y0 up to title+y1 (content moves up by y0-y1 = 220,
    "scroll_y1_dy": 430,      # less than the measured content area so that the move can be matched)
    "max_scrolls": 10,
    "blank_dy": 45,           # the description line under the title: tapping it closes popups
    "cell_half": 10,          # guard brightness: half size of the sampled square (logical px)
    "building_patch": (45, 5, 20),   # building brightness: from 45 to 5 px above the label, +-20 wide
    "spot_radius": 20,        # a guard this close to a tried spot (page coordinates) is the same guard; cells are ~33 apart
    "grid_half_w": 230,       # the page content spans this far left/right of the title (shift measurement)
    "bottom_labels": ("资源库", "军事基地"),   # once these are seen the scan has reached the last buildings
    "content_bottom_dy": 530, # the page content measured for scrolling ends this far below the title (above 停机坪)
    "scan_valid": 60,         # seconds a full page scan stays trusted for the "no ready building" shortcut
    "relocate_slack": 60,     # page_y may differ this much from where the guard was seen before scrolling again
    "tap_timeout": 5.0,       # seconds a tap on a target gets to open something
    "icon_timeout": 2.0,      # the map icon's popup shows within a second
    "want_grace": 2.0,        # seconds 袭击 still gets after another part of its popup showed
    "tap_settle": 1.0,        # a popup draws its parts over a few frames: look once more after this
    "building_tap_dy": 35,    # tap point above a building's label
}
FULL_HP = 100
TAP_BURST = 3                # taps per burst on idempotent buttons (tabs, 一键配队): a dropped tap is harmless
PENDING_REPAIR_TRIES = 3     # passes a failed repair is retried from pending_repair before giving up
HOLDER_OK_HP = 90            # the gear holder attacks again by itself above this hp (no swap)
DEBUG_DIR = None             # --debug-shots: save the OCR crops here
STATE_FILE = os.path.join(os.path.dirname(single_find_map["ZBase"]), "fortress_state.json")   # {"holder": N}
RETURN_TIMEOUT = 40 * 60     # seconds to wait for the fighting fleet to come back
POLL = 30
FAILED_TARGET_TTL = 15 * 60  # seconds a building is skipped after FAILED_TARGET_MISSES taps showed no 袭击
FAILED_TARGET_MISSES = 2     # taps on a building in one go that showed no 袭击: the first may be dropped

# something to attack on the fortress page: kind "building" (name 商店/委托站/...) or "guard"
# (name None); x, y in the reference frame
class Target(namedtuple("Target", "kind name x y")):
    __slots__ = ()
    label = property(lambda t: t.name or t.kind)


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
            s = 1 - float(np.abs(p.astype(int) - q.astype(int)).mean()) / 255
            if s > best:
                best, lab = s, cand
        if best >= 0.75 and lab != "?":
            out += lab
    return out


class FortressFight(ZoneExplore):
    def __init__(self, dry_run=False):
        super().__init__(dry_run=dry_run)
        self.holder = None        # fleet index currently carrying the best gear
        self.pending_repair = set()   # fleets whose repair could not be started yet
        self.repair_tries = {}        # fleet -> attempts made from pending_repair
        self.failed_targets = {}      # building name -> time its tap showed no 袭击
        self.page_y = 0.0             # how far down the fortress page is scrolled (logical px, measured)
        self.tried_spots = []         # (x, page y, time) of guards that opened no 袭击
        self.page_scanned = 0.0       # when the whole fortress page was last scanned (0: not since opened)
        self.fortress_title = None    # title position on the open fortress page (the header does not scroll)
        log(f"FortressFight ready (code={_code_version()})")

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
        if single_find("ZFortressTitle"):
            self.leave_fortress()
        return super().close_popup(tries)

    def leave_fortress(self):
        """Fortress page -> zone map through the "<" button at the bottom left."""
        for _ in range(3):
            self.invalidate_shot()
            gs = self.shot()[1]
            if not self.seen("ZFortressTitle", gs=gs):
                self.fortress_title = None
                return True
            k = self.seen(*self.FORTRESS_DIALOGS, gs=gs)    # a guard popup / dialog / building panel on top
            if k is not None:
                self.clear_fortress_dialogs(k)
            if not self.press("ZFortressBack", "< (leave fortress)", gone="ZFortressTitle"):
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

    def has_boss_artifact(self):
        """True when the top-right slot of the open fleet tab shows 残骸本源."""
        title = self.fleet_title()
        if title is None:
            return False
        self.invalidate_shot()
        gray = self.shot()[1]
        dx, dy = EQUIP_LAYOUT["artifact_slot"]
        # other gold artifacts (冰核本源, 蓝冰本源) match this icon at <= 0.79, 残骸本源 at >= 0.99
        for cx, cy, conf in match_all(gray, self.full_template("ZArtifactSlot"), 0.9):
            if abs(cx / self.sft - (title.x + dx)) < 40 and abs(cy / self.sft - (title.y + dy)) < 40:
                return True
        return False

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

    def load_state(self):
        try:
            import json
            with open(STATE_FILE) as f:
                return json.load(f)
        except Exception:
            return {}

    def save_state(self, **kw):
        import json
        state = self.load_state()
        state.update(kw)
        with open(STATE_FILE, "w") as f:
            json.dump(state, f)

    def find_gear_holder(self):
        """The fleet carrying the best equipment. The last known holder is kept in STATE_FILE and
        only re-checked on its own tab; all five tabs are compared against the standard loadout
        screenshot only when that check fails. 战力 is logged for reference only."""
        if not self.open_fleet_page():
            return None
        powers, scores = {}, {}
        for i in range(1, SHIP_LAYOUT["slots"] + 1):
            self.select_tab(i)
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
            self.unequip_right_artifacts(index)
            if UNEQUIP_BOTTOM_ARTIFACTS:
                self.unequip_bottom_artifacts(index)
            # the one thing the next fleet cannot do without: 残骸本源 must be off this fleet
            for _ in range(2):
                if not self.open_fleet_page() or not self.select_tab(index):
                    log(f"Fleet {index}: cannot verify the artifact slot, fleet page not open")
                    return False
                if not self.has_boss_artifact():
                    break
                log(f"残骸本源 is still on fleet {index}; stripping its artifacts again")
                self.unequip_right_artifacts(index)
            else:
                log(f"Could not strip 残骸本源 from fleet {index}")
                return False
        return ok

    def unequip_right_artifacts(self, index):
        """The artifact slots in the right column (rows 1 and 2) each open their own edit page;
        the equipped artifact sits in the preview area above 取消/确认, tapping it removes it."""
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
        if not self.open_fleet_page():
            return False
        self.select_tab(index)
        b = get_center("ZAutoEquip", "Single")
        if b is None:
            log("一键配队 not found")
            return False
        self.burst(b.x, b.y, TAP_BURST)             # idempotent: repeated taps re-apply the same loadout
        time.sleep(2)
        if self.wait_for("ZRepairOk", 3):           # a confirmation dialog, if any
            self.click_button("ZRepairOk", 2, force=True)
        return True

    def ensure_boss_artifact(self, index):
        """Top-right artifact slot must hold 残骸本源."""
        dx, dy = EQUIP_LAYOUT["artifact_slot"]
        if not self.open_slot_page(index, dx, dy, "artifact slot", self.artifact_page_open):
            log("The artifact page did not open")
            return False
        target = get_center("ZArtifactTarget", "Single")
        check = get_center("ZArtifactCheck", "Single")
        if target is None:
            log("残骸本源 not found in the artifact grid")
            self.click_button("ZCancel", 2, force=True)
            return False
        if check is not None and abs(check.x - target.x) < 60 and abs(check.y - target.y) < 80:
            log("残骸本源 already equipped")
            self.click_button("ZCancel", 2, force=True)
            return True
        self.click(target.x, target.y, 1.5, "残骸本源", force=True)
        ok = self.confirm_edit("编辑低级神器")
        log("Artifact set to 残骸本源" if ok else "编辑低级神器 could not be confirmed")
        return ok

    def repair_fleet(self, index):
        """一键配队 first (a fleet without a loadout cannot be repaired), then the shared
        verified repair (修理舰队 -> 确认 -> "舰队修理中..." shown)."""
        if not self.auto_equip(index):
            return False
        ok = self.confirm_repair(index)
        if not ok:
            self.save_debug(f"repair_failed_{index}")
        return ok

    def swap_gear(self, holder, target):
        log(f"Move the best gear from fleet {holder} to fleet {target}")
        # the fleet page is open now anyway: make sure the remembered holder really has the gear
        if not self.open_fleet_page():
            return False
        self.select_tab(holder)
        score = self.loadout_score()
        if score < EQUIP_LAYOUT["loadout_th"]:
            log(f"Fleet {holder} does not match the standard loadout ({score:.2f}); re-checking all tabs")
            self.save_state(holder=None)
            found = self.find_gear_holder()
            if found is None or found == target:
                self.close_fleet_page()
                return False
            holder = self.holder = found
        if not self.unequip_all(holder):
            return False
        if not self.auto_equip(target):
            return False
        if not self.ensure_boss_artifact(target):
            return False
        self.open_fleet_page()
        self.select_tab(target)
        score = self.loadout_score()
        log(f"Fleet {target} loadout vs standard: {score:.2f}")
        if score < EQUIP_LAYOUT["loadout_th"]:
            log("Loadout differs from the standard screenshot; check the equipment by hand")
        if not self.repair_fleet(holder):
            self.pending_repair.add(holder)     # retried at the start of every later pass
        self.close_fleet_page()
        return True

    # ------------------------------------------------------------------ fortress page
    def open_fortress(self):
        """Zone map -> fortress icon -> info popup -> 袭击 -> fortress page. Each step is
        retried: taps on the map are sometimes dropped by the emulator."""
        if single_find("ZFortressTitle"):
            if self.fortress_title is None:     # first sight of the page this run: it may be scrolled
                self.scroll_to_top()
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
            icon = get_center("ZFortressMap", "Single")
            if icon is None:
                log(f"铸械要塞 icon not on screen (attempt {attempt + 1})")
                self.save_debug("no_fortress_icon")
                continue
            log(f"铸械要塞 icon at ({icon.x:.0f},{icon.y:.0f})")
            # the icon opens an info popup (位置/坐标/距离/守卫等级) with a 袭击 button; a second
            # tap is only sent when nothing opened (the popup covers the icon with 前往 etc.)
            opened = self.tap_until(icon.x, icon.y, "铸械要塞", TAP_BURST, ("ZFortressTitle", "ZGuardAttack", "ZGo"),
                                    want=None, timeout=FORTRESS["icon_timeout"])
            if opened is None:
                log(f"Fortress icon did not respond (attempt {attempt + 1})")
                continue
            if opened != "ZFortressTitle":
                log(f"Fortress popup ({opened}) -> 袭击")
                if not self.press("ZGuardAttack", "袭击 (fortress popup)", appears="ZFortressTitle") \
                        and self.seen("ZFortressTitle", "ZGo", fresh=True) == "ZGo":
                    log("No 袭击 on the popup, using 前往")
                    self.click_button("ZGo", 2.5, force=True)
            if self.wait_for("ZFortressTitle", 8):      # the page may take a few seconds to load
                self.page_y, self.fortress_title, self.page_scanned = 0.0, None, 0.0   # fresh page, at the top
                return True
            log(f"Fortress page not seen after the popup (attempt {attempt + 1})")
            self.close_popup()
        self.save_debug("fortress_page_missing")
        return False

    def guard_cells(self, gray, title):
        """[(x, y, bright)] of every guard cell on the fortress page (logical px)."""
        t = self.full_template("ZGuardBright")
        h = int(FORTRESS["cell_half"] * self.sft)
        out = []
        for cx, cy, conf in match_all(gray, t, FORTRESS["guard_th"]):
            x, y = cx / self.sft, cy / self.sft
            if title is not None and y < title.y + FORTRESS["grid_top_dy"]:
                continue
            cell = gray[cy - h:cy + h, cx - h:cx + h]
            out.append((x, y, float(cell.mean()) >= FORTRESS["bright_min"]))
        return out

    # building name labels on the fortress page (商店/委托站/指挥所 on the first screen, 资源库/
    # 军事基地 further down). A ready building (guards around it cleared and recovered) is bright
    # above its label: pages/boss/building_ready.png 商店 ~118, the still guarded 委托站/指挥所
    # ~50. A raided one stays bright but wears a yellow 已损坏 badge over the building
    # (building_broken.png) until it recovers. A ready building's tap shows 袭击 below the label
    # (building_clicked.png), the same button and dispatch list as a guard.
    BUILDING_LABELS = (("ZShopLabel", "商店"), ("ZDepotLabel", "委托站"), ("ZCommandLabel", "指挥所"),
                       ("ZResourceLabel", "资源库"), ("ZMilitaryLabel", "军事基地"))
    BUILDING_LABEL_TH = 0.8     # real labels match >= 0.97 on every page screenshot, other labels <= 0.68
    BADGE_TH = 0.8
    BADGE_DX, BADGE_DY = 45, (5, 70)    # 已损坏 badge centre relative to the label: |dx| and dy above

    def buildings(self, gray, title):
        """[(name, x, y, state)] for every building label on screen, top to bottom; state is
        "ready", "dim" (guarded) or "broken" (已损坏 badge). Labels are matched below the
        header only (on the unscrolled page 商店's label sits ~324 px below the title, a label
        nearer than grid_top_dy has its building hidden under the header); the badge is looked
        for only when some building is bright."""
        top, bottom, half = (int(v * self.sft) for v in FORTRESS["building_patch"])
        # the patch above the label must lie below the header too
        y0 = int((title.y + FORTRESS["grid_top_dy"]) * self.sft) + top if title is not None else 0
        y0 = max(0, min(y0, gray.shape[0]))
        below = gray[y0:]
        found = []
        for key, name in self.BUILDING_LABELS:
            hits = match_all(below, self.full_template(key), self.BUILDING_LABEL_TH)
            if not hits:
                continue
            cx, cy, _ = hits[0]                 # match_all yields the best match first
            cy += y0
            if cy - top < 0:
                continue
            patch = gray[cy - top:cy - bottom, max(0, cx - half):cx + half]      # the building above its label
            found.append((name, cx / self.sft, cy / self.sft, float(patch.mean()) >= FORTRESS["building_bright_min"]))
        badges = []
        if any(b[3] for b in found):            # the badge may reach above the label band
            badges = [(cx / self.sft, cy / self.sft)
                      for cx, cy, _ in match_all(gray, self.full_template("ZBrokenBadge"), self.BADGE_TH)]
        out = []
        for name, x, y, bright in found:
            broken = any(abs(bx - x) < self.BADGE_DX and self.BADGE_DY[0] < y - by < self.BADGE_DY[1] for bx, by in badges)
            out.append((name, x, y - FORTRESS["building_tap_dy"], "broken" if broken else "ready" if bright else "dim"))
        return sorted(out, key=lambda b: (b[2], b[1]))

    def visible_targets(self):
        """(ready building or None, bright guards top to bottom, names of the building labels
        on screen); one capture for all. Buildings whose taps showed no 袭击 recently and guard
        spots that opened nothing (page coordinates, FAILED_TARGET_TTL) are skipped."""
        self.invalidate_shot()
        gray = self.shot()[1]
        title = self.anchor("ZFortressTitle", gray) or self.fortress_title   # the header does not scroll
        if title is not None:
            self.fortress_title = title
        blds = self.buildings(gray, title)
        now = time.time()
        for name, t in list(self.failed_targets.items()):
            if now - t > FAILED_TARGET_TTL:
                del self.failed_targets[name]
        log("Buildings: " + (", ".join(f"{n} {st}{' (skipped)' if n in self.failed_targets else ''}" for n, _, _, st in blds)
                             or "none on screen"))
        building = next((Target("building", n, x, y) for n, x, y, st in blds
                         if st == "ready" and n not in self.failed_targets), None)
        cells = self.guard_cells(gray, title)
        r = FORTRESS["spot_radius"]
        self.tried_spots = [t for t in self.tried_spots if now - t[2] <= FAILED_TARGET_TTL]
        bright = sorted((c for c in cells if c[2] and not any(abs(c[0] - sx) < r and abs(c[1] + self.page_y - sy) < r
                                                              for sx, sy, _ in self.tried_spots)),
                        key=lambda c: (c[1], c[0]))
        log(f"Guards: {len(cells)} cells, {len(bright)} attackable")
        guards = [Target("guard", None, x, y) for x, y, _ in bright]
        return building, guards, {n for n, _, _, _ in blds}

    def scroll_fortress(self, up=True):
        """Scroll the fortress page (it is taller than the screen). Returns False when the page
        did not move, i.e. the end was reached."""
        from zone_explore import drag as _drag
        title = self.fortress_title or get_center("ZFortressTitle", "Single")
        if title is None:
            return None                         # not on the fortress page (None, not "end")
        x = title.x + FORTRESS["scroll_x_dx"]
        y0, y1 = title.y + FORTRESS["scroll_y0_dy"], title.y + FORTRESS["scroll_y1_dy"]
        if not up:
            y0, y1 = y1, y0
        # the page content between the header and the window bottom, for measuring the move
        self.invalidate_shot()
        h, w = self.shot()[1].shape
        region = (max(0, title.x - FORTRESS["grid_half_w"]), title.y + FORTRESS["grid_top_dy"],
                  min(w / self.sft, title.x + FORTRESS["grid_half_w"]), min(h / self.sft, title.y + FORTRESS["content_bottom_dy"]))
        before = self.grab_region(region)
        if before.size == 0:
            log("Fortress page content area is off screen")
            return None
        rx0, ry0 = self.to_real(x, y0)
        rx1, ry1 = self.to_real(x, y1)
        if self.dry_run:
            log(f"[DRY] would scroll the fortress page {'up' if up else 'down'}")
        _drag(rx0, ry0, rx1, ry1)
        self.invalidate_shot()
        time.sleep(0.6)
        self.wait_still()
        after = self.grab_region(region)
        # "did not move" as measure_shift sees it (static_diff), so that the page end is reported
        # even when a glowing cell changes a few pixels
        moved = float(np.abs(before.astype(int) - after.astype(int)).mean()) > DRAG_LAYOUT["static_diff"]
        if moved:
            shift = self.measure_shift(before, after, 0, y1 - y0)
            if shift is not None and abs(shift[1]) < 2:
                moved = False                   # matched at zero: only the lighting changed
            else:
                dy = -shift[1] if shift is not None else (y0 - y1)     # content up = page scrolled down
                if shift is None:
                    log("  scroll move not measurable, nominal distance assumed")
                self.page_y = max(0.0, self.page_y + dy)
        log(f"Fortress page scroll {'up' if up else 'down'}: {'moved' if moved else 'end'} (page at {self.page_y:.0f})")
        return moved

    def scroll_to_top(self):
        """Scroll down to the page end; page_y is only reset when the top was really reached."""
        for _ in range(FORTRESS["max_scrolls"] + 1):
            moved = self.scroll_fortress(up=False)
            if moved is None:
                return False                    # page not there: page_y stays as it was
            if not moved:
                self.page_y = 0.0
                self.page_scanned = 0.0         # the page moved: what was scanned may have changed
                return True
        return False

    def pick_target(self, current_first=False):
        """A ready building anywhere on the page (scanned top to bottom), otherwise the first
        bright guard seen on the way, after scrolling back to its screen and locating it again
        (the scroll is not exact). The scan stops early once the bottom buildings have been
        seen and a guard is in hand. `current_first` takes what the current screen offers
        before scanning: a ready building, or a guard when the page was already scanned since
        it was opened. Leaves the page at the top when nothing is attackable."""
        first = None
        if current_first:
            first = self.visible_targets()
            if first[0] is not None:
                return first[0]
            if first[1] and time.time() - self.page_scanned < FORTRESS["scan_valid"]:
                return first[1][0]
        if self.page_y > 0:                     # left mid-way by an earlier pick
            self.scroll_to_top()
            first = None
        guard, steps, seen_labels = None, 0, set()
        for i in range(FORTRESS["max_scrolls"] + 1):
            building, guards, names = first if (i == 0 and first is not None) else self.visible_targets()
            seen_labels |= names
            if building is not None:
                return building
            if guards and guard is None:
                guard = (i, guards[0], self.page_y)
            if guard is not None and seen_labels >= set(FORTRESS["bottom_labels"]):
                steps = i                       # the last buildings seen, none ready, a guard in hand
                self.page_scanned = time.time()
                break
            if i == FORTRESS["max_scrolls"] or not self.scroll_fortress(up=True):
                steps = i
                self.page_scanned = time.time()
                break
        if guard is None:
            if steps:
                self.scroll_to_top()
            return None
        step, g, guard_page_y = guard
        for _ in range(steps - step):           # straight back to the guard's screen
            self.scroll_fortress(up=False)
        if steps != step:                       # scrolled: locate the guard again
            # look; wait once when the page should be right (animation); then correct one step
            # towards where the guard was seen, then two steps the other way (one undoes the
            # first fix), looking again after each move
            toward = self.page_y < guard_page_y
            fixes = ([None] if abs(self.page_y - guard_page_y) < FORTRESS["relocate_slack"] else []) + [toward, not toward, not toward]
            for attempt in range(len(fixes) + 1):
                _, guards, _ = self.visible_targets()
                g = guards[0] if guards else None
                if g is not None or attempt == len(fixes):
                    break
                log(f"Guard not found again after scrolling back (attempt {attempt + 1}); page at {self.page_y:.0f}, seen at {guard_page_y:.0f}")
                if fixes[attempt] is None:
                    self.wait_still()
                else:
                    self.scroll_fortress(up=fixes[attempt])
            if g is None:
                self.save_debug("guard_lost")
                self.scroll_to_top()
        return g

    MODAL_KEYS = ("ZBuyPrompt", "ZContinueHint", "ZEstimateLabel", "ZCancel")   # the tap went nowhere else

    def tap_until(self, x, y, what, taps, keys, want="ZGuardAttack", timeout=None):
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
    FORTRESS_DIALOGS = ("ZBuyPrompt", "ZContinueHint", "ZEstimateLabel", "ZCancel", "ZGuardAttack") + tuple(
        k for k in ZoneExplore.DIALOGS if k not in ("ZBuyPrompt", "ZContinueHint", "ZEstimateLabel", "ZCancel",
                                                    "ZGuardAttack", "ZFleetSpeed"))

    def clear_fortress_dialogs(self, on_top=None, passes=3):
        """Dismiss what lies over the fortress page (purchase prompt, 点击任意处继续, estimate
        dialog, building panel, dispatch list, guard popup). `on_top` is the key already
        detected by the caller. Stops as soon as nothing is seen."""
        return self.dismiss_all(self.FORTRESS_DIALOGS, passes, first=on_top)

    def blank_spot(self):
        """On the fortress page: the description text under the title (the map's plain_spot
        needs the map anchors, which the fortress page does not show)."""
        title = self.anchor("ZFortressTitle") or self.fortress_title   # the header may be dimmed by the popup
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
            if on_top == "ZGuardAttack":
                if self.press("ZGuardAttack", f"袭击 ({target.label})", gone="ZGuardAttack"):
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
            self.failed_targets[target.name] = time.time()
        else:
            log(f"This guard opens no 袭击; skipped for {FAILED_TARGET_TTL // 60} min")
            self.tried_spots.append((target.x, target.y + self.page_y, time.time()))
        return "no_attack"

    def pick_dispatch_card(self, index):
        title = get_center("ZDispatchTitle", "Single")
        if title is None:
            return False
        self.click(title.x + DISPATCH_CARDS["dx"], title.y + DISPATCH_CARDS["dy0"] + (index - 1) * DISPATCH_CARDS["spacing"],
                   2, f"fleet card {index}", force=True)
        return True

    def attack_with(self, index):
        """Select an attackable target on the fortress page and send fleet `index`. The action
        is spent at the final 袭击 of the estimate dialog: when the purchase prompt pops up there
        (or anywhere earlier), the actions are bought and the whole selection is redone."""
        if not self.open_fortress():
            log("Could not open the fortress page")
            return False
        target = self.pick_target()
        if target is None:
            log("Nothing attackable on the fortress page")
            return False
        for _ in range(5):
            log(f"Attack {target.label} at ({target.x:.0f},{target.y:.0f}) with fleet {index}")
            result = self.raid_once(index, target)
            if result in ("launched", "cancelled"):     # cancelled = dry run
                self.leave_fortress()                   # back to the map with the "<" button
                return True
            if result in ("retry", "no_attack"):
                # the page may have been left or re-opened at the top: locate a target afresh
                # (a target that opened no 袭击 is already on the skip lists)
                if not self.open_fortress():
                    break
                target = self.pick_target(current_first=True)
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
            target = self.pick_target(current_first=True)    # the page was scanned moments ago
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
            if single_find("ZBuyPrompt"):
                return "buy"
            if single_find("ZEstimateLabel"):
                if self.dry_run:
                    log("[DRY] estimate dialog reached -> would press 袭击; cancelling")
                    self.press("ZCancel", "取消 (dry run)", gone="ZEstimateLabel")
                    return "cancelled"
                if not self.press("ZAttack", "袭击 (estimate)", gone="ZEstimateLabel"):   # estimates do not matter
                    return "buy" if single_find("ZBuyPrompt") else "failed"
                # the action is charged here: give a purchase prompt a moment to show up
                for _ in range(6):
                    if single_find("ZBuyPrompt"):
                        return "buy"
                    time.sleep(0.5)
                log("Attack launched")
                return "launched"
            if single_find("ZDispatchTitle"):
                self.pick_dispatch_card(index)
                continue
            if single_find("ZContinueHint"):
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

    KNOWN_PAGES = ("ZExplore", "ZFortressTitle", "ZMyFleet")

    def on_known_page(self):
        return any(single_find(k) for k in self.KNOWN_PAGES)

    def enter_map_from_main(self):
        """Started on the game main screen (dice board): go to 星际探险 first."""
        if self.on_known_page():
            return True
        if single_find("ZStarExplore"):
            log("Main screen -> 星际探险")
            return self.enter_zone_explore()
        log("Start the program on the zone map or on the game main screen")
        return False

    def run(self, monitor=False):
        if monitor:
            self.wait_for_dice_run()
        else:
            self.enter_map_from_main()
        calibrated = False
        while True:
            if not self.on_map():
                if not self.close_popup() and not self.enter_map_from_main():
                    log("Not on the zone map and no known page to leave; waiting")
                    self.save_debug("unknown_page")
                    if self.dry_run:
                        return
                    time.sleep(POLL)
                    continue
            if not calibrated and self.on_map():
                calibrated = self.calibrate_scale()   # needs the map anchors; once per run
            ships = self.scan_ships()
            if self.pending_repair:
                opened = False
                for i in sorted(self.pending_repair):
                    s = ships.get(i, {})
                    if s.get("status") == "repairing" or s.get("hp") == FULL_HP:
                        self.pending_repair.discard(i)      # nothing left to repair
                    elif s.get("idle"):
                        opened = True
                        self.repair_tries[i] = self.repair_tries.get(i, 0) + 1
                        if self.repair_fleet(i) or self.repair_tries[i] >= PENDING_REPAIR_TRIES:
                            if self.repair_tries[i] >= PENDING_REPAIR_TRIES:
                                log(f"Fleet {i}: giving up on the repair after {PENDING_REPAIR_TRIES} tries")
                            self.pending_repair.discard(i)
                if opened:
                    self.close_fleet_page()
                    ships = self.scan_ships()
            if self.holder is None:
                # every start looks for the gear afresh (it may have been moved by hand); inside
                # the loop the holder is remembered and only verified when swapping
                self.holder = self.find_gear_holder()
                self.close_fleet_page()
                log(f"Gear holder: fleet {self.holder}; map page back: {self.on_map()}")
                ships = self.scan_ships()           # the earlier scan may have seen the dimmed bar
            if self.holder is None:
                log("Could not tell which fleet has the best gear")
                return
            if not self.on_map():
                self.close_fleet_page()
                ships = self.scan_ships()
            h = ships.get(self.holder, {})
            if not h.get("idle"):
                # the gear is on a fleet that is still out (sailing / fighting / returning):
                # nothing can be swapped until it is back
                log(f"Fleet {self.holder} (best gear) is {h.get('status', 'unknown')}; waiting for it to return")
                if self.dry_run:
                    return
                time.sleep(POLL)
                continue
            if h.get("hp") is not None and h["hp"] > HOLDER_OK_HP:
                log(f"Fleet {self.holder} still has {h['hp']}% hp: attacking again without a gear swap")
                target = self.holder
            else:
                fresh = [i for i, s in ships.items()
                         if s["idle"] and s["hp"] == FULL_HP and i != self.holder]
                if not fresh:
                    log("No idle fleet at 100% hp; waiting")
                    if self.dry_run:
                        return
                    time.sleep(POLL)
                    continue
                target = fresh[0]
                if not self.swap_gear(self.holder, target):
                    log("Gear swap failed")
                    if self.dry_run:
                        return
                    time.sleep(POLL)
                    continue
                self.holder = target
                self.save_state(holder=target)
            if not self.attack_with(target):
                if self.dry_run:
                    return
                time.sleep(POLL)
                continue
            if self.dry_run:
                return
            log(f"Waiting for fleet {target} to return")
            self.wait_back(target)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry", action="store_true", help="Detect and log only")
    parser.add_argument("--delay", type=int, default=3)
    parser.add_argument("--debug-shots", action="store_true", help="Save OCR crops to pics/<platform>/zone/debug/")
    parser.add_argument("-m", "--monitor", action="store_true",
                        help="Wait on the dice board until the dice run out, enter 星际探险, then fight")
    args = parser.parse_args()
    if args.debug_shots:
        DEBUG_DIR = os.path.join(os.path.dirname(single_find_map["ZBase"]), "debug")
        os.makedirs(DEBUG_DIR, exist_ok=True)
    time.sleep(args.delay)
    FortressFight(dry_run=args.dry).run(monitor=args.monitor)
