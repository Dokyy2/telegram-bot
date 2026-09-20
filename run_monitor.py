"""نقطة تشغيل واحدة لـ Fleet Monitor بعد فحص الجاهزية."""

from __future__ import annotations

from monitor_doctor import main as doctor_main


def main() -> int:
    if doctor_main() != 0:
        print("\nلن يبدأ البوت حتى تكتمل متطلبات الفحص أعلاه.")
        return 1
    from monitor_bot import TelegramMonitor

    TelegramMonitor().run_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
