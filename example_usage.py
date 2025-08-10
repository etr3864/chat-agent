#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
דוגמה לשימוש בפונקציות החדשות למניעת כפילויות ב-MongoDB
"""

from mongodb_manager import mongodb_manager
from datetime import datetime

def example_usage():
    """דוגמה לשימוש בפונקציות החדשות"""
    
    print("🚀 דוגמה לשימוש בפונקציות החדשות למניעת כפילויות")
    
    # דוגמה 1: יצירת ליד חדש
    print("\n📝 דוגמה 1: יצירת ליד חדש")
    lead_data = {
        "customer_name": "ישראל ישראלי",
        "summary": "לקוח מתעניין במוצר X, מחיר: 1000 ש\"ח",
        "timestamp": "2025-08-10T12:00:00.000Z",
        "gender": "זכר",
        "total_messages": 5
    }
    
    try:
        # השתמש בפונקציה החדשה במקום insert ישיר
        mongodb_manager.upsert_lead_with_notified(lead_data)
        print("✅ ליד נוצר בהצלחה עם notified=false")
    except Exception as e:
        print(f"❌ שגיאה ביצירת ליד: {e}")
    
    # דוגמה 2: עדכון ליד קיים
    print("\n🔄 דוגמה 2: עדכון ליד קיים")
    updated_data = {
        "phone_number": "972501234567",  # אותו מספר טלפון
        "summary": "לקוח מתעניין במוצר X, מחיר: 1200 ש\"ח (עודכן)",
        "total_messages": 7
    }
    
    try:
        # הפונקציה תעדכן רק את השדות שסיפקת, לא תמחק אחרים
        mongodb_manager.upsert_lead_with_notified(updated_data)
        print("✅ ליד עודכן בהצלחה (שדות אחרים נשמרו)")
    except Exception as e:
        print(f"❌ שגיאה בעדכון ליד: {e}")
    
    # דוגמה 3: קבלת לידים שלא נשלחה להם התראה
    print("\n📋 דוגמה 3: קבלת לידים שלא נשלחה להם התראה")
    try:
        unnotified_leads = mongodb_manager.get_unnotified_leads()
        print(f"📊 נמצאו {len(unnotified_leads)} לידים שלא נשלחה להם התראה")
        
        for lead in unnotified_leads[:3]:  # הצג רק 3 ראשונים
            print(f"  - {lead.get('customer_name', 'ללא שם')} ({lead.get('phone_number', 'ללא מספר')})")
            
    except Exception as e:
        print(f"❌ שגיאה בקבלת לידים: {e}")
    
    # דוגמה 4: סימון ליד כשהודעה נשלחה (לאחר שליחה מוצלחת ב-n8n)
    print("\n✅ דוגמה 4: סימון ליד כשהודעה נשלחה")
    try:
        # בדוק אם יש לידים
        leads = mongodb_manager.get_unnotified_leads()
        if leads:
            first_lead_id = leads[0]["_id"]
            mongodb_manager.mark_lead_notified(first_lead_id)
            print(f"✅ ליד {first_lead_id} סומן כשהודעה נשלחה")
        else:
            print("ℹ️ אין לידים לסימון")
            
    except Exception as e:
        print(f"❌ שגיאה בסימון ליד: {e}")
    
    # דוגמה 5: שימוש בפונקציה הקיימת save_summary (שכבר מעודכנת)
    print("\n💾 דוגמה 5: שימוש ב-save_summary המעודכן")
    summary_data = {
        "customer_name": "שרה כהן",
        "summary": "לקוחה מתעניינת במוצר Y",
        "timestamp": "2025-08-10T13:00:00.000Z",
        "gender": "נקבה",
        "total_messages": 3
    }
    
    try:
        success = mongodb_manager.save_summary("972509876543", summary_data)
        if success:
            print("✅ סיכום נשמר בהצלחה עם הפונקציה המעודכנת")
        else:
            print("❌ שמירת סיכום נכשלה")
    except Exception as e:
        print(f"❌ שגיאה בשמירת סיכום: {e}")

def test_time_format():
    """בדוק את פורמט הזמן"""
    print("\n⏰ בדיקת פורמט זמן")
    try:
        time_str = mongodb_manager._now_iso_utc()
        print(f"זמן נוכחי ב-UTC ISO: {time_str}")
        
        # בדוק שהפורמט נכון
        if time_str.endswith('Z') and 'T' in time_str:
            print("✅ פורמט זמן תקין")
        else:
            print("❌ פורמט זמן לא תקין")
            
    except Exception as e:
        print(f"❌ שגיאה בבדיקת זמן: {e}")

if __name__ == "__main__":
    print("🔧 בדיקת פונקציות חדשות למניעת כפילויות")
    
    # בדוק חיבור ל-MongoDB
    if mongodb_manager.is_connected():
        print("✅ חיבור ל-MongoDB פעיל")
        
        # הרץ דוגמאות
        example_usage()
        test_time_format()
        
    else:
        print("❌ אין חיבור ל-MongoDB")
        print("⚠️ ודא שה-MongoDB פועל ושמשתני הסביבה מוגדרים נכון")
    
    print("\n🏁 סיום בדיקת פונקציות")
