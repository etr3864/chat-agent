#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ניהול סיכומי שיחה
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
        print("3. ייצא את כל הסיכומים לקובץ טקסט")
        print("4. הצג סטטיסטיקות")
        print("5. יציאה")
        print("="*50)
        
        choice = input("בחר אפשרות (1-5): ").strip()
        
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
            filename = input("שם הקובץ (ברירת מחדל: all_summaries.txt): ").strip()
            if not filename:
                filename = "all_summaries.txt"
            summaries_manager.export_to_txt(filename)
            
        elif choice == "4":
            show_statistics()
            
        elif choice == "5":
            print("👋 להתראות!")
            break
            
        else:
            print("❌ בחירה לא תקינה, נסה שוב")

def show_statistics():
    """הצג סטטיסטיקות"""
    summaries = summaries_manager.get_all_summaries()
    
    if not summaries:
        print("❌ אין סיכומים שמורים")
        return
    
    total_customers = len(summaries)
    total_messages = sum(s['total_messages'] for s in summaries.values())
    
    # ספירת מין
    gender_count = {}
    for summary in summaries.values():
        gender = summary['gender']
        gender_count[gender] = gender_count.get(gender, 0) + 1
    
    print("\n📊 סטטיסטיקות")
    print("="*30)
    print(f"👥 סה״כ לקוחות: {total_customers}")
    print(f"💬 סה״כ הודעות: {total_messages}")
    print(f"📈 ממוצע הודעות ללקוח: {total_messages/total_customers:.1f}")
    
    print("\n👥 התפלגות לפי מין:")
    for gender, count in gender_count.items():
        percentage = (count / total_customers) * 100
        print(f"   {gender}: {count} ({percentage:.1f}%)")

if __name__ == "__main__":
    main() 