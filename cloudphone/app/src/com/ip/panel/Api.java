package com.ip.panel;

import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.net.URLEncoder;

/** The supervisor inside the phone (cloudphone/phone/supervisor.py) on http://127.0.0.1:8765. */
final class Api {
    static final String BASE = "http://127.0.0.1:8765";

    private Api() {}

    static String get(String path) throws Exception {
        return call("GET", path, 5000);
    }

    static String post(String path, int timeoutMs) throws Exception {
        return call("POST", path, timeoutMs);
    }

    static String enc(String s) throws Exception {
        return URLEncoder.encode(s, "UTF-8");
    }

    private static String call(String method, String path, int timeoutMs) throws Exception {
        HttpURLConnection c = (HttpURLConnection) new URL(BASE + path).openConnection();
        c.setRequestMethod(method);
        c.setConnectTimeout(2000);
        c.setReadTimeout(timeoutMs);
        if (method.equals("POST")) {
            c.setDoOutput(true);
            c.getOutputStream().close();
        }
        int code = c.getResponseCode();
        InputStream in = code < 400 ? c.getInputStream() : c.getErrorStream();
        ByteArrayOutputStream out = new ByteArrayOutputStream();
        byte[] buf = new byte[8192];
        for (int n; in != null && (n = in.read(buf)) > 0; ) {
            out.write(buf, 0, n);
        }
        c.disconnect();
        return out.toString("UTF-8");
    }
}
