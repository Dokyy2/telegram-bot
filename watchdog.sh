#!/data/data/com.termux/files/usr/bin/bash

# 1. منع النظام من تجميد المعالج أثناء قفل الشاشة
termux-wake-lock

# 2. الانتقال لمجلد البوت
cd /data/data/com.termux/files/home/telegram-bot || cd /data/data/com.termux/files/home

# 3. حلقة المراقبة وإعادة التشغيل الصامت
while true; do
    # التأكد من وجود إنترنت قبل المحاولة لتفادي استهلاك المعالج
    until ping -c 1 8.8.8.8 >/dev/null 2>&1; do
        sleep 5
    done

    # تشغيل البوت وإعادة تشغيله فوراً إذا سقط
    python3 interactive_bot.py > /dev/null 2>&1

    # الانتظار قبل إعادة المحاولة في حال وجود خطأ في الكود
    sleep 3
done
