package com.ip.panel;

import android.app.Activity;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.provider.Settings;
import android.widget.Toast;

/** The launcher icon: shows the floating panel (asks for the overlay permission first). */
public class MainActivity extends Activity {
    @Override
    protected void onCreate(Bundle state) {
        super.onCreate(state);
        if (Build.VERSION.SDK_INT >= 33
                && checkSelfPermission("android.permission.POST_NOTIFICATIONS") != PackageManager.PERMISSION_GRANTED) {
            // the notification carries 打开面板 / 停止 while a script runs
            requestPermissions(new String[]{"android.permission.POST_NOTIFICATIONS"}, 1);
            return;
        }
        open();
    }

    @Override
    public void onRequestPermissionsResult(int code, String[] perms, int[] results) {
        open();
    }

    private void open() {
        if (!Settings.canDrawOverlays(this)) {
            Toast.makeText(this, "请允许“星球脚本”显示在其他应用上层", Toast.LENGTH_LONG).show();
            startActivity(new Intent(Settings.ACTION_MANAGE_OVERLAY_PERMISSION, Uri.parse("package:" + getPackageName())));
        } else {
            Intent i = new Intent(this, OverlayService.class).setAction(OverlayService.ACTION_PANEL);
            if (Build.VERSION.SDK_INT >= 26) {
                startForegroundService(i);
            } else {
                startService(i);
            }
        }
        finish();
    }
}
