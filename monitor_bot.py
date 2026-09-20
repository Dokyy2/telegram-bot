"""بوت متابعة فنية بسيط ومستقر لجهاز Termux واحد.

الأوامر المتاحة ثابتة: الحالة، البطارية، الشبكة، التخزين، الصوت، ومدة التشغيل.
"""

from __future__ import annotations

import logging
import socket
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from logging.handlers import RotatingFileHandler
from typing import Callable

import requests

import config
from monitor_tasks import (
    battery_report,
    dashboard_report,
    network_report,
    sound_report,
    storage_report,
    uptime_report,
)


DEVICE_NAME = getattr(config, "DEVICE_NAME", socket.gethostname())
TOKEN = config.TOKEN
ALLOWED_CHAT_ID = int(config.MY_CHAT_ID)
POLL_TIMEOUT_SECONDS = 30
MAX_WORKERS = 2
MAX_QUEUED_JOBS = 4

COMMANDS: dict[str, Callable[[], str]] = {
    "/status": dashboard_report,
    "/battery": battery_report,
    "/network": network_report,
    "/storage": storage_report,
    "/sound": sound_report,
    "/uptime": uptime_report,
}


def configure_logging() -> logging.Logger:
    logger = logging.getLogger("fleet_monitor")
    logger.setLevel(logging.INFO)
    if logger.handlers:
        return logger
    handler = RotatingFileHandler("monitor.log", maxBytes=512_000, backupCount=3, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(handler)
    return logger


class TelegramMonitor:
    def __init__(self) -> None:
        self.base_url = f"https://api.telegram.org/bot{TOKEN}"
        self.logger = configure_logging()
        self.executor = ThreadPoolExecutor(max_workers=MAX_WORKERS, thread_name_prefix="monitor")
        self.job_slots = threading.BoundedSemaphore(MAX_QUEUED_JOBS)
        self.sessions = threading.local()

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

    def send(self, chat_id: int, text: str, keyboard: bool = False) -> None:
        payload: dict[str, object] = {"chat_id": chat_id, "text": text}
        if keyboard:
            payload["reply_markup"] = {
                "inline_keyboard": [
                    [{"text": "📈 الحالة الكاملة", "callback_data": "/status"}],
                    [
                        {"text": "🔋 البطارية", "callback_data": "/battery"},
                        {"text": "📶 الشبكة", "callback_data": "/network"},
                    ],
                    [
                        {"text": "💾 التخزين", "callback_data": "/storage"},
                        {"text": "🔊 الصوت", "callback_data": "/sound"},
                    ],
                    [{"text": "⏱️ مدة التشغيل", "callback_data": "/uptime"}],
                ]
            }
        try:
            self._api("sendMessage", **payload)
        except (requests.RequestException, RuntimeError, ValueError) as error:
            self.logger.error("تعذر إرسال رسالة: %s", error)

    def _run_job(self, chat_id: int, command: str) -> None:
        try:
            report = COMMANDS[command]()
            self.send(chat_id, f"📱 {DEVICE_NAME}\n\n{report}", keyboard=True)
        except Exception:
            self.logger.exception("فشلت المهمة %s", command)
            self.send(chat_id, f"⚠️ {DEVICE_NAME}: تعذر تنفيذ الطلب. راجع monitor.log")
        finally:
            self.job_slots.release()

    def queue_job(self, chat_id: int, command: str) -> None:
        if not self.job_slots.acquire(blocking=False):
            self.send(chat_id, f"⏳ {DEVICE_NAME}: توجد طلبات قيد التنفيذ، جرّب بعد لحظات.")
            return
        self.executor.submit(self._run_job, chat_id, command)

    def _authorized(self, chat_id: int) -> bool:
        if chat_id == ALLOWED_CHAT_ID:
            return True
        self.logger.warning("تم تجاهل طلب من محادثة غير معتمدة: %s", chat_id)
        return False

    def _handle_command(self, chat_id: int, command: str) -> None:
        if not self._authorized(chat_id):
            return
        command = command.split(maxsplit=1)[0].lower()
        if command in {"/start", "/help"}:
            self.send(chat_id, f"✅ {DEVICE_NAME} متصل وجاهز للمتابعة الفنية.", keyboard=True)
        elif command in COMMANDS:
            self.queue_job(chat_id, command)
        else:
            self.send(chat_id, "الأمر غير متاح. استخدم /start لعرض لوحة المتابعة.", keyboard=True)

    def _handle_update(self, update: dict) -> None:
        if "message" in update:
            message = update["message"]
            text = message.get("text")
            if text:
                self._handle_command(message["chat"]["id"], text)
            return
        callback = update.get("callback_query")
        if not callback:
            return
        chat_id = callback["message"]["chat"]["id"]
        try:
            self._api("answerCallbackQuery", callback_query_id=callback["id"], timeout=8)
        except (requests.RequestException, RuntimeError, ValueError) as error:
            self.logger.warning("تعذر تأكيد الزر: %s", error)
        self._handle_command(chat_id, callback.get("data", ""))

    def run_forever(self) -> None:
        offset: int | None = None
        self.logger.info("بدأت المتابعة للجهاز: %s", DEVICE_NAME)
        self.send(ALLOWED_CHAT_ID, f"🟢 {DEVICE_NAME} بدأ ويعمل.", keyboard=True)
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
            except (requests.RequestException, RuntimeError, ValueError) as error:
                self.logger.warning("انقطع الاتصال أو حدث خطأ مؤقت: %s", error)
                time.sleep(5)


if __name__ == "__main__":
    TelegramMonitor().run_forever()
