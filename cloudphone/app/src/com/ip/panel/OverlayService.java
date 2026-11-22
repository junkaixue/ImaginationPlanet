package com.ip.panel;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.graphics.Color;
import android.graphics.PixelFormat;
import android.graphics.drawable.GradientDrawable;
import android.os.Build;
import android.os.Handler;
import android.os.IBinder;
import android.os.Looper;
import android.os.SystemClock;
import android.util.TypedValue;
import android.view.Gravity;
import android.view.MotionEvent;
import android.view.View;
import android.view.WindowManager;
import android.widget.Button;
import android.widget.HorizontalScrollView;
import android.widget.LinearLayout;
import android.widget.RadioButton;
import android.widget.RadioGroup;
import android.widget.TextView;
import android.widget.Toast;

import org.json.JSONArray;
import org.json.JSONObject;
import org.json.JSONTokener;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.atomic.AtomicBoolean;

/**
 * The floating panel: a small draggable bubble; a tap opens the list of scripts with 开始 / 停止 /
 * 更新, the running script and its last log lines. Everything goes through the supervisor
 * (Api); when it is not running (after a reboot) 启动服务 starts it through the local adb.
 *
 * The bubble can be dragged and tapped; while a script runs it is small, green and half
 * transparent (it hides less of the screenshots), parked at the top right by default: no
 * template fortress_fight reads is there (checked on the saved pages; zone_explore's resource
 * scan reads the whole map and needs a HIDE before its shots). The
 * scripts tap the screen by position: before a touch on the bubble or the panel, a script
 * (adb_device.py) broadcasts ACTION_HIDE in the same shell as the touch, and the app steps aside
 * for the time asked (panel closed, bubble invisible and touch-through: window alpha 0, Android
 * 12+ passes touches through an overlay only at <= 0.8); a press under way then opens nothing.
 * Scripts announce with ACTION_HELLO that they do this; while one runs that has not, the bubble
 * stays touch-through (an older script would tap into it). The panel closes when a script starts.
 */
public class OverlayService extends Service {
    static final String ACTION_PANEL = "com.ip.panel.PANEL", ACTION_STOP = "com.ip.panel.STOP";
    static final String ACTION_HIDE = "com.ip.panel.HIDE";     // extra "ms": how long (a script's tap)
    static final String ACTION_HELLO = "com.ip.panel.HELLO";   // a script that steps around the bubble
    private static final long HELLO_LEASE_MS = 3 * 60 * 1000;   // (scripts repeat it every minute)
    private static final int IDLE_DP = 44, RUN_DP = 34;
    private static final int POLL_MS = 3000;
    private static final int IDLE_COLOR = 0xCC7B3FE4, RUNNING_COLOR = 0xCC2E9E5B;
    private static final String START_SUPERVISOR = "sh /data/local/tmp/ip/start.sh";

    private WindowManager wm;
    private TextView bubble;
    private LinearLayout panel;
    private WindowManager.LayoutParams bubbleLp, panelLp;
    private TextView status, message, logView;
    private RadioGroup list;
    private HorizontalScrollView groupScroll;
    private LinearLayout groupRow;          // one button per kind of feature (the scripts' "group")
    private Map<String, List<String[]>> groups = new LinkedHashMap<>();   // group -> [id, name], file order
    private boolean loaded, jumpToRunning;  // the list was read / show the running script's group next
    private boolean rendering;              // (checks made by render() are not the user's pick)
    private String groupShown, selected, codeSeen;   // the group on screen, the script picked, the code version
    private Button startSupervisor;
    private final Handler ui = new Handler(Looper.getMainLooper());
    private final ExecutorService poller = Executors.newSingleThreadExecutor();   // status, list
    private final ExecutorService actions = Executors.newCachedThreadPool();     // 开始/停止/更新/启动服务:
                                                                                 // 停止 never waits for 更新
    private final AtomicBoolean polling = new AtomicBoolean();
    private boolean panelShown, destroyed, known;   // known: a status was read since the start
    private String running;
    private double runningSince;    // the run's start (/status "since", epoch seconds: this phone's clock)

