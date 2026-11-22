"""Runs the game scripts inside the cloud phone and is driven by the floating panel app (and by
cloudphone/cp.sh on the Mac) over http://127.0.0.1:8765 (this phone only).

    GET  /scripts         [{"id", "name", "group"}] from scripts.json (the panel groups them)
    GET  /status          what runs, since when, the last log lines, the code version
    GET  /log?n=200       the running (or last) script's log tail, text
    POST /start?id=ID     stop what runs, bring the game to the front, start ID
    POST /stop            stop what runs
    POST /update          fetch the newest code from GitHub (a git checkout in /ip/app), copy its
                          cloudphone/phone files to /ip, start the running script again on it,
                          the supervisor itself when its code changed, and install a changed
                          panel app. Refused when the phone has newer code from the Mac
                          (cp.sh code, not pushed yet), unless ?force=1

One script runs at a time (one game). A script that fails (ends by itself with an error exit,
e.g. fortress_fight's "errors keep coming") is started again after RESTART_WAIT s, at most
MAX_RESTARTS times an hour; one that finishes (exit 0) is not, nor a dry run (its "restart":
false in scripts.json, the default for args with --dry). The running script is remembered in
state.json: a supervisor started again (cp.sh restart, or after a reboot by the panel app)
starts it again.
"""
import filecmp
import hashlib
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

HOME = "/ip"
APP = f"{HOME}/app"
PHONE_FILES = f"{APP}/cloudphone/phone"     # the repo's copy of the files in HOME
PANEL_APK = f"{APP}/cloudphone/app/panel.apk"
PANEL_SHA = f"{HOME}/panel.apk.sha"       # the sha1 of the panel app installed last (cp.sh app / update)
SCRATCH = "update."                       # prefix of an update's scratch folders in HOME/tmp
LOCAL_CODE = f"{HOME}/local_code"         # "<epoch> <commit>": code or phone files came from the Mac (cp.sh
                                          # code / setup) and are that new; no update to an older commit
# what of the repo the phone checks out (cp.sh code_github has the same list): the root scripts,
# the zone templates, the phone files and the panel app
SPARSE = ["/*.py", "/pics/mac/zone/*", "!/pics/mac/zone/pages/", "!/pics/mac/zone/debug/",
          "/cloudphone/phone/", "/cloudphone/app/panel.apk"]
LOGS = f"{HOME}/logs"
STATE = f"{HOME}/state.json"
SCRIPTS = f"{HOME}/scripts.json"
SUPERVISOR_PID = f"{HOME}/supervisor.pid"
SCRIPT_PID = f"{HOME}/script.pid"   # the running script's process group, for a supervisor started again
PORT = 8765
DEVICE = "127.0.0.1:5555"           # the phone itself, through its own adbd
GAME = "com.tfgame.planet"
EXTRA_ARGS = ["--adb", DEVICE, "--delay", "0"]
RESTART_WAIT = 60
MAX_RESTARTS = 5                    # per hour
STOP_GRACE = 240                    # seconds a script gets after SIGTERM to end at a safe point (a gear
                                    # swap finished or undone, the attack in hand sent), then SIGKILL
ADB_TIMEOUT = 30


def log(msg):
    print(time.strftime("[%Y-%m-%d %H:%M:%S] ") + msg, flush=True)


_logged = set()


