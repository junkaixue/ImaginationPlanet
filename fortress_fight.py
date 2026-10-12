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
    6. Map -> 铸械要塞 -> click a bright guard (dim ones are not attackable yet) -> 袭击 ->
       派遣舰队 list: pick the fresh fleet's card (it also has the highest 战力) -> battle
       estimate: always attack. When no guard is bright, the buildings (商店/委托站/指挥所)
       whose guards are cleared are attacked the same way.
    7. Wait for the fleet to come back, then repeat with the next full-hp fleet.

Only one fleet fights at a time (there is one set of best gear). No zoom or map dragging.

Usage:
    python fortress_fight.py --dry      # does the gear swap and repair for real, cancels at the attack
    python fortress_fight.py            # full loop
"""

import argparse
import os
import time

import cv2
import numpy as np
import pyautogui

from common import single_find, get_center, get_all, single_find_map
from log_helper import log
from click import click_at
from zone_explore import (ZoneExplore, match_all, Point, FLEET_PAGE_LAYOUT, SHIP_LAYOUT, MATCH_TH,
                          _code_version)

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
    "burst_gap": 0.12,         # seconds between removal taps (bursts are cheap, extra taps hit "+")
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
    "scroll_dy": 380,         # the page is taller than the screen: scroll this much per step
    "scroll_x_dx": 0,         # scroll gesture column, relative to the title
    "scroll_y0_dy": 650,      # gesture from title+y0 up to title+y1 (content moves up)
    "scroll_y1_dy": 270,
    "max_scrolls": 6,
}
FULL_HP = 100
HOLDER_OK_HP = 90            # the gear holder attacks again by itself above this hp (no swap)
DEBUG_DIR = None             # --debug-shots: save the OCR crops here
STATE_FILE = os.path.join(os.path.dirname(single_find_map["ZBase"]), "fortress_state.json")   # {"holder": N}
RETURN_TIMEOUT = 40 * 60     # seconds to wait for the fighting fleet to come back
POLL = 60


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
        log(f"FortressFight ready (code={_code_version()})")

    # ------------------------------------------------------------------ fleet page
    EDIT_PAGES = ("ZEditFleetTitle", "ZEditCatTitle", "ZEditGearTitle", "ZEditArtifactTitle")

    def edit_page_open(self):
        k = next((k for k in self.EDIT_PAGES if single_find(k)), None)
        if k is None and single_find("ZCloseHint") and not single_find("ZMyFleet") and get_center("ZRepairOk", "Single"):
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
        """Edit sub-pages are confirmed, not cancelled; then the generic popup handling."""
        if self.edit_page_open():
            self.confirm_edit("close_popup")
        return super().close_popup(tries)

    def open_fleet_page(self):
        if single_find("ZMyFleet"):
            return True
        if self.edit_page_open():
            self.confirm_edit("open_fleet_page")
            if single_find("ZMyFleet"):
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

    def select_tab(self, index):
        title = self.fleet_title()
        if title is None:
            return False
        self.click(title.x + FLEET_PAGE_LAYOUT["tab_dx0"] + (index - 1) * FLEET_PAGE_LAYOUT["tab_spacing"],
                   title.y + FLEET_PAGE_LAYOUT["tab_dy"], 1.5, f"fleet tab {index}", force=True)
        return True

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
        if not self.open_fleet_page():
            return False
        self.select_tab(index)
        title = self.fleet_title()
        self.click(title.x + EQUIP_LAYOUT["slot_dx"][0], title.y + EQUIP_LAYOUT["row_dy"][0], 2, "gear slot", force=True)
        if not self.wait_for("ZEditFleetTitle", 8):
            log("编辑舰队 did not open")
            self.close_popup()
            return False
        et = get_center("ZEditFleetTitle", "Single")
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
        if ok and UNEQUIP_BOTTOM_ARTIFACTS:
            self.unequip_bottom_artifacts(index)
        return ok

    def unequip_right_artifacts(self, index):
        """The artifact slots in the right column (rows 1 and 2) each open their own edit page;
        the equipped artifact sits in the preview area above 取消/确认, tapping it removes it."""
        for row in ARTIFACT_SLOTS["rows"]:
            if not self.open_fleet_page():
                return False
            self.select_tab(index)
            title = self.fleet_title()
            self.click(title.x + EQUIP_LAYOUT["slot_dx"][4], title.y + EQUIP_LAYOUT["row_dy"][row], 2,
                       f"artifact slot row {row + 1}", force=True)
            if not self.wait_for("ZCloseHint", 6):
                log(f"Artifact page for row {row + 1} did not open")
                continue
            ok = get_center("ZRepairOk", "Single")
            if ok is None:
                log("确认 not found on the artifact page")
                self.close_popup()
                continue
            px, py = ARTIFACT_SLOTS["preview_from_confirm"]
            self.burst(ok.x + px, ok.y + py, 3)
            self.confirm_edit(f"artifact row {row + 1}")
        return True

    def burst(self, x, y, times):
        """Tap the same spot many times quickly: removal taps on an already empty position do
        nothing, so over-tapping is harmless and far more reliable than counting."""
        rx, ry = self.to_real(x, y)
        for _ in range(times):
            click_at(rx, ry)
            time.sleep(EDIT_LAYOUT["burst_gap"])
        self.invalidate_shot()
        return times

    def tab_selected(self, et, tab_dx):
        """The selected tab shows a bright underline below its label."""
        self.invalidate_shot()
        gray = self.shot()[1]
        cx, cy = et.x + tab_dx, et.y + EDIT_LAYOUT["tab_underline_dy"]
        x1, x2 = int((cx - EDIT_LAYOUT["tab_half_w"]) * self.sft), int((cx + EDIT_LAYOUT["tab_half_w"]) * self.sft)
        y1, y2 = int((cy - 5) * self.sft), int((cy + 5) * self.sft)
        band = gray[y1:y2, x1:x2]
        if band.size == 0:
            return False
        rows = band.mean(axis=1)
        return float(rows.max()) > 110          # unselected tabs stay below ~45 here

    def select_edit_tab(self, et, name, tab_dx):
        for attempt in range(EDIT_LAYOUT["tab_retries"]):
            self.click(et.x + tab_dx, et.y + EDIT_LAYOUT["tab_dy"], 1.2, f"tab {name}", force=True)
            if self.tab_selected(et, tab_dx):
                return True
            log(f"  tab {name} not selected yet (attempt {attempt + 1})")
        return False

    def unequip_cats(self, index):
        """The cat slot (left of the artifact) opens 编辑猫护法; the three equipped cats sit at
        the bottom, tapping the leftmost one repeatedly removes them."""
        if not self.open_fleet_page():
            return False
        self.select_tab(index)
        title = self.fleet_title()
        dx, dy = CAT_LAYOUT["slot"]
        self.click(title.x + dx, title.y + dy, 2, "cat slot", force=True)
        if not self.wait_for("ZEditCatTitle", 8):
            log("编辑猫护法 did not open")
            self.close_popup()
            return False
        ct = get_center("ZEditCatTitle", "Single")
        ix, iy = CAT_LAYOUT["item"]
        self.burst(ct.x + ix, ct.y + iy, CAT_LAYOUT["count"] * 3)
        ok = self.confirm_edit("编辑猫护法")
        log("Cats removed" if ok else "编辑猫护法 could not be confirmed")
        return ok

    def unequip_bottom_artifacts(self, index):
        """The four bottom-row artifact slots open 编辑装备 (tabs 炬团令牌/烙印/战旗/密契); the
        equipped one is shown in the preview area. Clicking the preview is assumed to remove it."""
        if not self.open_fleet_page():
            return False
        self.select_tab(index)
        title = self.fleet_title()
        self.click(title.x + EQUIP_LAYOUT["slot_dx"][0], title.y + EQUIP_LAYOUT["row_dy"][4], 2, "bottom artifact slot", force=True)
        if not self.wait_for("ZEditGearTitle", 8):
            log("编辑装备 did not open")
            self.close_popup()
            return False
        gt = get_center("ZEditGearTitle", "Single")
        for tab_dx in GEAR_LAYOUT["tab_dx"]:
            for attempt in range(EDIT_LAYOUT["tab_retries"]):
                self.click(gt.x + tab_dx, gt.y + GEAR_LAYOUT["tab_dy"], 1.2, "gear tab", force=True)
                if self.tab_selected(gt, tab_dx):
                    break
                log(f"  gear tab {tab_dx:+} not selected yet (attempt {attempt + 1})")
            px, py = GEAR_LAYOUT["preview"]
            self.burst(gt.x + px, gt.y + py, 3)
        ok = self.confirm_edit("编辑装备")
        log("Bottom artifacts cleared" if ok else "编辑装备 could not be confirmed")
        return ok

    def auto_equip(self, index):
        if not self.open_fleet_page():
            return False
        self.select_tab(index)
        if not self.click_button("ZAutoEquip", 2, force=True):
            log("一键配队 not found")
            return False
        if self.wait_for("ZRepairOk", 3):           # a confirmation dialog, if any
            self.click_button("ZRepairOk", 2, force=True)
        return True

    def ensure_boss_artifact(self, index):
        """Top-right artifact slot must hold 残骸本源."""
        if not self.open_fleet_page():
            return False
        self.select_tab(index)
        title = self.fleet_title()
        dx, dy = EQUIP_LAYOUT["artifact_slot"]
        self.click(title.x + dx, title.y + dy, 2, "artifact slot", force=True)
        opened = False
        for _ in range(16):
            if self.edit_page_open():
                opened = True
                break
            time.sleep(0.5)
        if not opened:
            log("The artifact page did not open")
            self.close_popup()
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
        """一键配队 first (a fleet without a loadout cannot be repaired), then 修理舰队."""
        if not self.auto_equip(index):
            return False
        ok = self.click_button("ZRepair", 2, force=True)
        if ok and self.wait_for("ZRepairPrompt", 6):
            ok = self.click_button("ZRepairOk", 2, force=True)
        log(f"Fleet {index} repair {'confirmed' if ok else 'failed'}")
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
        self.repair_fleet(holder)
        self.close_fleet_page()
        return True

    # ------------------------------------------------------------------ fortress page
    def open_fortress(self):
        if single_find("ZFortressTitle"):
            return True
        if not self.on_map():
            self.close_popup()
        # the program is started in the central zone with the fortress on screen; no zone logic
        icon = get_center("ZFortressMap", "Single")
        if icon is None:
            log("铸械要塞 icon not on screen")
            self.save_debug("no_fortress_icon")
            return False
        log(f"铸械要塞 icon at ({icon.x:.0f},{icon.y:.0f})")
        self.click(icon.x, icon.y, 2.5, "铸械要塞", force=True)
        # the icon opens an info popup (位置/坐标/距离/守卫等级) with a 袭击 button -> fortress page
        if self.wait_for("ZGuardAttack", 5):
            log("Fortress popup -> 袭击")
            self.click_button("ZGuardAttack", 2.5, force=True)
        elif single_find("ZGo"):
            self.click_button("ZGo", 2.5, force=True)
        if self.wait_for("ZFortressTitle", 8):
            return True
        log("Fortress page title not seen after clicking the icon")
        self.save_debug("fortress_page_missing")
        return False

    def guard_cells(self):
        """[(x, y, bright)] of every guard cell on the fortress page (logical px)."""
        title = get_center("ZFortressTitle", "Single")
        color, gray = self.shot()
        t = self.full_template("ZGuardBright")
        out = []
        for cx, cy, conf in match_all(gray, t, FORTRESS["guard_th"]):
            x, y = cx / self.sft, cy / self.sft
            if title is not None and y < title.y + FORTRESS["grid_top_dy"]:
                continue
            cell = gray[cy - 20:cy + 20, cx - 20:cx + 20]
            out.append((x, y, float(cell.mean()) >= FORTRESS["bright_min"]))
        return out

    def buildings(self):
        """[(name, x, y, bright)] for 商店 / 委托站 / 指挥所."""
        color, gray = self.shot()
        out = []
        for key, name in (("ZShopLabel", "商店"), ("ZDepotLabel", "委托站"), ("ZCommandLabel", "指挥所")):
            p = get_center(key, "Single")
            if p is None:
                continue
            px, py = int(p.x * self.sft), int(p.y * self.sft)
            patch = gray[max(0, py - 90):py - 10, max(0, px - 40):px + 40]      # the building above its label
            out.append((name, p.x, p.y - 35, float(patch.mean()) >= FORTRESS["building_bright_min"]))
        return out

    def visible_target(self):
        cells = self.guard_cells()
        bright = [c for c in cells if c[2]]
        log(f"Guards: {len(cells)} cells, {len(bright)} attackable")
        if bright:
            bright.sort(key=lambda c: (c[1], c[0]))
            x, y, _ = bright[0]
            return "guard", x, y
        for name, x, y, ok in self.buildings():
            if ok:
                return name, x, y
        return None

    def scroll_fortress(self, up=True):
        """Scroll the fortress page (it is taller than the screen). Returns False when the page
        did not move, i.e. the end was reached."""
        from zone_explore import drag as _drag
        title = get_center("ZFortressTitle", "Single")
        if title is None:
            return False
        x = title.x + FORTRESS["scroll_x_dx"]
        y0, y1 = title.y + FORTRESS["scroll_y0_dy"], title.y + FORTRESS["scroll_y1_dy"]
        if not up:
            y0, y1 = y1, y0
        self.invalidate_shot()
        before = self.shot()[1]
        rx0, ry0 = self.to_real(x, y0)
        rx1, ry1 = self.to_real(x, y1)
        if self.dry_run:
            log(f"[DRY] would scroll the fortress page {'up' if up else 'down'}")
        _drag(rx0, ry0, rx1, ry1)
        self.invalidate_shot()
        time.sleep(0.6)
        self.wait_still()
        after = self.shot()[1]
        moved = float(np.abs(before.astype(int) - after.astype(int)).mean()) > 3.0
        log(f"Fortress page scroll {'up' if up else 'down'}: {'moved' if moved else 'end'}")
        return moved

    def pick_target(self):
        """First attackable thing on the page, scrolling down through it when the visible part
        has none. Scrolls back up when nothing is found at all."""
        for i in range(FORTRESS["max_scrolls"] + 1):
            t = self.visible_target()
            if t is not None:
                return t
            if i == FORTRESS["max_scrolls"] or not self.scroll_fortress(up=True):
                break
        for _ in range(FORTRESS["max_scrolls"]):
            if not self.scroll_fortress(up=False):
                break
        return None

    def pick_dispatch_card(self, index):
        title = get_center("ZDispatchTitle", "Single")
        if title is None:
            return False
        self.click(title.x + DISPATCH_CARDS["dx"], title.y + DISPATCH_CARDS["dy0"] + (index - 1) * DISPATCH_CARDS["spacing"],
                   2, f"fleet card {index}", force=True)
        return True

    def attack_with(self, index):
        """Select an attackable target on the fortress page and send fleet `index`."""
        if not self.open_fortress():
            log("Could not open the fortress page")
            return False
        target = self.pick_target()
        if target is None:
            log("Nothing attackable on the fortress page")
            return False
        name, x, y = target
        log(f"Attack {name} at ({x:.0f},{y:.0f}) with fleet {index}")
        # a dry run goes all the way to the battle estimate (selecting the guard, 袭击 and the
        # fleet card are reversible) and cancels there instead of attacking
        self.click(x, y, 1.5, name, force=True)
        if not self.click_button("ZGuardAttack", 2, force=True):
            log("袭击 did not appear")
            self.save_debug("no_guard_attack")
            return False
        for _ in range(12):
            if single_find("ZEstimateLabel"):
                if self.dry_run:
                    log("[DRY] estimate dialog reached -> would press 袭击; cancelling")
                    self.click_button("ZCancel", 2, force=True)
                    self.close_popup()
                    return True
                self.click_button("ZAttack", 2)         # estimates do not matter here
                log("Attack launched")
                self.close_popup()
                return True
            if single_find("ZDispatchTitle"):
                self.pick_dispatch_card(index)
                continue
            if single_find("ZBuyPrompt"):
                self.handle_buy_prompt(True)
                continue
            if single_find("ZContinueHint"):
                self.click_button("ZContinueHint", 1.5)
                continue
            time.sleep(1)
        log("Attack flow did not reach the estimate dialog")
        self.close_popup()
        return False

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

    def run(self):
        self.calibrate_scale()
        while True:
            if not self.on_map():
                self.close_popup()
            if self.holder is None:
                # every start looks for the gear afresh (it may have been moved by hand); inside
                # the loop the holder is remembered and only verified when swapping
                self.holder = self.find_gear_holder()
                self.close_fleet_page()
                log(f"Gear holder: fleet {self.holder}; map page back: {self.on_map()}")
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
    args = parser.parse_args()
    if args.debug_shots:
        DEBUG_DIR = os.path.join(os.path.dirname(single_find_map["ZBase"]), "debug")
        os.makedirs(DEBUG_DIR, exist_ok=True)
    time.sleep(args.delay)
    FortressFight(dry_run=args.dry).run()
