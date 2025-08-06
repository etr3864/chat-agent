#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
הרצה מהירה - בדיקת המערכת
"""

import os
import sys
from datetime import datetime

def check_dependencies():
    """בדוק תלויות"""
    print("🔍 בודק תלויות...")
    
    required_packages = [
        'openai', 'flask', 'requests', 'python-dotenv', 'pymongo'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"✅ {package}")
        except ImportError:
            print(f"❌ {package} - חסר")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\n⚠️ חסרות תלויות: {', '.join(missing_packages)}")
        print("💡 הרץ: pip install -r requirements.txt")
        return False
    
    print("✅ כל התלויות מותקנות")
    return True

def check_env_file():
    """בדוק קובץ .env"""
    print("\n🔍 בודק קובץ .env...")
    
    if not os.path.exists('.env'):
        print("❌ קובץ .env לא נמצא")
        print("💡 צור קובץ .env עם המשתנים הבאים:")
        print("   OPENAI_API_KEY=your_key_here")
        print("   ULTRA_INSTANCE_ID=your_instance_id")
        print("   ULTRA_TOKEN=your_token")
        print("   MONGODB_URI=mongodb://localhost:27017/ (אופציונלי)")
        return False
    
    print("✅ קובץ .env נמצא")
    return True

def test_mongodb_connection():
    """בדוק חיבור MongoDB"""
    print("\n🔍 בודק חיבור MongoDB...")
    
    try:
        from mongodb_manager import mongodb_manager
        
        if mongodb_manager.is_connected():
            print("✅ MongoDB מחובר")
            return True
        else:
            print("⚠️ MongoDB לא מחובר - המערכת תעבוד עם JSON")
            return True
            
    except Exception as e:
        print(f"⚠️ שגיאה בבדיקת MongoDB: {e}")
        print("💡 המערכת תעבוד עם JSON בלבד")
        return True

def test_summary_system():
    """בדוק מערכת סיכומים"""
    print("\n🔍 בודק מערכת סיכומים...")
    
    try:
        from conversation_summaries import summaries_manager
        
        # בדוק סיכומים קיימים
        summaries = summaries_manager.get_all_summaries()
        print(f"📊 סיכומים קיימים: {len(summaries)}")
        
        # בדוק סטטיסטיקות
        stats = summaries_manager.get_statistics()
        if stats:
            print(f"📈 לקוחות: {stats.get('total_customers', 0)}")
            print(f"💬 הודעות: {stats.get('total_messages', 0)}")
        
        print("✅ מערכת סיכומים עובדת")
        return True
        
    except Exception as e:
        print(f"❌ שגיאה במערכת סיכומים: {e}")
        return False

def show_menu():
    """הצג תפריט"""
    print("\n" + "="*50)
    print("🚀 VALUE+ Bot - תפריט מהיר")
    print("="*50)
    print("1. בדיקה מלאה של המערכת")
    print("2. בדוק תלויות")
    print("3. בדוק MongoDB")
    print("4. ניהול סיכומים")
    print("5. בדיקת MongoDB מתקדמת")
    print("6. יציאה")
    print("="*50)

def main():
    """תפריט ראשי"""
    while True:
        show_menu()
        choice = input("בחר אפשרות (1-6): ").strip()
        
        if choice == "1":
            print("\n🔄 מתחיל בדיקה מלאה...")
            
            # בדיקות
            deps_ok = check_dependencies()
            env_ok = check_env_file()
            mongo_ok = test_mongodb_connection()
            summary_ok = test_summary_system()
            
            print("\n📊 תוצאות בדיקה:")
            print(f"📦 תלויות: {'✅' if deps_ok else '❌'}")
            print(f"🔧 .env: {'✅' if env_ok else '❌'}")
            print(f"🗄️ MongoDB: {'✅' if mongo_ok else '⚠️'}")
            print(f"📊 סיכומים: {'✅' if summary_ok else '❌'}")
            
            if all([deps_ok, env_ok, summary_ok]):
                print("\n🎉 המערכת מוכנה לשימוש!")
                print("💡 הרץ: python whatsapp_webhook.py")
            else:
                print("\n⚠️ יש בעיות שצריך לפתור")
        
        elif choice == "2":
            check_dependencies()
        
        elif choice == "3":
            test_mongodb_connection()
        
        elif choice == "4":
            print("\n🔄 מפעיל ניהול סיכומים...")
            os.system("python manage_summaries.py")
        
        elif choice == "5":
            print("\n🔄 מפעיל בדיקת MongoDB מתקדמת...")
            os.system("python test_mongodb.py")
        
        elif choice == "6":
            print("👋 להתראות!")
            break
        
        else:
            print("❌ בחירה לא תקינה")

if __name__ == "__main__":
    main() 