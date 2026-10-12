"""
Zone Explore - auto dispatch 5 fleets to resource points on the zone map.

Flow (confirmed with screenshots in pics/mac/zone/pages/):
    box:     map -> click box -> popup "前往" -> "派遣舰队" list -> click idle fleet (done)
    battle:  map -> click target -> target page "袭击" -> "派遣舰队" list -> click idle fleet
             -> "战斗预估" dialog: 大胜/小胜/不分伯仲 -> "袭击", 大败/小败 -> "取消"
    factory: map -> click factory -> factory page with 5 occupant slots (one fleet per lord);
             if our fleet is already there, skip; else click a free slot, or attack the
             occupant whose estimate is a win.
    repair:  ship hp < REPAIR_BELOW and idle -> bottom "队伍" -> "我的舰队" -> tab of that
             fleet -> "修理舰队" -> confirm.

The map is much larger than the screen: every round the view is dragged to the top-left
corner and then swept row by row (serpentine) until the map cannot be dragged any further.
Each drag is measured by re-finding a patch of the map in the next screenshot, so the
sweep stops exactly at the edges and the same resource is not counted twice.

Templates live in pics/<platform>/zone/ and are registered in common.single_find_map
with a "Z" prefix. Capture page screenshots with:
    python capture_template.py zone --full

Usage:
    python zone_explore.py --dry        # drag + detect only, no dispatch clicks
    python zone_explore.py --drag-test  # one drag left and back, prints the measured shift
    python zone_explore.py --click-test # click 50% then 75% to verify clicks reach the game
    python zone_explore.py --monitor    # wait in the dice run, enter 星际探险 when the dice run out
    python zone_explore.py --zone-test 03   # switch to zone 03 through the chooser and verify
    python zone_explore.py              # full loop
    python imaginationplanet.py -ze     # same through the main entry
"""

import argparse
import math
import os
import platform
import time
from collections import namedtuple

import cv2
import numpy as np
import pyautogui

from click import click_at, drag
from common import (get_scaling_factor, single_find, get_center, get_all, find_all_with_path,
                    screen_shot, single_find_map, simple_single_find, single_find_with_path)
from log_helper import log

Point = namedtuple('Point', ['x', 'y'])
Candidate = namedtuple('Candidate', ['kind', 'score', 'x', 'y'])
Spot = namedtuple('Spot', ['kind', 'score', 'mx', 'my', 'zone'])   # memorized resource, map coords + zone

# Resource priority: higher score is dispatched first. Kinds not listed are ignored
# (green small ships, small blue battles, alliance crystals, fortress).
RESOURCE_SCORES = {
    "ZFactory1": 100,       # factories always first
    "ZFactory2": 100,
    "ZFactory3": 100,
    "ZFactory4": 100,       # blue factory with an ore symbol
    "ZYellowBox": 4,        # golden chest, 4 points
    "ZBigBattle": 3,        # blue big battle, 3 points
    "ZRedBigBattle": 3,     # red big battle with star badge, 3 points
    "ZYellowBoss": 4,       # yellow boss car, battle type, 4 points
    "ZBox": 3,              # purple box, 3 points
    # "ZRedVehicle": 3,     # red car icon: user reports it is a small target, not worth an action
}
FACTORY_KINDS = {"ZFactory1", "ZFactory2", "ZFactory3", "ZFactory4"}
# Valuable kinds that may be half hidden under undiscovered map: also match each half of
# the template (top/bottom/left/right) with a stricter threshold and click the visible half.
PARTIAL_KINDS = {"ZFactory1", "ZFactory2", "ZFactory3", "ZFactory4", "ZBigBattle", "ZRedBigBattle", "ZYellowBox", "ZYellowBoss"}
PARTIAL_TH = 0.85
# Grayscale matching cannot tell icons apart by colour. The 3-point box is PURPLE (bright
# pixels ~R159 G135 B230); the common teal box (~R125 G227 B208) has the same shape and is
# not worth an action. Each rule gets the mean RGB of the icon's bright pixels.
KIND_COLOR_RULES = {
    "ZBox": lambda r, g, b: b > g + 30 and r > g,          # purple / pink, not teal
}
ICON_COLOR_HALF = 12   # logical px: box around the icon center used for the colour sample

# Battle estimates. Anything in LOSS_ESTIMATES (or unknown) is cancelled.
WIN_ESTIMATES = ["ZBigWin", "ZSmallWin", "ZDraw"]
LOSS_ESTIMATES = ["ZBigLoss", "ZSmallLoss"]

REPAIR_BELOW = 50          # repair an idle ship whose hp% is below this

# Actions: every dispatch spends one action (the "n/25" counter under the base icon).
# Free actions regenerate over time; when they are gone, 150 coins buy 5 (30 coins each),
# so bought actions are only worth spending on high-value targets.
ACTION_BUY_ENABLED = True      # buy "星级指令 x5" for 150 coins when free actions are gone
ACTION_PACK_COINS = 150
ACTION_PACK_SIZE = 5
MIN_SCORE_FREE_ACTION = 1      # with free actions left, anything in RESOURCE_SCORES is fine
MIN_SCORE_BOUGHT_ACTION = 1    # user: always buy actions, coins are the only limit
MAX_PACKS_PER_RUN = 10         # coin limit: at most this many 150-coin packs per process run
MATCH_TH = 0.8
POLL_SECONDS = 90
# Monitor mode: stay in the dice run ("自动投掷中") and switch to 星际探险 once the dice run out
# ("更多骰子" popup), or when the run button has shown "长按自动" for RUN_IDLE_SECONDS.
MONITOR_POLL = 30
RUN_IDLE_SECONDS = 180
MORE_DICE_LAYOUT = {"close_dx": -95, "close_dy": 510}   # empty spot relative to the "更多骰子" title
DISPATCH_STEPS = 14        # max page transitions for one dispatch

# ---- Layouts, in LOGICAL pixels, measured on the Mac emulator window at 75% zoom from
# ---- pics/mac/zone/pages/*.png (physical px / 2). Re-measure if the window size changes.

# Ship status bar, relative to the center of ZBase ("16级基地" icon).
SHIP_LAYOUT = {
    "slots": 5,
    "status_dx0": 83.5,     # base center -> ship 1 status text center, x
    "status_dy": 39.5,      # base center -> status text center, y
    "spacing": 58.0,        # distance between consecutive ship slots
    "hp_bar_dy": -19,       # status text center -> hp bar center, y
    "hp_bar_half_w": 24,
    "hp_bar_half_h": 7,
    "actions_dx": -11,      # base center -> "n/25" action counter center
    "actions_dy": 106,
    "actions_half_w": 30,
    "actions_half_h": 10,
}
# Ship status templates with thresholds; the best-confidence match wins per slot ("返航中" and
# "出航中" differ by one character). Unmatched slots are "unknown" and treated as busy.
SHIP_STATUS = [("ZIdle", "idle", 0.85), ("ZBuilding", "building", 0.8), ("ZReturning", "returning", 0.8),
               ("ZSailing", "sailing", 0.8), ("ZRepairing", "repairing", 0.8),
               ("ZCrossSailing", "cross_sailing", 0.8)]

# Zoom bar: the selected level is drawn on a purple pill, the others on the dark bar.
# Positions relative to the center of the "50%" label; the look is decided by color.
ZOOM_LAYOUT = {"dx75": 79.5, "half_w": 30, "half_h": 12, "selected_min_r": 100, "selected_min_b": 120}

# Map area that can hold clickable resources: x relative to ZBase, y relative to ZBase / ZTeam.
MAP_LAYOUT = {"x_min_dx": 15, "x_max_dx": 430, "y_min_dy": 120, "y_max_team_dy": -105}
# Parts of the map area covered by fixed UI (right column: 冰封探索礼, 通缉榜, 任务榜, 我的基地,
# zone thumbnail). Resources under them cannot be clicked; the sweep sees them one stop later.
MAP_EXCLUDE = [(375, 440, 95, 315), (375, 440, 585, 820)]      # (x0, x1, y0, y1) relative to ZBase
MEASURE_X_MAX_DX = 365      # drag movement is measured left of the right UI column (it never moves)

# Map dragging. A drag moves the map content by (dx, dy); the real movement is measured by
# finding a patch of the old screen in the new one. |measured| < edge_frac * |asked| = edge.
DRAG_LAYOUT = {
    "margin": 20,           # keep the finger this far inside the map area
    "overlap_x": 100,       # logical px kept in view between two stops: room for one icon (<= 90)
    "overlap_y": 80,        # and for the measurement strip (overlap - 2 * strip_inset >= 60)
    "edge_retries": 2,      # a zero move without the frame line in view is retried this often
    "hidden_sides": ("top",),   # the top frame line sits under the title bar and is never visible
    "band_x_min_dx": 20,    # horizontal gesture band: x relative to ZBase, left of the right column
    "band_x_max_dx": 365,
    "band_y_dys": (340, 400, 460, 520),   # candidate rows (relative to ZBase) between 任务榜 and 我的基地
    "vert_x_dxs": (0, -60, 60, -120),     # candidate columns for vertical drags, relative to the area centre
    "finger_half": 18,      # the finger must land on plain map: std of this window must be low
    "plain_std": 22,
    "strip_inset": 10,      # logical px trimmed from the overlap strip used to measure movement
    "patch_min_std": 8,     # a strip flatter than this is empty space, only the static test is used
    "area_min_std": 12,     # "did not move" is only believed when the map area has some structure
    "max_unknown_edge": 3,  # consecutive unmeasurable drags towards a hidden edge count as the edge
    "patch_th": 0.6,        # min match of the overlap strip to trust the measured movement
    "edge_frac": 0.25,
    "static_diff": 4.0,     # mean abs pixel diff below this = nothing moved
    "settle": 0.7,          # seconds to wait after a drag before measuring
    "max_drags": 40,        # per direction, safety cap
}
SWEEP_ENABLED = True
# The zone map is framed by purple lines (RGB ~167,102,206). When the frame line of the side we
# are about to reveal is already inside the map area, that side is fully visible: it is an edge.
BOUNDARY_LAYOUT = {"min_r": 110, "min_b": 150, "max_g": 130, "min_bg_diff": 60, "min_ratio": 0.5}
# Dispatch policy:
#   "survey": sweep the whole map first and memorize every resource with its map coordinates,
#             then go back to them best-first (factories are taken immediately during the sweep
#             because other lords compete for them).
#   "greedy": dispatch to whatever is on each screen while sweeping (old behaviour).
DISPATCH_MODE = "survey"
IMMEDIATE_KINDS = FACTORY_KINDS       # dispatched as soon as seen during the survey
NAV_TOLERANCE = 80                    # logical px: re-detected icon must be this close to the memorized spot
RESEEN_TOLERANCE = 120                # logical px: a same-kind spot this close in map coords is the same one

# Zones. The chooser (bottom-right thumbnail button) shows "远古深寒区" with the zones laid out
# around the centre. The layout is fixed, so the cards are clicked at offsets (logical px) from
# the one base coordinate used everywhere: the ZBase icon at the top left. "central" = 深寒战场.
# ZONES is the visiting order; the central zone's spots are dispatched before the others'.
ZONES = ["central", "02", "03", "04", "05", "06", "07"]      # 01 is skipped on purpose (user)
ZONE_LAYOUT = {
    "cards": {"01": (187.7, 212.6), "02": (41.1, 264.1), "03": (336.8, 264.1), "04": (41.1, 444.1), "05": (336.8, 444.1), "06": (41.1, 608.6), "07": (336.8, 608.6), "central": (187.7, 516.0)},   # from the ZBase icon center
    "title_dx": 28, "title_dy": 75, "title_half_w": 62, "title_half_h": 13,   # map title digits, from ZBase
    "title_match_th": 0.9,
    # "深寒外环0X区" is 7 glyphs from x=19 to 220 in the learned crops; glyphs 5-6 are the digits
    "digit_c0": 128, "digit_c1": 196, "digit_match_th": 0.95, "digit_margin": 0.03,
}
# Rival fleets heading to the same target: clicking the target shows a panel "舰队N同目标点舰队:"
# with one "预计到达: hh:mm:ss" per rival. Our own remaining time is the countdown under the
# ship's status in the top bar.
RIVAL_LAYOUT = {"etas_dx0": -80, "etas_dy0": 8, "etas_dx1": 360, "etas_dy1": 58,
                "countdown_dy": 1, "countdown_half_w": 36, "countdown_half_h": 8}

# The zone title ("深寒战场" / "深寒外环04区") is recognised by comparing the title box with crops
# learned on earlier visits (pics/<platform>/zone/zone_titles/<zone>.png); OCR of the digits is
# only a fallback because it misreads some numbers ("04" -> "0").
ZONE_TITLE_DIR = os.path.join(os.path.dirname(single_find_map["ZBase"]), "zone_titles")
SURVEY_TTL = 10 * 60                  # seconds a zone's memorized spots stay valid before re-surveying
# Outer zones are surveyed for these kinds only and without the route-line checks (fast scan);
# the central zone is surveyed for everything.
OUTER_KINDS = ("ZFactory1", "ZFactory2", "ZFactory3", "ZFactory4", "ZYellowBox", "ZYellowBoss", "ZBox")
SHOT_TTL = 0.3                        # seconds a screenshot is reused by the detectors of one stop
DEBUG_SHOT_DIR = None                 # set by --debug-shots: every survey stop saves what the scanner saw
MIN_IDLE_FOR_OTHER_ZONES = 2          # outer zones are only surveyed with at least this many idle ships

