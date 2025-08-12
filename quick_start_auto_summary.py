#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
הפעלה מהירה של מערכת הסיכום האוטומטי
Quick start for the Auto Summary System
"""

import os
import sys
import time
from datetime import datetime

def main():
    """הפעלה מהירה של המערכת"""
    print("🚀 מערכת הסיכום האוטומטי - הפעלה מהירה")
    print("=" * 50)
    
    # בדוק אם יש את כל הקבצים הנדרשים
    required_files = [
        "auto_summarizer.py",
        "chatbot.py",
        "whatsapp_webhook.py"
    ]
    
    missing_files = []
    for file in required_files:
        if not os.path.exists(file):
            missing_files.append(file)
    
    if missing_files:
        print(f"❌ קבצים חסרים: {', '.join(missing_files)}")
        print("אנא וודא שכל הקבצים נמצאים בתיקייה הנוכחית")
        return False
    
    print("✅ כל הקבצים הנדרשים נמצאים")
    
    try:
        # ייבא את המערכת
        print("📥 מייבא את מערכת הסיכום האוטומטי...")
        from auto_summarizer import start_auto_summarizer, get_auto_summarizer_status
        
        # בדוק סטטוס התחלתי
        print("📊 סטטוס התחלתי:")
        status = get_auto_summarizer_status()
        for key, value in status.items():
            print(f"   {key}: {value}")
        
        # התחל את המערכת
        print("\n🚀 מפעיל את המערכת...")
        start_auto_summarizer()
        
        # המתן קצת
        time.sleep(2)
        
        # בדוק סטטוס אחרי הפעלה
        print("\n📊 סטטוס אחרי הפעלה:")
        status = get_auto_summarizer_status()
        for key, value in status.items():
            print(f"   {key}: {value}")
        
        if status['running']:
            print("\n✅ המערכת הופעלה בהצלחה!")
            print("🔍 המערכת תבדוק שיחות ישנות כל 5 דקות")
            print("⏰ שיחות שעברו יותר משעה יקבלו סיכום אוטומטי")
            print("💡 שלח 'בדוק סיכום' למנהל כדי לראות סטטוס")
            
            # הרץ למשך דקה לבדיקה
            print("\n⏱️ הרצה למשך דקה לבדיקה...")
            start_time = datetime.now()
            
            try:
                while True:
                    time.sleep(10)  # בדיקה כל 10 שניות
                    elapsed = (datetime.now() - start_time).total_seconds()
                    
                    if elapsed >= 60:  # דקה
                        break
                    
                    # הדפס סטטוס כל 10 שניות
                    status = get_auto_summarizer_status()
                    print(f"📊 {elapsed:.0f}s: {status['total_conversations']} שיחות, {status['summarized_conversations']} מסוכמות")
                    
            except KeyboardInterrupt:
                print("\n🛑 עצירה ידנית...")
            
            print("\n✅ בדיקה הושלמה!")
            return True
            
        else:
            print("❌ המערכת לא הופעלה")
            return False
            
    except ImportError as e:
        print(f"❌ שגיאה בייבוא: {e}")
        print("אנא וודא שכל התלויות מותקנות:")
        print("pip install -r requirements.txt")
        return False
        
    except Exception as e:
        print(f"❌ שגיאה כללית: {e}")
        import traceback
        traceback.print_exc()
        return False

def show_help():
    """הצג עזרה"""
    print("""
📖 עזרה - מערכת הסיכום האוטומטי

🎯 מטרה:
מערכת זו מבצעת סיכום אוטומטי של שיחות WhatsApp 
שעברו יותר משעה מההודעה האחרונה.

⚡ איך זה עובד:
1. המערכת בודקת כל 5 דקות את כל השיחות
2. מזהה שיחות שעברו יותר משעה
3. מבצעת סיכום אוטומטי לשיחות ישנות
4. שומרת את הסיכום בקבצים ו-MongoDB

🚀 הפעלה:
python quick_start_auto_summary.py

📊 פקודות מנהל (WhatsApp):
- "בדוק סיכום" - בדוק סטטוס המערכת
- "הפעל סיכום" - הפעל את המערכת
- "עצור סיכום" - עצור את המערכת
- "סכם הכל" - סיכום כפוי לכל השיחות

📁 קבצים:
- auto_summarizer.py - המערכת הראשית
- chatbot.py - אינטגרציה עם הבוט
- whatsapp_webhook.py - אינטגרציה עם השרת

🔧 הגדרות:
- מרווח בדיקה: 5 דקות (300 שניות)
- זמן סיכום: שעה (3600 שניות)
- מינימום הודעות: 5 הודעות לשיחה

💡 טיפים:
- המערכת רצה אוטומטית כשהשרת עולה
- לא מפריעה לפעילות הרגילה של הבוט
- מונעת סיכום כפול של שיחות
- מטפלת בשגיאות בצורה חכמה
""")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ["--help", "-h", "help"]:
        show_help()
    else:
        success = main()
        if success:
            print("\n🎉 המערכת פועלת בהצלחה!")
            print("💡 שלח 'בדוק סיכום' למנהל כדי לראות סטטוס")
        else:
            print("\n❌ הפעלת המערכת נכשלה")
            print("💡 שלח 'python quick_start_auto_summary.py --help' לעוד מידע")
