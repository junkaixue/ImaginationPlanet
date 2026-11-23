---
name: cloudphone
description: Set up, update, run and debug the game scripts (fortress_fight.py etc.) inside the Android cloud phone (红手指). Use when the user mentions the cloud phone / 云手机 / 红手指, a new or replaced phone instance, deploying or updating the scripts on the phone, the floating panel (浮窗), or testing a new feature on the phone.
---

# Cloud phone: setup, update, run, debug

The scripts run **inside** the Android cloud phone: an Alpine Linux under proot in
`/data/local/tmp/ip` (no root, no app needed), which drives the game through the phone's own
adbd at `127.0.0.1:5555` (`--adb` mode of `adb_device.py`). A supervisor (`supervisor.py`,
`http://127.0.0.1:8765`, phone-local) runs one script at a time; the floating panel app
(`com.ip.panel`, label 星球脚本) lists the scripts with 开始 / 停止 / 更新. The Mac only
talks to the phone over adb through Tailscale, with `cloudphone/cp.sh`.

Read `cloudphone/README.md` for the layout of the files; this skill is the procedure.
`cloudphone/USER_GUIDE.md` is the user's guide (Chinese): when a change alters what it
describes (panel, scripts, update, restart rules, commands), update it in the same commit.

## Rules
- Answer the user in Chinese.
- The phone is the user's live game account. `--dry` runs stop before the final 袭击; a real
  run spends actions. Ask before starting a non-dry script unless the user asked for it.
- Never pull full-size screenshots over the network (a 1 MB PNG takes ~13 s over the Tailscale
  relay). Use `cp.sh peek` / `cp.sh pull` (JPEG made on the phone, ~1 s).
- Do not type secrets into the phone. The phone's clipboard may hold the user's Tailscale key.
- After every commit, run the code-review skill (global rule) and amend fixes while unpushed.

## Find the phone
`cloudphone/.serial` holds `HOST:5555` (git-ignored); `-s HOST:5555` or `$CP_SERIAL` override.
There are two phones, one per game account: jx (the default, `.serial`) and gs (`-a gs`, address
in `cloudphone/.serial.gs`). Know which one a command goes to before running it.
An account is a config, not an option: the phone's `/ip/account` names it, the supervisor then
lists `cloudphone/phone/scripts.NAME.json` and fortress_fight.py matches
`pics/mac/zone/loadout_standard_NAME.png`; without a name or such a file, the default ones (jx).
A new account-specific value goes into such a per-account file, never into a script option.
`adb devices` / `cp.sh status` show whether it answers. If not: Tailscale on the Mac and the
phone must be up (`/Applications/Tailscale.app/Contents/MacOS/Tailscale status`), and USB
debugging on in the phone's 开发者选项.

## New or replaced instance (the user does two things by hand)
1. On the phone (through 易览 or the 红手指 app): 设置 → 关于手机 → tap 版本号 7× → 系统 →
   开发者选项 → **USB 调试 on** (红手指 then opens adbd on port 5555).
