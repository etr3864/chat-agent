#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ניהול סיכומי שיחה עם MongoDB
"""

from conversation_summaries import summaries_manager

def main():
    """תפריט ראשי לניהול סיכומים"""
    while True:
        print("\n" + "="*50)
        print("📊 ניהול סיכומי שיחה - VALUE+ Bot")
        print("="*50)
        print("1. הצג את כל הסיכומים")
        print("2. חפש סיכום לפי מספר טלפון")
        print("3. חפש סיכום לפי שם לקוח")
        print("4. ייצא את כל הסיכומים לקובץ טקסט")
        print("5. הצג סטטיסטיקות")
        print("6. בדוק חיבור MongoDB")
        print("7. יציאה")
        print("="*50)
        
        choice = input("בחר אפשרות (1-7): ").strip()
        
        if choice == "1":
            print("\n")
            summaries_manager.print_all_summaries()
            
        elif choice == "2":
            phone = input("הכנס מספר טלפון: ").strip()
            if not phone.endswith("@c.us"):
                phone += "@c.us"
            print("\n")
            summaries_manager.print_summary(phone)
            
        elif choice == "3":
            name = input("הכנס שם לקוח: ").strip()
            print("\n")
            search_results = summaries_manager.search_summaries(name)
            
            if search_results:
                print(f"🔍 נמצאו {len(search_results)} תוצאות:")
                print("=" * 60)
                for i, summary in enumerate(search_results, 1):
                    print(f"\n{i}. 📱 {summary['phone_number']}")
                    print(f"   👤 {summary['customer_name']} ({summary['gender']})")
                    print(f"   📅 {summary['timestamp']}")
                    print(f"   💬 {summary['total_messages']} הודעות")
                    print("-" * 40)
            else:
                print("❌ לא נמצאו תוצאות")
            
        elif choice == "4":
            filename = input("שם הקובץ (ברירת מחדל: all_summaries.txt): ").strip()
            if not filename:
                filename = "all_summaries.txt"
            summaries_manager.export_to_txt(filename)
            
        elif choice == "5":
            show_statistics()
            
        elif choice == "6":
            check_mongodb_connection()
            
        elif choice == "7":
            print("👋 להתראות!")
            break
            
        else:
            print("❌ בחירה לא תקינה, נסה שוב")

def show_statistics():
    """הצג סטטיסטיקות"""
    stats = summaries_manager.get_statistics()
    
    if not stats:
        print("❌ אין סיכומים שמורים")
        return
    
    print("\n📊 סטטיסטיקות")
    print("="*30)
    print(f"👥 סה״כ לקוחות: {stats['total_customers']}")
    print(f"💬 סה״כ הודעות: {stats['total_messages']}")
    print(f"📈 ממוצע הודעות ללקוח: {stats['avg_messages_per_customer']}")
    
    if 'gender_distribution' in stats:
        print("\n👥 התפלגות לפי מין:")
        for gender, count in stats['gender_distribution'].items():
            percentage = (count / stats['total_customers']) * 100
            print(f"   {gender}: {count} ({percentage:.1f}%)")

def check_mongodb_connection():
    """בדוק חיבור MongoDB"""
    print("\n🔍 בדיקת חיבור MongoDB")
    print("="*30)
    
    if hasattr(summaries_manager, 'mongodb_available'):
        if summaries_manager.mongodb_available:
            print("✅ MongoDB מחובר ועובד")
            
            # נסה לקבל סטטיסטיקות
            try:
                from mongodb_manager import mongodb_manager
                stats = mongodb_manager.get_statistics()
                if stats:
                    print(f"📊 יש {stats.get('total_customers', 0)} סיכומים ב-MongoDB")
                else:
                    print("📊 אין סיכומים ב-MongoDB עדיין")
            except Exception as e:
                print(f"⚠️ שגיאה בבדיקת MongoDB: {e}")
        else:
            print("❌ MongoDB לא מחובר")
            print("💡 כדי לחבר MongoDB, הוסף את המשתנים הבאים ל-.env:")
            print("   MONGODB_URI=mongodb://localhost:27017/")
            print("   MONGODB_DATABASE=chatbot_db")
            print("   MONGODB_COLLECTION=conversation_summaries")
    else:
        print("❌ MongoDB לא זמין במערכת")

if __name__ == "__main__":
    main() 