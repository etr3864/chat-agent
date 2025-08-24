# worker_min.py
"""
Minimal Background Worker for Render
-----------------------------------
מריץ את הסקד'ולר הקיים שלך בלופ אינסופי כתהליך נפרד.
נדרש שהפונקציה run_auto_summary_scheduler תוגדר בקובץ whatsapp_webhook.py.

הערות:
- אל תגדיר ENABLE_SCHEDULER=1 בשירות ה-Web כדי שלא ירוץ שם גם.
- ודא שכל משתני הסביבה (Mongo/OpenAI/UltraMsg וכו') קיימים גם בשירות ה-Worker.
"""

import os
import sys
import traceback

# מומלץ לוודא שה־web לא ירים את הסקד'ולר:
os.environ.setdefault("ENABLE_SCHEDULER", "0")

try:
    # נייבא את פונקציית הסקד'ולר מתוך הקוד הקיים שלך
    from whatsapp_webhook import run_auto_summary_scheduler
except Exception:
    print("[worker_min] ERROR: failed to import run_auto_summary_scheduler from whatsapp_webhook.py", file=sys.stderr)
    print(traceback.format_exc(), file=sys.stderr)
    sys.exit(1)


def main() -> None:
    """
    מפעיל את הסקד'ולר: יוצר משימות schedule ורץ בלולאה (כבר ממומש אצלך).
    אין צורך להוסיף כאן לולאת sleep — היא קיימת בתוך run_auto_summary_scheduler().
    """
    print("[worker_min] Starting auto-summary scheduler worker...")
    try:
        run_auto_summary_scheduler()
    except Exception:
        print("[worker_min] ERROR: scheduler crashed", file=sys.stderr)
        print(traceback.format_exc(), file=sys.stderr)
        # ב־Render, יציאה בקוד שגיאה תגרום לריסטארט אוטומטי של ה־Worker
        sys.exit(1)


if __name__ == "__main__":
    main()
