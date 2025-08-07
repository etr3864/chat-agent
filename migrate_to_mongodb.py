#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
מיגרציה של סיכומי שיחה מ-JSON ל-MongoDB
"""

import json
import os
from datetime import datetime, timezone
from conversation_summaries import summaries_manager

def migrate_json_to_mongodb():
    """העבר את כל הסיכומים מ-JSON ל-MongoDB"""
    print("🔄 מתחיל מיגרציה מ-JSON ל-MongoDB...")
    print("=" * 50)
    
    # בדוק אם MongoDB זמין
    if not summaries_manager.mongodb_available:
        print("❌ MongoDB לא זמין. אנא הגדר את משתני הסביבה הנדרשים.")
        print("💡 הוסף לקובץ .env:")
        print("   MONGODB_URI=mongodb://localhost:27017/")
        print("   MONGODB_DATABASE=chatbot_db")
        print("   MONGODB_COLLECTION=conversation_summaries")
        return False
    
    # טען סיכומים מ-JSON
    json_summaries = summaries_manager.summaries
    
    if not json_summaries:
        print("📄 אין סיכומים ב-JSON למיגרציה")
        return True
    
    print(f"📊 נמצאו {len(json_summaries)} סיכומים ב-JSON")
    
    # העבר כל סיכום ל-MongoDB
    success_count = 0
    error_count = 0
    
    for user_id, summary in json_summaries.items():
        try:
            # הוסף תאריך מיגרציה בפורמט UTC ISO 8601 עם דיוק של שניות
            summary["migrated_at"] = datetime.now(timezone.utc).isoformat(timespec='seconds') + "Z"
            
            # שמור ב-MongoDB
            from mongodb_manager import mongodb_manager
            if mongodb_manager.save_summary(user_id, summary):
                success_count += 1
                print(f"✅ {user_id} - {summary.get('customer_name', 'לא ידוע')}")
            else:
                error_count += 1
                print(f"❌ {user_id} - שגיאה בשמירה")
                
        except Exception as e:
            error_count += 1
            print(f"❌ {user_id} - שגיאה: {e}")
    
    print("=" * 50)
    print(f"✅ מיגרציה הושלמה!")
    print(f"📊 הצלחות: {success_count}")
    print(f"❌ שגיאות: {error_count}")
    
    if success_count > 0:
        print("\n💡 המיגרציה הושלמה בהצלחה!")
        print("🔍 בדוק את התוצאות עם: python manage_summaries.py")
    
    return error_count == 0

def backup_json_file():
    """צור גיבוי של קובץ ה-JSON"""
    json_file = summaries_manager.summaries_file
    
    if os.path.exists(json_file):
        backup_file = f"{json_file}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        try:
            with open(json_file, 'r', encoding='utf-8-sig') as src:
                with open(backup_file, 'w', encoding='utf-8-sig') as dst:
                    dst.write(src.read())
            print(f"💾 גיבוי נוצר: {backup_file}")
            return backup_file
        except Exception as e:
            print(f"❌ שגיאה ביצירת גיבוי: {e}")
            return None
    return None

def verify_migration():
    """בדוק שהמיגרציה הצליחה"""
    print("\n🔍 בודק מיגרציה...")
    
    json_count = len(summaries_manager.summaries)
    
    if summaries_manager.mongodb_available:
        from mongodb_manager import mongodb_manager
        mongo_summaries = mongodb_manager.get_all_summaries()
        mongo_count = len(mongo_summaries)
        
        print(f"📄 JSON: {json_count} סיכומים")
        print(f"🗄️ MongoDB: {mongo_count} סיכומים")
        
        if mongo_count >= json_count:
            print("✅ המיגרציה הצליחה!")
            return True
        else:
            print("❌ המיגרציה לא הושלמה במלואה")
            return False
    else:
        print("❌ MongoDB לא זמין לבדיקה")
        return False

def main():
    """תפריט ראשי למיגרציה"""
    print("🚀 מיגרציה מ-JSON ל-MongoDB")
    print("=" * 50)
    print("1. צור גיבוי של JSON")
    print("2. בצע מיגרציה")
    print("3. בדוק מיגרציה")
    print("4. בצע הכל (גיבוי + מיגרציה + בדיקה)")
    print("5. יציאה")
    print("=" * 50)
    
    choice = input("בחר אפשרות (1-5): ").strip()
    
    if choice == "1":
        backup_file = backup_json_file()
        if backup_file:
            print(f"✅ גיבוי נוצר: {backup_file}")
    
    elif choice == "2":
        success = migrate_json_to_mongodb()
        if success:
            print("✅ מיגרציה הושלמה בהצלחה!")
    
    elif choice == "3":
        verify_migration()
    
    elif choice == "4":
        print("\n🔄 מתחיל תהליך מלא...")
        
        # גיבוי
        backup_file = backup_json_file()
        if backup_file:
            print(f"✅ גיבוי נוצר: {backup_file}")
        
        # מיגרציה
        success = migrate_json_to_mongodb()
        if success:
            print("✅ מיגרציה הושלמה!")
            
            # בדיקה
            if verify_migration():
                print("🎉 התהליך הושלם בהצלחה!")
            else:
                print("⚠️ יש בעיות במיגרציה")
    
    elif choice == "5":
        print("👋 להתראות!")
    
    else:
        print("❌ בחירה לא תקינה")

if __name__ == "__main__":
    main() 