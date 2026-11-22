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
  into `cloudphone/app/.sdk`). Commit `panel.apk` + `panel.apk.src` with the source change.
- New script entry for the panel: add it to `cloudphone/phone/scripts.json`
  (`{"id", "name", "args"}`, optional `"restart": false`; dry runs are never restarted). The
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
- The panel bubble lets touches through while a script runs (the scripts tap by position and
  would hit it); controls are then in the notification (打开面板 / 停止) or the app icon.
- After a phone reboot the supervisor is gone: 浮窗 → 启动服务 starts it through the app's own
  adb client (LocalAdb.java); it resumes the script that was running (state.json).
- Debug shots accumulate in `/ip/app/pics/mac/zone/debug`; clear with `cp.sh sh "rm app/pics/mac/zone/debug/*"`.
- Toggling USB debugging (or anything that restarts adbd) may end the supervisor too: then
  浮窗 → 启动服务, or `cp.sh up`.
- `run.sh` uses proot `--kill-on-exit`: whatever a command leaves behind ends with it. The
  supervisor keeps the Alpine adb server (started at its start), so short calls find it.
