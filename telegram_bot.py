# -*- coding: utf-8 -*-
"""
==============================================================================
   Telegram Bot Server - Cloud & VPS Edition (Render / VPS Compatible)
   Bot: @Cloud_phon_bot
==============================================================================
"""

import os
import sys
import re
import csv
import time
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import requests

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import telegram_service

BOT_TOKEN = telegram_service.DEFAULT_TOKEN

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

IGNORED_SUBDOMAINS = {
    "api", "app", "tracking", "status", "staging", "dev", "test", "demo",
    "admin", "cdn", "mail", "www", "portal", "login", "dashboard", "help",
    "support", "assets", "static", "images", "img", "m", "mobile", "preview",
    "beta", "docs", "media", "files", "download", "auth", "sso"
}


# ==============================================================================
# خادم ويب خفيف لإبقاء البوت نشطاً على المنصات السحابية المجانية (Render.com)
# ==============================================================================
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.end_headers()
        html = "<h3>⚡ Tracker Telegram Bot is Live 24/7 on Cloud!</h3><p>Status: Healthy</p>"
        self.wfile.write(html.encode("utf-8"))

    def log_message(self, format, *args):
        pass  # تعطيل سجلات الطلبات لتفادي الإزعاج


def start_health_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    print(f"[*] Cloud Health Server listening on port {port}...")
    server.serve_forever()


def search_platform(target):
    """البحث في المصادر السريعة لاستخراج النطاقات"""
    found_subs = set()

    # 1. HackerTarget
    try:
        url_ht = f"https://api.hackertarget.com/hostsearch/?q={target}"
        res = requests.get(url_ht, headers=HEADERS, timeout=8)
        if res.status_code == 200 and "error" not in res.text.lower():
            for line in res.text.splitlines():
                if "," in line:
                    host = line.split(",")[0].strip().lower()
                    if host.endswith(f".{target}"):
                        found_subs.add(host)
    except Exception:
        pass

    # 2. RapidDNS
    try:
        url_rapid = f"https://rapiddns.io/subdomain/{target}?full=1"
        res = requests.get(url_rapid, headers=HEADERS, timeout=8)
        if res.status_code == 200:
            found = re.findall(r"[\w\.-]+\." + re.escape(target), res.text, re.IGNORECASE)
            for d in found:
                d = d.strip().lower()
                if d.endswith(f".{target}"):
                    found_subs.add(d)
    except Exception:
        pass

    # 3. crt.sh
    try:
        url_crt = f"https://crt.sh/?q=%25.{target}&output=json"
        res = requests.get(url_crt, headers=HEADERS, timeout=6)
        if res.status_code == 200:
            for entry in res.json():
                name_val = entry.get("name_value", "")
                for sub in name_val.split("\n"):
                    sub = sub.strip().lower()
                    if "*" not in sub and sub.endswith(f".{target}"):
                        found_subs.add(sub)
    except Exception:
        pass

    results = []
    for sub in found_subs:
        prefix = sub.replace(f".{target}", "").strip()
        if prefix and prefix not in IGNORED_SUBDOMAINS and "." not in prefix:
            results.append({
                "platform": target,
                "tenant": prefix,
                "domain": sub,
                "url": f"https://{sub}"
            })

    results.sort(key=lambda x: x["tenant"])
    return results


def run_bot():
    # تشغيل خادم المنفذ في الخلفية حتى ينجح فحص Render.com
    threading.Thread(target=start_health_server, daemon=True).start()

    print(f"[*] جاري الاتصال بالبوت: @Cloud_phon_bot...")
    bot_info = telegram_service.get_bot_info(BOT_TOKEN)
    if not bot_info:
        print("[-] خطأ: فشل التحقق من توكن البوت!")
        return

    bot_username = bot_info.get("username", "")
    print(f"[✓] البوت يعمل بنجاح! المعرف: @{bot_username}")
    print("[*] في انتظار الأوامر من مستخدمي التلغرام...")

    last_update_id = 0

    while True:
        try:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates?offset={last_update_id + 1}&timeout=30"
            res = requests.get(url, timeout=35).json()

            if not res.get("ok"):
                time.sleep(2)
                continue

            updates = res.get("result", [])
            for update in updates:
                last_update_id = update["update_id"]
                msg = update.get("message")
                if not msg or "text" not in msg:
                    continue

                chat_id = str(msg["chat"]["id"])
                user_text = msg["text"].strip()
                sender_name = msg["from"].get("first_name", "User")

                print(f"[*] رسالة جديدة من {sender_name} ({chat_id}): {user_text}", flush=True)

                config = telegram_service.load_config()
                config["chat_id"] = chat_id
                telegram_service.save_config(config)

                if user_text.startswith("/start") or user_text.startswith("/help"):
                    welcome = (
                        f"👋 مرحباً بك يا <b>{sender_name}</b>!\n\n"
                        f"🤖 أنا بوت <b>Tracker &amp; CNAME Extractor</b>.\n\n"
                        f"🆔 معرف حسابك (Chat ID):\n<code>{chat_id}</code>\n\n"
                        f"📌 <b>كيف تستخدمني؟</b>\n"
                        f"أرسل اسم أي منصة تتبع مستهدفة مباشرة في رسالة، مثلاً:\n"
                        f"👉 <code>everflowclient.io</code>\n"
                        f"👉 <code>go2cloud.org</code>\n\n"
                        f"وسأقوم فوراً بفحص كافة النطاقات واستخراج روابط المعلنين والشركات وإرسال ملف الإكسل (CSV) إليك! 🚀"
                    )
                    telegram_service.send_telegram_message(BOT_TOKEN, chat_id, welcome)

                elif user_text.startswith("/id"):
                    telegram_service.send_telegram_message(BOT_TOKEN, chat_id, f"معرف حسابك (Chat ID) هو:\n<code>{chat_id}</code>")

                else:
                    target = user_text.lower().replace("https://", "").replace("http://", "").split("/")[0].strip()
                    if "." not in target:
                        telegram_service.send_telegram_message(
                            BOT_TOKEN, chat_id,
                            "⚠️ يرجى إرسال اسم نطاق صحيح، مثال: <code>everflowclient.io</code>"
                        )
                        continue

                    telegram_service.send_telegram_message(
                        BOT_TOKEN, chat_id,
                        f"⏳ <b>جاري البحث في قاعدة البيانات عن:</b> <code>{target}</code>...\nيرجى الانتظار ثوانٍ معدودة."
                    )

                    results = search_platform(target)

                    if not results:
                        telegram_service.send_telegram_message(
                            BOT_TOKEN, chat_id,
                            f"❌ لم يتم العثور على أي نطاقات نشطة لـ <code>{target}</code>."
                        )
                    else:
                        csv_filename = os.path.join(
                            os.path.dirname(os.path.abspath(__file__)),
                            f"results_{target.replace('.', '_')}.csv"
                        )
                        with open(csv_filename, "w", newline="", encoding="utf-8-sig") as f:
                            writer = csv.writer(f)
                            writer.writerow(["Platform", "Company/Tenant", "Full Domain", "Direct Link"])
                            for r in results:
                                writer.writerow([r["platform"], r["tenant"], r["domain"], r["url"]])

                        telegram_service.send_full_report(BOT_TOKEN, chat_id, target, results, csv_filename)

        except Exception as e:
            time.sleep(2)


if __name__ == "__main__":
    try:
        run_bot()
    except KeyboardInterrupt:
        print("\n[!] تم إيقاف البوت.")
