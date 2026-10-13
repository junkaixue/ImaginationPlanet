"""
金秋赏月 - keep a seat in the festival pavilion.

Pages (pics/mac/zone/pages/festival/):
    activity page  "月满华诞" list, first banner 金秋赏月 with a 前往>> button
    festival page  pavilions 巅峰I/II/III号赏月亭; a yellow "我" bubble over a pavilion means we
                   already sit there -> press the back arrow (bottom left) and stop
    pavilion page  rows 观赏位1排, 2排, ...; a free seat shows 占据 above 无人占领, an occupied
                   seat shows an avatar with 挑战 (never pressed). From row 2 on, press the first
                   占据; the page scrolls for the lower rows.

Usage:
    python festival_sit.py            # one pass: sit if not seated, return to the activity page
    python festival_sit.py --loop 10  # repeat every 10 minutes (the seat may be taken from us)
    python festival_sit.py --dry      # navigate and report, do not press 占据
"""

import argparse
import os
import time

import cv2

from click import move_to
from common import single_find, get_center, get_all
from log_helper import log
from zone_explore import ZoneExplore, drag, _code_version

FEST = {
    "row_skip_first_pavilion": 1,   # pavilion I: row 1 is never used; other pavilions use every row
    "row_gap_min": 60,        # logical px below the first row label where row 2 starts
    "scroll_dy": 300,         # pavilion list scroll per step (logical px)
    "card_dx": 155, "card_dy": 94,   # name card of the left seat, relative to the row label
    "card2_dx": 318,          # name card of the right seat
    "row_h": 135,             # a row's buttons and cards lie within this below its label
    "row_drag": 290,          # horizontal drag per step inside a row (each row is a carousel)
    "max_row_drags": 8,
    "max_scrolls": 0,         # pavilions have 3 or 4 rows, all on one screen: no vertical scrolling
    "settle": 1.0,
}


DEBUG_DIR = None


