#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
בדיקת MongoDB - סקריפט בדיקה מהירה
"""

import os
from datetime import datetime
from dotenv import load_dotenv

# טען משתני סביבה
load_dotenv()

def test_mongodb_connection():
    """בדוק חיבור MongoDB"""
    print("🔍 בודק חיבור MongoDB...")
    print("=" * 40)
    
    # בדוק משתני סביבה
    mongo_uri = os.getenv("MONGODB_URI")
    database_name = os.getenv("MONGODB_DATABASE")
    collection_name = os.getenv("MONGODB_COLLECTION")
    
    print(f"🔗 URI: {mongo_uri or 'לא מוגדר'}")
    print(f"🗄️ Database: {database_name or 'לא מוגדר'}")
    print(f"📁 Collection: {collection_name or 'לא מוגדר'}")
    
    if not mongo_uri:
        print("❌ MONGODB_URI לא מוגדר")
        return False
    
    try:
        # נסה להתחבר
        from mongodb_manager import mongodb_manager
        
        if mongodb_manager.is_connected():
            print("✅ MongoDB מחובר בהצלחה!")
            return True
        else:
            print("❌ MongoDB לא מחובר")
            return False
            
    except Exception as e:
        print(f"❌ שגיאה בחיבור: {e}")
        return False

def test_summary_operations():
    """בדוק פעולות סיכום"""
    print("\n🧪 בודק פעולות סיכום...")
    print("=" * 40)
    
    try:
        from conversation_summaries import summaries_manager
        
        # בדוק אם MongoDB זמין
        if summaries_manager.mongodb_available:
            print("✅ MongoDB זמין במערכת")
        else:
            print("⚠️ MongoDB לא זמין, משתמש ב-JSON")
        
        # בדוק סיכומים קיימים
        all_summaries = summaries_manager.get_all_summaries()
        print(f"📊 סיכומים קיימים: {len(all_summaries)}")
        
        # בדוק סטטיסטיקות
        stats = summaries_manager.get_statistics()
        if stats:
            print(f"📈 סטטיסטיקות: {stats.get('total_customers', 0)} לקוחות")
        
        return True
        
    except Exception as e:
        print(f"❌ שגיאה בבדיקת פעולות: {e}")
        return False

def test_search_functionality():
    """בדוק פונקציונליות חיפוש"""
    print("\n🔍 בודק פונקציונליות חיפוש...")
    print("=" * 40)
    
    try:
        from conversation_summaries import summaries_manager
        
        # בדוק חיפוש
        search_results = summaries_manager.search_summaries("test")
        print(f"🔍 תוצאות חיפוש 'test': {len(search_results)}")
        
        return True
        
    except Exception as e:
        print(f"❌ שגיאה בבדיקת חיפוש: {e}")
        return False

def create_test_summary():
    """צור סיכום בדיקה"""
    print("\n🧪 יוצר סיכום בדיקה...")
    print("=" * 40)
    
    try:
        from conversation_summaries import summaries_manager
        
        # נתוני בדיקה
        test_user_id = "test_user@c.us"
        test_summary = "זהו סיכום בדיקה שנוצר על ידי הסקריפט"
        test_conversations = {
            test_user_id: [
                {"role": "user", "content": "היי, אני משתמש בדיקה"},
                {"role": "assistant", "content": "שלום! איך אני יכול לעזור?"}
            ]
        }
        
        # הוסף סיכום
        summaries_manager.add_summary(test_user_id, test_summary, test_conversations, "משתמש בדיקה")
        
        print("✅ סיכום בדיקה נוצר בהצלחה!")
        return True
        
    except Exception as e:
        print(f"❌ שגיאה ביצירת סיכום בדיקה: {e}")
        return False

def main():
    """תפריט בדיקה ראשי"""
    print("🧪 בדיקת MongoDB - VALUE+ Bot")
    print("=" * 50)
    print("1. בדוק חיבור MongoDB")
    print("2. בדוק פעולות סיכום")
    print("3. בדוק חיפוש")
    print("4. צור סיכום בדיקה")
    print("5. בדיקה מלאה")
    print("6. יציאה")
    print("=" * 50)
    
    choice = input("בחר אפשרות (1-6): ").strip()
    
    if choice == "1":
        test_mongodb_connection()
    
    elif choice == "2":
        test_summary_operations()
    
    elif choice == "3":
        test_search_functionality()
    
    elif choice == "4":
        create_test_summary()
    
    elif choice == "5":
        print("🔄 מתחיל בדיקה מלאה...")
        
        # בדיקות
        connection_ok = test_mongodb_connection()
        operations_ok = test_summary_operations()
        search_ok = test_search_functionality()
        test_summary_ok = create_test_summary()
        
        print("\n📊 תוצאות בדיקה:")
        print(f"🔗 חיבור: {'✅' if connection_ok else '❌'}")
        print(f"📊 פעולות: {'✅' if operations_ok else '❌'}")
        print(f"🔍 חיפוש: {'✅' if search_ok else '❌'}")
        print(f"🧪 סיכום בדיקה: {'✅' if test_summary_ok else '❌'}")
        
        if all([connection_ok, operations_ok, search_ok, test_summary_ok]):
            print("\n🎉 כל הבדיקות עברו בהצלחה!")
        else:
            print("\n⚠️ יש בעיות במערכת")
    
    elif choice == "6":
        print("👋 להתראות!")
    
    else:
        print("❌ בחירה לא תקינה")

if __name__ == "__main__":
    main() 