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
import time

import numpy as np

from common import single_find, get_center, get_all
from log_helper import log
from zone_explore import ZoneExplore, drag, _code_version

FEST = {
    "row_skip": 1,            # rows to skip from the top (row 1 is never used)
    "row_gap_min": 60,        # logical px below the first row label where row 2 starts
    "scroll_dy": 300,         # pavilion list scroll per step (logical px)
    "max_scrolls": 4,
    "settle": 1.0,
}


class FestivalSit(ZoneExplore):
    def __init__(self, dry_run=False):
        super().__init__(dry_run=dry_run)
        log(f"FestivalSit ready (code={_code_version()})")

    # ------------------------------------------------------------------ pages
    def page(self):
        if single_find("ZFestOccupy") or single_find("ZFestRow"):
            return "pavilion"
        if single_find("ZFestPav1"):
            return "festival"
        if single_find("ZFestTitle"):
            return "activity"
        return None

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

    def free_seats(self):
        """占据 buttons below the first row, top first."""
        rows = get_all("ZFestRow", "Single")
        seats = get_all("ZFestOccupy", "Single")
        if not rows:
            return seats
        top = min(r.y for r in rows)
        rows_sorted = sorted(r.y for r in rows)
        cutoff = rows_sorted[FEST["row_skip"]] - 30 if len(rows_sorted) > FEST["row_skip"] else top + FEST["row_gap_min"]
        return sorted([s for s in seats if s.y > cutoff], key=lambda s: s.y)

    def scroll_pavilion(self):
        rows = get_all("ZFestRow", "Single")
        if not rows:
            return False
        x = max(r.x for r in rows) + 200
        y0 = max(r.y for r in rows)
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
        return float(np.abs(before.astype(int) - after.astype(int)).mean()) > 3.0

    def sit(self):
        for i in range(FEST["max_scrolls"] + 1):
            seats = self.free_seats()
            log(f"Pavilion: {len(seats)} free seat(s) below row 1 on this screen")
            if seats:
                s = seats[0]
                if self.dry_run:
                    log(f"[DRY] would press 占据 at ({s.x:.0f},{s.y:.0f})")
                    return True
                self.click(s.x, s.y, 2.5, "占据")
                # a confirmation may follow; 确认 shares the repair-ok template
                if self.wait_for("ZRepairOk", 3):
                    self.click_button("ZRepairOk", 2, force=True)
                time.sleep(2)
                return True
            if i == FEST["max_scrolls"] or not self.scroll_pavilion():
                break
        log("No free seat found below row 1")
        return False

    # ------------------------------------------------------------------ one pass
    def run_once(self):
        pg = self.page()
        log(f"Page: {pg}")
        if pg == "activity":
            if not self.open_festival():
                log("Could not open 金秋赏月")
                return False
            pg = "festival"
        if pg == "festival":
            if self.seated():
                log("Already seated (我 bubble) -> back to the activity page")
                self.back()
                return True
            pavs = self.pavilions()
            log(f"{len(pavs)} pavilion(s) on screen")
            for n, label in enumerate(pavs, 1):
                if not self.open_pavilion(label, f"pavilion {n}"):
                    log(f"Pavilion {n} did not open")
                    continue
                ok = self.sit()
                self.back()
                time.sleep(1.5)
                if ok or self.seated():
                    log(f"Seated in pavilion {n}")
                    self.back()
                    return True
                log(f"Pavilion {n} is full, trying the next one")
            log("No free seat in any pavilion on screen")
            self.back()
            return False
        if pg == "pavilion":
            ok = self.sit()
            self.back()
            return ok
        log("Not on a festival page: start on the 月满华诞 activity page")
        return False

    def run(self, loop_minutes=0):
        while True:
            try:
                self.run_once()
            except Exception as e:
                log(f"Festival error: {e}")
            if not loop_minutes:
                return
            time.sleep(loop_minutes * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry", action="store_true")
    parser.add_argument("--loop", type=int, default=0, help="Repeat every N minutes")
    parser.add_argument("--delay", type=int, default=3)
    args = parser.parse_args()
    time.sleep(args.delay)
    FestivalSit(dry_run=args.dry).run(args.loop)
