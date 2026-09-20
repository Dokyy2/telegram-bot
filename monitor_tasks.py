"""مهام المتابعة الفنية المسموح بها لأجهزة Termux.

لا يقبل هذا الملف أوامر من الخارج؛ كل الأوامر ثابتة ومخصصة لتشخيص حالة الجهاز.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any


def _termux_json(program: str, timeout: int = 8) -> dict[str, Any] | list[dict[str, Any]]:
    """شغّل برنامج Termux ثابتًا وأعد ناتجه JSON بصورة آمنة."""
    result = subprocess.run(
        [program], capture_output=True, check=True, text=True, timeout=timeout
    )
    return json.loads(result.stdout)


def _error(label: str, error: Exception) -> str:
    return f"⚠️ تعذر قراءة {label}: {error}"


def battery_report() -> str:
    try:
        data = _termux_json("termux-battery-status")
        assert isinstance(data, dict)
        return (
            "🔋 البطارية\n"
            f"النسبة: {data.get('percentage', 'غير متاح')}%\n"
            f"الحالة: {data.get('status', 'غير متاح')}\n"
            f"الشحن: {data.get('plugged', 'غير متاح')}\n"
            f"الحرارة: {data.get('temperature', 'غير متاح')}°C\n"
            f"الصحة: {data.get('health', 'غير متاح')}"
        )
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError, AssertionError) as error:
        return _error("حالة البطارية", error)


def network_report() -> str:
    try:
        data = _termux_json("termux-wifi-connectioninfo")
        assert isinstance(data, dict)
        ssid = data.get("ssid")
        if not ssid or ssid == "<unknown ssid>":
            return "📶 الشبكة\nالاتصال: بيانات هاتف أو لا توجد شبكة Wi‑Fi متاحة"
        return f"📶 الشبكة\nالاتصال: Wi‑Fi\nاسم الشبكة: {ssid}"
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError, AssertionError) as error:
        return _error("حالة الشبكة", error)


def storage_report() -> str:
    try:
        stats = os.statvfs(Path.home())
        total_gb = (stats.f_blocks * stats.f_frsize) / (1024**3)
        free_gb = (stats.f_bavail * stats.f_frsize) / (1024**3)
        used_gb = total_gb - free_gb
        usage = (used_gb / total_gb * 100) if total_gb else 0
        return (
            "💾 التخزين المتاح لتطبيق Termux\n"
            f"المستخدم: {used_gb:.2f} GB ({usage:.0f}%)\n"
            f"المتاح: {free_gb:.2f} GB\n"
            f"الإجمالي: {total_gb:.2f} GB"
        )
    except OSError as error:
        return _error("التخزين", error)


def sound_report() -> str:
    try:
        data = _termux_json("termux-volume")
        assert isinstance(data, list)
        lines = ["🔊 مستويات الصوت"]
        for item in data:
            stream = item.get("stream", "غير معروف")
            lines.append(f"{stream}: {item.get('volume', '?')}/{item.get('max_volume', '?')}")
        return "\n".join(lines)
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError, AssertionError) as error:
        return _error("مستويات الصوت", error)


def uptime_report() -> str:
    try:
        result = subprocess.run(
            ["uptime", "-p"], capture_output=True, check=True, text=True, timeout=5
        )
        return f"⏱️ التشغيل\n{result.stdout.strip()}"
    except (OSError, subprocess.SubprocessError) as error:
        return _error("مدة التشغيل", error)


def dashboard_report() -> str:
    """ملخص واحد سريع؛ لا يجمع أي محتوى شخصي من الجهاز."""
    return "\n\n".join(
        [battery_report(), network_report(), storage_report(), uptime_report()]
    )
