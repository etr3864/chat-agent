#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
קובץ בדיקה למערכת הסיכום האוטומטי
Test file for the Auto Summary System
"""

import time
from datetime import datetime, timedelta
from auto_summarizer import AutoSummarizer, start_auto_summarizer, stop_auto_summarizer, get_auto_summarizer_status

def test_auto_summarizer():
    """בדיקה בסיסית של המערכת"""
    print("🧪 מתחיל בדיקה של מערכת הסיכום האוטומטי...")
    
    # בדוק סטטוס התחלתי
    print(f"📊 סטטוס התחלתי: {get_auto_summarizer_status()}")
    
    # התחל את המערכת
    print("🚀 מפעיל את המערכת...")
    start_auto_summarizer()
    
    # המתן קצת
    time.sleep(2)
    
    # בדוק סטטוס אחרי הפעלה
    print(f"📊 סטטוס אחרי הפעלה: {get_auto_summarizer_status()}")
    
    # הרץ למשך דקה לבדיקה
    print("⏱️ הרצה למשך דקה לבדיקה...")
    for i in range(12):  # 12 פעמים * 5 שניות = דקה
        time.sleep(5)
        status = get_auto_summarizer_status()
        print(f"📊 סטטוס אחרי {i+1} בדיקות: {status}")
        
        # בדוק אם המערכת רצה
        if not status['running']:
            print("⚠️ המערכת נעצרה בטרם עת!")
            break
    
    # עצור את המערכת
    print("🛑 עוצר את המערכת...")
    stop_auto_summarizer()
    
    # בדוק סטטוס סופי
    print(f"📊 סטטוס סופי: {get_auto_summarizer_status()}")
    
    print("✅ בדיקה הושלמה!")

def test_manual_control():
    """בדיקת שליטה ידנית במערכת"""
    print("🎮 בדיקת שליטה ידנית...")
    
    # צור מופע חדש
    summarizer = AutoSummarizer(check_interval=10)  # בדיקה כל 10 שניות
    
    print(f"📊 סטטוס מופע חדש: {summarizer.get_status()}")
    
    # התחל
    summarizer.start()
    print("✅ המערכת הופעלה")
    
    # המתן קצת
    time.sleep(3)
    
    # בדוק סטטוס
    print(f"📊 סטטוס אחרי הפעלה: {summarizer.get_status()}")
    
    # עצור
    summarizer.stop()
    print("🛑 המערכת הופסקה")
    
    # בדוק סטטוס סופי
    print(f"📊 סטטוס סופי: {summarizer.get_status()}")
    
    print("✅ בדיקת שליטה ידנית הושלמה!")

def test_error_handling():
    """בדיקת טיפול בשגיאות"""
    print("🔧 בדיקת טיפול בשגיאות...")
    
    try:
        # נסה ליצור מופע עם פרמטרים לא תקינים
        summarizer = AutoSummarizer(check_interval=-1)  # מרווח שלילי
        print("⚠️ לא הייתה שגיאה עם מרווח שלילי")
    except Exception as e:
        print(f"✅ שגיאה נתפסה כמצופה: {e}")
    
    try:
        # נסה לעצור מערכת שלא רצה
        summarizer = AutoSummarizer()
        summarizer.stop()
        print("✅ עצירה של מערכת שלא רצה עובדת")
    except Exception as e:
        print(f"❌ שגיאה בעצירה: {e}")
    
    print("✅ בדיקת טיפול בשגיאות הושלמה!")

if __name__ == "__main__":
    print("🚀 מתחיל בדיקות מערכת הסיכום האוטומטי")
    print("=" * 50)
    
    try:
        # בדיקה בסיסית
        test_auto_summarizer()
        print("\n" + "=" * 50)
        
        # בדיקת שליטה ידנית
        test_manual_control()
        print("\n" + "=" * 50)
        
        # בדיקת טיפול בשגיאות
        test_error_handling()
        print("\n" + "=" * 50)
        
        print("🎉 כל הבדיקות הושלמו בהצלחה!")
        
    except Exception as e:
        print(f"❌ שגיאה כללית בבדיקות: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n🏁 סיום בדיקות")