class FestivalSit(ZoneExplore):
    def __init__(self, dry_run=False):
        super().__init__(dry_run=dry_run)
        log(f"FestivalSit ready (code={_code_version()})")

    def save_debug(self, name, boxes=()):
        if not DEBUG_DIR:
            return
        self.invalidate_shot()
        img = cv2.cvtColor(self.shot()[0], cv2.COLOR_RGB2BGR).copy()
        for x, y, lab in boxes:
            px, py = int(x * self.sft), int(y * self.sft)
            cv2.rectangle(img, (px - 40, py - 30), (px + 40, py + 30), (0, 0, 255), 3)
            cv2.putText(img, lab, (px - 40, py - 36), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        path = os.path.join(DEBUG_DIR, f"{time.strftime('%H%M%S')}_{name}.png")
        cv2.imwrite(path, img)
        log(f"Debug shot saved: {path}")

    # ------------------------------------------------------------------ pages
    def page(self):
        if single_find("ZFestOccupy") or single_find("ZFestRow"):
            return "pavilion"
        if single_find("ZFestPav1"):
            return "festival"
        if single_find("ZFestTitle"):
            return "activity"
        if single_find("ZFestMainBtn"):
            return "main"
        return None

    def open_activity(self):
        """Game main screen -> the 金秋赏月 button on the right side -> activity page."""
        b = get_center("ZFestMainBtn", "Single")
        if b is None:
            return False
        self.click(b.x, b.y - 40, 2.5, "金秋赏月 (main screen)", force=True)
        return self.wait_for("ZFestTitle", 8) or self.wait_for("ZFestPav1", 3)

    def back(self):
        c = get_center("ZFestBack", "Single")
        if c is None:
            return False
        self.click(c.x, c.y, 2, "back arrow", force=True)
        return True

    def open_festival(self):
        """Activity page -> 金秋赏月 (the 前往 button right below the banner title)."""
        title = get_center("ZFestTitle", "Single")
        gos = get_all("ZFestGo", "Single")
        if title is None or not gos:
            return False
        below = [g for g in gos if g.y > title.y and g.y - title.y < 120]
        go = min(below or gos, key=lambda g: g.y)
        self.click(go.x, go.y, 2.5, "金秋赏月 前往", force=True)
        return self.wait_for("ZFestPav1", 8)

    def seated(self):
        return single_find("ZFestMe")

    def pavilions(self):
        """Pavilion labels on the festival page, in order I, II, III, ... (top to bottom)."""
        labels = get_all("ZFestPavilion", "Single")
        return sorted(labels, key=lambda p: (p.y, p.x))

    def open_pavilion(self, label, name):
        self.click(label.x - 60, label.y - 60, 2.5, name, force=True)
        return self.wait_for("ZFestRow", 8)

    def scroll_pavilion(self):
        rows = get_all("ZFestRow", "Single")
        if not rows:
            return False
        # the list scrolls when dragged on a name card (the card sits ~94 px below the row
        # label, left column ~155 px right of it); buttons and empty space do not drag
        x = rows[0].x + FEST["card_dx"]
        y0 = max(r.y for r in rows) + FEST["card_dy"]
        y1 = y0 - FEST["scroll_dy"]
        self.invalidate_shot()
        before = self.shot()[1]
        rx0, ry0 = self.to_real(x, y0)
        rx1, ry1 = self.to_real(x, y1)
        drag(rx0, ry0, rx1, ry1)
        self.invalidate_shot()
        time.sleep(FEST["settle"])
        self.wait_still()
        after = self.shot()[1]
        return self.frame_diff(before, after) > 3.0

    def row_free_seat(self, label):
        """First 占据 inside this row's band (the row is a carousel: cards slide left)."""
        self.invalidate_shot()
        seats = sorted(get_all("ZFestOccupy", "Single"), key=lambda s: s.x)
        empties = get_all("ZFestEmpty", "Single")
        log(f"  占据 on screen: {[(round(s.x), round(s.y)) for s in seats]}  无人占领: {[(round(e.x), round(e.y)) for e in empties]}")
        for s in seats:
            if label.y < s.y < label.y + FEST["row_h"]:
                return s
        for e in empties:               # an empty seat whose 占据 button was not matched
            if label.y < e.y < label.y + FEST["row_h"]:
                log("  无人占领 seen without a 占据 match; using the button above it")
                return type(e)(e.x, e.y - 60)
        return None

    def drag_row(self, label):
        """Slide the row's carousel left by dragging on its right name card."""
        y = label.y + FEST["card_dy"]
        x0, x1 = label.x + FEST["card2_dx"], label.x + FEST["card2_dx"] - FEST["row_drag"]
        self.invalidate_shot()
        gray = self.shot()[1]
        by0, by1 = int(label.y * self.sft), int((label.y + FEST["row_h"]) * self.sft)
        before = gray[by0:by1].copy()
        rx0, ry0 = self.to_real(x0, y)
        rx1, ry1 = self.to_real(x1, y)
        drag(rx0, ry0, rx1, ry1)
        self.invalidate_shot()
        time.sleep(FEST["settle"])
        self.wait_still()
        after = self.shot()[1][by0:by1]
        return self.frame_diff(before, after) > 3.0

    def take_seat(self, s):
        if self.dry_run:
            rx, ry = self.to_real(s.x, s.y)
            move_to(rx, ry)
            log(f"[DRY] 占据 at ({s.x:.0f},{s.y:.0f}): mouse moved there, not pressed")
            time.sleep(3)
            return True
        self.click(s.x, s.y, 2.5, "占据")
        if self.wait_for("ZRepairOk", 3):           # a confirmation, if any
            self.click_button("ZRepairOk", 2, force=True)
        time.sleep(2)
        return True

    def sit(self, skip_rows=0):
        """Rows top to bottom (minus `skip_rows` at the top); inside a row slide the carousel
        until a 占据 shows."""
        for i in range(FEST["max_scrolls"] + 1):
            rows = sorted(get_all("ZFestRow", "Single"), key=lambda r: r.y)
            usable = rows[skip_rows:] if i == 0 else rows
            log(f"Pavilion screen {i + 1}: {len(rows)} row label(s), {len(usable)} usable")
            for n, label in enumerate(usable):
                for k in range(FEST["max_row_drags"] + 1):
                    s = self.row_free_seat(label)
                    if s is not None:
                        log(f"Row at y={label.y:.0f}: free seat after {k} slide(s)")
                        return self.take_seat(s)
                    if k == FEST["max_row_drags"]:
                        break
                    moved = self.drag_row(label)
                    self.save_debug(f"row{n + 1}_slide{k + 1}", [(label.x, label.y, "row")])
                    if not moved:
                        log(f"  row did not slide (attempt {k + 1})")
                        break
                log(f"Row at y={label.y:.0f}: full")
            if i == FEST["max_scrolls"] or not self.scroll_pavilion():
                break
        log("No free seat in this pavilion")
        return False

    # ------------------------------------------------------------------ one pass
    def run_once(self):
        pg = self.page()
        log(f"Page: {pg}")
        if pg == "main":
            if not self.open_activity():
                log("Could not open 金秋赏月 from the main screen")
                return False
            pg = self.page()
            log(f"Page: {pg}")
        if pg == "activity":
            if not self.open_festival():
                log("Could not open 金秋赏月")
                return False
            pg = "festival"
        if pg == "festival":
            if self.seated() and not self.dry_run:
                log("Already seated (我 bubble) -> back to the activity page")
                self.back()
                return True
            if self.seated():
                log("[DRY] already seated (我 bubble); continuing anyway to test the seat search")
            pavs = self.pavilions()
            log(f"{len(pavs)} pavilion(s) on screen")
            n = 0
            while n < len(pavs):
                n += 1
                label = pavs[n - 1]
                if not self.open_pavilion(label, f"pavilion {n}"):
                    log(f"Pavilion {n} did not open")
                    continue
                ok = self.sit(FEST["row_skip_first_pavilion"] if n == 1 else 0)
                self.back()
                time.sleep(1.5)
                if ok or (not self.dry_run and self.seated()):
                    log(f"Seated in pavilion {n}")
                    self.back()
                    return True
                log(f"Pavilion {n} is full, trying the next one")
                if not self.wait_for("ZFestPavilion", 5):
                    log("Festival page did not come back")
                    return False
                pavs = self.pavilions() or pavs   # re-locate: the page may have moved
            log("No free seat in any pavilion on screen")
            self.back()
            return False
        if pg == "pavilion":
            ok = self.sit(FEST["row_skip_first_pavilion"])
            self.back()
            return ok
        log("Not on a festival page: start on the game main screen or the 月满华诞 activity page")
        return False

    def run(self, loop_minutes=0):
        while True:
            try:
                self.run_once()
            except Exception as e:
                log(f"Festival error: {e}")
            if not loop_minutes:
                return
            # return to the main screen so the next pass (and other scripts) start from there
            for _ in range(3):
                if self.page() in (None, "main"):
                    break
                self.back()
                time.sleep(1.5)
            time.sleep(loop_minutes * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry", action="store_true")
    parser.add_argument("--loop", type=int, default=0, help="Repeat every N minutes")
    parser.add_argument("--delay", type=int, default=3)
    parser.add_argument("--debug-shots", action="store_true")
    args = parser.parse_args()
    if args.debug_shots:
        from common import single_find_map
        DEBUG_DIR = os.path.join(os.path.dirname(single_find_map["ZBase"]), "debug")
        os.makedirs(DEBUG_DIR, exist_ok=True)
    time.sleep(args.delay)
    FestivalSit(dry_run=args.dry).run(args.loop)
