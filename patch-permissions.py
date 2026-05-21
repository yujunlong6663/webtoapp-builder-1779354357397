#!/usr/bin/env python3
import os
import shutil
import glob
import re

print("=== Patching Android project (v3.4) ===")

MANIFEST = "android/app/src/main/AndroidManifest.xml"

if not os.path.exists(MANIFEST):
    print("ERROR: AndroidManifest.xml not found!")
    print("Listing android/ directory:")
    for root, dirs, files in os.walk("android"):
        for f in files:
            print(os.path.join(root, f))
    exit(1)

# 1. Modify AndroidManifest.xml using string replacement (preserves formatting)
with open(MANIFEST, "r", encoding="utf-8") as f:
    manifest = f.read()

manifest_perms = ['android.permission.ACCESS_FINE_LOCATION', 'android.permission.ACCESS_COARSE_LOCATION', 'android.permission.CAMERA', 'android.permission.CALL_PHONE', 'android.permission.READ_PHONE_STATE']
for perm in manifest_perms:
    if perm not in manifest:
        tag = '    <uses-permission android:name="' + perm + '" />'
        manifest = manifest.replace('</manifest>', tag + '\n</manifest>')
        print("Added permission: " + perm)

if 'usesCleartextTraffic' not in manifest:
    manifest = manifest.replace('<application', '<application android:usesCleartextTraffic="true"')
    print("Added usesCleartextTraffic=true")

if 'android.intent.action.DIAL' not in manifest:
    if '<queries>' in manifest:
        tel_block = '''        <intent>
            <action android:name="android.intent.action.DIAL" />
            <data android:scheme="tel" />
        </intent>'''
        manifest = manifest.replace('<queries>', '<queries>\n' + tel_block)
    else:
        tel_block = '''    <queries>
        <intent>
            <action android:name="android.intent.action.DIAL" />
            <data android:scheme="tel" />
        </intent>
    </queries>'''
        manifest = manifest.replace('<application', tel_block + '\n    <application')
    print("Added tel intent query")

with open(MANIFEST, "w", encoding="utf-8") as f:
    f.write(manifest)
print("AndroidManifest.xml updated")

# 2. Replace MainActivity.java
activity_dir = "android/app/src/main/java/com/webtoapp/appu1q2m8"
for f in glob.glob("android/app/src/main/java/**/MainActivity.*", recursive=True):
    os.remove(f)
    print("Removed: " + f)
os.makedirs(activity_dir, exist_ok=True)

MAINACTIVITY_JAVA = r"""package com.webtoapp.appu1q2m8;

import android.app.AlertDialog;
import android.content.Context;
import android.content.DialogInterface;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.location.LocationManager;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.provider.Settings;
import android.util.Log;
import android.webkit.WebView;
import androidx.core.app.ActivityCompat;
import androidx.core.content.ContextCompat;
import com.getcapacitor.BridgeActivity;

public class MainActivity extends BridgeActivity {

    private static final String TAG = "WebToApp";
    private static final int PERM_REQ = 100;
    private String[] reqPerms = new String[]{"android.permission.ACCESS_FINE_LOCATION", "android.permission.ACCESS_COARSE_LOCATION", "android.permission.CAMERA", "android.permission.CALL_PHONE", "android.permission.READ_PHONE_STATE"};
    private Handler gpsTimer = null;

    @Override
    public void onCreate(Bundle b) {
        super.onCreate(b);
        Log.d(TAG, "onCreate");
        requestPerms();
        new Handler(Looper.getMainLooper()).postDelayed(new Runnable() {
            public void run() { setupGps(); }
        }, 1500);
        new Handler(Looper.getMainLooper()).postDelayed(new Runnable() {
            public void run() { checkGpsEnabled(); }
        }, 2500);
    }

    @Override
    public void onResume() {
        super.onResume();
        requestPerms();
        new Handler(Looper.getMainLooper()).postDelayed(new Runnable() {
            public void run() { checkGpsEnabled(); }
        }, 500);
    }

    private void setupGps() {
        try {
            if (getBridge() == null) {
                new Handler(Looper.getMainLooper()).postDelayed(new Runnable() {
                    public void run() { setupGps(); }
                }, 2000);
                return;
            }
            WebView wv = getBridge().getWebView();
            if (wv == null) {
                new Handler(Looper.getMainLooper()).postDelayed(new Runnable() {
                    public void run() { setupGps(); }
                }, 2000);
                return;
            }
            injectGps(wv);
            gpsTimer = new Handler(Looper.getMainLooper());
            gpsTimer.postDelayed(new Runnable() {
                public void run() {
                    if (gpsTimer == null) return;
                    try {
                        WebView v = getBridge().getWebView();
                        if (v != null) injectGps(v);
                    } catch (Exception ex) {
                        Log.e(TAG, "GPS inject err: " + ex.getMessage());
                    }
                    if (gpsTimer != null) gpsTimer.postDelayed(this, 5000);
                }
            }, 5000);
            Log.d(TAG, "GPS override started");
        } catch (Exception e) {
            Log.e(TAG, "GPS setup err: " + e.getMessage());
        }
    }

    private void injectGps(WebView wv) {
        String js = "(function(){if(!navigator.geolocation)return;var g=navigator.geolocation;var og=g.getCurrentPosition.bind(g);var ow=g.watchPosition.bind(g);var CG=(window.Capacitor&&window.Capacitor.Plugins)?window.Capacitor.Plugins.Geolocation:null;g.getCurrentPosition=function(s,e,o){o=o||{};o.enableHighAccuracy=true;o.maximumAge=0;if(o.timeout===undefined)o.timeout=30000;if(CG){CG.getCurrentPosition(o).then(function(p){if(s)s({coords:p.coords,timestamp:p.timestamp})}).catch(function(er){if(e)e({code:1,message:er.message||String(er)})})}else{og(s,e,o)}};g.watchPosition=function(s,e,o){o=o||{};o.enableHighAccuracy=true;o.maximumAge=0;if(CG){return CG.watchPosition(o,function(p){if(s)s({coords:p.coords,timestamp:p.timestamp})},function(er){if(e)e({code:1,message:er.message||String(er)})})}else{return ow(s,e,o)}}})();";
        wv.evaluateJavascript(js, null);
    }

    private void checkGpsEnabled() {
        try {
            LocationManager lm = (LocationManager) getSystemService(Context.LOCATION_SERVICE);
            if (lm != null && !lm.isProviderEnabled(LocationManager.GPS_PROVIDER)) {
                new AlertDialog.Builder(this)
                    .setTitle("GPS未开启")
                    .setMessage("应用需要GPS定位服务，请开启GPS后重新打开应用")
                    .setPositiveButton("去设置", new DialogInterface.OnClickListener() {
                        public void onClick(DialogInterface dialog, int which) {
                            startActivity(new Intent(Settings.ACTION_LOCATION_SOURCE_SETTINGS));
                        }
                    })
                    .setNegativeButton("取消", null)
                    .show();
            }
        } catch (Exception e) {
            Log.e(TAG, "GPS check err: " + e.getMessage());
        }
    }

    @Override
    public void onDestroy() {
        gpsTimer = null;
        super.onDestroy();
    }

    private void requestPerms() {
        if (reqPerms == null || reqPerms.length == 0) return;
        java.util.ArrayList needed = new java.util.ArrayList();
        for (int i = 0; i < reqPerms.length; i++) {
            if (ContextCompat.checkSelfPermission(this, reqPerms[i]) != PackageManager.PERMISSION_GRANTED) {
                needed.add(reqPerms[i]);
            }
        }
        if (needed.size() > 0) {
            String[] perms = new String[needed.size()];
            for (int j = 0; j < needed.size(); j++) perms[j] = (String)needed.get(j);
            ActivityCompat.requestPermissions(this, perms, PERM_REQ);
        }
    }

    @Override
    public void onRequestPermissionsResult(int reqCode, String[] perms, int[] results) {
        super.onRequestPermissionsResult(reqCode, perms, results);
    }
}
"""