# Reference window: every layout and template was captured when the ZBase->ZTeam distance was
# this many physical px. The emulator window can be resized; the round start re-measures it and
# screenshots are rescaled to the reference size, clicks scaled back.
REFERENCE_ANCHOR_DIST = 1681.0
ANCHOR_VERIFY_RADIUS = 40     # logical px searched around a cached anchor before a full search
# Fixed UI, as offsets (logical px, reference window) from the one base coordinate: the center of
# the ZBase icon. Only resources move; everything else is clicked by offset, no image matching.
FIXED_UI = {
    "team": (276.25, 794.25),         # bottom "队伍" button
    "zoom50": (110.5, 710.5),         # "50%" label; 75% is +79.5 to the right
    "select_zone": (402.25, 706.75),  # bottom-right zone chooser thumbnail
    "my_base": (401.0, 628.75),       # "我的基地" button
}
ANCHOR_TH = 0.7

# Our own fleets en route draw a white dashed line from the base to the target. A resource at
# the end of such a line already has a ship (ours, maybe sent by hand) and must not get another.
ROUTE_LAYOUT = {
    "white_min": 215,        # min of R,G,B for a "white" pixel
    "white_spread": 30,      # max (max-min) of R,G,B
    "min_seg": 100,          # physical px, shortest segment Hough may return
    "max_gap": 24,           # physical px, bridges the gaps between dashes
    "min_len": 200,          # physical px, merged line; map labels are at most ~140 px wide
    "min_transitions": 30,   # on/off changes along the line: dashes, not a solid edge (text: <= 25)
    "max_on": 0.8,           # solid white things (ice edges) are not routes
    "end_radius": 45,        # logical px: resource within this of a line end is "targeted"
    "beyond_from": 35,       # logical px: a line that keeps going this far past the icon ...
    "beyond_to": 130,        # ... only passes through it; the icon is not the target
    "beyond_min_on": 0.08,
    "blue_min_on": 0.35,     # rival dashes fill >= 35% of their line (icon-frame rows: <= 30%)
}

# Factory page: occupant slot centers relative to the "当前贡献最高领主" marker center.
FACTORY_LAYOUT = {"slots": 5, "dx0": -47, "spacing": 80, "dy": 381, "free_plus_dy": -25,
                  "quota_dx": 115, "quota_dy": -190, "quota_half_w": 140, "quota_half_h": 10}

# "我的舰队" page: fleet tab centers relative to the title center.
FLEET_PAGE_LAYOUT = {"tab_dx0": -151, "tab_spacing": 76, "tab_dy": 66}

# Boosting a sailing fleet: click its rocket icon in the top bar (icon_dy above the status text;
# cross-zone fleets sometimes need several clicks) -> panel with "加速" -> dialog with one row per
# booster -> "使用" sits use_dx/use_dy from the row label. Quantum = +73500 星里/s, ~250 coins.
BOOST_LAYOUT = {"icon_dy": -40, "max_clicks": 4, "use_dx": 170, "use_dy": 20.5}
# Which booster to use against the fastest rival, by its arrival time: (limit_s, booster, max count)
BOOST_PLAN = [(60, "ZQuantumBoost", 1), (180, "ZSuperBoost", 3), (float("inf"), "ZLargeBoost", 5)]
FACTORY_BOOST = "contested" # "never" | "always" (quantum-boost every fleet sent to a factory) |
                            # "contested": after sending, click the target again; if the rival panel
                            # shows an arrival time shorter than our countdown, use one quantum boost.
                            # Applies to every factory, and in the central zone to any target that
                            # had a rival's blue line (outer zones skip such ordinary targets).


