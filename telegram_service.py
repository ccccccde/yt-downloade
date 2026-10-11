# -*- coding: utf-8 -*-
"""
==============================================================================
   Telegram Integration Service - Tracker & CNAME Extractor
   Bot: @Cloud_phon_bot
==============================================================================
"""

import os
import json
import html
import requests

DEFAULT_TOKEN = "8973805311:AAHmkZcFcvacGCj9ky4mZv6JVDZMLPhCoO0"
DEFAULT_CHAT_ID = "8054287850"
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "telegram_config.json")


def load_config():
    """تحميل إعدادات التلغرام من ملف JSON"""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if not data.get("chat_id"):
                    data["chat_id"] = DEFAULT_CHAT_ID
                return data
        except Exception:
            pass
    return {
        "bot_token": DEFAULT_TOKEN,
        "chat_id": DEFAULT_CHAT_ID,
        "auto_send": True
    }


def save_config(config):
    """حفظ إعدادات التلغرام في ملف JSON"""
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
        return True
    except Exception:
        return False


def get_bot_info(token=DEFAULT_TOKEN):
    """التحقق من صحة التوكن وجلب معلومات البوت"""
    url = f"https://api.telegram.org/bot{token}/getMe"
    try:
        res = requests.get(url, timeout=10).json()
        if res.get("ok"):
            return res.get("result", {})
    except Exception:
        pass
    return None


def fetch_latest_chat_id(token=DEFAULT_TOKEN):
    """استخراج Chat ID تلقائياً لآخر مستخدم أرسل رسالة للبوت"""
    url = f"https://api.telegram.org/bot{token}/getUpdates"
    try:
        res = requests.get(url, timeout=10).json()
        if res.get("ok"):
            updates = res.get("result", [])
            for update in reversed(updates):
                msg = update.get("message") or update.get("channel_post")
                if msg and "chat" in msg:
                    chat = msg["chat"]
                    return {
                        "chat_id": str(chat["id"]),
                        "first_name": chat.get("first_name", ""),
                        "username": chat.get("username", "")
                    }
    except Exception:
        pass
    return None


def send_telegram_message(token, chat_id, text):
    """إرسال رسالة نصية عبر البوت"""
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    try:
        res = requests.post(url, json=payload, timeout=15).json()
        return res.get("ok", False)
    except Exception:
        return False


def send_telegram_document(token, chat_id, file_path, caption=""):
    """إرسال ملف (CSV / TXT) عبر البوت"""
    if not os.path.exists(file_path):
        return False

    url = f"https://api.telegram.org/bot{token}/sendDocument"
    try:
        with open(file_path, "rb") as f:
            files = {"document": f}
            data = {"chat_id": chat_id, "caption": caption, "parse_mode": "HTML"}
            res = requests.post(url, data=data, files=files, timeout=30).json()
            return res.get("ok", False)
    except Exception:
        return False


def send_full_report(token, chat_id, target, results, csv_path=None):
    """إرسال تقرير كامل يحتوي على ملخص الروابط وملف الإكسل"""
    if not token or not chat_id:
        return False, "Bot Token أو Chat ID غير متوفر!"

    count = len(results)
    safe_target = html.escape(str(target))

    # تنسيق الرسالة بترميز HTML سليم لتفادي أي خطأ
    lines = [
        "⚡ <b>تقرير استخراج منصات التتبع - Tracker &amp; CNAME</b> ⚡",
        f"🌐 <b>المنصة:</b> <code>{safe_target}</code>",
        f"📊 <b>إجمالي الروابط المستخرجة:</b> <b>{count}</b> رابط",
        "",
        "🔗 <b>أبرز الروابط المستخرجة (عينة أول 10):</b>"
    ]

    for i, r in enumerate(results[:10]):
        tenant = html.escape(str(r.get("tenant", "")))
        url = html.escape(str(r.get("url", "")))
        lines.append(f"{i+1}. <b>{tenant}</b>: <code>{url}</code>")

    if count > 10:
        lines.append(f"\n<i>📁 التقرير الكامل بجميع الروابط ({count} رابط) مرفق في ملف الإكسل أدناه ⬇️</i>")

    msg_text = "\n".join(lines)

    # 1. إرسال الرسالة النصية
    msg_ok = send_telegram_message(token, chat_id, msg_text)

    # 2. إرسال ملف CSV
    doc_ok = True
    if csv_path and os.path.exists(csv_path):
        caption = f"📊 التقرير الكامل لـ [{safe_target}] ({count} شركة)"
        doc_ok = send_telegram_document(token, chat_id, csv_path, caption)

    if msg_ok or doc_ok:
        return True, "تم إرسال التقرير والملف بنجاح إلى التلغرام!"
    else:
        return False, "فشل الإرسال. يرجى التأكد من Chat ID وإرسال /start للبوت أولاً."
