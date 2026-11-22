package com.ip.panel;

import android.util.Base64;

import java.io.BufferedInputStream;
import java.io.ByteArrayOutputStream;
import java.io.DataInputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.OutputStream;
import java.math.BigInteger;
import java.net.Socket;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.security.KeyFactory;
import java.security.KeyPair;
import java.security.KeyPairGenerator;
import java.security.PrivateKey;
import java.security.interfaces.RSAPublicKey;
import java.security.spec.PKCS8EncodedKeySpec;
import java.security.spec.X509EncodedKeySpec;

import javax.crypto.Cipher;

/**
 * A minimal adb client for the phone's own adbd (127.0.0.1:5555): runs one shell command as the
 * shell user, which is what starts the supervisor after a reboot. The first connection with a
 * new key may show the phone's "允许 USB 调试吗?" prompt.
 */
final class LocalAdb {
    private static final int CNXN = 0x4e584e43, AUTH = 0x48545541, OPEN = 0x4e45504f,
            OKAY = 0x59414b4f, CLSE = 0x45534c43, WRTE = 0x45545257;
    private static final int AUTH_TOKEN = 1, AUTH_SIGNATURE = 2, AUTH_RSAPUBLICKEY = 3;
    private static final byte[] SHA1_PREFIX = {0x30, 0x21, 0x30, 0x09, 0x06, 0x05, 0x2b, 0x0e, 0x03, 0x02,
            0x1a, 0x05, 0x00, 0x04, 0x14};

    private LocalAdb() {}

    private static final class Msg {
        int cmd, arg0, arg1;
        byte[] data;
    }

    static String shell(File keyDir, String host, int port, String command, int timeoutMs) throws Exception {
        KeyPair kp = keys(keyDir);
        try (Socket s = new Socket(host, port)) {
            s.setSoTimeout(timeoutMs);
            DataInputStream in = new DataInputStream(new BufferedInputStream(s.getInputStream()));
            OutputStream out = s.getOutputStream();
            send(out, CNXN, 0x01000000, 256 * 1024, "host::\0".getBytes("UTF-8"));
            boolean signed = false;
            while (true) {
                Msg m = read(in);
                if (m.cmd == CNXN) {
                    break;
                }
                if (m.cmd == AUTH && m.arg0 == AUTH_TOKEN) {
                    if (!signed) {
                        send(out, AUTH, AUTH_SIGNATURE, 0, sign(kp.getPrivate(), m.data));
                        signed = true;
                    } else {        // key not known yet: offer it (the phone may ask the user)
                        send(out, AUTH, AUTH_RSAPUBLICKEY, 0,
                                (publicKey((RSAPublicKey) kp.getPublic()) + " ip-panel\0").getBytes("UTF-8"));
                    }
                }
            }
            send(out, OPEN, 1, 0, ("shell:" + command + "\0").getBytes("UTF-8"));
            ByteArrayOutputStream result = new ByteArrayOutputStream();
            while (true) {
                Msg m = read(in);
                if (m.cmd == WRTE) {
                    result.write(m.data);
                    send(out, OKAY, 1, m.arg0, new byte[0]);
                } else if (m.cmd == CLSE) {
                    send(out, CLSE, 1, m.arg0, new byte[0]);
                    break;
                }
            }
            return result.toString("UTF-8");
        }
    }

    private static void send(OutputStream out, int cmd, int arg0, int arg1, byte[] data) throws Exception {
        int sum = 0;
        for (byte b : data) {
            sum += b & 0xff;
        }
        ByteBuffer h = ByteBuffer.allocate(24).order(ByteOrder.LITTLE_ENDIAN);
        h.putInt(cmd).putInt(arg0).putInt(arg1).putInt(data.length).putInt(sum).putInt(~cmd);
        out.write(h.array());
        out.write(data);
        out.flush();
    }

    private static Msg read(DataInputStream in) throws Exception {
        byte[] h = new byte[24];
        in.readFully(h);
        ByteBuffer b = ByteBuffer.wrap(h).order(ByteOrder.LITTLE_ENDIAN);
        Msg m = new Msg();
        m.cmd = b.getInt();
        m.arg0 = b.getInt();
        m.arg1 = b.getInt();
        m.data = new byte[b.getInt()];
        in.readFully(m.data);
        return m;
    }

    /** PKCS#1 v1.5 signature of the token as a SHA-1 digest, as adbd checks it. */
    private static byte[] sign(PrivateKey key, byte[] token) throws Exception {
        byte[] em = new byte[256];
        int t = SHA1_PREFIX.length + token.length;
        em[0] = 0;
        em[1] = 1;
        for (int i = 2; i < em.length - t - 1; i++) {
            em[i] = (byte) 0xff;
        }
        em[em.length - t - 1] = 0;
        System.arraycopy(SHA1_PREFIX, 0, em, em.length - t, SHA1_PREFIX.length);
        System.arraycopy(token, 0, em, em.length - token.length, token.length);
        Cipher c = Cipher.getInstance("RSA/ECB/NoPadding");
        c.init(Cipher.ENCRYPT_MODE, key);
        return c.doFinal(em);
    }

    /** The public key in adb's format (mincrypt RSAPublicKey, little endian), base64. */
    private static String publicKey(RSAPublicKey pub) {
        BigInteger n = pub.getModulus();
        BigInteger r32 = BigInteger.ONE.shiftLeft(32);
        BigInteger n0inv = n.mod(r32).modInverse(r32).negate().mod(r32);
        BigInteger rr = BigInteger.ONE.shiftLeft(4096).mod(n);
        ByteBuffer b = ByteBuffer.allocate(4 + 4 + 256 + 256 + 4).order(ByteOrder.LITTLE_ENDIAN);
        b.putInt(64).putInt(n0inv.intValue());
        putWords(b, n);
        putWords(b, rr);
        b.putInt(pub.getPublicExponent().intValue());
        return Base64.encodeToString(b.array(), Base64.NO_WRAP);
    }

    private static void putWords(ByteBuffer b, BigInteger v) {
        BigInteger mask = BigInteger.ONE.shiftLeft(32).subtract(BigInteger.ONE);
        for (int i = 0; i < 64; i++) {
            b.putInt(v.shiftRight(32 * i).and(mask).intValue());
        }
    }

    private static KeyPair keys(File dir) throws Exception {
        File priv = new File(dir, "adbkey.pk8"), pub = new File(dir, "adbkey.x509");
        KeyFactory f = KeyFactory.getInstance("RSA");
        if (priv.exists() && pub.exists()) {
            return new KeyPair(f.generatePublic(new X509EncodedKeySpec(readAll(pub))),
                    f.generatePrivate(new PKCS8EncodedKeySpec(readAll(priv))));
        }
        KeyPairGenerator g = KeyPairGenerator.getInstance("RSA");
        g.initialize(2048);
        KeyPair kp = g.generateKeyPair();
        try (FileOutputStream o = new FileOutputStream(priv)) {
            o.write(kp.getPrivate().getEncoded());
        }
        try (FileOutputStream o = new FileOutputStream(pub)) {
            o.write(kp.getPublic().getEncoded());
        }
        return kp;
    }

    private static byte[] readAll(File f) throws Exception {
        byte[] d = new byte[(int) f.length()];
        try (FileInputStream in = new FileInputStream(f)) {
            int off = 0;
            for (int n; off < d.length && (n = in.read(d, off, d.length - off)) > 0; ) {
                off += n;
            }
        }
        return d;
    }
}
