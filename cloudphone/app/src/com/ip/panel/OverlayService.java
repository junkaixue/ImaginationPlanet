package com.ip.panel;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.content.Intent;
import android.graphics.Color;
import android.graphics.PixelFormat;
import android.graphics.drawable.GradientDrawable;
import android.os.Build;
import android.os.Handler;
import android.os.IBinder;
import android.os.Looper;
import android.util.TypedValue;
import android.view.Gravity;
import android.view.MotionEvent;
import android.view.View;
import android.view.WindowManager;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.RadioButton;
import android.widget.RadioGroup;
import android.widget.TextView;

import org.json.JSONArray;
import org.json.JSONObject;

import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.atomic.AtomicBoolean;

/**
 * The floating panel: a small draggable bubble; a tap opens the list of scripts with 开始 / 停止 /
 * 更新, the running script and its last log lines. Everything goes through the supervisor
 * (Api); when it is not running (after a reboot) 启动服务 starts it through the local adb.
 *
 * The scripts tap the screen by position, and a tap on the bubble or the panel would land on
 * them: while a script runs the bubble lets touches through (window alpha <= 0.8, which Android
 * 12+ requires for that; dimmed, "运行中"), and the panel closes whenever a script starts (开始,
 * 更新, a resume or an automatic restart). The notification (打开面板 / 停止) or the app icon
 * opens the panel then.
 */
public class OverlayService extends Service {
    static final String ACTION_PANEL = "com.ip.panel.PANEL", ACTION_STOP = "com.ip.panel.STOP";
    private static final int POLL_MS = 3000;
    private static final float THROUGH_ALPHA = 0.5f;   // touches pass an overlay only at <= 0.8
    private static final String START_SUPERVISOR = "sh /data/local/tmp/ip/start.sh";

    private WindowManager wm;
    private TextView bubble;
    private LinearLayout panel;
    private WindowManager.LayoutParams bubbleLp, panelLp;
    private TextView status, message, logView;
    private RadioGroup list;
    private Button startSupervisor;
    private final Handler ui = new Handler(Looper.getMainLooper());
    private final ExecutorService poller = Executors.newSingleThreadExecutor();   // status, list
    private final ExecutorService actions = Executors.newCachedThreadPool();     // 开始/停止/更新/启动服务:
                                                                                 // 停止 never waits for 更新
    private final AtomicBoolean polling = new AtomicBoolean();
    private boolean panelShown, destroyed, known;   // known: a status was read since the start
    private String running;
    private double runningSince;

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
        ui.post(poll);
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        String a = intent == null ? null : intent.getAction();
        if (ACTION_PANEL.equals(a) && !panelShown) {
            togglePanel();
        } else if (ACTION_STOP.equals(a)) {
            action("/stop", 20000);
        }
        return START_STICKY;
    }

    @Override
    public void onDestroy() {
        destroyed = true;                   // (late network callbacks are dropped)
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
        b.setContentTitle("星球脚本").setContentText("运行时浮窗不挡点击：在这里打开面板或停止")
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
        GradientDrawable bg = new GradientDrawable();
        bg.setShape(GradientDrawable.OVAL);
        bg.setColor(0xCC7B3FE4);
        bubble.setBackground(bg);
        bubbleLp = new WindowManager.LayoutParams(dp(44), dp(44), overlayType(),
                WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE, PixelFormat.TRANSLUCENT);
        bubbleLp.gravity = Gravity.TOP | Gravity.START;
        bubbleLp.x = 0;
        bubbleLp.y = dp(260);
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
                        if (!moved) {
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

    /** Running: dimmed and touch-through; idle: the normal bubble. */
    private void updateBubble() {
        boolean run = running != null;
        bubble.setText(run ? "运行中" : "脚本");
        int flags = run ? bubbleLp.flags | WindowManager.LayoutParams.FLAG_NOT_TOUCHABLE
                : bubbleLp.flags & ~WindowManager.LayoutParams.FLAG_NOT_TOUCHABLE;
        float alpha = run ? THROUGH_ALPHA : 1f;
        if (flags != bubbleLp.flags || alpha != bubbleLp.alpha) {
            bubbleLp.flags = flags;
            bubbleLp.alpha = alpha;         // (the window's alpha counts, not the view's)
            wm.updateViewLayout(bubble, bubbleLp);
        }
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

        list = new RadioGroup(this);
        panel.addView(list);

        LinearLayout row = new LinearLayout(this);
        row.addView(button("开始", v -> startSelected()));
        row.addView(button("停止", v -> action("/stop", 20000)));
        row.addView(button("更新", v -> action("/update", 600000)));
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
        loadScripts();
        refreshStatus();
    }

    // ------------------------------------------------------------------ supervisor
    private void loadScripts() {
        poller.execute(() -> {
            try {
                JSONArray a = new JSONArray(Api.get("/scripts"));
                onUi(() -> {
                    list.removeAllViews();
                    for (int i = 0; i < a.length(); i++) {
                        JSONObject s = a.optJSONObject(i);
                        RadioButton r = new RadioButton(this);
                        r.setText(s.optString("name"));
                        r.setTag(s.optString("id"));
                        r.setTextColor(Color.WHITE);
                        r.setTextSize(13);
                        list.addView(r);
                        if (s.optString("id").equals(running)) {
                            r.setChecked(true);
                        }
                    }
                });
            } catch (Exception e) {
                onUi(() -> list.removeAllViews());
            }
        });
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
                String text = (run != null ? "运行中: " + st.optString("name") : "未运行"
                        + (st.isNull("last_exit") ? "" : " (上次退出 " + st.optInt("last_exit") + ")"))
                        + "\n代码: " + st.optString("code");
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
                    if (changed || list.getChildCount() == 0) {
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
            action("/start?id=" + Api.enc((String) v.getTag()), 120000);
        } catch (Exception e) {
            message.setText("出错: " + e.getMessage());
        }
    }

    private void action(String path, int timeoutMs) {
        message.setText("请稍候…");
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