def match_all(gray, template, th):
    """All matches of a template array in a grayscale image: list of (cx, cy, conf)."""
    if template is None or gray.shape[0] < template.shape[0] or gray.shape[1] < template.shape[1]:
        return []
    result = cv2.matchTemplate(gray, template, cv2.TM_CCOEFF_NORMED)
    h, w = template.shape[:2]
    out = []
    while True:
        _, mx, _, loc = cv2.minMaxLoc(result)
        if mx < th:
            break
        x, y = loc
        out.append((x + w // 2, y + h // 2, mx))
        m = int(max(w, h) * 1.2)
        result[max(0, y - m // 2):y + m // 2, max(0, x - m // 2):x + m // 2] = 0
    return out


# pyautogui.screenshot is wrapped once per process so that common.py's matchers see the game at
# the reference window size; the scale is shared, and close() restores the original.
_SCREENSHOT = {"orig": None, "scale": 1.0}


def _scaled_screenshot(*a, **k):
    img = _SCREENSHOT["orig"](*a, **k)
    if img.mode != "RGB":
        # macOS screenshots come back RGBA; every colour sampler here reshapes to (-1, 3)
        # and would scramble the channels on a 4-channel array
        img = img.convert("RGB")
    s = _SCREENSHOT["scale"]
    if abs(s - 1.0) > 0.005:
        img = img.resize((round(img.width / s), round(img.height / s)))
    return img


def _install_screenshot_scaler():
    if pyautogui.screenshot is not _scaled_screenshot:
        _SCREENSHOT["orig"] = pyautogui.screenshot
        _SCREENSHOT["scale"] = 1.0
        pyautogui.screenshot = _scaled_screenshot


def _uninstall_screenshot_scaler():
    if pyautogui.screenshot is _scaled_screenshot and _SCREENSHOT["orig"] is not None:
        pyautogui.screenshot = _SCREENSHOT["orig"]


def _code_version():
    """Short git hash of the working copy, so a log can be matched to the code that produced it."""
    try:
        import subprocess
        here = os.path.dirname(os.path.abspath(__file__))
        return subprocess.check_output(["git", "-C", here, "rev-parse", "--short", "HEAD"],
                                       stderr=subprocess.DEVNULL, timeout=3).decode().strip()
    except Exception:
        return "unknown"


class ZoneExplore:
    def __init__(self, dry_run=False):
        self.dry_run = dry_run
        self.is_mac = platform.system() == "Darwin"
        self.sft = get_scaling_factor()
        self.visited = {}          # spot key (map coords) -> timestamp, avoids re-sending to the same spot
        self.visited_ttl = 1800
        self.rounds = 0
        self.fails = 0
        self.attack_quota = None
        self.actions = None        # (left, max) from the counter, None when unreadable
        self.packs_bought = 0
        self.ocr = None            # None = unknown, True/False once probed
        self.offset = [0.0, 0.0]   # how far the map content has been dragged since the corner
        self.sweep_from_top = True
        self.partials = {}         # kind -> list of (name, template array)
        self.full_templates = {}   # kind -> grayscale template array
        self.anchors = {}          # fixed UI anchors found earlier: key -> Point (verified locally on reuse)
        self.contested = {}        # spot key -> time: a rival's blue line ends there (race + boost)
        self._route_masks = {}     # "white"/"blue" -> (mask, origin) of the last route detection
        self.spots = []            # memorized resources of the current round (map coordinates)
        self.last_dispatched = None   # ship index that left in the last successful dispatch
        self.last_shift = (0.0, 0.0)  # how far the view moved during the last dispatch
        self.rescan_needed = False    # set when a memorized resource is gone (zone memory dropped)
        self._shot, self._shot_time = None, 0.0
        self.last_drag_unknown = False
        self._scan_frame = None
        self.last_landmarks = []      # every template hit of the last scan (any colour): used as landmarks
        self.prev_landmarks = None    # landmarks of the previous survey stop
        self.prev_offset = None       # offset at the previous survey stop
        self.zone = None           # current zone name ("central", "02", ...) or None when unknown
        self.zone_spots = {}       # zone -> {"time": t, "spots": [Spot]} memorized across rounds
        self.win_scale = 1.0       # current window size / reference window size
        _install_screenshot_scaler()
        self._orig_screenshot = _SCREENSHOT["orig"]
        log(f"ZoneExplore init. platform={platform.system()} sft={self.sft} dry_run={dry_run} code={_code_version()}")

    # ------------------------------------------------------------------ screenshots
    def shot(self):
        """(color RGB, gray) of the screen, reused for SHOT_TTL seconds so that the detectors of
        one stop (page check, frame lines, resources, gesture) share one capture."""
        now = time.time()
        if self._shot is None or now - self._shot_time > SHOT_TTL:
            color = np.array(pyautogui.screenshot())
            self._shot = (color, cv2.cvtColor(color, cv2.COLOR_RGB2GRAY))
            self._shot_time = now
        return self._shot

    def invalidate_shot(self):
        self._shot_time = 0.0

    def wait_still(self, timeout=2.5):
        """Block until two captures 0.25 s apart look the same: the map keeps gliding for a
        moment after a drag, and a frame taken mid-glide shows icons at the wrong place."""
        self.invalidate_shot()
        prev = self.shot()[1]
        start = time.time()
        while time.time() - start < timeout:
            time.sleep(0.25)
            self.invalidate_shot()
            cur = self.shot()[1]
            if float(np.abs(prev.astype(int) - cur.astype(int)).mean()) < 1.5:
                return True
            prev = cur
        return False

    # ------------------------------------------------------------------ window scale
    def close(self):
        """Restore the unscaled pyautogui.screenshot for the rest of the process."""
        _uninstall_screenshot_scaler()

    def to_real(self, x, y):
        """Reference-frame logical coordinates -> real screen logical coordinates."""
        return x * self.win_scale, y * self.win_scale

    def raw_click(self, x, y):
        rx, ry = self.to_real(x, y)
        click_at(rx, ry)
        self.invalidate_shot()

    def calibrate_scale(self):
        """Measure the ZBase->ZTeam distance on an unscaled screenshot and set win_scale."""
        shot = np.array(self._orig_screenshot())
        gray = cv2.cvtColor(shot, cv2.COLOR_RGB2GRAY)
        best = None
        for s in [1.0, 0.98, 0.96, 1.02, 0.94, 1.04, 0.92, 1.06, 0.90, 1.08, 0.88, 1.10]:
            pts = []
            for key in ("ZBase", "ZTeam"):
                t = cv2.imread(single_find_map[key], 0)
                ts = cv2.resize(t, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
                r = cv2.matchTemplate(gray, ts, cv2.TM_CCOEFF_NORMED)
                _, conf, _, loc = cv2.minMaxLoc(r)
                pts.append((conf, loc[0] + ts.shape[1] / 2, loc[1] + ts.shape[0] / 2))
            conf = min(p[0] for p in pts)
            if best is None or conf > best[0]:
                best = (conf, pts)
            if conf > 0.97:
                break
        if best is None or best[0] < 0.8:
            log("Scale calibration: anchors not found, keeping previous scale")
            return False
        (_, bx, by), (_, tx, ty) = best[1]
        dist = ((tx - bx) ** 2 + (ty - by) ** 2) ** 0.5
        scale = dist / REFERENCE_ANCHOR_DIST
        if abs(scale - self.win_scale) > 0.005:
            log(f"Window scale {scale:.3f} (anchor distance {dist:.0f} px)")
        self.win_scale = scale
        _SCREENSHOT["scale"] = scale
        return True

    # ------------------------------------------------------------------ anchors (cached)
    def anchor(self, key, gray=None):
        """Center of a fixed UI element. Positions found earlier are reused after a cheap local
        check (the window may move a little); a full search runs only when that fails."""
        t = self.full_template(key)
        if t is None:
            return None
        if gray is None:
            gray = self.shot()[1]
        th, tw = t.shape
        cached = self.anchors.get(key)
        if cached is not None:
            r = int(ANCHOR_VERIFY_RADIUS * self.sft)
            cx, cy = int(cached.x * self.sft), int(cached.y * self.sft)
            x1, y1 = max(0, cx - tw // 2 - r), max(0, cy - th // 2 - r)
            x2, y2 = min(gray.shape[1], cx + tw // 2 + r), min(gray.shape[0], cy + th // 2 + r)
            if x2 - x1 >= tw and y2 - y1 >= th:
                res = cv2.matchTemplate(gray[y1:y2, x1:x2], t, cv2.TM_CCOEFF_NORMED)
                _, conf, _, loc = cv2.minMaxLoc(res)
                if conf >= ANCHOR_TH:
                    p = Point((x1 + loc[0] + tw / 2) / self.sft, (y1 + loc[1] + th / 2) / self.sft)
                    self.anchors[key] = p
                    return p
        res = cv2.matchTemplate(gray, t, cv2.TM_CCOEFF_NORMED)
        _, conf, _, loc = cv2.minMaxLoc(res)
        if conf < ANCHOR_TH:
            self.anchors.pop(key, None)
            return None
        p = Point((loc[0] + tw / 2) / self.sft, (loc[1] + th / 2) / self.sft)
        self.anchors[key] = p
        return p

    def ui(self, name):
        """Screen position (reference frame) of a fixed UI element, from the ZBase icon."""
        base = self.anchor("ZBase")
        if base is None:
            return None
        dx, dy = FIXED_UI[name]
        return Point(base.x + dx, base.y + dy)

    # ------------------------------------------------------------------ helpers
    def click(self, x, y, delay=1.0, what="", force=False):
        """Click in the reference frame. Dry runs only log, except for `force` clicks (closing
        popups, zoom): without them a dry run gets stuck behind the first dialog it opens."""
        if self.dry_run and not force:
            log(f"[DRY] would click {what} at ({x:.0f},{y:.0f})")
            return
        self.raw_click(x, y)
        time.sleep(delay)

    def click_button(self, but, delay=1.5, retries=4, force=False):
        """Click a template button; returns True if it was found and clicked."""
        for _ in range(retries):
            c = get_center(but, "Single")
            if c is not None:
                self.click(c.x, c.y, delay, but, force=force)
                return True
            time.sleep(0.5)
        return False

    def wait_for(self, but, timeout=10):
        start = time.time()
        while time.time() - start < timeout:
            if single_find(but):
                return True
            time.sleep(0.5)
        return False

    def find(self, but, th=MATCH_TH):
        return simple_single_find(but, "Single", th)

    def spot_key(self, x, y):
        """Key of a screen position in map coordinates (independent of dragging)."""
        mx, my = x - self.offset[0], y - self.offset[1]
        return round(mx / 40) * 1000 + round(my / 40)

    def prune_visited(self):
        now = time.time()
        self.visited = {k: t for k, t in self.visited.items() if now - t < self.visited_ttl}

    def ocr_digits(self, color, cx, cy, half_w, half_h):
        """OCR digits inside a logical-pixel box; returns the raw text or ''."""
        if self.ocr is False:
            return ""
        try:
            import pytesseract
            x1, x2 = int((cx - half_w) * self.sft), int((cx + half_w) * self.sft)
            y1, y2 = int((cy - half_h) * self.sft), int((cy + half_h) * self.sft)
            patch = color[y1:y2, x1:x2].astype(int)
            bright = (patch[..., 0] + patch[..., 1] + patch[..., 2]) > 480
            mask = np.where(bright, 0, 255).astype(np.uint8)
            mask = cv2.resize(mask, None, fx=4, fy=4, interpolation=cv2.INTER_CUBIC)
            mask = cv2.copyMakeBorder(mask, 20, 20, 20, 20, cv2.BORDER_CONSTANT, value=255)
            txt = pytesseract.image_to_string(mask, config="--psm 7 -c tessedit_char_whitelist=0123456789/%")
            self.ocr = True
            return txt.strip()
        except ImportError as e:
            log(f"OCR unavailable ({e}); hp and quota will be unknown")
            self.ocr = False
            return ""
        except Exception as e:
            log(f"OCR failed for this box ({e})")
            return ""

    # ------------------------------------------------------------------ page state
    def on_map(self):
        """True only when the map is clear: no dialog, no target popup (前往), no fleet panel.
        Template matching ignores dimming, so the map's own markers stay visible under a popup."""
        gs = self.shot()[1]
        f = lambda key: single_find_with_path(single_find_map[key], gs, MATCH_TH)
        return (f("ZExplore") and not f("ZCloseHint") and not f("ZContinueHint") and not f("ZBuyPrompt")
                and not f("ZGo") and not f("ZFleetSpeed") and not f("ZDispatchTitle"))

    def plain_spot(self):
        """A calm point on the map area (no icon, no button) to tap for closing popups."""
        region = self.map_region()
        if region is None:
            return None
        x1, y1, x2, y2 = region
        gray = self.shot()[1]
        h = int(DRAG_LAYOUT["finger_half"] * self.sft)
        best = None
        for fx, fy in [(0.1, 0.9), (0.5, 0.9), (0.1, 0.5), (0.5, 0.5), (0.3, 0.7), (0.7, 0.7), (0.1, 0.3)]:
            x, y = x1 + (x2 - x1) * fx, y1 + (y2 - y1) * fy
            px, py = int(x * self.sft), int(y * self.sft)
            win = gray[max(0, py - h):py + h, max(0, px - h):px + h]
            std = float(win.std()) if win.size else 999.0
            if best is None or std < best[0]:
                best = (std, x, y)
        return Point(best[1], best[2])

    def close_popup(self, tries=6):
        """Get back to the map from any dialog. Clicks for real even in dry runs."""
        for _ in range(tries):
            if self.on_map():
                return True
            if single_find("ZBuyPrompt"):
                self.click_button("ZBuyCancel", force=True)
            elif single_find("ZContinueHint"):
                self.click_button("ZContinueHint", force=True)
            elif single_find("ZCancel"):
                self.click_button("ZCancel", force=True)
            elif single_find("ZCloseHint"):
                c = get_center("ZCloseHint", "Single")
                self.click(c.x, c.y + 30, 1.5, "empty space", force=True)
            elif single_find("ZBackArrow"):
                self.click_button("ZBackArrow", force=True)
            elif single_find("ZFleetSpeed"):
                self.close_fleet_panel(self.last_dispatched or 1)
            elif single_find("ZGo") or single_find("ZDispatchTitle"):
                p = self.plain_spot()
                if p is not None:
                    self.click(p.x, p.y, 1.5, "map (close target popup)", force=True)
            else:
                time.sleep(1)
        return self.on_map()

    def zoom75_selected(self):
        """True when the 75% label sits on the purple (selected) pill. Returns None if the
        zoom bar is not visible."""
        c = self.ui("zoom50")
        if c is None:
            return None
        color = np.array(pyautogui.screenshot())
        cx, cy = c.x + ZOOM_LAYOUT["dx75"], c.y
        x1, x2 = int((cx - ZOOM_LAYOUT["half_w"]) * self.sft), int((cx + ZOOM_LAYOUT["half_w"]) * self.sft)
        y1, y2 = int((cy - ZOOM_LAYOUT["half_h"]) * self.sft), int((cy + ZOOM_LAYOUT["half_h"]) * self.sft)
        mean = color[y1:y2, x1:x2, :3].reshape(-1, 3).mean(axis=0)   # RGB
        return bool(mean[0] > ZOOM_LAYOUT["selected_min_r"] and mean[2] > ZOOM_LAYOUT["selected_min_b"])

    def ensure_zoom(self):
        """Keep the map at 75%. Template matching cannot tell the selected label apart (same
        glyphs, different background), so the pill color decides. Clicks even in dry mode:
        detection needs the right zoom."""
        sel = self.zoom75_selected()
        if sel is None:
            log("Zoom bar not found")
            return False
        if sel:
            return True
        c = self.ui("zoom50")
        log("Zoom is not 75% -> clicking 75%")
        self.raw_click(c.x + ZOOM_LAYOUT["dx75"], c.y)
        time.sleep(2)
        return bool(self.zoom75_selected())

    # ------------------------------------------------------------------ ships
    def scan_ships(self):
        """Return dict index -> {'status','idle','hp','x','y'} read from the top bar."""
        base = self.anchor("ZBase")
        if base is None:
            log("Ship bar anchor (ZBase) not found")
            return {}
        gray = screen_shot()
        color = np.array(pyautogui.screenshot())
        status_pts = []
        for key, name, th in SHIP_STATUS:
            path = single_find_map.get(key)
            if path is None or not os.path.exists(path):
                continue
            for cx, cy, conf in find_all_with_path(path, gray, th):
                status_pts.append((name, cx / self.sft, cy / self.sft, conf))

        ships = {}
        for i in range(SHIP_LAYOUT["slots"]):
            sx = base.x + SHIP_LAYOUT["status_dx0"] + i * SHIP_LAYOUT["spacing"]
            sy = base.y + SHIP_LAYOUT["status_dy"]
            status, best = "unknown", 0
            for name, px, py, conf in status_pts:
                if abs(px - sx) < SHIP_LAYOUT["spacing"] / 2 and abs(py - sy) < 30 and conf > best:
                    status, best = name, conf
            txt = self.ocr_digits(color, sx, sy + SHIP_LAYOUT["hp_bar_dy"],
                                  SHIP_LAYOUT["hp_bar_half_w"], SHIP_LAYOUT["hp_bar_half_h"])
            digits = "".join(ch for ch in txt if ch.isdigit())
            hp = max(0, min(100, int(digits))) if digits else None
            ships[i + 1] = {"status": status, "idle": status == "idle", "hp": hp, "x": sx, "y": sy}
        log("Ships: " + ", ".join(
            f"S{i}:{s['status']}" + ("" if s["hp"] is None else f"({s['hp']}%)") for i, s in ships.items()))
        return ships

    def idle_ships(self, ships):
        return [i for i, s in ships.items() if s["idle"] and (s["hp"] is None or s["hp"] >= REPAIR_BELOW)]

    def read_actions(self):
        """Read the 'n/25' action counter under the base icon. Returns (left, max) or None."""
        base = self.anchor("ZBase")
        if base is None:
            return None
        color = np.array(pyautogui.screenshot())
        txt = self.ocr_digits(color, base.x + SHIP_LAYOUT["actions_dx"], base.y + SHIP_LAYOUT["actions_dy"],
                              SHIP_LAYOUT["actions_half_w"], SHIP_LAYOUT["actions_half_h"])
        if "/" not in txt:
            return None
        left, right = txt.split("/", 1)
        left = "".join(ch for ch in left if ch.isdigit())
        right = "".join(ch for ch in right if ch.isdigit())
        if not left or not right:
            return None
        self.actions = (int(left), int(right))
        log(f"Actions: {self.actions[0]}/{self.actions[1]}")
        return self.actions

    # ------------------------------------------------------------------ map area / dragging
    def map_region(self):
        """(x_min, y_min, x_max, y_max) in logical px of the draggable map area, or None."""
        top = self.anchor("ZBase")
        if top is None:
            return None
        bottom = self.ui("team")
        return (top.x + MAP_LAYOUT["x_min_dx"], top.y + MAP_LAYOUT["y_min_dy"],
                top.x + MAP_LAYOUT["x_max_dx"], bottom.y + MAP_LAYOUT["y_max_team_dy"])

    def measure_region(self):
        """The map area without the fixed right-hand UI column: static icons inside the
        overlap strip would otherwise match at zero shift and hide a real move."""
        region = self.map_region()
        base = self.anchor("ZBase")
        if region is None or base is None:
            return region
        return (region[0], region[1], min(region[2], base.x + MEASURE_X_MAX_DX), region[3])

    def grab_region(self, region):
        """Grayscale physical-pixel crop of the map area."""
        gray = self.shot()[1]
        x1, y1, x2, y2 = (int(v * self.sft) for v in region)
        return gray[y1:y2, x1:x2]

    def measure_shift(self, before, after, dx, dy):
        """How far the content really moved between two crops of the map area, in logical px.
        The part of `before` that should still be visible after moving by (dx, dy) is matched
        in `after`; among equally good peaks (the grid repeats) the one nearest the expected
        movement wins. Returns (sx, sy) or None when it cannot be measured."""
        h, w = before.shape
        px, py = int(round(dx * self.sft)), int(round(dy * self.sft))
        inset = int(DRAG_LAYOUT["strip_inset"] * self.sft)
        # visible part of `before`: x in [max(0,-px), w + min(0,-px)], same for y
        x1, x2 = max(0, -px) + inset, w + min(0, -px) - inset
        y1, y2 = max(0, -py) + inset, h + min(0, -py) - inset
        if x2 - x1 < 60 or y2 - y1 < 60:
            return None
        strip = before[y1:y2, x1:x2]
        if float(strip.std()) < DRAG_LAYOUT["patch_min_std"]:
            # plain grid in the overlap strip: decide between "did not move" and "moved as
            # asked" by comparing the whole area aligned both ways. An area that is itself
            # plain grid looks the same after any move, so "did not move" needs structure.
            diff0 = float(np.abs(before.astype(int) - after.astype(int)).mean())
            if diff0 < DRAG_LAYOUT["static_diff"]:
                return (0.0, 0.0) if float(before.std()) >= DRAG_LAYOUT["area_min_std"] else None
            moved = after[y1 + py:y2 + py, x1 + px:x2 + px] if 0 <= y1 + py and 0 <= x1 + px else None
            if moved is not None and moved.shape == strip.shape:
                diff1 = float(np.abs(strip.astype(int) - moved.astype(int)).mean())
                if diff1 < diff0 * 0.5:
                    return float(dx), float(dy)
            return None
        res = cv2.matchTemplate(after, strip, cv2.TM_CCOEFF_NORMED)
        _, peak, _, _ = cv2.minMaxLoc(res)
        if peak < DRAG_LAYOUT["patch_th"]:
            diff = float(np.abs(before.astype(int) - after.astype(int)).mean())
            if diff < DRAG_LAYOUT["static_diff"] and float(before.std()) >= DRAG_LAYOUT["area_min_std"]:
                return 0.0, 0.0
            return None
        # expected top-left of the strip in `after`
        ex, ey = x1 + px, y1 + py
        ys, xs = np.where(res >= max(DRAG_LAYOUT["patch_th"], peak - 0.05))
        best = min(zip(xs, ys), key=lambda p: abs(p[0] - ex) + abs(p[1] - ey))
        return (best[0] - x1) / self.sft, (best[1] - y1) / self.sft

    def boundary_sides(self, region=None):
        """Which purple frame lines are visible inside the map area: {'left': x, 'right': x,
        'top': y, 'bottom': y} in logical px."""
        region = region or self.map_region()
        if region is None:
            return {}
        color = self.shot()[0]
        x1, y1, x2, y2 = (int(v * self.sft) for v in region)
        rgb = color[y1:y2, x1:x2].astype(int)
        r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
        mask = ((r > BOUNDARY_LAYOUT["min_r"]) & (b > BOUNDARY_LAYOUT["min_b"]) & (g < BOUNDARY_LAYOUT["max_g"])
                & (b - g > BOUNDARY_LAYOUT["min_bg_diff"]))
        h, w = mask.shape
        cols = mask.sum(axis=0) / h
        rows = mask.sum(axis=1) / w
        sides = {}
        cx, cy = w / 2, h / 2
        for x in np.where(cols >= BOUNDARY_LAYOUT["min_ratio"])[0]:
            side = "left" if x < cx else "right"
            sides.setdefault(side, (x1 + x) / self.sft)
        for y in np.where(rows >= BOUNDARY_LAYOUT["min_ratio"])[0]:
            side = "top" if y < cy else "bottom"
            sides.setdefault(side, (y1 + y) / self.sft)
        return sides

    def pick_gesture(self, region, dx, dy):
        """Start/end of the drag gesture. Several candidate lines are tried and the first whose
        start and end land on plain map (no icon, no button) is used: a finger on an icon or on
        a UI button (通缉榜/任务榜 on the right) opens something instead of dragging."""
        x1, y1, x2, y2 = region
        m = DRAG_LAYOUT["margin"]
        cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
        clamp = lambda v, lo, hi: max(lo, min(hi, v))
        base = self.anchor("ZBase")
        # the finger must stay inside the map frame: a gesture that ends beyond a visible frame
        # line (outside the zone) is not accepted by the game, so the usable span shrinks there
        sides = self.boundary_sides(region)
        fx1 = max(x1 + m, sides["left"] + 15) if "left" in sides else x1 + m
        fx2 = min(x2 - m, sides["right"] - 15) if "right" in sides else x2 - m
        fy1 = max(y1 + m, sides["top"] + 15) if "top" in sides else y1 + m
        fy2 = min(y2 - m, sides["bottom"] - 15) if "bottom" in sides else y2 - m
        x1, x2, y1, y2 = fx1 - m, fx2 + m, fy1 - m, fy2 + m      # so that x1 + m == fx1 below
        cands = []
        if dy == 0 and base is not None:
            bx1 = max(base.x + DRAG_LAYOUT["band_x_min_dx"], fx1)
            bx2 = min(base.x + DRAG_LAYOUT["band_x_max_dx"], fx2)
            bcx = (bx1 + bx2) / 2
            for ddy in DRAG_LAYOUT["band_y_dys"]:
                by = base.y + ddy
                if y1 + m <= by <= y2 - m:
                    cands.append((clamp(bcx - dx / 2, bx1, bx2), by, clamp(bcx + dx / 2, bx1, bx2), by))
        elif dx == 0:
            for ddx in DRAG_LAYOUT["vert_x_dxs"]:
                vx = clamp(cx + ddx, x1 + m, x2 - m)
                cands.append((vx, clamp(cy - dy / 2, y1 + m, y2 - m), vx, clamp(cy + dy / 2, y1 + m, y2 - m)))
        else:
            cands.append((clamp(cx - dx / 2, x1 + m, x2 - m), clamp(cy - dy / 2, y1 + m, y2 - m),
                          clamp(cx + dx / 2, x1 + m, x2 - m), clamp(cy + dy / 2, y1 + m, y2 - m)))
        gray = self.shot()[1]
        h = int(DRAG_LAYOUT["finger_half"] * self.sft)

        def busy(x, y):
            px, py = int(x * self.sft), int(y * self.sft)
            win = gray[max(0, py - h):py + h, max(0, px - h):px + h]
            return float(win.std()) if win.size else 999.0

        scored = sorted(cands, key=lambda c: max(busy(c[0], c[1]), busy(c[2], c[3])))
        best = scored[0]
        if max(busy(best[0], best[1]), busy(best[2], best[3])) > DRAG_LAYOUT["plain_std"]:
            log("No plain spot for the drag gesture, using the calmest candidate")
        return best

    def drag_map(self, dx, dy):
        """Move the map content by (dx, dy) logical px. Returns 'moved', 'edge' or 'fail'."""
        region = self.map_region()
        if region is None:
            log("Map area anchors not found, cannot drag")
            return "fail"
        x1, y1, x2, y2 = region
        sides = self.boundary_sides(region)
        for cond, side in ((dx < 0, "right"), (dx > 0, "left"), (dy < 0, "bottom"), (dy > 0, "top")):
            if cond and side in sides:
                log(f"Drag ({dx:.0f},{dy:.0f}): {side} frame line visible at {sides[side]:.0f} -> edge")
                return "edge"
        sx, sy, ex, ey = self.pick_gesture(region, dx, dy)
        dx, dy = ex - sx, ey - sy

        asked = (dx ** 2 + dy ** 2) ** 0.5
        want_side = "right" if dx < 0 else "left" if dx > 0 else "bottom" if dy < 0 else "top"
        for attempt in range(DRAG_LAYOUT["edge_retries"] + 1):
            if attempt:
                # a drag that did not move the map without the frame line in view: a popup may
                # have opened, or the finger landed on something. Close popups, pick again.
                sx, sy, ex, ey = self.pick_gesture(region, dx, dy)
                dx, dy = ex - sx, ey - sy
            if not self.on_map():
                self.close_popup()
            mregion = self.measure_region()
            before = self.grab_region(mregion)
            rsx, rsy = self.to_real(sx, sy)
            rex, rey = self.to_real(ex, ey)
            drag(rsx, rsy, rex, rey)
            self.invalidate_shot()
            time.sleep(DRAG_LAYOUT["settle"])
            self.wait_still()
            after = self.grab_region(mregion)
            shift = self.measure_shift(before, after, dx, dy)
            if shift is None:
                time.sleep(1.0)          # maybe still animating (rubber band at the edge); look again
                self.invalidate_shot()
                after = self.grab_region(mregion)
                shift = self.measure_shift(before, after, dx, dy)
            self.last_drag_unknown = shift is None
            if shift is None:
                log(f"Drag ({dx:.0f},{dy:.0f}): movement unknown (plain map), assuming it worked")
                self.offset[0] += dx
                self.offset[1] += dy
                return "moved"
            got = (shift[0] ** 2 + shift[1] ** 2) ** 0.5
            if got < DRAG_LAYOUT["edge_frac"] * asked:
                self.debug_drag(before, after, dx, dy, shift)
            self.offset[0] += shift[0]
            self.offset[1] += shift[1]
            if got >= DRAG_LAYOUT["edge_frac"] * asked:
                log(f"Drag ({dx:.0f},{dy:.0f}): moved ({shift[0]:.0f},{shift[1]:.0f})")
                return "moved"
            if not self.on_map():
                log(f"Drag ({dx:.0f},{dy:.0f}): a dialog opened instead of dragging, closing it and retrying")
                self.close_popup()
                continue
            sides = self.boundary_sides(region)
            if want_side in sides:
                log(f"Drag ({dx:.0f},{dy:.0f}): moved ({shift[0]:.0f},{shift[1]:.0f}), {want_side} frame line at {sides[want_side]:.0f} -> edge")
                return "edge"
            if want_side in DRAG_LAYOUT["hidden_sides"]:
                log(f"Drag ({dx:.0f},{dy:.0f}): moved ({shift[0]:.0f},{shift[1]:.0f}), {want_side} frame line is hidden by the UI -> edge")
                return "edge"
            log(f"Drag ({dx:.0f},{dy:.0f}): moved ({shift[0]:.0f},{shift[1]:.0f}) but no {want_side} frame line in view, retrying")
        log(f"Drag ({dx:.0f},{dy:.0f}): no movement after retries -> edge assumed")
        return "edge"

    def go_to_corner(self, dx, dy):
        """Drag to a corner and anchor the map frame there: map (0,0) = the frame lines when
        they are visible, otherwise the view itself. Repeatable, so spots survive zone switches."""
        self.drag_to_edge(dx, 0)
        self.drag_to_edge(0, dy)
        self.offset = [0.0, 0.0]
        sides = self.boundary_sides()
        if "left" in sides:
            self.offset[0] = sides["left"]
        if "top" in sides:
            self.offset[1] = sides["top"]
        log(f"Corner reached, frame lines {sides}, offset {self.offset}")

    def drag_steps(self):
        """Step sizes so that consecutive stops overlap by one icon width only."""
        region = self.map_region()
        if region is None:
            return None
        x1, y1, x2, y2 = region
        return (x2 - x1 - DRAG_LAYOUT["overlap_x"], y2 - y1 - DRAG_LAYOUT["overlap_y"])

    def drag_to_edge(self, dx, dy):
        unknown = 0
        for _ in range(DRAG_LAYOUT["max_drags"]):
            r = self.drag_map(dx, dy)
            if r != "moved":
                return r == "edge"
            unknown = unknown + 1 if self.last_drag_unknown else 0
            if unknown >= DRAG_LAYOUT["max_unknown_edge"]:
                log("Several drags in a row could not be measured on plain map -> treating as the edge")
                return True
            if not self.on_map():
                self.close_popup()
        return False

    # ------------------------------------------------------------------ resources
    def route_endpoints(self, color, region, line="white"):
        """End points (logical px) of dashed route lines inside the map area. "white" lines are
        our own fleets, "blue" (light cyan) lines are other lords' fleets."""
        x1, y1, x2, y2 = (int(v * self.sft) for v in region)
        rgb = color[y1:y2, x1:x2].astype(int)
        mn, mx = rgb.min(axis=2), rgb.max(axis=2)
        if line == "blue":
            # rival dashes are light blue (B > G > R); the teal box icons (G > B) must not count,
            # rows of them would otherwise form fake lines
            # (dash pixels ~R104 G187 B213; the purple-blue tile frames ~R110 G146 B195 are out)
            r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
            mask = ((b > r + 50) & (b > g + 5) & (b > 185) & (g > 160) & (r < 135)).astype(np.uint8) * 255
        else:
            mask = ((mn > ROUTE_LAYOUT["white_min"]) & (mx - mn < ROUTE_LAYOUT["white_spread"])).astype(np.uint8) * 255
        lines = cv2.HoughLinesP(mask, 1, np.pi / 360, threshold=40,
                                minLineLength=ROUTE_LAYOUT["min_seg"], maxLineGap=ROUTE_LAYOUT["max_gap"])
        if lines is None:
            return []
        merged = []
        for ax, ay, bx, by in (l[0] for l in lines):
            ang = math.atan2(by - ay, bx - ax) % math.pi
            cx, cy = (ax + bx) / 2, (ay + by) / 2
            for m in merged:
                da = abs(ang - m["ang"])
                da = min(da, math.pi - da)
                px, py = m["pts"][0]
                d = abs(math.cos(m["ang"]) * (py - cy) - math.sin(m["ang"]) * (px - cx))
                if da < 0.06 and d < 10:
                    m["pts"] += [(ax, ay), (bx, by)]
                    break
            else:
                merged.append({"ang": ang, "pts": [(ax, ay), (bx, by)]})
        ends = []
        h, w = mask.shape
        self._route_masks[line] = (mask, (x1, y1))
        for m in merged:
            ux, uy = math.cos(m["ang"]), math.sin(m["ang"])
            a = min(m["pts"], key=lambda p: p[0] * ux + p[1] * uy)
            b = max(m["pts"], key=lambda p: p[0] * ux + p[1] * uy)
            n = int(math.hypot(b[0] - a[0], b[1] - a[1]))
            if n < ROUTE_LAYOUT["min_len"]:
                continue
            on, trans, prev = 0, 0, 0
            for i in range(n):
                x = min(w - 1, int(a[0] + (b[0] - a[0]) * i / n))
                y = min(h - 1, int(a[1] + (b[1] - a[1]) * i / n))
                v = 1 if mask[y, x] else 0
                on += v
                trans += v != prev
                prev = v
            if trans < ROUTE_LAYOUT["min_transitions"] or on / n > ROUTE_LAYOUT["max_on"]:
                continue
            if line == "blue" and on / n < ROUTE_LAYOUT["blue_min_on"]:
                continue        # rows of icon frames leave sparse pixels along a Hough line
            # each end with the outward direction (from the other end towards it)
            for p, q in ((a, b), (b, a)):
                L = math.hypot(p[0] - q[0], p[1] - q[1]) or 1
                ends.append((Point((x1 + p[0]) / self.sft, (y1 + p[1]) / self.sft),
                             ((p[0] - q[0]) / L, (p[1] - q[1]) / L)))
        return ends

    def line_continues(self, x, y, ux, uy, line="white"):
        """True if the dashes keep going past (x, y) in direction (ux, uy): the line only
        crosses this icon instead of ending at it."""
        entry = self._route_masks.get(line)
        if entry is None:
            return False
        mask, (ox, oy) = entry
        h, w = mask.shape
        on = n = 0
        for d in range(ROUTE_LAYOUT["beyond_from"], ROUTE_LAYOUT["beyond_to"], 2):
            px = int((x + ux * d) * self.sft) - ox
            py = int((y + uy * d) * self.sft) - oy
            if 0 <= px < w and 0 <= py < h:
                n += 1
                on += 1 if mask[py, px] else 0
        return n > 10 and on / n > ROUTE_LAYOUT["beyond_min_on"]

    def targeted_by_route(self, x, y, ends, line="white"):
        for e, (ux, uy) in ends:
            if abs(e.x - x) < ROUTE_LAYOUT["end_radius"] and abs(e.y - y) < ROUTE_LAYOUT["end_radius"]:
                if not self.line_continues(x, y, ux, uy, line):
                    return True
        return False

    def icon_rgb(self, color, x, y, half=ICON_COLOR_HALF):
        """Mean RGB of the bright pixels around a logical point."""
        x1, x2 = int((x - half) * self.sft), int((x + half) * self.sft)
        y1, y2 = int((y - half) * self.sft), int((y + half) * self.sft)
        p = color[max(0, y1):y2, max(0, x1):x2, :3].reshape(-1, 3).astype(int)
        bright = p[p.sum(axis=1) > 400]
        return tuple(bright.mean(axis=0)) if len(bright) else (0, 0, 0)

    def color_ok(self, kind, color, x, y):
        rule = KIND_COLOR_RULES.get(kind)
        if rule is None:
            return True
        r, g, b = self.icon_rgb(color, x, y)
        return bool(rule(r, g, b))

    def full_template(self, kind):
        if kind not in self.full_templates:
            path = single_find_map.get(kind)
            self.full_templates[kind] = cv2.imread(path, 0) if path and os.path.exists(path) else None
        return self.full_templates[kind]

    def partial_templates(self, kind):
        if kind not in self.partials:
            path = single_find_map.get(kind)
            t = cv2.imread(path, 0) if path and os.path.exists(path) else None
            if t is None:
                self.partials[kind] = []
            else:
                h, w = t.shape
                self.partials[kind] = [("top", t[:h // 2]), ("bottom", t[h // 2:]),
                                       ("left", t[:, :w // 2]), ("right", t[:, w // 2:])]
        return self.partials[kind]

    def scan_resources(self, kinds=None, light=False):
        """Find every scoreable resource visible on the map, best first. `kinds` restricts the
        templates; `light` skips the route-line checks (outer-zone survey)."""
        color, gray = self.shot()
        self._scan_frame = color
        region = self.map_region()
        x_min, y_min, x_max, y_max = region if region else (0, 0, 10 ** 6, 10 ** 6)
        base = self.anchor("ZBase", gray)
        ends = self.route_endpoints(color, region) if region and not light else []
        if ends:
            log("Route line ends: " + ", ".join(f"({e.x:.0f},{e.y:.0f})" for e, _ in ends))
        blue_ends = self.route_endpoints(color, region, "blue") if region and not light else []
        if blue_ends:
            log("Rival line ends: " + ", ".join(f"({e.x:.0f},{e.y:.0f})" for e, _ in blue_ends))
        contested = 0

        # Match inside the map area only (plus a margin for icons on the border): ~7x faster.
        pad = 60
        gx1, gy1 = int(max(0, (x_min - pad) * self.sft)), int(max(0, (y_min - pad) * self.sft))
        gx2, gy2 = int(min(gray.shape[1], (x_max + pad) * self.sft)), int(min(gray.shape[0], (y_max + pad) * self.sft))
        sub = gray[gy1:gy2, gx1:gx2]
        found = []
        landmarks = []
        targeted = 0
        wrong_color = 0
        skipped_visited = 0
        skipped_ui = 0
        for kind, score in RESOURCE_SCORES.items():
            if kinds is not None and kind not in kinds:
                continue
            path = single_find_map.get(kind)
            if path is None or not os.path.exists(path):
                continue
            full_t = self.full_template(kind)
            hits = [((gx1 + cx) / self.sft, (gy1 + cy) / self.sft, "full") for cx, cy, _ in match_all(sub, full_t, MATCH_TH)]
            if kind in PARTIAL_KINDS:
                for name, tmpl in self.partial_templates(kind):
                    for cx, cy, _ in match_all(sub, tmpl, PARTIAL_TH):
                        x, y = (gx1 + cx) / self.sft, (gy1 + cy) / self.sft
                        if any(abs(x - hx) < 35 and abs(y - hy) < 35 for hx, hy, _ in hits):
                            continue
                        hits.append((x, y, name))
            for x, y, how in hits:
                if not (y_min < y < y_max and x_min < x < x_max):
                    continue
                landmarks.append((kind + ("" if how == "full" else f"[{how}]"), x, y))
                if base is not None and any(base.x + ex0 < x < base.x + ex1 and base.y + ey0 < y < base.y + ey1
                                            for ex0, ex1, ey0, ey1 in MAP_EXCLUDE):
                    skipped_ui += 1
                    continue
                if not self.color_ok(kind, color, x, y):     # cheap, kept in light mode too
                    wrong_color += 1
                    if DEBUG_SHOT_DIR and kind == "ZBox":
                        rgb = self.icon_rgb(color, x, y)
                        if rgb[2] > rgb[1]:                  # bluish: a purple box the rule rejected?
                            log(f"  colour reject {kind} at ({x:.0f},{y:.0f}) RGB={tuple(round(v) for v in rgb)} shape={color.shape} dtype={color.dtype}")
                    continue
                if self.spot_key(x, y) in self.visited:
                    skipped_visited += 1
                    continue
                if self.targeted_by_route(x, y, ends):
                    targeted += 1
                    continue
                if blue_ends and self.targeted_by_route(x, y, blue_ends, "blue"):
                    if kind in FACTORY_KINDS or self.zone == "central":
                        # a rival is on the way: still go, and boost if it would arrive first
                        self.contested[self.spot_key(x, y)] = time.time()
                    else:
                        contested += 1      # outer zone, ordinary resource: not worth the race
                        continue
                if any(abs(f.x - x) < 35 and abs(f.y - y) < 35 for f in found):
                    continue   # the same icon matched by two kinds (e.g. two factory templates)
                found.append(Candidate(kind + ("" if how == "full" else f"[{how}]"), score, x, y))
        found.sort(key=lambda c: (-c.score, c.y, c.x))
        self.last_landmarks = landmarks
        log(f"Resources: {len(found)}" + (f" (+{targeted} already targeted by our ships)" if targeted else "")
            + (f" (+{wrong_color} same shape, wrong colour)" if wrong_color else "")
            + (f" (+{contested} with a rival on the way)" if contested else "")
            + (f" (+{skipped_visited} visited recently)" if skipped_visited else "")
            + (f" (+{skipped_ui} under the UI column)" if skipped_ui else "")
            + (f" [kinds={len(kinds)}]" if kinds is not None else "")
            + " -> " + ", ".join(f"{c.kind}@({c.x:.0f},{c.y:.0f})" for c in found[:8]))
        return found

    # ------------------------------------------------------------------ dispatch
    def pick_idle_fleet(self):
        """On the '派遣舰队' list, click the first idle fleet card (the one showing 能量)."""
        cards = get_all("ZEnergy", "Single")
        if not cards:
            log("No idle fleet in the list")
            return False
        cards.sort(key=lambda p: p.y)
        self.click(cards[0].x, cards[0].y, 2, "idle fleet")
        return True

    def wait_after_pick(self, timeout=6):
        """After clicking a fleet card: 'estimate' (battle dialog), 'map' (sent), 'factory'
        (back on the factory page) or 'unknown'. Polls instead of trusting a fixed sleep,
        otherwise a late estimate dialog would be cancelled by close_popup()."""
        start = time.time()
        while time.time() - start < timeout:
            gs = screen_shot()
            f = lambda key: single_find_with_path(single_find_map[key], gs, MATCH_TH)
            if f("ZEstimateLabel"):
                return "estimate"
            if f("ZBuyPrompt") or f("ZContinueHint"):
                return "unknown"
            if f("ZExplore") and not f("ZDispatchTitle") and not f("ZCloseHint"):
                return "map"
            if f("ZFactoryPage"):
                return "factory"
            time.sleep(0.5)
        return "unknown"

    def read_estimate(self):
        for est in WIN_ESTIMATES:
            if self.find(est):
                return est, True
        for est in LOSS_ESTIMATES:
            if self.find(est):
                return est, False
        return "unknown", False

    def handle_buy_prompt(self, allow_buy):
        """'是否花费150幻想币购买星级指令x5?' -> 确定, then '点击任意处继续'. Returns True if bought."""
        if not allow_buy or self.packs_bought >= MAX_PACKS_PER_RUN:
            log("Action purchase prompt -> cancel (not allowed for this target)")
            self.click_button("ZBuyCancel", 1.5)
            return False
        log(f"Buying {ACTION_PACK_SIZE} actions for {ACTION_PACK_COINS} coins")
        self.click_button("ZBuyOk", 2)
        self.packs_bought += 1
        if self.wait_for("ZContinueHint", 6):
            self.click_button("ZContinueHint", 1.5)
        return True

    def dispatch(self, cand, allow_buy=False):
        """Drive the pages after clicking a resource until the fleet is sent or we give up."""
        log(f"Dispatch -> {cand.kind} at ({cand.x:.0f},{cand.y:.0f}) allow_buy={allow_buy}")
        self.visited[self.spot_key(cand.x, cand.y)] = time.time()
        contested = self.contested.pop(self.spot_key(cand.x, cand.y), None) is not None
        idle_before = set(self.idle_ships(self.scan_ships()))
        region = self.measure_region()
        before = self.grab_region(region) if region else None
        ok = self._dispatch(cand, allow_buy)
        self.last_shift = (0.0, 0.0)
        if before is not None and self.on_map():
            # the game sometimes recenters the view after a dispatch: keep offsets and the
            # candidate's position consistent for everything that follows
            self.invalidate_shot()
            shift = self.measure_shift(before, self.grab_region(region), 0, 0)
            if shift is not None and (abs(shift[0]) > 5 or abs(shift[1]) > 5):
                self.offset[0] += shift[0]
                self.offset[1] += shift[1]
                self.last_shift = shift
                log(f"Map view moved after dispatch by ({shift[0]:.0f},{shift[1]:.0f}), offsets corrected")
        if ok:
            time.sleep(2)
            idle_after = set(self.idle_ships(self.scan_ships()))
            gone = sorted(idle_before - idle_after)
            self.last_dispatched = gone[0] if gone else None
            is_factory = cand.kind.split("[")[0] in FACTORY_KINDS
            if self.last_dispatched and (is_factory or contested):
                now = Candidate(cand.kind, cand.score, cand.x + self.last_shift[0], cand.y + self.last_shift[1])
                if FACTORY_BOOST == "always" and is_factory:
                    self.boost_ship(self.last_dispatched)
                elif FACTORY_BOOST != "never":
                    self.check_rivals_and_boost(now)
        return ok

    # ------------------------------------------------------------------ rivals
    def ocr_times(self, color, x1, y1, x2, y2):
        """All hh:mm:ss values inside a logical-px box, as seconds."""
        try:
            import pytesseract
            import re
            px1, py1 = int(max(0, x1 * self.sft)), int(max(0, y1 * self.sft))
            px2, py2 = int(x2 * self.sft), int(y2 * self.sft)
            g = cv2.cvtColor(color[py1:py2, px1:px2], cv2.COLOR_RGB2GRAY)
            g = cv2.resize(g, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
            g = cv2.threshold(g, 150, 255, cv2.THRESH_BINARY_INV)[1]
            g = cv2.copyMakeBorder(g, 10, 10, 10, 10, cv2.BORDER_CONSTANT, value=255)
            txt = pytesseract.image_to_string(g, config="--psm 6 -c tessedit_char_whitelist=0123456789:")
            out = []
            for h, m, s in re.findall(r"(\d{1,2}):(\d{2}):(\d{2})", txt):
                out.append(int(h) * 3600 + int(m) * 60 + int(s))
            return out
        except Exception as e:
            log(f"Time OCR failed: {e}")
            return []

    def read_rival_etas(self):
        """Arrival times (seconds) of the rival fleets listed on the target popup."""
        p = get_center("ZRivalPanel", "Single")
        if p is None:
            return []
        color = np.array(pyautogui.screenshot())
        return self.ocr_times(color, p.x + RIVAL_LAYOUT["etas_dx0"], p.y + RIVAL_LAYOUT["etas_dy0"],
                              p.x + RIVAL_LAYOUT["etas_dx1"], p.y + RIVAL_LAYOUT["etas_dy1"])

    def read_ship_countdown(self, index):
        """Remaining travel time (seconds) shown under ship `index` in the top bar, or None."""
        base = self.anchor("ZBase")
        if base is None:
            return None
        sx = base.x + SHIP_LAYOUT["status_dx0"] + (index - 1) * SHIP_LAYOUT["spacing"]
        sy = base.y + SHIP_LAYOUT["status_dy"] + RIVAL_LAYOUT["countdown_dy"]
        color = np.array(pyautogui.screenshot())
        times = self.ocr_times(color, sx - RIVAL_LAYOUT["countdown_half_w"], sy - RIVAL_LAYOUT["countdown_half_h"],
                               sx + RIVAL_LAYOUT["countdown_half_w"], sy + RIVAL_LAYOUT["countdown_half_h"])
        return times[0] if times else None

    def check_rivals_and_boost(self, cand):
        """After sending a fleet: open the target again, read the rivals' arrival times and, if
        the fastest rival beats our countdown, boost by the user's rule (BOOST_PLAN): rival under
        1 min -> one quantum; 1-3 min -> super boosters, up to 3; over 3 min -> large boosters,
        up to 5. After every booster our countdown is re-read and boosting stops as soon as we
        arrive first."""
        time.sleep(3)
        self.click(cand.x, cand.y, 2, "target again (rival check)")
        if not self.wait_for("ZGo", 6):
            log("Target popup did not open for the rival check")
            self.close_popup()
            return False
        etas = self.read_rival_etas() if single_find("ZRivalPanel") else []
        ours = self.read_ship_countdown(self.last_dispatched)
        log(f"Rival arrival times {etas}s, ours {ours}s")
        self.close_popup()
        if not etas or (ours is not None and ours < min(etas)):
            return False
        rival = min(etas)
        booster, max_n = next((b, n) for limit, b, n in BOOST_PLAN if rival < limit)
        log(f"A rival arrives in {rival}s -> up to {max_n} x {booster}")
        used = 0
        for _ in range(max_n):
            if not self.boost_ship(self.last_dispatched, booster):
                break
            used += 1
            ours = self.read_ship_countdown(self.last_dispatched)
            log(f"After {used} booster(s): ours {ours}s vs rival {rival}s")
            if ours is not None and ours < rival:
                break
        return used > 0

    def _dispatch(self, cand, allow_buy):
        self.click(cand.x, cand.y, 1.5, cand.kind)
        if self.dry_run:
            return True

        picked = False
        ok = False
        for step in range(DISPATCH_STEPS):
            if single_find("ZBuyPrompt"):
                if not self.handle_buy_prompt(allow_buy):
                    break
                continue
            if single_find("ZContinueHint"):
                self.click_button("ZContinueHint", 1.5)
                continue
            if single_find("ZEstimateLabel"):
                est, win = self.read_estimate()
                if win:
                    log(f"Estimate {est} -> attack")
                    self.click_button("ZAttack")
                    ok = True
                else:
                    log(f"Estimate {est} -> cancel")
                    self.click_button("ZCancel")
                break
            if single_find("ZDispatchTitle") or single_find("ZFleetDetail"):
                if picked:
                    time.sleep(1)
                    continue
                picked = self.pick_idle_fleet()
                if not picked:
                    break
                # boxes finish here (back on the map); battles continue to the estimate dialog
                state = self.wait_after_pick()
                if state == "map":
                    ok = True
                    break
                continue
            if single_find("ZFactoryPage"):
                ok = self.handle_factory()
                break
            if single_find("ZGo"):
                self.click_button("ZGo", 2)
                continue
            if single_find("ZTargetPage") or single_find("ZAttackPage"):
                # friendly targets also offer 同盟交流; the user wants 袭击 for every target
                self.click_button("ZAttackPage", 2)
                continue
            if single_find("ZAttack"):
                self.click_button("ZAttack", 2)
                continue
            if self.on_map():
                ok = picked
                break
            time.sleep(1)
        self.close_popup()
        log(f"Dispatch {'ok' if ok else 'failed'}")
        return ok

    def read_attack_quota(self):
        marker = self.anchor("ZFactoryPage")
        if marker is None:
            return None
        color = np.array(pyautogui.screenshot())
        txt = self.ocr_digits(color, marker.x + FACTORY_LAYOUT["quota_dx"], marker.y + FACTORY_LAYOUT["quota_dy"],
                              FACTORY_LAYOUT["quota_half_w"], FACTORY_LAYOUT["quota_half_h"])
        if "/" in txt:
            left = "".join(ch for ch in txt.split("/")[0] if ch.isdigit())
            if left:
                return int(left)
        return None

    def handle_factory(self):
        """Factory page: skip if our fleet is already inside, take a free slot, else attack
        the occupant whose estimate is a win. Returns True when a fleet was sent."""
        if single_find("ZOccupied") or single_find("ZOurGoing"):
            log("Our fleet already occupies / is heading to this factory")
            return False
        marker = self.anchor("ZFactoryPage")
        if marker is None:
            return False
        self.attack_quota = self.read_attack_quota()
        log(f"Factory: attack quota left = {self.attack_quota}")

        slots = []
        for i in range(FACTORY_LAYOUT["slots"]):
            slots.append(Point(marker.x + FACTORY_LAYOUT["dx0"] + i * FACTORY_LAYOUT["spacing"],
                               marker.y + FACTORY_LAYOUT["dy"]))
        # A free slot shows a "+" with "可派舰队" under it; the "+" sits above the label.
        # The description text above also contains "可派遣舰队" (0.85), so only the slot row counts.
        row_y = marker.y + FACTORY_LAYOUT["dy"]
        free = [Point(p.x, p.y + FACTORY_LAYOUT["free_plus_dy"]) for p in get_all("ZSlotFree", "Single")
                if abs(p.y - row_y) < 80]
        occupied = get_all("ZSlotPower", "Single")
        taken = [s for s in slots
                 if any(abs(o.x - s.x) < FACTORY_LAYOUT["spacing"] / 2 for o in occupied)
                 and not any(abs(f.x - s.x) < FACTORY_LAYOUT["spacing"] / 2 for f in free)]
        log(f"Factory slots: {len(free)} free, {len(taken)} occupied")

        # Any free slot can be clicked; otherwise attack occupants. Quota is ignored.
        order = free + taken
        for s in order:
            self.click(s.x, s.y, 2, "factory slot")
            for step in range(DISPATCH_STEPS):
                if single_find("ZBuyPrompt"):
                    if not self.handle_buy_prompt(True):
                        return False
                    continue
                if single_find("ZContinueHint"):
                    self.click_button("ZContinueHint", 1.5)
                    continue
                if single_find("ZEstimateLabel"):
                    est, win = self.read_estimate()
                    if win:
                        log(f"Estimate {est} -> attack occupant")
                        self.click_button("ZAttack")
                        return True
                    log(f"Estimate {est} -> cancel, try next slot")
                    self.click_button("ZCancel")
                    break
                if single_find("ZDispatchTitle") or single_find("ZFleetDetail"):
                    if not self.pick_idle_fleet():
                        return False
                    state = self.wait_after_pick()
                    if state == "map" or (s in free and state == "factory"):
                        return True
                    continue
                if single_find("ZTargetPage") or single_find("ZAttackPage"):
                    self.click_button("ZAttackPage", 2)
                    continue
                if single_find("ZAttack"):
                    self.click_button("ZAttack", 2)
                    continue
                if single_find("ZGo"):
                    self.click_button("ZGo", 2)
                    continue
                if single_find("ZFactoryPage"):
                    time.sleep(1)
                    if step >= 3:
                        break   # the click did nothing
                    continue
                time.sleep(1)
            if not single_find("ZFactoryPage"):
                self.close_popup()
                return False
        log("No usable factory slot")
        return False

    # ------------------------------------------------------------------ boost
    def open_fleet_panel(self, index):
        """Click a ship's rocket icon in the top bar until the fleet panel ("当前速度") shows."""
        base = self.anchor("ZBase")
        if base is None:
            return False
        x = base.x + SHIP_LAYOUT["status_dx0"] + (index - 1) * SHIP_LAYOUT["spacing"]
        y = base.y + SHIP_LAYOUT["status_dy"] + BOOST_LAYOUT["icon_dy"]
        for _ in range(BOOST_LAYOUT["max_clicks"]):
            self.raw_click(x, y)
            time.sleep(1.5)
            if single_find("ZFleetSpeed"):
                return True
        return single_find("ZFleetSpeed")

    def close_fleet_panel(self, index):
        """The panel is dismissed by clicking the same ship again; fall back to close_popup."""
        if not single_find("ZFleetSpeed"):
            return True
        base = self.anchor("ZBase")
        if base is not None:
            self.raw_click(base.x + SHIP_LAYOUT["status_dx0"] + (index - 1) * SHIP_LAYOUT["spacing"],
                           base.y + SHIP_LAYOUT["status_dy"] + BOOST_LAYOUT["icon_dy"])
            time.sleep(1.5)
        if single_find("ZFleetSpeed"):
            region = self.map_region()
            if region:
                self.click(region[0] + 15, region[1] + 15, 1.5, "map (close fleet panel)", force=True)
        return not single_find("ZFleetSpeed")

    def boost_ship(self, index, booster="ZQuantumBoost"):
        """Use one booster on a sailing fleet. Returns True when 使用 was clicked."""
        log(f"Boost ship {index} with {booster}")
        if not self.open_fleet_panel(index):
            log("Fleet panel did not open (ship not sailing?)")
            return False
        if not self.click_button("ZAccelerate", 2) or not self.wait_for("ZBoostPage", 8):
            log("Boost dialog did not open")
            self.close_fleet_panel(index)
            return False
        row = get_center(booster, "Single")
        if row is None:
            log(f"{booster} row not found")
            self.close_popup()
            self.close_fleet_panel(index)
            return False
        if self.dry_run:
            log(f"[DRY] would click 使用 at ({row.x + BOOST_LAYOUT['use_dx']:.0f},{row.y + BOOST_LAYOUT['use_dy']:.0f})")
            ok = False
        else:
            self.click(row.x + BOOST_LAYOUT["use_dx"], row.y + BOOST_LAYOUT["use_dy"], 2, "使用")
            ok = True
            if single_find("ZContinueHint"):
                self.click_button("ZContinueHint", 1.5)
        self.close_popup()
        self.close_fleet_panel(index)
        log("Boost used" if ok else "Boost not used")
        return ok

    # ------------------------------------------------------------------ repair
    def repair_ship(self, index):
        log(f"Repair ship {index}")
        if self.dry_run:
            return True
        team = self.ui("team")
        if team is not None:
            self.click(team.x, team.y, 2, "队伍")
        if team is None or not self.wait_for("ZMyFleet", 8):
            log("Fleet page did not open")
            self.close_popup()
            return False
        title = self.anchor("ZMyFleet")
        tx = title.x + FLEET_PAGE_LAYOUT["tab_dx0"] + (index - 1) * FLEET_PAGE_LAYOUT["tab_spacing"]
        ty = title.y + FLEET_PAGE_LAYOUT["tab_dy"]
        self.click(tx, ty, 2, f"fleet tab {index}")
        ok = self.click_button("ZRepair", 2)
        if ok and self.wait_for("ZRepairPrompt", 6):
            ok = self.click_button("ZRepairOk", 2)
            log("Repair confirmed" if ok else "Repair confirm button not found")
        self.close_popup()
        return ok

    # ------------------------------------------------------------------ main loop
    def process_screen(self):
        """Dispatch to everything worth it on the current screen.
        Returns False when the sweep should stop (no idle ship / no usable action)."""
        if not self.on_map() and not self.close_popup():
            return False
        for _ in range(SHIP_LAYOUT["slots"]):
            ships = self.scan_ships()
            if not ships:
                return False
            if not self.idle_ships(ships):
                log("No idle ship")
                return False
            actions = self.read_actions()
            free_left = actions[0] if actions else None
            allow_buy = False
            if free_left is not None and free_left <= 0:
                if not ACTION_BUY_ENABLED or self.packs_bought >= MAX_PACKS_PER_RUN:
                    log("No free actions left and buying is off -> wait for regeneration")
                    return False
                min_score = MIN_SCORE_BOUGHT_ACTION
                allow_buy = True
            else:
                min_score = MIN_SCORE_FREE_ACTION
            cands = [c for c in self.scan_resources() if c.score >= min_score]
            if not cands:
                return True
            if self.dry_run:
                log(f"[DRY] would dispatch to {cands[0]} (min score {min_score})")
                return True
            self.dispatch(cands[0], allow_buy=allow_buy)
            time.sleep(2)
        return True

    def sweep(self, on_screen=None):
        """Serpentine sweep over the whole map, calling on_screen() at every stop (it returns
        False to stop early). Alternates between starting at the top-left and the bottom-left
        corner to save drags."""
        on_screen = on_screen or self.process_screen
        steps = self.drag_steps()
        if steps is None:
            log("Map area anchors not found")
            return False
        step_x, step_y = steps
        if on_screen == self.survey_screen:     # bound methods compare equal, never `is`
            self.sweep_from_top = True          # map coordinates are anchored at the top-left corner
        vdir = 1 if self.sweep_from_top else -1    # content movement for the next row (up = -step_y)
        log(f"Sweep: to the {'top' if self.sweep_from_top else 'bottom'}-left corner")
        self.go_to_corner(step_x, step_y * vdir)
        hdir = -1                                   # content moves left -> we look further right
        rows = 0
        while rows < DRAG_LAYOUT["max_drags"]:
            rows += 1
            for _ in range(DRAG_LAYOUT["max_drags"]):
                if not on_screen():
                    log("Sweep stopped early")
                    self.sweep_from_top = not self.sweep_from_top
                    return True
                r = self.drag_map(step_x * hdir, 0)
                if r == "fail":
                    return False
                if r == "edge":
                    break
            r = self.drag_map(0, -step_y * vdir)
            if r == "fail":
                return False
            if r == "edge":
                break
            hdir = -hdir
        log(f"Sweep finished ({rows} rows)")
        self.sweep_from_top = not self.sweep_from_top
        return True

    # ------------------------------------------------------------------ zones
    def title_crop(self):
        """Grayscale crop (reference physical px) of the zone title box, or None."""
        base = self.anchor("ZBase")
        if base is None or not single_find("ZExplore"):
            return None
        gray = screen_shot()
        cx, cy = base.x + ZONE_LAYOUT["title_dx"], base.y + ZONE_LAYOUT["title_dy"]
        hw, hh = ZONE_LAYOUT["title_half_w"], ZONE_LAYOUT["title_half_h"]
        x1, x2 = int((cx - hw) * self.sft), int((cx + hw) * self.sft)
        y1, y2 = int((cy - hh) * self.sft), int((cy + hh) * self.sft)
        return gray[y1:y2, x1:x2]

    def learned_titles(self):
        titles = {}
        if os.path.isdir(ZONE_TITLE_DIR):
            for fn in os.listdir(ZONE_TITLE_DIR):
                if fn.endswith(".png"):
                    titles[fn[:-4]] = cv2.imread(os.path.join(ZONE_TITLE_DIR, fn), 0)
        return titles

    def learn_title(self, name):
        crop = self.title_crop()
        if crop is None:
            return False
        os.makedirs(ZONE_TITLE_DIR, exist_ok=True)
        cv2.imwrite(os.path.join(ZONE_TITLE_DIR, f"{name}.png"), crop)
        log(f"Learned the title of zone {name}")
        return True

    def read_zone(self):
        """Zone name from the map title. Central ("深寒战场") is matched as a whole; outer zones
        differ only in two digits, so after aligning a learned title on the crop only the digit
        glyphs are compared. OCR of those glyphs is the fallback for zones not learned yet."""
        crop = self.title_crop()
        if crop is None:
            return None
        pad = 8
        padded = cv2.copyMakeBorder(crop, pad, pad, pad, pad, cv2.BORDER_REPLICATE)
        titles = {n: t for n, t in self.learned_titles().items()
                  if t is not None and t.shape[0] <= padded.shape[0] and t.shape[1] <= padded.shape[1]}
        central = titles.pop("central", None)
        central_conf = 0.0
        if central is not None:
            central_conf = cv2.minMaxLoc(cv2.matchTemplate(padded, central, cv2.TM_CCOEFF_NORMED))[1]
            if central_conf >= ZONE_LAYOUT["title_match_th"]:
                return "central"
        c0, c1 = ZONE_LAYOUT["digit_c0"], ZONE_LAYOUT["digit_c1"]
        scores, aligned = {}, None
        for name, t in titles.items():
            r = cv2.matchTemplate(padded, t, cv2.TM_CCOEFF_NORMED)
            _, _, _, loc = cv2.minMaxLoc(r)
            al = padded[loc[1]:loc[1] + t.shape[0], loc[0]:loc[0] + t.shape[1]]
            if aligned is None:
                aligned = al
            scores[name] = float(cv2.matchTemplate(al[:, c0:c1], t[:, c0:c1], cv2.TM_CCOEFF_NORMED).max())
        if scores:
            ranked = sorted(scores.items(), key=lambda kv: -kv[1])
            best, second = ranked[0][1], ranked[1][1] if len(ranked) > 1 else 0.0
            if best >= ZONE_LAYOUT["digit_match_th"] and best - second >= ZONE_LAYOUT["digit_margin"]:
                return ranked[0][0]
        digits = self.ocr_title_digits(aligned if aligned is not None else crop)
        if digits:
            return digits
        if central_conf >= 0.8:
            return "central"
        return None

    def ocr_title_digits(self, title):
        """OCR of the two digit glyphs of an (aligned) outer-zone title crop -> '05' or ''."""
        c0, c1 = ZONE_LAYOUT["digit_c0"], ZONE_LAYOUT["digit_c1"]
        dg = title[:, c0:c1]
        if dg.size == 0:
            return ""
        try:
            import pytesseract
            dg = cv2.resize(dg, None, fx=4, fy=4, interpolation=cv2.INTER_CUBIC)
            dg = cv2.threshold(dg, 150, 255, cv2.THRESH_BINARY_INV)[1]
            dg = cv2.copyMakeBorder(dg, 20, 20, 20, 20, cv2.BORDER_CONSTANT, value=255)
            txt = pytesseract.image_to_string(dg, config="--psm 7 -c tessedit_char_whitelist=0123456789")
        except Exception:
            return ""
        digits = "".join(ch for ch in txt if ch.isdigit())
        return digits[-2:].zfill(2) if digits else ""

    def switch_zone(self, name):
        """Open the zone chooser and enter the named zone. Returns True when on that zone's map."""
        if name not in ZONE_LAYOUT["cards"]:
            log(f"Unknown zone {name}")
            return False
        if self.zone is None:
            self.zone = self.read_zone()
        if self.zone == name and self.on_map():
            return True
        log(f"Switch zone {self.zone} -> {name}")
        if self.dry_run:
            log("[DRY] zone switching is skipped in dry mode")
            return False
        self.close_popup()
        if name == "central":
            # the base icon at the top left jumps straight to our base in the central zone
            base = self.anchor("ZBase")
            if base is not None:
                self.click(base.x, base.y, 3, "base icon -> central")
        else:
            sel = self.ui("select_zone")
            if sel is None:
                return False
            self.click(sel.x, sel.y, 2.5, "zone chooser")
            if not self.wait_for("ZZoneList", 8):
                log("Zone chooser did not open")
                self.close_popup()
                return False
            base = self.anchor("ZBase")
            dx, dy = ZONE_LAYOUT["cards"][name]
            self.click(base.x + dx, base.y + dy, 3, f"zone {name}")
        if not self.wait_for("ZExplore", 12):
            log("Map did not appear after choosing the zone")
            self.close_popup()
            return False
        time.sleep(1)
        self.ensure_zoom()
        seen = self.read_zone()
        if seen == name:
            self.zone = name
            return True
        if name not in self.learned_titles() and self.title_looks_like(name, seen):
            self.learn_title(name)          # first visit: verified as far as OCR allows
            self.zone = name
            return True
        log(f"Landed on zone {seen}, expected {name}")
        self.zone = seen
        return False

    def title_looks_like(self, name, seen):
        """Before learning a title: it must not be a known other zone, and the OCR of the digit
        glyphs (or their absence for central) must agree with the requested zone."""
        if seen is not None and seen != name:
            return False
        crop = self.title_crop()
        if crop is None:
            return False
        digits = self.ocr_title_digits(crop)
        if name == "central":
            return digits == ""
        return digits == name

    # ------------------------------------------------------------------ survey then dispatch
    def to_map(self, x, y):
        return x - self.offset[0], y - self.offset[1]

    def to_screen(self, mx, my):
        return mx + self.offset[0], my + self.offset[1]

    def can_dispatch(self):
        """(idle ship count, allow_buy) or (0, False) when nothing can be sent right now.
        A dry run pretends all ships are idle so the whole flow can be exercised any time."""
        ships = self.scan_ships()
        idle = self.idle_ships(ships) if ships else []
        if self.dry_run:
            return SHIP_LAYOUT["slots"], False
        if not idle:
            return 0, False
        actions = self.read_actions()
        free_left = actions[0] if actions else None
        if free_left is not None and free_left <= 0:
            if not ACTION_BUY_ENABLED or self.packs_bought >= MAX_PACKS_PER_RUN:
                log("No free actions left and buying is off")
                return 0, False
            return len(idle), True
        return len(idle), False

    def debug_drag(self, before, after, dx, dy, shift):
        """With --debug-shots: save the before/after map crops of a drag judged as 'no move'."""
        if not DEBUG_SHOT_DIR:
            return
        os.makedirs(DEBUG_SHOT_DIR, exist_ok=True)
        gap = np.full((before.shape[0], 20), 128, np.uint8)
        img = np.hstack([before, gap, after])
        cv2.putText(img, f"asked ({dx:.0f},{dy:.0f}) measured ({shift[0]:.0f},{shift[1]:.0f})", (10, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.2, 255, 2)
        path = os.path.join(DEBUG_SHOT_DIR, f"{time.strftime('%H%M%S')}_drag_{self.zone}.png")
        cv2.imwrite(path, img)
        log(f"Debug drag shot saved: {path}")

    def debug_shot(self, cands):
        """With --debug-shots: save the frame the scanner used, detections boxed, so a "the log
        says 0 but I see a box" report can be checked against exactly what the program saw."""
        if not DEBUG_SHOT_DIR:
            return
        color = self._scan_frame if self._scan_frame is not None else self.shot()[0]
        np.save(os.path.join(DEBUG_SHOT_DIR, "last_scan_frame.npy"), color) if os.path.isdir(DEBUG_SHOT_DIR) else None
        img = cv2.cvtColor(color, cv2.COLOR_RGB2BGR).copy()
        region = self.map_region()
        if region:
            x1, y1, x2, y2 = (int(v * self.sft) for v in region)
            cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 255), 2)
        for c in cands:
            cx, cy = int(c.x * self.sft), int(c.y * self.sft)
            cv2.rectangle(img, (cx - 40, cy - 40), (cx + 40, cy + 40), (0, 0, 255), 3)
            cv2.putText(img, c.kind, (cx - 40, cy - 48), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        os.makedirs(DEBUG_SHOT_DIR, exist_ok=True)
        path = os.path.join(DEBUG_SHOT_DIR, f"{time.strftime('%H%M%S')}_{self.zone}_{len(cands)}.png")
        cv2.imwrite(path, img)
        log(f"Debug shot saved: {path}")

    def survey_screen(self):
        """Memorize everything on this screen; dispatch IMMEDIATE_KINDS right away."""
        if not self.on_map() and not self.close_popup():
            return False
        for _ in range(4):                  # re-scan after each immediate dispatch (the view may
            dispatched = False              # have moved and the candidate list is stale)
            outer = self.zone is not None and self.zone != "central"
            cands = self.scan_resources(kinds=OUTER_KINDS if outer else None, light=outer)
            self.debug_shot(cands)
            corrected = self.correct_offset_from_landmarks()   # voting first; the per-spot fallback stays otherwise
            for c in cands:
                mx, my = self.to_map(c.x, c.y)
                same = [s for s in self.spots
                        if s.kind == c.kind and abs(s.mx - mx) < RESEEN_TOLERANCE and abs(s.my - my) < RESEEN_TOLERANCE]
                if same:
                    # the same resource seen again in the overlap: its memorized position is the
                    # truth, so a drift of the drag offsets (e.g. an unmeasurable drag) is
                    # corrected here instead of accumulating
                    s = same[0]
                    ddx, ddy = mx - s.mx, my - s.my
                    if not corrected and (abs(ddx) > 4 or abs(ddy) > 4):
                        self.offset[0] += ddx
                        self.offset[1] += ddy
                        corrected = True
                        log(f"Offset corrected by ({ddx:.0f},{ddy:.0f}) from a re-seen {c.kind}")
                    continue
                base_kind = c.kind.split("[")[0]
                if base_kind in IMMEDIATE_KINDS and not self.dry_run:
                    n, allow_buy = self.can_dispatch()
                    if n > 0:
                        self.dispatch(c, allow_buy=allow_buy)
                        dispatched = True
                        break
                self.spots.append(Spot(c.kind, c.score, mx, my, self.zone))
            if not dispatched:
                self.prev_landmarks = list(self.last_landmarks)
                self.prev_offset = list(self.offset)
                return True
        self.prev_landmarks = list(self.last_landmarks)
        self.prev_offset = list(self.offset)
        return True

    def correct_offset_from_landmarks(self):
        """The icons seen at the previous stop that are still on screen tell exactly how far the
        map moved: every same-kind pair votes for a displacement, the biggest cluster wins. If
        it disagrees with what the drag measurement (or assumption) produced, the offsets are
        corrected, so the same resource is never memorized twice."""
        if not self.prev_landmarks or self.prev_offset is None or not self.last_landmarks:
            return False
        assumed = (self.offset[0] - self.prev_offset[0], self.offset[1] - self.prev_offset[1])
        votes = []
        for pk, px, py in self.prev_landmarks:
            for ck, cx, cy in self.last_landmarks:
                if pk == ck:
                    votes.append((cx - px, cy - py, pk))
        best, best_n = None, 0
        for vx, vy, _ in votes:
            n = sum(1 for ox, oy, _ in votes if abs(ox - vx) < 8 and abs(oy - vy) < 8)
            if n > best_n:
                best, best_n = (vx, vy), n
        if best is None:
            return False
        rare = any(k != "ZBox" for ox, oy, k in votes if abs(ox - best[0]) < 8 and abs(oy - best[1]) < 8)
        if best_n < 2 and not rare:
            return False
        step_x, step_y = self.drag_steps() or (400, 600)
        if abs(best[0]) > 1.3 * step_x or abs(best[1]) > 1.3 * step_y:
            return False
        ddx, ddy = best[0] - assumed[0], best[1] - assumed[1]
        if abs(ddx) > 4 or abs(ddy) > 4:
            self.offset[0] += ddx
            self.offset[1] += ddy
            log(f"Landmarks ({best_n} votes) say the map moved ({best[0]:.0f},{best[1]:.0f}), "
                f"not ({assumed[0]:.0f},{assumed[1]:.0f}) -> offset corrected by ({ddx:.0f},{ddy:.0f})")
            return True
        return False

    def navigate_to(self, spot):
        """Drag until the memorized spot is near the center of the map area, switching zone and
        re-anchoring at the top-left corner first when needed."""
        if spot.zone is not None and spot.zone != self.zone:
            if not self.switch_zone(spot.zone):
                return False
            steps = self.drag_steps()
            if steps is None:
                return False
            self.go_to_corner(steps[0], steps[1])
        region = self.map_region()
        if region is None:
            return False
        cx, cy = (region[0] + region[2]) / 2, (region[1] + region[3]) / 2
        for _ in range(DRAG_LAYOUT["max_drags"]):
            sx, sy = self.to_screen(spot.mx, spot.my)
            dx, dy = cx - sx, cy - sy
            if abs(dx) < 15 and abs(dy) < 15:
                return True
            r = self.drag_map(dx, dy)
            if r == "fail":
                return False
            if r == "edge":
                # the map cannot move further; fine if the spot is already on screen
                sx, sy = self.to_screen(spot.mx, spot.my)
                return region[0] < sx < region[2] and region[1] < sy < region[3]
        return False

    def verify_spot(self, spot):
        """Re-detect a memorized resource around its expected screen position only (fast), with
        the colour and route-line checks. Returns [Candidate] or []."""
        sx, sy = self.to_screen(spot.mx, spot.my)
        base_kind = spot.kind.split("[")[0]
        color = np.array(pyautogui.screenshot())
        gray = cv2.cvtColor(color, cv2.COLOR_RGB2GRAY)
        tol = NAV_TOLERANCE
        x1, y1 = int(max(0, (sx - tol) * self.sft)), int(max(0, (sy - tol) * self.sft))
        x2, y2 = int(min(gray.shape[1], (sx + tol) * self.sft)), int(min(gray.shape[0], (sy + tol) * self.sft))
        sub = gray[y1:y2, x1:x2]
        hits = [((x1 + cx) / self.sft, (y1 + cy) / self.sft) for cx, cy, _ in match_all(sub, self.full_template(base_kind), MATCH_TH)]
        if not hits and base_kind in PARTIAL_KINDS:
            for _, tmpl in self.partial_templates(base_kind):
                hits += [((x1 + cx) / self.sft, (y1 + cy) / self.sft) for cx, cy, _ in match_all(sub, tmpl, PARTIAL_TH)]
        region = self.map_region()
        ends = self.route_endpoints(color, region) if region else []
        # the survey may be minutes old: re-check for rival (blue) lines right before going
        blue_ends = self.route_endpoints(color, region, "blue") if region else []
        out = []
        for x, y in hits:
            if not self.color_ok(base_kind, color, x, y):
                continue
            if self.targeted_by_route(x, y, ends):
                log("Memorized spot already has one of our ships on the way")
                continue
            if blue_ends and self.targeted_by_route(x, y, blue_ends, "blue"):
                if base_kind in FACTORY_KINDS or self.zone == "central":
                    log("Memorized spot has a rival on the way -> go and race (boost if needed)")
                    self.contested[self.spot_key(x, y)] = time.time()
                else:
                    log("Memorized spot now has a rival on the way -> skip")
                    continue
            out.append(Candidate(spot.kind, spot.score, x, y))
        out.sort(key=lambda c: abs(c.x - sx) + abs(c.y - sy))
        return out

    def forget_spot(self, spot):
        entry = self.zone_spots.get(spot.zone)
        if entry and spot in entry["spots"]:
            entry["spots"].remove(spot)

    def survey_zones(self):
        """Survey the zones whose memory is older than SURVEY_TTL (or was invalidated) and collect
        all spots. The central zone is the main one; outer zones are only surveyed while at least
        MIN_IDLE_FOR_OTHER_ZONES ships are idle."""
        now = time.time()
        for name in ZONES:
            entry = self.zone_spots.get(name)
            if entry and now - entry["time"] < SURVEY_TTL:
                continue
            if name != "central":
                n, _ = self.can_dispatch()
                if n < MIN_IDLE_FOR_OTHER_ZONES:
                    log(f"Zone {name}: only {n} idle ship(s), outer zones need {MIN_IDLE_FOR_OTHER_ZONES} -> skipped")
                    break
            if self.dry_run and name != (self.zone or name):
                log(f"[DRY] would switch to zone {name} and survey it")
                continue
            if not self.switch_zone(name):
                if self.dry_run and self.zone_spots.get(name) is None and name == self.zone:
                    pass
                else:
                    continue
            self.spots = []
            if not self.sweep(self.survey_screen):
                continue
            self.zone_spots[name] = {"time": time.time(), "spots": list(self.spots)}
            log(f"Zone {name}: {len(self.spots)} spot(s) memorized")
            n, _ = self.can_dispatch()
            if n <= 0:
                break
        self.spots = [s for e in self.zone_spots.values() for s in e["spots"]]
        return True

    def dispatch_memorized(self):
        """Go back to the memorized spots best-first while ships and actions last."""
        rank = {z: i for i, z in enumerate(ZONES)}
        self.spots.sort(key=lambda s: (-s.score, rank.get(s.zone, 99), abs(s.mx) + abs(s.my)))
        log("Survey: " + ", ".join(f"{s.kind}@{s.zone}({s.mx:.0f},{s.my:.0f})" for s in self.spots[:10])
            + (f" ... {len(self.spots)} total" if len(self.spots) > 10 else ""))
        sent = 0
        for spot in list(self.spots):
            n, allow_buy = self.can_dispatch()
            if n <= 0:
                log("No idle ship or no usable action left")
                break
            if self.dry_run:
                log(f"[DRY] would navigate to {spot} and dispatch")
                sent += 1
                if sent >= n:
                    break
                continue
            if not self.navigate_to(spot):
                log(f"Could not navigate to {spot}")
                continue
            sx, sy = self.to_screen(spot.mx, spot.my)
            near = self.verify_spot(spot)
            if not near:
                log(f"{spot.kind} no longer at {spot.zone}({spot.mx:.0f},{spot.my:.0f}) -> zone memory invalidated")
                self.spots = [s for s in self.spots if s.zone != spot.zone]
                self.zone_spots.pop(spot.zone, None)
                self.rescan_needed = True
                continue
            if self.dispatch(near[0], allow_buy=allow_buy):
                sent += 1
            self.spots.remove(spot)
            self.forget_spot(spot)
            time.sleep(2)
        log(f"Dispatched {sent} fleet(s) this round")
        return True

    def single_round(self):
        if not self.on_map():
            log("Not on the map page")
            if not self.close_popup():
                return False
        self.calibrate_scale()
        self.ensure_zoom()
        self.prune_visited()
        self.zone = self.read_zone()
        log(f"Current zone: {self.zone}")

        ships = self.scan_ships()
        if not ships:
            return False
        for i, s in ships.items():
            if s["idle"] and s["hp"] is not None and s["hp"] < REPAIR_BELOW:
                self.repair_ship(i)
                ships = self.scan_ships()
                break
        if not self.idle_ships(ships):
            log("No idle ship" + (" (dry run continues anyway)" if self.dry_run else ""))
            if not self.dry_run:
                return True
        actions = self.read_actions()
        if actions and actions[0] <= 0 and (not ACTION_BUY_ENABLED or self.packs_bought >= MAX_PACKS_PER_RUN):
            log("No free actions left and buying is off -> wait for regeneration")
            if not self.dry_run:
                return True
        if not SWEEP_ENABLED:
            return self.process_screen() or True
        if DISPATCH_MODE != "survey":
            return self.sweep()
        # survey -> dispatch; when a memorized resource turned out to be gone, that zone is
        # re-surveyed and dispatching continues from the fresh list (once per round)
        for _ in range(2):
            self.rescan_needed = False
            if not self.survey_zones():
                return False
            if not self.dispatch_memorized():
                return False
            n, _ = self.can_dispatch()
            if not self.rescan_needed or n <= 0:
                break
            log("Memorized resources disappeared -> rescanning")
        return True

    def enter_zone_explore(self):
        """From the main (dice) page: close the dice popup and click 星际探险 until the map shows."""
        for _ in range(3):
            c = get_center("ZMoreDice", "Single")
            if c is None:
                break
            self.click(c.x + MORE_DICE_LAYOUT["close_dx"], c.y + MORE_DICE_LAYOUT["close_dy"], 1.5, "close dice popup")
        if not self.click_button("ZStarExplore", 3):
            log("星际探险 button not found")
            return False
        if self.wait_for("ZExplore", 15):
            log("Entered zone explore")
            return True
        log("Map page did not appear after 星际探险 (screenshot the page that opened)")
        return False

    def monitor(self):
        """Watch the dice run; when it ends, enter 星际探险 and keep dispatching fleets."""
        log("Monitor: waiting for the dice run to end")
        idle_since = None
        while True:
            try:
                if single_find("ZExplore"):
                    self.rounds += 1
                    log(f"=== round {self.rounds} ===")
                    ok = self.single_round()
                    self.fails = 0 if ok else self.fails + 1
                    if self.fails >= 5:
                        log("Too many failures, trying to recover")
                        self.close_popup()
                        self.fails = 0
                    if self.dry_run:
                        return
                    log(f"Sleep {POLL_SECONDS}s")
                    time.sleep(POLL_SECONDS)
                    continue
                if single_find("ZMoreDice"):
                    log("Dice ran out -> entering 星际探险")
                    if self.dry_run:
                        log("[DRY] would close the popup and click 星际探险")
                        return
                    self.enter_zone_explore()
                    time.sleep(3)
                    continue
                if single_find("ZAutoThrowing"):
                    idle_since = None
                    log("Run in progress")
                elif single_find("ZLongPressAuto"):
                    idle_since = idle_since or time.time()
                    waited = time.time() - idle_since
                    log(f"Run button idle for {waited:.0f}s")
                    if waited >= RUN_IDLE_SECONDS:
                        log("Run has been idle long enough -> entering 星际探险")
                        if self.dry_run:
                            return
                        self.enter_zone_explore()
                        idle_since = None
                        time.sleep(3)
                        continue
                else:
                    log("Unknown page, waiting")
            except Exception as e:
                log(f"Monitor error: {e}")
            time.sleep(MONITOR_POLL)

    def run(self):
        while True:
            self.rounds += 1
            log(f"=== round {self.rounds} ===")
            try:
                ok = self.single_round()
            except Exception as e:
                log(f"Round error: {e}")
                ok = False
            self.fails = 0 if ok else self.fails + 1
            if self.fails >= 5:
                log("Too many failures, trying to recover")
                self.close_popup()
                self.fails = 0
            if self.dry_run:
                return
            log(f"Sleep {POLL_SECONDS}s")
            time.sleep(POLL_SECONDS)

    def click_test(self):
        """Click 50% then 75% on the zoom bar and report whether the game reacted."""
        c = self.ui("zoom50")
        if c is None:
            log("Zoom bar not found")
            return
        log(f"zoom 75% selected before: {self.zoom75_selected()}")
        self.raw_click(c.x, c.y)
        time.sleep(2)
        log(f"after clicking 50%: zoom 75% selected = {self.zoom75_selected()}  (expect False)")
        self.raw_click(c.x + ZOOM_LAYOUT["dx75"], c.y)
        time.sleep(2)
        log(f"after clicking 75%: zoom 75% selected = {self.zoom75_selected()}  (expect True)")

    def drag_test(self):
        """One drag left, one drag right; prints what the measurement sees."""
        self.ensure_zoom()
        steps = self.drag_steps()
        log(f"Map area {self.map_region()} steps {steps}")
        if steps is None:
            return
        self.drag_map(-steps[0], 0)
        self.scan_resources()
        self.drag_map(steps[0], 0)
        self.drag_map(0, -steps[1])
        self.scan_resources()
        self.drag_map(0, steps[1])
        log(f"Net offset after the round trip: ({self.offset[0]:.0f},{self.offset[1]:.0f})")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry", action="store_true", help="Drag and detect only, no dispatch clicks")
    parser.add_argument("--drag-test", action="store_true", help="One drag each way, print the measured movement")
    parser.add_argument("--click-test", action="store_true", help="Click 50% then 75% on the zoom bar")
    parser.add_argument("--boost-test", type=int, metavar="SHIP",
                        help="Open the boost dialog of ship 1-5 (with --dry: stop before 使用)")
    parser.add_argument("--debug-shots", action="store_true",
                        help="Save every survey stop's frame with detections to pics/<platform>/zone/debug/")
    parser.add_argument("--zone-test", metavar="ZONE",
                        help="Switch to a zone (central, 02..07) and report which zone the map shows")
    parser.add_argument("-m", "--monitor", action="store_true",
                        help="Watch the dice run; enter 星际探险 when the dice run out, then dispatch fleets")
    parser.add_argument("--delay", type=int, default=3, help="Seconds to switch to the game window")
    args = parser.parse_args()
    time.sleep(args.delay)
    if args.debug_shots:
        DEBUG_SHOT_DIR = os.path.join(os.path.dirname(single_find_map["ZBase"]), "debug")
    z = ZoneExplore(dry_run=args.dry)
    if args.click_test:
        z.click_test()
    elif args.boost_test:
        z.boost_ship(args.boost_test)
    elif args.zone_test:
        z.calibrate_scale()
        z.zone = z.read_zone()
        log(f"Current zone: {z.zone}")
        log(f"switch_zone({args.zone_test}) -> {z.switch_zone(args.zone_test)}; now on zone {z.zone}")
    elif args.monitor:
        z.monitor()
    elif args.drag_test:
        z.drag_test()
    else:
        z.run()