    private long hiddenUntil, helloAt;  // elapsedRealtime: hidden for a script's touch / the last HELLO
    private long helloWall;             // currentTimeMillis of that HELLO (to tell whose run sent it)
    private final Runnable unhide = this::applyBubble;
    private final BroadcastReceiver hideReceiver = new BroadcastReceiver() {
        @Override
        public void onReceive(Context c, Intent i) {
            if (ACTION_HELLO.equals(i.getAction())) {
                helloAt = SystemClock.elapsedRealtime();
                helloWall = System.currentTimeMillis();
                applyBubble();
            } else {
                hideFor(i.getIntExtra("ms", 1500));
            }
        }
    };
    private GradientDrawable bubbleBg;

    private final Runnable poll = new Runnable() {     // always: the bubble follows the state
        @Override
        public void run() {
            refreshStatus();
            ui.postDelayed(this, POLL_MS);
        }
    };

    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }

    @Override
    public void onCreate() {
        super.onCreate();
        foreground();
        wm = (WindowManager) getSystemService(WINDOW_SERVICE);
        buildBubble();
        buildPanel();
        IntentFilter f = new IntentFilter(ACTION_HIDE);
        f.addAction(ACTION_HELLO);
        if (Build.VERSION.SDK_INT >= 33) {
            registerReceiver(hideReceiver, f, RECEIVER_EXPORTED);    // (the scripts send it from the shell)
        } else {
            registerReceiver(hideReceiver, f);
        }
        ui.post(poll);
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        String a = intent == null ? null : intent.getAction();
        if (ACTION_PANEL.equals(a) && !panelShown) {
            togglePanel();
        } else if (ACTION_STOP.equals(a)) {
            action("/stop", 300000);       // (a script ends after the step in hand: up to 4 min)
        }
        return START_STICKY;
    }

    @Override
    public void onDestroy() {
        destroyed = true;                   // (late network callbacks are dropped)
        unregisterReceiver(hideReceiver);
        ui.removeCallbacksAndMessages(null);
        poller.shutdownNow();
        actions.shutdownNow();
        if (panelShown) {
            wm.removeView(panel);
            panelShown = false;
        }
        wm.removeView(bubble);
        super.onDestroy();
    }

    /** Run on the UI thread unless the service is gone. */
    private void onUi(Runnable r) {
        ui.post(() -> {
            if (!destroyed) {
                r.run();
            }
        });
    }

    private void foreground() {
        String ch = "panel";
        NotificationManager nm = (NotificationManager) getSystemService(NOTIFICATION_SERVICE);
        Notification.Builder b;
        if (Build.VERSION.SDK_INT >= 26) {
            nm.createNotificationChannel(new NotificationChannel(ch, "星球脚本", NotificationManager.IMPORTANCE_LOW));
            b = new Notification.Builder(this, ch);
        } else {
            b = new Notification.Builder(this);
        }
        b.setContentTitle("星球脚本").setContentText("点小圆点或这里打开面板，也可以直接停止")
                .setSmallIcon(android.R.drawable.ic_media_play)
                .setContentIntent(selfIntent(ACTION_PANEL, 1))
                .addAction(new Notification.Action.Builder(null, "打开面板", selfIntent(ACTION_PANEL, 1)).build())
                .addAction(new Notification.Action.Builder(null, "停止", selfIntent(ACTION_STOP, 2)).build());
        startForeground(1, b.build());
    }

    private PendingIntent selfIntent(String action, int code) {
        Intent i = new Intent(this, OverlayService.class).setAction(action);
        return PendingIntent.getService(this, code, i, PendingIntent.FLAG_IMMUTABLE | PendingIntent.FLAG_UPDATE_CURRENT);
    }

    private int dp(float v) {
        return (int) TypedValue.applyDimension(TypedValue.COMPLEX_UNIT_DIP, v, getResources().getDisplayMetrics());
    }

    private static int overlayType() {
        return Build.VERSION.SDK_INT >= 26 ? WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY
                : WindowManager.LayoutParams.TYPE_PHONE;
    }

    // ------------------------------------------------------------------ bubble
    private void buildBubble() {
        bubble = new TextView(this);
        bubble.setText("脚本");
        bubble.setTextColor(Color.WHITE);
        bubble.setTextSize(12);
        bubble.setGravity(Gravity.CENTER);
        bubbleBg = new GradientDrawable();
        bubbleBg.setShape(GradientDrawable.OVAL);
        bubbleBg.setColor(IDLE_COLOR);
        bubble.setBackground(bubbleBg);
        bubbleLp = new WindowManager.LayoutParams(dp(44), dp(44), overlayType(),
                WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE, PixelFormat.TRANSLUCENT);
        bubbleLp.gravity = Gravity.TOP | Gravity.START;
        bubbleLp.x = getResources().getDisplayMetrics().widthPixels - dp(IDLE_DP) - dp(4);   // top right:
        bubbleLp.y = dp(4);                 // the scripts rarely look or tap there
        bubble.setOnTouchListener(new View.OnTouchListener() {
            float downX, downY;
            int startX, startY;
            boolean moved;

            @Override
            public boolean onTouch(View v, MotionEvent e) {
                switch (e.getAction()) {
                    case MotionEvent.ACTION_DOWN:
                        downX = e.getRawX();
                        downY = e.getRawY();
                        startX = bubbleLp.x;
                        startY = bubbleLp.y;
                        moved = false;
                        return true;
                    case MotionEvent.ACTION_MOVE:
                        int dx = (int) (e.getRawX() - downX), dy = (int) (e.getRawY() - downY);
                        if (Math.abs(dx) + Math.abs(dy) > dp(6)) {
                            moved = true;
                        }
                        bubbleLp.x = startX + dx;
                        bubbleLp.y = startY + dy;
                        wm.updateViewLayout(bubble, bubbleLp);
                        return true;
                    case MotionEvent.ACTION_UP:
                        // (a press under way when a script's HIDE came opens nothing)
                        if (!moved && SystemClock.elapsedRealtime() >= hiddenUntil) {
                            togglePanel();
                        }
                        return true;
                    default:
                        return false;
                }
            }
        });
        wm.addView(bubble, bubbleLp);
    }

    /** Green "运行" while a script runs, purple "脚本" otherwise. */
    private void updateBubble() {
        boolean run = running != null;
        bubble.setText(run ? "运行" : "脚本");
        bubble.setTextSize(run ? 11 : 12);
        bubbleBg.setColor(run ? RUNNING_COLOR : IDLE_COLOR);
        applyBubble();
    }

    /** Size, alpha and touchability for the state: hidden for a script's touch; running (small,
     *  half transparent; touchable only while the script has said HELLO); idle. */
    private void applyBubble() {
        if (destroyed) {
            return;
        }
        long now = SystemClock.elapsedRealtime();
        // the running script said HELLO: within the lease, and after it started (the supervisor's
        // clock is this phone's; a HELLO from the script before it does not count, one that came
        // before the poll noticed the new run does)
        boolean hidden = now < hiddenUntil, run = running != null,
                avoids = helloAt > 0 && now - helloAt < HELLO_LEASE_MS && helloWall >= (long) (runningSince * 1000);
        int size = dp(run ? RUN_DP : IDLE_DP);
        float alpha = hidden ? 0f : run ? (avoids ? 0.6f : 0.5f) : 1f;
        boolean touchable = !hidden && (!run || avoids);
        int flags = touchable ? bubbleLp.flags & ~WindowManager.LayoutParams.FLAG_NOT_TOUCHABLE
                : bubbleLp.flags | WindowManager.LayoutParams.FLAG_NOT_TOUCHABLE;
        if (size != bubbleLp.width || alpha != bubbleLp.alpha || flags != bubbleLp.flags) {
            bubbleLp.width = size;
            bubbleLp.height = size;
            bubbleLp.alpha = alpha;         // (the window's alpha counts for touches, not the view's)
            bubbleLp.flags = flags;
            wm.updateViewLayout(bubble, bubbleLp);
        }
    }

    /** A script is about to touch where the bubble or the panel is: out of its way for `ms`. */
    private void hideFor(int ms) {
        if (destroyed) {
            return;
        }
        if (panelShown) {
            togglePanel();
        }
        int span = Math.max(200, Math.min(ms, 10000));
        hiddenUntil = SystemClock.elapsedRealtime() + span;
        applyBubble();
        ui.removeCallbacks(unhide);
        ui.postDelayed(unhide, span + 50);
    }

    // ------------------------------------------------------------------ panel
    private Button button(String text, View.OnClickListener l) {
        Button b = new Button(this);
        b.setText(text);
        b.setTextSize(13);
        b.setAllCaps(false);
        b.setOnClickListener(l);
        return b;
    }

    private TextView text(int color, int size) {
        TextView t = new TextView(this);
        t.setTextColor(color);
        t.setTextSize(size);
        return t;
    }

    private void buildPanel() {
        panel = new LinearLayout(this);
        panel.setOrientation(LinearLayout.VERTICAL);
        panel.setPadding(dp(12), dp(10), dp(12), dp(10));
        GradientDrawable bg = new GradientDrawable();
        bg.setCornerRadius(dp(12));
        bg.setColor(0xEE1E1B2E);
        panel.setBackground(bg);

        TextView title = text(Color.WHITE, 16);
        title.setText("星球脚本");
        panel.addView(title);
        status = text(0xFFB8F5C8, 12);
        panel.addView(status);

        groupScroll = new HorizontalScrollView(this);
        groupRow = new LinearLayout(this);
        groupScroll.addView(groupRow);
        panel.addView(groupScroll);
        list = new RadioGroup(this);
        list.setOnCheckedChangeListener((g, id) -> {
            View v = g.findViewById(id);
            if (v != null && !rendering) {
                selected = (String) v.getTag();
            }
        });
        panel.addView(list);

        LinearLayout row = new LinearLayout(this);
        row.addView(button("开始", v -> startSelected()));
        row.addView(button("停止", v -> action("/stop", 300000)));
        row.addView(button("更新", v -> action("/update", 1800000)));    // (fetch, checkout, file list, a graceful stop, the game)
        panel.addView(row);

        message = text(0xFFFFD27F, 12);     // the last action's answer: stays until the next action
        panel.addView(message);
        logView = text(0xFFCCCCCC, 10);
        logView.setMaxLines(6);
        panel.addView(logView);

        LinearLayout row2 = new LinearLayout(this);
        startSupervisor = button("启动服务", v -> startSupervisor());
        startSupervisor.setVisibility(View.GONE);
        row2.addView(startSupervisor);
        row2.addView(button("收起", v -> togglePanel()));
        row2.addView(button("退出浮窗", v -> stopSelf()));
        panel.addView(row2);

        panelLp = new WindowManager.LayoutParams(dp(300), WindowManager.LayoutParams.WRAP_CONTENT, overlayType(),
                WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE, PixelFormat.TRANSLUCENT);
        panelLp.gravity = Gravity.TOP | Gravity.START;
    }

    private void togglePanel() {
        if (panelShown) {
            wm.removeView(panel);
            panelShown = false;
            return;
        }
        panelLp.x = dp(8);
        panelLp.y = Math.max(0, bubbleLp.y - dp(40));
        wm.addView(panel, panelLp);
        panelShown = true;
        jumpToRunning = true;
        loadScripts();
        refreshStatus();
    }

    // ------------------------------------------------------------------ supervisor
    private void loadScripts() {
        poller.execute(() -> {
            try {
                Map<String, List<String[]>> m = parseScripts(Api.get("/scripts"));
                onUi(() -> {
                    groups = m;
                    loaded = true;
                    String g = jumpToRunning ? groupOf(running) : null;
                    jumpToRunning = false;
                    if (g == null) {
                        g = groupShown != null && groups.containsKey(groupShown) ? groupShown
                                : groups.isEmpty() ? null : groups.keySet().iterator().next();
                    }
                    render(g);
                });
            } catch (Exception e) {
                onUi(() -> {
                    loaded = false;
                    groups = new LinkedHashMap<>();
                    render(null);
                    message.setText("脚本列表读不到: " + e.getMessage());
                });
            }
        });
    }

    /**
     * /scripts: [{"id", "name", "group"}] (a supervisor of 847be53: {"groups": [{"name", "items"}]};
     * a failure: {"error"}) into group -> [id, name] in file order; malformed entries are skipped.
     */
    private static Map<String, List<String[]>> parseScripts(String body) throws Exception {
        Object v = new JSONTokener(body).nextValue();
        JSONArray items = new JSONArray();
        if (v instanceof JSONArray) {
            items = (JSONArray) v;
        } else if (v instanceof JSONObject && ((JSONObject) v).has("groups")) {
            JSONArray gs = ((JSONObject) v).optJSONArray("groups");
            for (int i = 0; gs != null && i < gs.length(); i++) {
                JSONObject g = gs.optJSONObject(i);
                JSONArray its = g == null ? null : g.optJSONArray("items");
                for (int j = 0; its != null && j < its.length(); j++) {
                    JSONObject it = its.optJSONObject(j);
                    if (it != null) {
                        items.put(new JSONObject(it.toString()).put("group", g.optString("name", "")));
                    }
                }
            }
        } else if (v instanceof JSONObject) {
            throw new Exception(((JSONObject) v).optString("error", "unexpected answer"));
        } else {
            throw new Exception("unexpected answer");
        }
        Map<String, List<String[]>> m = new LinkedHashMap<>();
        for (int i = 0; i < items.length(); i++) {
            JSONObject it = items.optJSONObject(i);
            if (it == null || it.isNull("id") || it.optString("id", "").isEmpty()) {
                continue;
            }
            String id = it.optString("id");
            String name = it.isNull("name") ? id : it.optString("name", id);
            String group = it.isNull("group") || it.optString("group", "").isEmpty() ? "脚本" : it.optString("group");
            List<String[]> list = m.get(group);
            if (list == null) {
                list = new ArrayList<>();
                m.put(group, list);
            }
            list.add(new String[]{id, name});
        }
        return m;
    }

    /** The group holding script `id`, or null. */
    private String groupOf(String id) {
        for (Map.Entry<String, List<String[]>> e : groups.entrySet()) {
            for (String[] it : e.getValue()) {
                if (it[0].equals(id)) {
                    return e.getKey();
                }
            }
        }
        return null;
    }

    /** The group buttons (the shown one highlighted and scrolled into view) and its scripts: the
     *  one picked earlier checked, or else the running one. */
    private void render(String group) {
        groupShown = group;
        groupRow.removeAllViews();
        Button shown = null;
        for (String g : groups.keySet()) {
            Button b = button(g, v -> {
                if (!g.equals(groupShown)) {
                    render(g);
                }
            });
            b.setAlpha(g.equals(group) ? 1f : 0.55f);
            groupRow.addView(b);
            if (g.equals(group)) {
                shown = b;
            }
        }
        String check = selected != null && group != null && group.equals(groupOf(selected)) ? selected : running;
        rendering = true;
        list.removeAllViews();
        List<String[]> items = group == null ? null : groups.get(group);
        for (int j = 0; items != null && j < items.size(); j++) {
            RadioButton r = new RadioButton(this);
            r.setText(items.get(j)[1]);
            r.setTag(items.get(j)[0]);
            r.setTextColor(Color.WHITE);
            r.setTextSize(13);
            list.addView(r);
            if (items.get(j)[0].equals(check)) {
                r.setChecked(true);
            }
        }
        rendering = false;
        Button target = shown;
        if (target != null) {
            groupScroll.post(() -> groupScroll.smoothScrollTo(target.getLeft(), 0));
        }
    }

    private void refreshStatus() {
        if (!polling.compareAndSet(false, true)) {
            return;                         // the last poll has not answered yet
        }
        poller.execute(() -> {
            try {
                JSONObject st = new JSONObject(Api.get("/status"));
                String run = st.isNull("running") ? null : st.optString("running");
                double since = st.optDouble("since", 0);
                StringBuilder tail = new StringBuilder();
                JSONArray t = st.optJSONArray("tail");
                for (int i = 0; t != null && i < t.length(); i++) {
                    String line = t.optString(i);
                    tail.append(line.length() > 22 && line.startsWith("[") ? line.substring(12) : line).append('\n');
                }
                String text = (run != null ? (st.optBoolean("stopping") ? "停止中（等手上这一步做完）: " : "运行中: ")
                        + st.optString("name") : "未运行"
                        + (st.isNull("last_exit") ? "" : " (上次退出 " + st.optInt("last_exit") + ")"))
                        + "\n代码: " + st.optString("code")
                        + (st.isNull("updating") ? "" : "\n更新中：" + st.optString("updating"));
                onUi(() -> {
                    boolean changed = run == null ? running != null : !run.equals(running);
                    // (the first status only sets the baseline: the panel opened from the app icon
                    // while a script runs stays open)
                    boolean started = known && run != null && since != runningSince;
                    known = true;
                    running = run;
                    runningSince = run != null ? since : 0;
                    updateBubble();
                    if (started && panelShown) {
                        togglePanel();      // a script (re)started: out of the way of its taps
                    }
                    status.setText(text);
                    logView.setText(tail.toString().trim());
                    startSupervisor.setVisibility(View.GONE);
                    String code = st.optString("code");
                    boolean newCode = codeSeen != null && !code.equals(codeSeen);   // (an update)
                    codeSeen = code;
                    if (panelShown && (changed || newCode || !loaded)) {
                        jumpToRunning |= changed;
                        loadScripts();
                    }
                });
            } catch (Exception e) {
                onUi(() -> {
                    running = null;
                    updateBubble();
                    status.setText("服务未运行（手机重启过？）点“启动服务”");
                    logView.setText("");
                    startSupervisor.setVisibility(View.VISIBLE);
                });
            } finally {
                polling.set(false);
            }
        });
    }

    private void startSelected() {
        View v = list.findViewById(list.getCheckedRadioButtonId());
        if (v == null) {
            message.setText("先选一个脚本");
            return;
        }
        try {
            action("/start?id=" + Api.enc((String) v.getTag()), 420000);   // (the old script's graceful stop + the game)
        } catch (Exception e) {
            message.setText("出错: " + e.getMessage());
        }
    }

    /** A request to the supervisor. 开始/停止/更新 close the panel at once: a stop or a restart
     *  may take minutes, in which the script must see the game; the answer comes as a toast. */
    private void action(String path, int timeoutMs) {
        message.setText("请稍候…");
        if (panelShown) {
            togglePanel();
        }
        boolean update = path.startsWith("/update");
        Toast.makeText(this, path.startsWith("/stop") ? "正在停止（等手上这一步做完）"
                : update ? "正在更新：从 GitHub 拉代码，可能要几分钟，结果会提示；进度在面板里看" : "正在启动",
                update ? Toast.LENGTH_LONG : Toast.LENGTH_SHORT).show();
        actions.execute(() -> {
            String msg;
            try {
                msg = new JSONObject(Api.post(path, timeoutMs)).optString("result");
            } catch (Exception e) {
                msg = "出错: " + e.getMessage();
            }
            String m = msg;
            onUi(() -> {
                message.setText(m);
                if (!panelShown) {
                    Toast.makeText(this, m, Toast.LENGTH_LONG).show();
                }
                loaded = false;             // (an update may have changed the list: read it on the next open)
                refreshStatus();
            });
        });
    }

    private void startSupervisor() {
        message.setText("正在启动服务…");
        actions.execute(() -> {
            String msg;
            try {
                msg = LocalAdb.shell(getFilesDir(), "127.0.0.1", 5555, START_SUPERVISOR, 60000).trim();
            } catch (Exception e) {
                msg = "启动失败: " + e + "（开发者选项里 USB 调试要开着）";
            }
            String m = msg;
            onUi(() -> {
                message.setText(m);
                ui.postDelayed(this::refreshStatus, 2500);
            });
        });
    }
}
