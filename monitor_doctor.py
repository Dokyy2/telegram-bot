"""فحص جاهزية Fleet Monitor قبل التشغيل على Termux."""

from __future__ import annotations

import importlib
import shutil
import sys
from dataclasses import dataclass


SYSTEM_PROGRAMS = (
    "uptime",
)

REQUIRED_CONFIG = ("TOKEN", "MY_CHAT_ID")


@dataclass(frozen=True)
class CheckResult:
    label: str
    passed: bool
    detail: str


def run_checks() -> list[CheckResult]:
    results: list[CheckResult] = []
    
    missing_programs = [program for program in TERMUX_PROGRAMS if shutil.which(program) is None]
    results.append(
        CheckResult(
            "أدوات Termux",
            not missing_programs,
            "كل أدوات المتابعة موجودة."
            if not missing_programs
            else f"الناقص: {', '.join(missing_programs)}. ثبّت حزمة termux-api أولًا.",
        )
    )
    
    missing_system_programs = [program for program in SYSTEM_PROGRAMS if shutil.which(program) is None]
    results.append(
        CheckResult(
            "أدوات النظام",
            not missing_system_programs,
            "أدوات النظام الأساسية موجودة."
            if not missing_system_programs
            else f"الناقص: {', '.join(missing_system_programs)}.",
        )
    )

    try:
        config = importlib.import_module("config")
        missing_config = [name for name in REQUIRED_CONFIG if not getattr(config, name, None)]
        results.append(
            CheckResult(
                "إعدادات البوت",
                not missing_config,
                "TOKEN وMY_CHAT_ID موجودان دون إظهار قيمهما."
                if not missing_config
                else f"الناقص في config.py: {', '.join(missing_config)}",
            )
        )
    except Exception as error:
        results.append(CheckResult("إعدادات البوت", False, f"تعذر قراءة config.py: {error}"))

    return results


def ready() -> bool:
    return all(result.passed for result in run_checks())


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    results = run_checks()
    for result in results:
        marker = "✅" if result.passed else "❌"
        print(f"{marker} {result.label}: {result.detail}")
    return 0 if all(result.passed for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())