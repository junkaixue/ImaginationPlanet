"""Runs the game scripts inside the cloud phone and is driven by the floating panel app (and by
cloudphone/cp.sh on the Mac) over http://127.0.0.1:8765 (this phone only).

    GET  /scripts         [{"id", "name"}] from scripts.json
    GET  /status          what runs, since when, the last log lines, the code version
    GET  /log?n=200       the running (or last) script's log tail, text
    POST /start?id=ID     stop what runs, bring the game to the front, start ID
    POST /stop            stop what runs
    POST /update          fetch the newest code from GitHub (a git checkout in /ip/app), copy its
                          cloudphone/phone files to /ip, start the running script again on it
                          (and the supervisor itself when supervisor.py changed)

One script runs at a time (one game). A script that fails (ends by itself with an error exit,
e.g. fortress_fight's "errors keep coming") is started again after RESTART_WAIT s, at most
MAX_RESTARTS times an hour; one that finishes (exit 0) is not, nor a dry run (its "restart":
false in scripts.json, the default for args with --dry). The running script is remembered in
state.json: a supervisor started again (cp.sh restart, or after a reboot by the panel app)
starts it again.
"""
import filecmp
import json
import os
import shutil
import signal
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

HOME = "/ip"
APP = f"{HOME}/app"
PHONE_FILES = f"{APP}/cloudphone/phone"     # the repo's copy of the files in HOME
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
STOP_GRACE = 8                      # seconds between SIGTERM and SIGKILL
ADB_TIMEOUT = 30


def log(msg):
    print(time.strftime("[%Y-%m-%d %H:%M:%S] ") + msg, flush=True)


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
        self.restarts = []          # times of automatic restarts this hour
        self.logfile = None
        self.last_exit = None

    # ------------------------------------------------------------------ scripts
    @staticmethod
    def scripts():
        with open(SCRIPTS, encoding="utf-8") as f:
            return json.load(f)

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
        script = self.find(sid)
        if script is None:
            return f"no script {sid}"
        with self.start_lock:
            self.stop(remember=False)
            self.ensure_game()              # (outside self.lock: status and stop stay quick)
            with self.lock:
                if not manual and self.stopping and self.saved_running() != sid:
                    return "stopped meanwhile"
                os.makedirs(LOGS, exist_ok=True)
                self.logfile = f"{LOGS}/{sid}.log"
                with open(self.logfile, "a", encoding="utf-8") as out:
                    out.write(time.strftime(f"\n===== %Y-%m-%d %H:%M:%S start {script['name']} ({self.code_version()})\n"))
                    out.flush()
                    self.proc = subprocess.Popen(["python3", "-u"] + script["args"] + EXTRA_ARGS, cwd=APP,
                                                 stdout=out, stderr=subprocess.STDOUT, start_new_session=True)
                self.gen += 1
                self.script, self.since, self.stopping, self.last_exit = script, time.time(), False, None
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
        with self.lock:
            proc, self.stopping = self.proc, True
            if proc is not None and proc.poll() is None:
                os.killpg(proc.pid, signal.SIGTERM)
                try:
                    proc.wait(STOP_GRACE)
                except subprocess.TimeoutExpired:
                    os.killpg(proc.pid, signal.SIGKILL)
                    proc.wait()
                log(f"stopped {self.script['id']}")
            self.proc = None
            if os.path.exists(SCRIPT_PID):
                os.remove(SCRIPT_PID)
            if remember:
                self.save_state(None)
        return "ok"

    @staticmethod
    def stop_leftover():
        """A script started by an earlier supervisor (killed without stopping it) still runs:
        stop it, or two scripts would drive the game. The pid is checked to be a script still
        (after a reboot it may belong to anything)."""
        try:
            with open(SCRIPT_PID) as f:
                pgid = int(f.read().strip())
            if "python3" in cmdline(pgid):
                log(f"stopping a script left running (pid {pgid})")
                os.killpg(pgid, signal.SIGTERM)
                time.sleep(STOP_GRACE)
                if "python3" in cmdline(pgid):
                    os.killpg(pgid, signal.SIGKILL)
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
    def update(self):
        if not os.path.isdir(f"{APP}/.git"):
            return "the code is a copy from the Mac (cp.sh code); run `cp.sh code --github` once"
        r = subprocess.run(["sh", "-c", f"cd {APP} && git fetch -q --depth 1 origin main && git reset -q --hard FETCH_HEAD"],
                           capture_output=True, text=True, timeout=600)
        if r.returncode != 0:
            out = (r.stdout + r.stderr).strip()
            log("update failed: " + out.replace("\n", " | "))
            return "更新失败: " + out
        changed = self.copy_phone_files()
        msg = f"updated to {self.code_version()}"
        log(msg + (f"; phone files changed: {', '.join(changed)}" if changed else ""))
        if "supervisor.py" in changed:
            threading.Thread(target=self.reexec, daemon=True).start()
            return msg + ", restarting the supervisor"
        with self.lock:
            running = self.proc is not None and self.script is not None
            sid = self.script["id"] if running else None
        if running:
            self.start(sid)
        return msg + (", restarted" if running else "")

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

    def reexec(self):
        """Start the new supervisor.py in this process (same pid); the running script stops and
        the new one resumes it from state.json."""
        time.sleep(1)                       # (the /update answer goes out first)
        self.stop(remember=False)
        log("supervisor.py changed: starting it again")
        os.execv(sys.executable, [sys.executable, "-u", f"{HOME}/supervisor.py"])

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
                "name": script["name"] if script else None,
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
                return self.reply(200, [{"id": s["id"], "name": s["name"]} for s in SUP.scripts()])
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
                return self.reply(200, {"result": SUP.update()})
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
    SUP.stop_leftover()
    # the adb server lives in this long-running proot: short `run.sh` calls (peek, cp.sh sh)
    # then find it instead of forking one that would keep their proot waiting
    connect_adb()

    def on_term(signum, frame):     # (cp.sh restart): the script stops too, and resumes after
        SUP.stop(remember=False)
        os._exit(0)
    signal.signal(signal.SIGTERM, on_term)
    resume = SUP.saved_running()
    if resume:
        log(f"resuming {resume}")
        threading.Thread(target=SUP.start_retrying, args=(resume,), daemon=True).start()
    server.serve_forever()


if __name__ == "__main__":
    main()
