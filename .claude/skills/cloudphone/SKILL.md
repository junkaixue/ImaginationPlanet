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
`adb devices` / `cp.sh status` show whether it answers. If not: Tailscale on the Mac and the
phone must be up (`/Applications/Tailscale.app/Contents/MacOS/Tailscale status`), and USB
debugging on in the phone's 开发者选项.

## New or replaced instance (the user does two things by hand)
1. On the phone (through 易览 or the 红手指 app): 设置 → 关于手机 → tap 版本号 7× → 系统 →
   开发者选项 → **USB 调试 on** (红手指 then opens adbd on port 5555).
2. Install Tailscale (APK from `https://pkgs.tailscale.com/stable/`, or the phone's shell
   `curl` once adb works) and log in with the same account as the Mac (scan the QR / open the
   login link on the Mac). Note the 100.x address → write `HOST:5555` to `cloudphone/.serial`.
3. Then, from the Mac: `cloudphone/cp.sh all` (= setup + code --github + app + up). It is
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
  supervisor appends `--adb 127.0.0.1:5555 --delay 0`, which only fortress_fight.py accepts
  today: another script needs an `--adb` option (as in fortress_fight's `__main__`) first.
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
- The panel bubble stays draggable and tappable (small, half transparent and green while a
  script runs; top right by default). The scripts tap by position, so `AdbDevice.before_touch`
  reads the app's windows afresh before every touch (`dumpsys window`, ~0.06 s on the phone) and,
  for a touch on one, prefixes the input command with a `com.ip.panel.HIDE` broadcast (3 s,
  renewed per touch; the panel closes). An open panel over the spot is waited for up to 12 s.
  Scripts send `com.ip.panel.HELLO` every minute (touches and screenshots; the app keeps it 3 min);
  while a script that has not runs, the bubble is touch-through, so older script code never taps
  into it. A bubble parked over a template hides it from screenshots: keep it off the UI the
  scripts read. The top-right default was checked on the saved pages: no template fortress_fight
  reads is there, but zone_explore's resource scan reads the whole map (boxes do show up there),
  so a port of it needs a HIDE before its scan shots. Without the panel app installed (MuMu) AdbDevice skips the window checks.
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
  phone's `restart.sh`: SIGTERM every 10 s (one landing in an update's re-exec is lost) to the
  pid in supervisor.pid if that is a supervisor still (else to a supervisor.py found by its
  command line), then `start.sh`. After 10 min it goes on
  in the background (an hour at most) and the command ends with exit 3: do not `start`/`try`
  until `cp.sh status` answers from the new supervisor.
- 更新 keeps code that came from the Mac and is newer than GitHub's main: `cp.sh code`/`setup`
  write `/ip/local_code` ("<epoch> <commit>"), and an update whose fetched commit is older
  answers 没有更新 (`cp.sh update --force` or `code --github` go back anyway). Push before
  telling the user to tap 更新. An update shows `updating` in /status (the panel: 更新中), runs
  one at a time. It fetches the commit, then the contents of the changed files by a checkout
  into a scratch index and folder under `/ip/tmp` (the clone is blob:none: this is the real
  download), then resets locally. The two downloads give up below 1 KB/s for a minute and are
  tried once more on a network error (GitHub is slow from the phone at times: one fetch takes
  4 s, the next stalls); 更新失败（手机连 GitHub 不稳）is that: tap again later. A killed git's
  `app/.git/index.lock` is removed (at once after a timeout, else when older than 10 min).
- An update whose new supervisor.py does not load (a subprocess loads it as a module: syntax,
  imports, top level) does not re-exec: the old supervisor goes on and only restarts the script
  on its new code (log: "does not load"); a failed exec
  likewise leaves the old one taking starts again.
- Toggling USB debugging (or anything that restarts adbd) may end the supervisor too: then
  浮窗 → 启动服务, or `cp.sh up`.
- `run.sh` uses proot `--kill-on-exit`: whatever a command leaves behind ends with it. The
  supervisor keeps the Alpine adb server (started at its start), so short calls find it.
