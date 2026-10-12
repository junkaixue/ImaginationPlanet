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
    python fortress_fight.py --dry      # detect and log, no clicks except closing popups
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
from zone_explore import (ZoneExplore, match_all, Point, FLEET_PAGE_LAYOUT, SHIP_LAYOUT, MATCH_TH,
                          _code_version)

# ---- 我的舰队 page, logical px relative to the "我的舰队" title center (ZMyFleet)
EQUIP_LAYOUT = {
    "slot_dx": (-151, -76, 0, 76.5, 152.5),          # five columns of equipment slots
    "row_dy": (132.5, 207.5, 305, 380, 475),         # two gear rows, two chess rows, artifact row
    "artifact_slot": (152.5, 132.5),                 # top right: the 神器 slot
    "shield_slot": (152.5, 475),                     # bottom right lv.6 shield: never touched
    "power_dx": 0, "power_dy": 618, "power_half_w": 95, "power_half_h": 15,   # "战力:835.26万"
    "back_dx": -187,                                 # "<<" close arrow left of the title
    "loadout_dx": 3, "loadout_dy": 305,              # center of the loadout grid (ZLoadoutStandard)
    "loadout_th": 0.9,                               # the holder's grid matches the standard >= this ...
    "loadout_margin": 0.05,                          # ... and clearly better than every other tab
}
# ---- 编辑舰队 page, relative to its title center. The equipped items sit in the bottom area;
# clicking one removes it and the rest shift left, an empty place shows a "+" placeholder.
EDIT_LAYOUT = {
    "tab_dy": 65,
    "tabs": [   # (tab dx, possible item positions)
        (-76, [(-40, 500), (35, 500)]),                                  # 飞行器 (2)
        (-26, [(0, 500), (-40, 500), (35, 500)]),                        # 主题皮肤
        (24, [(0, 500), (-40, 500), (35, 500)]),                         # 骰子皮肤
        (75, [(dx, dy) for dy in (465, 542.5) for dx in (-152.5, -76.5, 0, 76, 152.5)]),   # 棋子 (10)
    ],
    "plus_radius": 45,
}
# ---- 编辑装备 page (bottom-row artifacts 炬团令牌/烙印/战旗/密契), relative to its title center
GEAR_LAYOUT = {"tab_dx": (-75, -25, 25, 75), "tab_dy": 62, "preview": (0, 470)}
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
DEBUG_DIR = None             # --debug-shots: save the OCR crops here
RETURN_TIMEOUT = 40 * 60     # seconds to wait for the fighting fleet to come back
POLL = 60