def kill_group(pgid):
    """SIGKILL to a script's process group (it leads its own); no error when it is empty."""
    try:
        os.killpg(pgid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        pass


def log_once(msg):
    if msg not in _logged:
        _logged.add(msg)
        log(msg)


def sha1(path):
    try:
        with open(path, "rb") as f:
            return hashlib.sha1(f.read()).hexdigest()
    except OSError:
        return None


LOADED = sha1(os.path.abspath(__file__))    # the code this process runs (an update re-execs when it differs)
# loads a supervisor.py as a module, main() not called (nothing bound or started): exit 0 when it loads
LOAD_CHECK = ("import importlib.util as u, sys\n"
              "s = u.spec_from_file_location('supervisor_check', sys.argv[1])\n"
              "s.loader.exec_module(u.module_from_spec(s))")


def adb(*args, timeout=ADB_TIMEOUT):
    """stdout of `adb -s DEVICE <args>`; raises when adb fails or the device is not there."""
    r = subprocess.run(["adb", "-s", DEVICE] + list(args), capture_output=True, timeout=timeout)
    if r.returncode != 0:
        raise RuntimeError(f"adb {' '.join(args[:2])}: {(r.stderr or r.stdout).decode('utf-8', 'replace').strip()}")
    return r.stdout.decode("utf-8", "replace")


def connect_adb():
    """This Linux's adb server learns the phone's adbd by `adb connect` (after a reboot it only
    knows emulator-5554 from its port scan). True when the device answers."""
    try:
        subprocess.run(["adb", "start-server"], capture_output=True, timeout=ADB_TIMEOUT)
        subprocess.run(["adb", "connect", DEVICE], capture_output=True, timeout=ADB_TIMEOUT)
        return adb("get-state").strip() == "device"
    except Exception as e:
        log(f"adb connect {DEVICE}: {e}")
        return False


def cmdline(pid):
    try:
        with open(f"/proc/{pid}/cmdline", "rb") as f:
            return f.read().replace(b"\0", b" ").decode("utf-8", "replace")
    except OSError:
        return ""


class Supervisor:
    def __init__(self):
        self.lock = threading.RLock()       # state; held only briefly
        self.start_lock = threading.Lock()  # one start at a time (it may wait for the game)
        self.proc = None
        self.script = None          # the script dict that runs (or ran last)
        self.since = None
        self.gen = 0                # counts starts: a restart only for the run that failed
        self.stopping = False
        self.stop_count = 0         # stops asked for by hand: a start waiting for the game gives way
        self.restarting = False     # the supervisor itself is going away (update / cp.sh restart)
        self.exit_instead = False   # a SIGTERM came while an update re-exec waited: exit, do not exec
        self.term_lock = threading.RLock()  # restarting and exit_instead change together (SIGTERM
                                            # handler and re-exec thread: no SIGTERM goes unseen)
        self.panel_note = None      # the outcome of the last panel app install (status)
        self.updating = None        # what an update under way is doing (shown in the panel), else None
        self.code_changed = False   # an update changed the code and the running script is not on it yet
        self.update_lock = threading.Lock()     # one update at a time
        self.restarts = []          # times of automatic restarts this hour
        self.logfile = None
        self.last_exit = None

    # ------------------------------------------------------------------ scripts
    @staticmethod
    def scripts():
        """scripts.json: a list of {"group", "id", "name", "args", "restart"?}; the panel shows
        one group (kind of feature) at a time. Kept a flat list so that older supervisors and
        panels read it too. Entries without an id or args, and a second use of an id (ids are
        global: state.json, logs, /start), are skipped with a log line."""
        with open(SCRIPTS, encoding="utf-8-sig") as f:
            data = json.load(f)
        if isinstance(data, dict):          # (the grouped form of 847be53)
            data = [dict(s, group=g.get("name", "")) for g in data.get("groups") or []
                    if isinstance(g, dict) for s in g.get("items") or [] if isinstance(s, dict)]
        out, seen = [], set()
        for s in data if isinstance(data, list) else []:
            if not isinstance(s, dict) or not s.get("id") or not isinstance(s.get("args"), list):
                log_once(f"scripts.json: skipped {s!r} (needs an id and args)")
            elif s["id"] in seen:
                log_once(f"scripts.json: id {s['id']} used twice; the second one is skipped")
            else:
                seen.add(s["id"])
                out.append(s)
        return out

    def find(self, sid):
        return next((s for s in self.scripts() if s["id"] == sid), None)

    @staticmethod
    def restartable(script):
        return script.get("restart", "--dry" not in script["args"])

    @staticmethod
    def code_version():
        if os.path.isdir(f"{APP}/.git"):
            git = ["git", "--no-optional-locks", "-C", APP]    # (no index.lock against an update)
            r = subprocess.run(git + ["log", "-1", "--format=%h %cd", "--date=format:%m-%d %H:%M"],
                               capture_output=True, text=True)
            dirty = subprocess.run(git + ["status", "--porcelain", "-uno"], capture_output=True, text=True)
            return r.stdout.strip() + (" +local" if dirty.stdout.strip() else "")
        return "local copy"

    # ------------------------------------------------------------------ game
    @staticmethod
    def game_in_front():
        out = adb("shell", "dumpsys", "window")
        return any(GAME in line for line in out.splitlines() if "mCurrentFocus" in line)

    def ensure_game(self):
        """Bring the game to the front (a script started on the launcher would wait forever).
        A failure is logged; the script's own adb connects by itself."""
        try:
            if not connect_adb():
                log("the phone's adbd does not answer (USB 调试 on?)")
                return
            if self.game_in_front():
                return
            log("The game is not in front: starting it")
            adb("shell", "monkey", "-p", GAME, "-c", "android.intent.category.LAUNCHER", "1")
            for _ in range(30):
                time.sleep(2)
                if self.game_in_front():
                    time.sleep(15)      # the main screen takes a while after the window shows
                    return
            log("The game did not come to the front")
        except Exception as e:
            log(f"could not check the game: {e}")

    # ------------------------------------------------------------------ run / stop
    def start(self, sid, remember=True, manual=True):
        if self.restarting:
            return "服务正在重启，稍后再试"
        script = self.find(sid)
        if script is None:
            return f"no script {sid}"
        stops = self.stop_count
        with self.start_lock:
            if not manual and self.saved_running() != sid:
                return "stopped meanwhile"  # (an automatic start no longer wanted: nothing is stopped)
            self.stop(remember=False)
            self.ensure_game()              # (outside self.lock: status and stop stay quick)
            with self.lock:
                if self.restarting or self.stop_count != stops or (not manual and self.saved_running() != sid):
                    return "stopped meanwhile"
                os.makedirs(LOGS, exist_ok=True)
                self.logfile = f"{LOGS}/{sid}.log"
                with open(self.logfile, "a", encoding="utf-8") as out:
                    out.write(time.strftime(f"\n===== %Y-%m-%d %H:%M:%S start {script.get('name', sid)} "
                                            f"({self.code_version()})\n"))
                    out.flush()
                    self.proc = subprocess.Popen(["python3", "-u"] + script["args"] + EXTRA_ARGS, cwd=APP,
                                                 stdout=out, stderr=subprocess.STDOUT, start_new_session=True)
                self.gen += 1
                self.script, self.since, self.stopping, self.last_exit = script, time.time(), False, None
                self.code_changed = False       # (it runs on the code that is there now)
                if manual:
                    self.restarts = []      # a start by hand gives the automatic restarts a new budget
                with open(SCRIPT_PID, "w") as f:
                    f.write(str(self.proc.pid))
                log(f"started {sid} (pid {self.proc.pid})")
                if remember:
                    self.save_state(sid)
                threading.Thread(target=self.watch, args=(self.proc, self.gen), daemon=True).start()
        return "ok"

    def stop(self, remember=True):
        """SIGTERM to the script itself (not its adb children, whose calls must not break
        mid-step): it ends at its next safe point, a gear swap finished or undone first. SIGKILL
        to the whole group after STOP_GRACE, and once the script has ended to what is left of the
        group (a script without a graceful stop dies at once, its adb call under way does not).
        The wait holds no lock (status stays live)."""
        with self.lock:
            proc, self.stopping = self.proc, True
            sid = self.script["id"] if self.script else None
            if remember:
                self.stop_count += 1
                self.save_state(None)
        try:
            if proc is not None and proc.poll() is None:
                log(f"stopping {sid}: it ends after the step in hand (at most {STOP_GRACE} s)")
                proc.send_signal(signal.SIGTERM)    # (no error when it has just ended by itself)
                try:
                    proc.wait(STOP_GRACE)
                except subprocess.TimeoutExpired:
                    log(f"{sid} did not end in {STOP_GRACE} s: killed")
                    kill_group(proc.pid)
                    proc.wait()
                kill_group(proc.pid)            # (usually nobody is left)
                log(f"stopped {sid}")
        finally:
            with self.lock:
                if self.proc is proc:
                    self.proc = None
                    if os.path.exists(SCRIPT_PID):
                        os.remove(SCRIPT_PID)
        return "ok"

    @staticmethod
    def stop_leftover():
        """A script started by an earlier supervisor (killed without stopping it) still runs:
        stop it, or two scripts would drive the game. The pid is checked to be a script still
        (after a reboot it may belong to anything); it gets the same graceful stop."""
        try:
            with open(SCRIPT_PID) as f:
                pid = int(f.read().strip())
            # (after a reboot the pid may be anyone's, this supervisor's own included: a script
            # leads its own process group and is not a supervisor)
            line = cmdline(pid)
            if pid != os.getpid() and os.getpgid(pid) == pid and "python3" in line and "supervisor.py" not in line:
                log(f"stopping a script left running (pid {pid})")
                os.kill(pid, signal.SIGTERM)
                for _ in range(STOP_GRACE):
                    if "python3" not in cmdline(pid):
                        break
                    time.sleep(1)
                kill_group(pid)                 # (after STOP_GRACE, or what it left behind)
        except (OSError, ValueError):
            pass
        if os.path.exists(SCRIPT_PID):
            os.remove(SCRIPT_PID)

    def watch(self, proc, gen):
        code = proc.wait()
        with self.lock:
            if gen != self.gen or self.stopping:
                return              # replaced or stopped on purpose
            self.last_exit, self.proc = code, None
            sid = self.script["id"]
            if code == 0 or not self.restartable(self.script):
                log(f"{sid} ended (exit {code}); not started again")
                self.save_state(None)
                return
            now = time.time()
            self.restarts = [t for t in self.restarts if now - t < 3600]
            if len(self.restarts) >= MAX_RESTARTS:
                log(f"{sid} failed (exit {code}); {MAX_RESTARTS} restarts this hour already: left stopped")
                self.save_state(None)
                return
            self.restarts.append(now)
        log(f"{sid} failed (exit {code}); starting it again in {RESTART_WAIT} s")
        time.sleep(RESTART_WAIT)
        with self.lock:
            if gen != self.gen or self.stopping:
                return              # started or stopped by hand meanwhile
        self.start_retrying(sid)

    def start_retrying(self, sid):
        """An automatic start (restart, resume): an error (adb hanging, a broken scripts.json)
        is logged and the start tried again later instead of being dropped."""
        for wait in (30, 60, 120, 300, 600):
            try:
                self.start(sid, manual=False)
                return
            except Exception as e:
                log(f"could not start {sid}: {e}; trying again in {wait} s")
                time.sleep(wait)
                if self.saved_running() != sid:
                    return          # stopped or replaced by hand meanwhile
        log(f"giving up starting {sid}")

    # ------------------------------------------------------------------ update
    def update(self, force=False):
        """The code of GitHub's main. One at a time; `updating` tells the panel what it is at (the
        fetch may take minutes). Code that came from the Mac and is newer than GitHub's commit
        (not pushed yet) is kept unless `force`: the update would put older code back."""
        if not os.path.isdir(f"{APP}/.git"):
            return "the code is a copy from the Mac (cp.sh code); run `cp.sh code --github` once"
        if not self.update_lock.acquire(blocking=False):
            return "已经在更新了：" + (self.updating or "")
        try:
            if self.restarting:             # (the re-exec of the last update waits for the script: a
                return "服务正在重启，稍后再点更新"     # new supervisor.py now would start unchecked)
            return self.update_locked(force)
        finally:
            self.updating = None
            self.update_lock.release()

    @staticmethod
    def local_code_time():
        try:
            with open(LOCAL_CODE) as f:
                return int(f.read().split()[0])
        except (OSError, ValueError, IndexError):
            return None

    # (what curl and git say when the network is the trouble; a certificate problem, which names
    # ssl too, is the phone's clock or its CA files and does not pass by itself)
    NETWORK_ERRORS = ("too slow", "timed out", "timeout", "could not resolve", "failed to connect",
                      "couldn't connect", "connection", "recv failure", "send failure", "empty reply",
                      "early eof", "rpc failed", "hung up", "unexpected disconnect", "ssl", "tls", "http/2")

    def git_step(self, args, timeout, env=None):
        """One git command of an update in the checkout: (ok, output). A download that stalls
        ends after a minute (lowSpeed) instead of holding the update. One that outlasts
        `timeout` gets SIGTERM, on which git removes its lock files itself; SIGKILL only when
        that does not end it. Both go to its whole group (its transport helper holds the output
        pipe too)."""
        git = ["git", "-C", APP, "-c", "http.lowSpeedLimit=1000", "-c", "http.lowSpeedTime=60"]
        proc = subprocess.Popen(git + args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=env,
                                start_new_session=True)
        try:
            out, _ = proc.communicate(timeout=timeout)
            return proc.returncode == 0, out.strip() or f"git {args[0]}: exit {proc.returncode}"
        except subprocess.TimeoutExpired:
            for sig in (signal.SIGTERM, signal.SIGKILL):
                try:
                    os.killpg(proc.pid, sig)
                except (ProcessLookupError, PermissionError):
                    pass
                try:
                    proc.communicate(timeout=15)
                    break
                except subprocess.TimeoutExpired:
                    continue
            if sig == signal.SIGKILL:
                self.clear_locks()          # (it could not remove its own: the next try needs them gone)
            return False, f"git {args[0]}: {timeout // 60} 分钟没做完"

    def network_trouble(self, out):
        """The output of a failed download step tells of the network (or it ran out of time).
        git's error lines (fatal:, error:) decide, all lines when there is none: one about a
        certificate rules the network out (the lines after it only follow from it), a warning
        or hint that names one does not."""
        if "分钟没做完" in out:
            return True
        lines = out.lower().splitlines()
        errors = [line for line in lines if line.lstrip().startswith(("fatal:", "error:"))] or lines
        return (not any("certificate" in line for line in errors)
                and any(k in line for line in errors for k in self.NETWORK_ERRORS))

    def retried(self, what, step):
        """A download step `step() -> (ok, output)`, tried once more when the network failed it
        (GitHub is slow from the phone at times); `what` is shown in the panel meanwhile."""
        for attempt in (1, 2):
            self.updating = what + ("，第 2 次尝试" if attempt == 2 else "")
            ok, out = step()
            if ok:
                return True, out
            log(f"update: {what}: try {attempt} failed: " + out.replace("\n", " | "))
            if not self.network_trouble(out):
                break                       # (a second try would fail the same way)
        return False, out

    def download_failed(self, step, out):
        if self.network_trouble(out):
            return "更新失败（手机连 GitHub 不稳，稍后再点）: " + out
        return f"更新失败（{step}）: " + out

    def scratch_checkout(self):
        """The contents of the files that changed, downloaded by a checkout of FETCH_HEAD into a
        scratch index and folder (the checkout itself holds no contents it does not need:
        blob:none). Cut off or failed, nothing of the real checkout is half done, and the reset
        after it needs no network. A scratch of its own for every try."""
        with tempfile.TemporaryDirectory(dir=f"{HOME}/tmp", prefix=SCRATCH) as scratch:
            os.mkdir(f"{scratch}/tree")
            env = dict(os.environ, GIT_DIR=f"{APP}/.git", GIT_INDEX_FILE=f"{scratch}/index",
                       GIT_WORK_TREE=f"{scratch}/tree")
            return self.git_step(["read-tree", "--reset", "-u", "FETCH_HEAD"], 300, env)

    @staticmethod
    def git_at_work():
        """A git runs on this phone that may hold a lock: any git (cp.sh code --github by hand,
        the maintenance a fetch leaves running in the background) but the lock-free ones of
        code_version (--no-optional-locks; the panel asks for the status every few seconds)."""
        try:
            pids = [p for p in os.listdir("/proc") if p.isdigit()]
        except OSError:
            return False
        for pid in pids:
            try:
                with open(f"/proc/{pid}/cmdline", "rb") as f:
                    argv = f.read().decode("utf-8", "replace").split("\0")
            except OSError:
                continue                    # (gone meanwhile)
            name = os.path.basename(argv[0])
            if (name == "git" or name.startswith("git-")) and "--no-optional-locks" not in argv:
                return True
        return False

    def clear_locks(self):
        """The lock files a killed git left in the checkout's .git (index.lock, shallow.lock, a
        ref's, the config's, ...). Only a running git holds a lock: with none at work every lock
        there is stale and goes, whatever its age; with one at work all stay. (A git that starts
        meanwhile fails on a stale lock, it does not take it over; a lock that appears after the
        look here is that git's and stays.)"""
        seen = time.time()
        locks = [os.path.join(root, name) for root, _, names in os.walk(f"{APP}/.git")
                 for name in names if name.endswith(".lock")]
        if not locks or self.git_at_work():
            return
        for lock in locks:
            try:
                if os.path.getmtime(lock) >= seen:
                    continue                # (taken after the look, by a git that started since)
                os.remove(lock)
                log(f"update: removed a stale {os.path.relpath(lock, APP)}")
            except OSError:
                pass                        # (gone meanwhile)

    def clear_leftovers(self):
        """What an update that was cut off left (the supervisor killed, the phone rebooted): its
        scratch folders and git's locks."""
        tmp = f"{HOME}/tmp"
        os.makedirs(tmp, exist_ok=True)
        for name in os.listdir(tmp):
            if name.startswith(SCRATCH):
                shutil.rmtree(f"{tmp}/{name}", ignore_errors=True)
        self.clear_locks()

    def update_locked(self, force):
        self.clear_leftovers()
        ok, out = self.retried("正在从 GitHub 拉代码（可能要几分钟）",
                               lambda: self.git_step(["fetch", "-q", "--depth", "1", "origin", "main"], 300))
        if not ok:
            return self.download_failed("拉代码", out)
        r = subprocess.run(["git", "-C", APP, "log", "-1", "--format=%ct %h %cd", "--date=format:%m-%d %H:%M",
                            "FETCH_HEAD"], capture_output=True, text=True)
        local = self.local_code_time()
        try:
            fetched_time, fetched = int(r.stdout.split()[0]), r.stdout.split(None, 1)[1].strip()
        except (ValueError, IndexError):
            fetched_time, fetched = None, "?"
        if not force and local is not None and fetched_time is not None and fetched_time < local:
            log(f"update: GitHub's main ({fetched}) is older than the code from the Mac on this phone: kept")
            return (f"没有更新：GitHub 上的代码（{fetched}）比手机上从电脑推来的代码旧，还没推送？"
                    "推送后再点更新")
        r = subprocess.run(["git", "-C", APP, "rev-parse", "HEAD", "FETCH_HEAD"], capture_output=True, text=True)
        heads = r.stdout.split()
        same = r.returncode == 0 and len(heads) == 2 and heads[0] == heads[1]
        r = subprocess.run(["git", "--no-optional-locks", "-C", APP, "status", "--porcelain", "-uno"],
                           capture_output=True, text=True)
        dirty = r.returncode != 0 or bool(r.stdout.strip())     # (changes from the Mac in the checkout)
        if not same:                        # (else: all is here)
            ok, out = self.retried("正在下载改动的文件", self.scratch_checkout)
            if not ok:
                return self.download_failed("下载文件", out)
        if not same or dirty:
            self.code_changed = True        # (until a script starts on it: also when this update fails)
        self.updating = "正在换上新代码"
        ok, out = self.git_step(["reset", "-q", "--hard", "FETCH_HEAD"], 120)
        if not ok:
            log("update failed: " + out.replace("\n", " | "))
            return "更新失败（换代码）: " + out
        ok, out = self.git_step(["sparse-checkout", "set", "--no-cone"] + SPARSE, 120)
        if not ok:                          # (the code is updated; only the file list stays as it was)
            log("update: sparse-checkout set failed: " + out.replace("\n", " | "))
        changed = self.copy_phone_files()
        if os.path.exists(LOCAL_CODE):      # (code and phone files are GitHub's now)
            os.remove(LOCAL_CODE)
        panel = os.path.exists(PANEL_APK) and sha1(PANEL_APK) != self.read(PANEL_SHA)
        own = sha1(f"{HOME}/supervisor.py") != LOADED   # (also after cp.sh code copied it)
        if not (self.code_changed or changed or panel or own):
            log(f"update: nothing new ({self.code_version()})")
            return f"已是最新: {self.code_version()}"      # (the script goes on: no restart for nothing)
        msg = f"updated to {self.code_version()}" + (", installing the new panel app" if panel else "")
        log(msg + (f"; phone files changed: {', '.join(changed)}" if changed else ""))
        if own:
            with self.term_lock:                # (no start slips in before the exec)
                if self.restarting:
                    return msg + "; the supervisor is restarting already"
                self.restarting = True
            threading.Thread(target=self.reexec, args=(panel,), daemon=True).start()
            return msg + ", restarting the supervisor"
        with self.lock:                         # (a script being stopped by hand stays stopped)
            running = self.proc is not None and self.script is not None and not self.stopping
            sid = self.script["id"] if running else None
        if running:
            result = self.start(sid)
            msg += ", restarted" if result == "ok" else f"; {result}"
        else:
            self.code_changed = False           # (nothing runs on the old code)
        if panel:                               # (after the answer: the install restarts the panel)
            threading.Thread(target=lambda: (time.sleep(2), self.install_panel()), daemon=True).start()
        return msg

    @staticmethod
    def read(path):
        try:
            with open(path) as f:
                return f.read().strip()
        except OSError:
            return None

    @staticmethod
    def adb_install(deadline, *flags):
        """`adb install` of the checkout's panel app. The cloud phone's install check refuses
        one now and then (INSTALL_FAILED_VERIFICATION_FAILURE) and passes it on the next try.
        One try may take 300 s; all of an install end by `deadline` (monotonic): a re-exec of
        the supervisor waits for it."""
        for attempt in (1, 2, 3):
            left = deadline - time.monotonic()
            if left < 5:
                raise RuntimeError("panel app install: out of time")
            try:
                return adb("install", *flags, PANEL_APK, timeout=min(300, left))
            except subprocess.TimeoutExpired:
                raise RuntimeError("adb install: no answer")
            except RuntimeError as e:
                if "VERIFICATION_FAILURE" not in str(e) or attempt == 3:
                    raise
                log(f"panel app: refused by the phone's install check (try {attempt}); again in 10 s")
                time.sleep(10)

    def install_panel(self):
        """Install the checkout's panel app through the phone's own adb (runtime permissions
        granted: no dialog over the game), then start it without opening its panel. One signed
        with another machine's key is installed afresh."""
        try:
            connect_adb()
            deadline = time.monotonic() + 360
            try:
                self.adb_install(deadline, "-r", "-g")
            except RuntimeError as e:
                if "UPDATE_INCOMPATIBLE" not in str(e):
                    raise
                adb("uninstall", "com.ip.panel")
                self.adb_install(time.monotonic() + 360, "-g")     # (its own time: no panel is worse)
            with open(PANEL_SHA, "w") as f:
                f.write(sha1(PANEL_APK))
            adb("shell", "appops", "set", "com.ip.panel", "SYSTEM_ALERT_WINDOW", "allow")
            adb("shell", "am", "start", "-n", "com.ip.panel/.MainActivity", "--ez", "quiet", "true")
            self.panel_note = time.strftime("panel app installed %m-%d %H:%M")
            log("panel app updated")
        except Exception as e:
            self.panel_note = f"panel app install failed: {e}"
            log(f"panel app update failed: {e}")

    @staticmethod
    def copy_phone_files():
        changed = []
        if not os.path.isdir(PHONE_FILES):
            return changed
        for name in os.listdir(PHONE_FILES):
            src, dst = f"{PHONE_FILES}/{name}", f"{HOME}/{name}"
            if os.path.isfile(src) and not (os.path.exists(dst) and filecmp.cmp(src, dst, shallow=False)):
                shutil.copyfile(src, dst)
                if name.endswith(".sh"):
                    os.chmod(dst, 0o755)
                changed.append(name)
        return changed

    def reexec(self, panel=False):
        """Start the new supervisor.py in this process (same pid); the running script stops and
        the new one resumes it from state.json. A changed panel app is installed first. A new
        file that does not load (a syntax error, a failing import, an error at its top level: it
        would end the service) is not started, and when the exec fails this one goes on: either
        way it takes starts again instead of answering 服务正在重启 for good."""
        time.sleep(1)                       # (the /update answer goes out first)
        new = f"{HOME}/supervisor.py"
        try:
            r = subprocess.run([sys.executable, "-c", LOAD_CHECK, new], capture_output=True, text=True,
                               timeout=120)
            ok, why = r.returncode == 0, (r.stderr.strip().splitlines() or [f"exit {r.returncode}"])[-1]
        except (OSError, subprocess.TimeoutExpired) as e:
            ok, why = False, str(e)
        if not ok:
            log(f"the new supervisor.py does not load ({why}): this one goes on")
        stopped = False
        try:
            if panel:
                self.install_panel()
            if ok:
                self.stop(remember=False)
                stopped = True
                if not self.exit_instead:   # (cp.sh restart meanwhile: it starts the next one)
                    log("supervisor.py changed: starting it again")
                    os.execv(sys.executable, [sys.executable, "-u", new])
        except Exception as e:
            log(f"restarting the supervisor failed ({e}): this one goes on")
        with self.term_lock:                # (a SIGTERM from here on stops this one by itself)
            self.restarting = False
            leave = self.exit_instead
        if leave:
            try:
                self.stop(remember=False)
            finally:
                os._exit(0)
        if stopped:                         # (the script was stopped for the exec)
            resume = self.saved_running()
        else:                               # (it still runs the old script code: restarted, as
            with self.lock:                 # an update without a new supervisor.py does)
                running = self.proc is not None and self.script is not None and not self.stopping
                resume = self.script["id"] if running else None
        if resume:
            self.start_retrying(resume)

    # ------------------------------------------------------------------ state
    @staticmethod
    def save_state(sid):
        with open(STATE, "w") as f:
            json.dump({"running": sid}, f)

    @staticmethod
    def saved_running():
        try:
            with open(STATE) as f:
                return json.load(f).get("running")
        except (OSError, ValueError):
            return None

    def status(self):
        with self.lock:
            running = self.proc is not None and self.proc.poll() is None
            script, since, last_exit, logfile = self.script, self.since, self.last_exit, self.logfile
        tail = self.tail(logfile, 8) if logfile and os.path.exists(logfile) else []
        return {"running": script["id"] if running else None,
                "stopping": running and self.stopping,
                "name": script.get("name", script["id"]) if script else None,
                "wanted": self.saved_running(),     # (state.json: what a restart or resume brings back)
                "panel": self.panel_note,
                "updating": self.updating,
                "since": since if running else None,
                "last_exit": last_exit, "tail": tail, "code": self.code_version()}

    @staticmethod
    def tail(path, n):
        with open(path, "rb") as f:
            f.seek(0, 2)
            f.seek(max(0, f.tell() - 64 * 1024))
            return f.read().decode("utf-8", "replace").splitlines()[-n:]


SUP = Supervisor()


class Handler(BaseHTTPRequestHandler):
    def reply(self, code, body, ctype="application/json"):
        data = body.encode("utf-8") if isinstance(body, str) else json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype + "; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        u = urlparse(self.path)
        q = parse_qs(u.query)
        try:
            if u.path == "/scripts":
                return self.reply(200, [{"id": s["id"], "name": s.get("name", s["id"]), "group": s.get("group", "")}
                                        for s in SUP.scripts()])
            if u.path == "/status":
                return self.reply(200, SUP.status())
            if u.path == "/log":
                n = int(q.get("n", ["200"])[0])
                path = SUP.logfile
                return self.reply(200, "\n".join(SUP.tail(path, n)) if path and os.path.exists(path) else "",
                                  "text/plain")
        except Exception as e:      # (a broken scripts.json, a bad n)
            return self.reply(500, {"error": str(e)})
        self.reply(404, {"error": "unknown"})

    def do_POST(self):
        u = urlparse(self.path)
        q = parse_qs(u.query)
        try:
            if u.path == "/start":
                return self.reply(200, {"result": SUP.start(q.get("id", [""])[0])})
            if u.path == "/stop":
                return self.reply(200, {"result": SUP.stop()})
            if u.path == "/update":
                return self.reply(200, {"result": SUP.update(force=q.get("force", ["0"])[0] == "1")})
        except Exception as e:      # (shown in the panel)
            return self.reply(500, {"result": f"error: {e}"})
        self.reply(404, {"error": "unknown"})

    def log_message(self, fmt, *args):
        pass                        # (the panel polls every few seconds)


def main():
    log(f"supervisor on 127.0.0.1:{PORT}, code {SUP.code_version()}")
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)     # (fails here when one runs already)
    with open(SUPERVISOR_PID, "w") as f:
        f.write(str(os.getpid()))

    def on_term(signum, frame):
        """cp.sh restart: the script ends at its safe point (up to STOP_GRACE) on a thread, so
        the server keeps answering meanwhile; it resumes under the next supervisor."""
        with SUP.term_lock:
            if SUP.restarting:              # (an update re-exec is under way: it exits instead)
                SUP.exit_instead = True
                return
            SUP.restarting = True

        def stop_and_exit():
            try:
                SUP.stop(remember=False)
            finally:
                os._exit(0)
        threading.Thread(target=stop_and_exit, daemon=True).start()
    signal.signal(signal.SIGTERM, on_term)

    def startup():
        with SUP.start_lock:                # (a 开始 meanwhile waits: no second script beside a leftover)
            SUP.stop_leftover()
            # the adb server lives in this long-running proot: short `run.sh` calls (peek,
            # cp.sh sh) then find it instead of forking one that would keep their proot waiting
            connect_adb()
        resume = SUP.saved_running()
        if resume:
            log(f"resuming {resume}")
            SUP.start_retrying(resume)
    threading.Thread(target=startup, daemon=True).start()
    server.serve_forever()


if __name__ == "__main__":
    main()