with open(os.path.join(activity_dir, "MainActivity.java"), "w") as f:
    f.write(MAINACTIVITY_JAVA)
print("Created MainActivity.java (" + str(len(MAINACTIVITY_JAVA)) + " bytes)")

# 3. Update app name in strings.xml
strings_xml = "android/app/src/main/res/values/strings.xml"
app_name_value = "营口CRM"
if os.path.exists(strings_xml):
    with open(strings_xml, "r", encoding="utf-8") as f:
        content = f.read()
    # Only replace app_name and title_activity_main values, NOT package_name/custom_url_scheme
    content = re.sub(r'(<string name="app_name">)[^<]*(</string>)', r'\g<1>' + app_name_value + r'\g<2>', content)
    content = re.sub(r'(<string name="title_activity_main">)[^<]*(</string>)', r'\g<1>' + app_name_value + r'\g<2>', content)
    if 'app_name' not in content:
        content = content.replace('</resources>', '    <string name="app_name">' + app_name_value + '</string>\n</resources>')
    with open(strings_xml, "w", encoding="utf-8") as f:
        f.write(content)
    print("Updated strings.xml with app_name=" + app_name_value)
else:
    os.makedirs(os.path.dirname(strings_xml), exist_ok=True)
    with open(strings_xml, "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="utf-8"?>\n<resources>\n    <string name="app_name">' + app_name_value + '</string>\n    <string name="title_activity_main">' + app_name_value + '</string>\n</resources>\n')
    print("Created strings.xml with app_name=" + app_name_value)

# 4. Replace icons
icon_src = "app-icon.png"
if os.path.exists(icon_src):
    print("Custom icon detected, replacing all icon variants...")
    for density in ["mdpi", "hdpi", "xhdpi", "xxhdpi", "xxxhdpi"]:
        mipmap_dir = "android/app/src/main/res/mipmap-" + density
        os.makedirs(mipmap_dir, exist_ok=True)
        for icon_name in ["ic_launcher.png", "ic_launcher_round.png", "ic_launcher_foreground.png"]:
            shutil.copy2(icon_src, os.path.join(mipmap_dir, icon_name))
    # Remove adaptive icon XML to force using PNG icons
    for xml_file in glob.glob("android/app/src/main/res/**/ic_launcher.xml", recursive=True):
        os.remove(xml_file)
        print("Removed adaptive icon: " + xml_file)
    for xml_file in glob.glob("android/app/src/main/res/**/ic_launcher_round.xml", recursive=True):
        os.remove(xml_file)
        print("Removed adaptive round icon: " + xml_file)
    print("All icon variants replaced")
else:
    print("No custom icon, keeping defaults")

print("=== Patch completed! ===")

# 5. Verify: ensure package name in MainActivity matches directory
ma_path = os.path.join(activity_dir, "MainActivity.java")
if os.path.exists(ma_path):
    with open(ma_path, "r") as f:
        first_line = f.readline().strip()
    print("MainActivity.java package: " + first_line)
    expected_pkg = "package " + "com.webtoapp.appu1q2m8" + ";"
    if first_line != expected_pkg:
        print("WARNING: Package mismatch! Expected: " + expected_pkg + " Got: " + first_line)
    else:
        print("Package name verification OK")
else:
    print("ERROR: MainActivity.java not created at " + ma_path)
    exit(1)