class FortressFight(ZoneExplore):
    def __init__(self, dry_run=False):
        super().__init__(dry_run=dry_run)
        self.holder = None        # fleet index currently carrying the best gear
        log(f"FortressFight ready (code={_code_version()})")

    # ------------------------------------------------------------------ fleet page
    def open_fleet_page(self):
        if single_find("ZMyFleet"):
            return True
        if not self.on_map():
            self.close_popup()
        team = self.ui("team")
        if team is None:
            return False
        self.click(team.x, team.y, 2, "队伍", force=True)
        return self.wait_for("ZMyFleet", 8)

    def fleet_title(self):
        return self.anchor("ZMyFleet")

    def close_fleet_page(self):
        """Close 我的舰队 (and anything on top of it). The top bar is dimmed under the panel, so
        ship status and hp can only be read once it is closed."""
        for _ in range(4):
            if single_find("ZEditFleetTitle") or single_find("ZEditGearTitle") or single_find("ZEditArtifactTitle"):
                self.click_button("ZCancel", 1.5, force=True)
                continue
            title = self.fleet_title()
            if title is None or not single_find("ZMyFleet"):
                break
            self.click(title.x + EQUIP_LAYOUT["back_dx"], title.y, 1.5, "close 我的舰队", force=True)
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
        try:
            import pytesseract
            import re
            patch = color[y1:y2, x1:x2].astype(int)
            # the number is yellow; "战力:" is white and would be read as digits
            r, g, b = patch[..., 0], patch[..., 1], patch[..., 2]
            yellow = (r > 170) & (g > 140) & (b < 130)
            mask = np.where(yellow, 0, 255).astype(np.uint8)
            mask = cv2.resize(mask, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
            mask = cv2.copyMakeBorder(mask, 10, 10, 10, 10, cv2.BORDER_CONSTANT, value=255)
            txt = pytesseract.image_to_string(mask, config="--psm 7 -c tessedit_char_whitelist=0123456789.")
            if DEBUG_DIR:
                cv2.imwrite(os.path.join(DEBUG_DIR, f"power_{time.strftime('%H%M%S')}.png"),
                            cv2.cvtColor(color[y1:y2, x1:x2], cv2.COLOR_RGB2BGR))
            nums = re.findall(r"\d+\.\d+|\d+", txt)
            if not nums:
                return None
            whole, _, frac = nums[0].partition(".")
            return float(f"{whole}.{frac[:2]}") if frac else float(whole)   # "万" is read as a trailing digit
        except Exception as e:
            log(f"战力 OCR failed: {e}")
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

    def find_gear_holder(self):
        """The fleet carrying the best equipment: the tab whose whole grid matches the standard
        loadout screenshot. 战力 is logged for reference only (OCR confuses 5 and 9 at times)."""
        if not self.open_fleet_page():
            return None
        powers, scores = {}, {}
        for i in range(1, SHIP_LAYOUT["slots"] + 1):
            self.select_tab(i)
            powers[i] = self.read_power()
            scores[i] = self.loadout_score()
        log("Fleet power: " + ", ".join(f"{i}:{p}" for i, p in powers.items())
            + " | loadout match: " + ", ".join(f"{i}:{s:.2f}" for i, s in scores.items()))
        ranked = sorted(scores.items(), key=lambda kv: -kv[1])
        best, second = ranked[0], ranked[1] if len(ranked) > 1 else (None, 0.0)
        if best[1] >= EQUIP_LAYOUT["loadout_th"] and best[1] - second[1] >= EQUIP_LAYOUT["loadout_margin"]:
            return best[0]
        log("No fleet matches the standard loadout; falling back to the highest 战力")
        valid = {i: p for i, p in powers.items() if p is not None}
        return max(valid, key=valid.get) if valid else None

    # ------------------------------------------------------------------ equipment moves
    def unequip_all(self, index):
        """Remove every piece of gear from fleet `index` through the 编辑舰队 tabs."""
        if not self.open_fleet_page():
            return False
        self.select_tab(index)
        title = self.fleet_title()
        self.click(title.x + EQUIP_LAYOUT["slot_dx"][0], title.y + EQUIP_LAYOUT["row_dy"][0], 2, "gear slot")
        if self.dry_run:
            log("[DRY] would clear 飞行器/主题皮肤/骰子皮肤/棋子 and confirm")
            return True
        if not self.wait_for("ZEditFleetTitle", 8):
            log("编辑舰队 did not open")
            self.close_popup()
            return False
        et = get_center("ZEditFleetTitle", "Single")
        for tab_dx, slots in EDIT_LAYOUT["tabs"]:
            self.click(et.x + tab_dx, et.y + EDIT_LAYOUT["tab_dy"], 1.5, "edit tab")
            removed = 0
            for _ in range(len(slots) + 2):
                pluses = get_all("ZPlusSlot", "Single")
                occupied = [Point(et.x + dx, et.y + dy) for dx, dy in slots
                            if not any(abs(p.x - et.x - dx) < EDIT_LAYOUT["plus_radius"]
                                       and abs(p.y - et.y - dy) < EDIT_LAYOUT["plus_radius"] for p in pluses)]
                if not occupied or (pluses and removed >= len(slots)):
                    break
                self.click(occupied[0].x, occupied[0].y, 1.0, "equipped item (remove)")
                removed += 1
                if not pluses and removed >= len(slots):
                    break
            log(f"  tab {tab_dx:+}: {removed} removal click(s)")
        ok = self.click_button("ZRepairOk", 2)      # the "确认" button shares the template
        log("Gear removed and confirmed" if ok else "确认 not found after removing gear")
        if ok and UNEQUIP_BOTTOM_ARTIFACTS:
            self.unequip_bottom_artifacts(index)
        return ok

    def unequip_bottom_artifacts(self, index):
        """The four bottom-row artifact slots open 编辑装备 (tabs 炬团令牌/烙印/战旗/密契); the
        equipped one is shown in the preview area. Clicking the preview is assumed to remove it."""
        if not self.open_fleet_page():
            return False
        self.select_tab(index)
        title = self.fleet_title()
        self.click(title.x + EQUIP_LAYOUT["slot_dx"][0], title.y + EQUIP_LAYOUT["row_dy"][4], 2, "bottom artifact slot")
        if not self.wait_for("ZEditGearTitle", 8):
            log("编辑装备 did not open")
            self.close_popup()
            return False
        gt = get_center("ZEditGearTitle", "Single")
        for tab_dx in GEAR_LAYOUT["tab_dx"]:
            self.click(gt.x + tab_dx, gt.y + GEAR_LAYOUT["tab_dy"], 1.5, "gear tab")
            px, py = GEAR_LAYOUT["preview"]
            self.click(gt.x + px, gt.y + py, 1.0, "equipped artifact (remove)")
        ok = self.click_button("ZRepairOk", 2)
        log("Bottom artifacts cleared" if ok else "确认 not found on 编辑装备")
        return ok

    def auto_equip(self, index):
        if not self.open_fleet_page():
            return False
        self.select_tab(index)
        if self.dry_run:
            log(f"[DRY] would press 一键配队 on fleet {index}")
            return True
        if not self.click_button("ZAutoEquip", 2):
            log("一键配队 not found")
            return False
        if self.wait_for("ZRepairOk", 3):           # a confirmation dialog, if any
            self.click_button("ZRepairOk", 2)
        return True

    def ensure_boss_artifact(self, index):
        """Top-right artifact slot must hold 残骸本源."""
        if not self.open_fleet_page():
            return False
        self.select_tab(index)
        title = self.fleet_title()
        dx, dy = EQUIP_LAYOUT["artifact_slot"]
        self.click(title.x + dx, title.y + dy, 2, "artifact slot")
        if self.dry_run:
            log("[DRY] would select 残骸本源 and confirm")
            return True
        if not self.wait_for("ZEditArtifactTitle", 8):
            log("编辑低级神器 did not open")
            self.close_popup()
            return False
        target = get_center("ZArtifactTarget", "Single")
        check = get_center("ZArtifactCheck", "Single")
        if target is None:
            log("残骸本源 not found in the artifact grid")
            self.click_button("ZCancel", 2)
            return False
        if check is not None and abs(check.x - target.x) < 60 and abs(check.y - target.y) < 80:
            log("残骸本源 already equipped")
            self.click_button("ZCancel", 2)
            return True
        self.click(target.x, target.y, 1.5, "残骸本源")
        ok = self.click_button("ZRepairOk", 2)
        log("Artifact set to 残骸本源" if ok else "确认 not found on the artifact page")
        return ok

    def repair_fleet(self, index):
        """一键配队 first (a fleet without a loadout cannot be repaired), then 修理舰队."""
        if not self.auto_equip(index):
            return False
        if self.dry_run:
            log(f"[DRY] would repair fleet {index}")
            return True
        ok = self.click_button("ZRepair", 2)
        if ok and self.wait_for("ZRepairPrompt", 6):
            ok = self.click_button("ZRepairOk", 2)
        log(f"Fleet {index} repair {'confirmed' if ok else 'failed'}")
        return ok

    def swap_gear(self, holder, target):
        log(f"Move the best gear from fleet {holder} to fleet {target}")
        if not self.unequip_all(holder):
            return False
        if not self.auto_equip(target):
            return False
        if not self.ensure_boss_artifact(target):
            return False
        if not self.dry_run:
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
        if self.read_zone() != "central":
            self.switch_zone("central")
        icon = get_center("ZFortressMap", "Single")
        if icon is None:
            log("铸械要塞 icon not on screen")
            return False
        self.click(icon.x, icon.y, 2.5, "铸械要塞", force=True)
        if single_find("ZGo"):
            self.click_button("ZGo", 2.5, force=True)
        return self.wait_for("ZFortressTitle", 8)

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
                   2, f"fleet card {index}")
        return True

    def attack_with(self, index):
        """Select an attackable target on the fortress page and send fleet `index`."""
        if not self.open_fortress():
            return False
        target = self.pick_target()
        if target is None:
            log("Nothing attackable on the fortress page")
            return False
        name, x, y = target
        log(f"Attack {name} at ({x:.0f},{y:.0f}) with fleet {index}")
        if self.dry_run:
            return True
        self.click(x, y, 1.5, name)
        if not self.click_button("ZGuardAttack", 2):
            log("袭击 did not appear")
            return False
        for _ in range(12):
            if single_find("ZEstimateLabel"):
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
                self.holder = self.find_gear_holder()
                self.close_fleet_page()
            if self.holder is None:
                log("Could not tell which fleet has the best gear")
                return
            fresh = self.full_hp_idle(exclude=self.holder)
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
