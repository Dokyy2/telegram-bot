"""مهام المتابعة الفنية المسموح بها لأجهزة Termux.
لا يقبل هذا الملف أوامر من الخارج؛ كل الأوامر ثابتة ومخصصة لتشخيص حالة الجهاز.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any

def _termux_json(program: str, timeout: int = 15) -> dict[str, Any] | list[dict[str, Any]]:
    """شغّل برنامج Termux ثابتًا وأعد ناتجه JSON بصورة آمنة."""
    result = subprocess.run(
        [program], capture_output=True, check=True, text=True, timeout=timeout
    )
    if not result.stdout.strip():
        return {}
    return json.loads(result.stdout)

def _error(label: str, error: Exception) -> str:
    return f"⚠️ تعذر قراءة {label}: {error}"

def battery_report() -> str:
    try:
        data = _termux_json("termux-battery-status")
        assert isinstance(data, dict)
        return (
            "🔋 *تفاصيل البطارية*\n"
            f"⚡ النسبة: {data.get('percentage', 'غير متاح')}%\n"
            f"🔌 الحالة: {data.get('status', 'غير متاح')}\n"
            f"🔌 متصل بالشاحن: {data.get('plugged', 'غير متاح')}\n"
            f"🌡️ الحرارة: {data.get('temperature', 'غير متاح')}°C\n"
            f"🩺 الصحة: {data.get('health', 'غير متاح')}"
        )
    except Exception as error:
        return _error("حالة البطارية", error)

def network_report() -> str:
    try:
        data = _termux_json("termux-wifi-connectioninfo")
        assert isinstance(data, dict)
        ssid = data.get("ssid")
        if not ssid or ssid == "<unknown ssid>":
            return "📶 *الشبكة*\nالاتصال: بيانات هاتف (Mobile Data) أو لا توجد شبكة Wi‑Fi متاحة"
        ip = data.get("ip", "غير متاح")
        return f"📶 *الشبكة (Wi-Fi)*\n🌐 اسم الشبكة: `{ssid}`\n🔗 عنوان IP: `{ip}`"
    except Exception as error:
        return _error("حالة الشبكة", error)

def storage_report() -> str:
    try:
        stats = os.statvfs(Path.home())
        total_gb = (stats.f_blocks * stats.f_frsize) / (1024**3)
        free_gb = (stats.f_bavail * stats.f_frsize) / (1024**3)
        used_gb = total_gb - free_gb
        usage = (used_gb / total_gb * 100) if total_gb else 0
        return (
            "📊 *حالة الجهاز (التخزين)*\n"
            f"💾 المستخدم: {used_gb:.2f} GB ({usage:.0f}%)\n"
            f"💾 المتاح: {free_gb:.2f} GB\n"
            f"💾 الإجمالي: {total_gb:.2f} GB"
        )
    except OSError as error:
        return _error("التخزين", error)

def sound_report() -> str:
    try:
        data = _termux_json("termux-volume")
        assert isinstance(data, list)
        lines = ["🔊 *مستويات الصوت*"]
        for item in data:
            stream = item.get("stream", "غير معروف")
            lines.append(f"🔹 {stream}: `{item.get('volume', '?')}/{item.get('max_volume', '?')}`")
        return "\n".join(lines)
    except Exception as error:
        return _error("مستويات الصوت", error)

def uptime_report() -> str:
    try:
        result = subprocess.run(
            ["uptime", "-p"], capture_output=True, check=True, text=True, timeout=5
        )
        return f"⏱️ *التشغيل*\n{result.stdout.strip()}"
    except Exception as error:
        return _error("مدة التشغيل", error)

def dashboard_report() -> str:
    return "\n\n".join([battery_report(), network_report(), storage_report(), uptime_report()])

def sms_report() -> str:
    try:
        messages = _termux_json("termux-sms-list -l 10")
        assert isinstance(messages, list)
        if not messages:
            return "📨 *الرسائل:* لا توجد رسائل."
            
        report = "📨 *آخر 10 رسائل SMS:*\n" + "—" * 20 + "\n\n"
        for idx, msg in enumerate(messages, start=1):
            sender = msg.get('number', 'مجهول')
            body = msg.get('body', '')
            date = msg.get('date', '')
            report += f"*{idx}. المرسل: {sender}*\n💬 النص: {body}\n⏱️ الوقت: {date}\n\n"
        return report
    except Exception as error:
        return _error("الرسائل", error)

def call_logs_report(limit: int = 10) -> str:
    try:
        result = subprocess.check_output(f"termux-call-log -l {limit}", shell=True, timeout=15)
        calls = json.loads(result.decode('utf-8', errors='ignore'))
        
        if not calls:
            return "📱 *سجل المكالمات:* لا توجد سجلات."
            
        report = f"📱 *سجل آخر {limit} مكالمة:*\n" + "—" * 20 + "\n\n"
        for idx, call in enumerate(reversed(calls), start=1):
            raw_name = str(call.get('name') or "").strip()
            # التعديل هنا: قراءة الحقل الصحيح الجديد phone_number بدلاً من number
            raw_number = str(call.get('phone_number') or call.get('number') or "").strip()
            
            ignore_list = ['unknown', 'unknown caller', 'null', 'none', '-1']
            if raw_name.lower() in ignore_list:
                raw_name = ""
            if raw_number.lower() in ignore_list:
                raw_number = ""
                
            if raw_name and raw_number and raw_name != raw_number:
                display_info = f"{raw_name} ({raw_number})"
            elif raw_number:
                display_info = f"{raw_number}"
            elif raw_name:
                display_info = f"{raw_name}"
            else:
                display_info = "رقم غير مسجل"
            
            call_type = call.get('type', '')
            date = call.get('date', '')
            duration = call.get('duration', '0')
            type_icon = "↗️ صادرة" if call_type == 'OUTGOING' else ("↙️ واردة" if call_type == 'INCOMING' else ("❌ فائتة" if call_type == 'MISSED' else call_type))

            report += f"*{idx}. {display_info}*\n   ├ النوع: {type_icon}\n   ├ الوقت: {date}\n   └ المدة: {duration} ثانية\n\n"
        return report
    except Exception as error:
        return _error("سجل المكالمات", error)

def location_report() -> str:
    try:
        result = subprocess.check_output("termux-location -p gps -c 1", shell=True, timeout=20)
        loc_data = json.loads(result.decode('utf-8', errors='ignore'))
        if lat := loc_data.get('latitude'):
            return f"📍 *تم تحديد الموقع بنجاح:*\n🔗 [عرض على الخريطة](https://maps.google.com/?q={lat},{loc_data.get('longitude')})"
        return "❌ تعذر الحصول على الإحداثيات، تأكد من تشغيل الـ GPS."
    except Exception as error:
        return _error("الموقع الجغرافي", error)