2. Install Tailscale (APK from `https://pkgs.tailscale.com/stable/`, or the phone's shell
   `curl` once adb works) and log in with the same account as the Mac (scan the QR / open the
   login link on the Mac). Note the 100.x address → write `HOST:5555` to `cloudphone/.serial`
   (the gs account's phone: `cloudphone/.serial.gs`).
3. Then, from the Mac: `cloudphone/cp.sh all` (= setup + code --github + app + up; another
   account's phone: `cp.sh -a NAME all`, which also writes `/ip/account`). proot comes through
   the Mac when the phone has none (the gs phone cannot reach raw.githubusercontent.com). It is
   idempotent; rerun any part on failure. `setup` takes ~2 min (downloads go to the phone from
   mirrors in China; the Mac's link is not used for them).
4. Open the game on the phone once and log in (the account can be online on one device only:
   stop MuMu/other phones first, "账号在其他设备登录" otherwise).

## Update the code
- Normal (after the user pushed to GitHub): 浮窗 → 更新, or `cp.sh update` (the supervisor does
  `git fetch --depth 1 origin main && git reset --hard`, then restarts the running script).
  The first time on a phone, `cp.sh code --github` makes `/ip/app` a sparse git checkout.
- Testing unpushed changes: `cp.sh code` copies this working tree (root `*.py`, `pics/mac/zone`
  without pages/ and debug/, and `cloudphone/phone/*`) over the checkout; `cp.sh update` (or
  `code --github`) later puts it back to origin/main.
- Changed `cloudphone/phone/*` (supervisor, scripts.json, ...): `cp.sh code` (or `setup`) then
  `cp.sh restart` (the running script stops and resumes).
- Changed the panel app (`cloudphone/app/src`, manifest): `cp.sh app` (rebuilds when the source
  hash differs from `panel.apk.src`; the first build downloads ~150 MB of Android build tools
  into `cloudphone/app/.sdk`). Commit `panel.apk` + `panel.apk.src` with the source change: 更新
  installs a changed `panel.apk` on the phone by itself. Keep the supervisor's replies readable
  by older panels (and scripts.json by older supervisors): add fields, do not reshape.
- New script entry for the panel: add a line to `cloudphone/phone/scripts.json`, a flat list
  `[{"group", "id", "name", "args", "restart"?}]` (flat so that every supervisor and panel
  version reads it; ids unique across the file; dry runs are never restarted). Groups follow the kinds of features in the repo: 星际探险 (fortress_fight,
  zone_explore), 跑图日常 (imaginationplanet/running, red_pack), 战斗 (boss_fight, tower_fight,
  fight), 活动 (festival_sit, the card games, star_pick_up, black_market_finder). The panel shows
  one group at a time; keep a group to the scripts that run on the phone. The
  supervisor appends `--adb 127.0.0.1:5555 --delay 0`, which fortress_fight.py and
  boss_fight.py (its device flow is world_boss.py) accept today: another script needs an
  `--adb` option (as in fortress_fight's `__main__`) first.
- 更新 also copies `cloudphone/phone/*` to /ip (and restarts the supervisor when
  supervisor.py changed); `setup.sh`/`run.sh` changes need `cp.sh setup` from the Mac.

## Develop and test a feature on the phone
1. Change the code on the Mac; quick offline checks with saved screenshots where possible.
2. `cp.sh code`, then a test run: `cp.sh try fortress_fight.py -oxz 41032 --dry --debug-shots`.
   `try` stops the supervisor's script first (two scripts must never drive the game), runs
   the command in the foreground (`TRY_TIMEOUT`, default 600 s) and starts the stopped script
   again afterwards. Never run a script with `cp.sh sh` while the supervisor runs one. A dry run
   still repairs fleets for real (修理舰队); it stops before the final 袭击.
3. Look at the screen: `cp.sh peek [scale]` → JPEG path; read it. Debug shots the script saved:
   `cp.sh pull app/pics/mac/zone/debug/NAME.png`. List them with `cp.sh sh "ls app/pics/mac/zone/debug | tail"`.
4. One-off probes: write a small Python file into the phone's app folder (via `cp.sh sh` heredoc
   or `adb push`) that does `click.use_device(AdbDevice("127.0.0.1:5555"))` first, then imports
   fortress_fight; replace `click._device.tap/drag` with a function that raises when the probe
   must not touch the game.
5. Manual taps for exploring: `adb -s SERIAL shell input tap X Y` in **device px** (a peek at
   scale 0.5 → multiply by 2). Script coordinates are reference logical px: device = logical ×
   2 × (screen width / 993.8).
6. Commit, review, and tell the user to push; then 浮窗 → 更新 on the phone.

## Facts that cost time to find
- 红手指 blocks installing Termux (`INSTALL_FAILED_VERIFICATION_FAILURE`); UserLAnd's 2021
  build cannot fetch its app list. proot + Alpine under the adb shell user works.
- The phone (Android 13, 720×1280) shell has `curl`, `wget`, `nc`; `su` is not reachable from
  adb. The Alpine adb client is accepted by the phone's adbd without a prompt.
- Screenshots inside the phone: ~0.3 s. Templates are the Mac set (`pics/mac/zone`); screenshots
  are scaled to the Mac reference width 993.8 px (`adb_device.REF_WIDTH`), so no template
  needs recapturing; all checked ones score ≥ 0.98.
- Each map zoom level keeps its own view; after a new login the 75% map opens on our base, and
  `bring_fortress_into_view` searches from there by colour (暗焰要塞 has the same outline).
- The panel bubble (small, half transparent and green while a script runs; top right by default,
  draggable anywhere) is out of the script's way by time, not by place: before every look at the
  screen `AdbDevice.hide_for_look` sends `com.ip.panel.HIDE` (10 s, the app's limit; renewed
  with 3 s left), and when the script goes idle (`FortressFight.nap`) `show_overlay` brings the
  bubble back. Under the bubble a button is not seen: a guard's 袭击 button was, and the script
  logged "opened nothing" 129 times in a night. While hidden, taps read the app's windows only
  every 10 s; a bubble that shows all the same (the app restarted) is hidden in the tap's own
  shell as before. An open panel is waited for up to 12 s.
  Scripts send `com.ip.panel.HELLO` every minute (touches and screenshots; the app keeps it 3 min);
  while a script that has not runs, the bubble is touch-through, so older script code never taps
  into it. A script that waits by its own sleeps (zone_explore's loop) has to call
  `show_overlay` there too when it is ported. Without the panel app installed (MuMu) AdbDevice
  skips all of this.
- Speed on the phone: screenshots are raw files through the folder both sides see (`/ip/tmp`,
  `shot.<pid>.raw`, one per process, removed before every capture and at exit; 0.23 s, PNG by adb
  0.4-0.6 s), a `burst` goes out in pieces of 6 s, one shell command each (within one HIDE and
  far from the adb timeout), and `fortress_fight --pace` (0.6 by default when the script runs on
  the phone) scales the fixed waits after taps and the poll while waiting. `pause()` is for
  those only. What is the game's own time stays in seconds (`time.sleep`, or a window with a
  deadline): a fade or a page that draws late before a single look, and how long a tap's effect
  is looked for before the tap is repeated (`PRESS_WAIT`, `CONFIRM_WAIT`; counted in looks they
  shrink with the pace and with faster screenshots). The fade after buying actions broke at 0.6
  this way. A burst in one shell command has its taps 0.1 s apart, so it is no safer than one
  tap against a page that is still settling: fine where the effect is checked and retried (tabs)
  or where many taps are spare (removal slots), not for a button whose effect nobody looks at.
  一键配队 was one: its three taps fell into a settling page once in 12 swaps, the fleet went out
  without the gear and came back with 0% (never in 204 swaps with single taps). Its taps, and
  those on an artifact's preview, are 0.35 s apart again (`UNCHECKED_TAP_GAP`), and a target
  whose loadout does not match the standard after 一键配队 gets it once more, then is not sent
  out: the swap stays in hand (holder stripped again, equipped again on the next pass; given up
  after 3 passes with the gear put back). To judge a pace, compare per swap: "page did not
  open", "no effect yet", "not shown after tap", "Attack not launched; next pass", and above all
  the loadout score after a swap (0.94 = all gear moved; below 0.9 the swap failed).
- Swap mode attacks every bright guard, whatever its level: nothing is left out (the user's
  rule; a level limit for it was tried and taken out again). Guard levels and ranks belong to
  the ordered mode only: do not carry them over to the swap mode (its log shows no levels
  either). A fleet came back with 0% twice: once with the whole gear on it, once sent out
  without the gear (the 一键配队 case above; the loadout score of the swap before tells the two
  apart). Both times it was under repair when the script looked next, without the script having
  started that (about 45 min); when it is the gear holder the gear is on it and the script
  waits ("Fleet N (best gear) is repairing; waiting"). When the page shows nothing to attack the
  script looks again every 30 s (`POLL`, not paced: the whole page is walked for it). A run buys
  at most 10 packs of actions (`MAX_PACKS_PER_RUN`); after that it attacks only as actions
  regrow ("Action purchase prompt -> cancel" in the log, one attack in 45 min): looks stuck, is
  the limit.
- World boss (战斗 group, `boss_fight.py --adb` = world_boss.py): the boss is there 11:00-13:00
  and 19:00-21:00 phone time only (the phone's clock is the Mac's PST + 16 h), so its pages can
  be seen and tested only then; the pages are saved in `pics/mac/zone/pages/worldboss/`. Main
  page 星际玩法 -> 星际冒险 list -> 世界BOSS 立即前往 -> 挑战 -> the fight (50 dice, a tap on
  the dice button is one throw) -> with no dice the button opens 购买确认 (sells dice; one
  button; closed by a tap beside it): the end -> the gift box (one gift a tap, 恭喜获得, the
  box goes with the last) -> 回家. The strong hit's popup (美食星系的帮助) has 免费 x2, 购买 20
  x3, 购买 100 x4: default 免费, `-d` the rightmost 购买; one tap is enough (the desktop
  script's tap below the button first is not needed).
- Dice are never bought, by a script or by hand while testing (the user's rule). A text-only
  "购买" template also matches the main page's 更多骰子 popup (0.95), and the main page's dice
  button is where the fight's is: tap a 购买 only on a page identified by something else (the
  fight's 回家, a 免费 in the same row).
- Templates with scenery behind them fail across accounts and bosses; cut the text or the
  button alone, on the phone, at the reference scale (`AdbDevice.screenshot()` saved as PNG,
  boxes in its px). A Windows template (`pics/*.png`) enlarged 1.31 times matches the
  reference screenshot (0.97-0.99): good for a first look, replaced by a real cut before a
  commit. OCR (`ocr_digits`) misreads this game's button font ("50" as "20", "20" as "90"):
  do not decide by it there.
- After a phone reboot the supervisor is gone: 浮窗 → 启动服务 starts it through the app's own
  adb client (LocalAdb.java); it resumes the script that was running (state.json).
- Debug shots accumulate in `/ip/app/pics/mac/zone/debug`; clear with `cp.sh sh "rm app/pics/mac/zone/debug/*"`.
- Stops are graceful: the supervisor SIGTERMs the script (not its adb children) and waits up to
  240 s; fortress_fight ends at a stop point (`stop_point`, `nap`), a gear swap in hand finished or
  abandoned (gear put back). A SIGKILL mid-swap leaves the gear loose; the next swap run sees no
  holder twice and gives 一键配队 to the last holder (`fortress_gear.json`, kept over a fresh
  clone with the other `STATE_FILES` in cp.sh) when it is in port (`recover_loose_gear`). Once
  the script has ended, the rest of its process group is killed (adb calls a script without a
  graceful stop left running). Code older than this has no stop points: restart it only while
  its log shows it waiting; `cp.sh code`/`setup` auto-restart only a supervisor whose /status
  has `stopping` (graceful), and print the manual advice otherwise. `cp.sh restart` runs the
  checkout's `phone/restart.sh` from the phone's `tmp/` (the phone's own copy stays): SIGTERM every 10 s (one landing in an update's re-exec is lost) to the
  pid in supervisor.pid if that is a supervisor still (else to a supervisor.py found by its
  command line), then `start.sh`. After 10 min it goes on
  in the background (an hour at most) and the command ends with exit 3: do not `start`/`try`
  until `cp.sh status` answers from the new supervisor.
- 更新 keeps code that came from the Mac and is newer than GitHub's main: `cp.sh code`/`setup`
  write `/ip/local_code` ("<epoch> <commit>"), and an update whose fetched commit is older
  answers 没有更新 (`cp.sh update --force` or `code --github` go back anyway). Push before
  telling the user to tap 更新. An update shows `updating` in /status (the panel: 更新中), runs
  one at a time. When git cannot reach github.com for the network (throttled from some cloud
  phones: the TLS handshake passes, then no data; `curl https://github.com/` hangs while
  `https://api.github.com/` answers in 0.3 s), the update goes through api.github.com by
  itself (`update_by_api`: newest commit, its file list, only the files whose blob sha differs,
  each checked, then moved in; `/ip/api_version` names the commit and git's HEAD of then, label
  `+api` while HEAD is still that one), and straight there for the next 6 hours
  (`/ip/git_blocked`, lifted when the API cannot do it); `cp.sh update --api` asks for it. 60 requests an hour without a
  login, 50 files an update: beyond that push from the Mac (`cp.sh code`). By git it fetches
  the commit, then the contents of the changed files by a checkout
  into a scratch index and folder under `/ip/tmp` (the clone is blob:none: this is the real
  download), then resets locally. The two downloads give up below 1 KB/s for a minute and are
  tried once more on a network error (GitHub is slow from the phone at times: one fetch takes
  4 s, the next stalls); 更新失败（手机连 GitHub 不稳）is that: tap again later. A step out of
  time gets SIGTERM first (git removes its locks), and the next update clears a cut-off one's
  scratch folders and the `*.lock` files in `.git` when no git runs on the phone (only a
  running git holds a lock; with one at work, a fetch's background maintenance included, all
  stay, and so does one that is not the file seen at the look any more). With nothing new
  (code, phone files, panel, supervisor) the answer is 已是最新 and the script is not
  restarted; a new supervisor.py that failed its load check is remembered and counts as
  nothing new until it changes. A check without a verdict (out of time, killed, out of
  memory, not started: the phone, not the file) is made again by the next update; the
  third one that ran out of time or was killed, for the same file within a day, counts as
  the verdict. When the new supervisor does not start, the running script is started again
  only if that update changed its code or a scripts list, and an automatic start that was
  refused meanwhile (after a crash) is made then. The code
  label in /status ends in ` +local` for code from the Mac and ` +?` when git status failed
  or gave no answer. `cp.sh code --github` hands over to a running supervisor (`/update?force=1`): it
  waits while that is busy (更新 under way, restarting; 15 min at most), exits 1 unless the
  answer is "updated to", and refuses when a supervisor process runs but does not answer:
  one writer of the checkout.
- An update whose new supervisor.py does not load (a subprocess loads it as a module: syntax,
  imports, top level) does not re-exec: the old supervisor goes on and only restarts the script
  on its new code (log: "does not load"); a failed exec
  likewise leaves the old one taking starts again.
- `adb install` of the panel app is refused now and then with
  `INSTALL_FAILED_VERIFICATION_FAILURE: com.ip.panel is not allowed to be installed` (the cloud
  phone's install check; the next try passes): `cp.sh app` and the supervisor's own install
  try up to three times (the supervisor's install tries within 6 min, 11.5 with a reinstall
  after an uninstall, plus a few short adb calls around them: its re-exec waits for that, so
  a `cp.sh restart` meanwhile may end with exit 3).
- Toggling USB debugging (or anything that restarts adbd) may end the supervisor too: then
  浮窗 → 启动服务, or `cp.sh up`.
- `run.sh` uses proot `--kill-on-exit`: whatever a command leaves behind ends with it. The
  supervisor keeps the Alpine adb server (started at its start), so short calls find it.
