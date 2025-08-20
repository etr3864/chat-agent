#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ניהול סיכומי שיחה נפרדים עם תמיכה ב-MongoDB ו-JSON
"""

import os
import json
from datetime import datetime
from typing import Dict, List, Optional

# נסה לייבא את MongoDB Manager
try:
    from mongodb_manager import mongodb_manager
    MONGODB_AVAILABLE = True
except ImportError:
    MONGODB_AVAILABLE = False
    print("⚠️ MongoDB לא זמין, משתמש ב-JSON בלבד")

# חילוץ שם הלקוח מהשיחה
def extract_customer_name(user_id: str, conversations: dict, pushname: str = "") -> str:
    # ראשית נסה להשתמש בשם מ-UltraMsg
    if pushname and pushname != "":
        return pushname
    
    if user_id not in conversations:
        return "לא ידוע"
    
    # חפש הודעות משתמש שמכילות מידע על שם
    user_messages = [msg["content"] for msg in conversations[user_id] if msg["role"] == "user"]
    
    for message in user_messages:
        # חפש תבניות נפוצות לשמות
        if "קוראים לי" in message or "שמי" in message or "אני" in message:
            # נסה לחלץ שם מההודעה
            words = message.split()
            for i, word in enumerate(words):
                if word in ["קוראים", "שמי", "אני"] and i + 1 < len(words):
                    return words[i + 1]
    
    return "לא ידוע"

# זיהוי מין הלקוח
def detect_customer_gender(user_id: str, conversations: dict) -> str:
    if user_id not in conversations:
        return "לא ידוע"
    
    # חפש הודעות משתמש שמכילות מידע על מין
    user_messages = [msg["content"] for msg in conversations[user_id] if msg["role"] == "user"]
    
    for message in user_messages:
        message_lower = message.lower()
        # חפש מילים שמעידות על מין
        if any(word in message_lower for word in ["אני גבר", "אני בן", "זכר", "גבר"]):
            return "זכר"
        elif any(word in message_lower for word in ["אני אישה", "אני בת", "נקבה", "אישה"]):
            return "נקבה"
    
    return "לא ידוע"

class ConversationSummaries:
    def __init__(self, summaries_file="conversation_summaries.json"):
        self.summaries_file = summaries_file
        self.summaries = self.load_summaries()
        # אל תינעל על מצב החיבור בזמן האתחול בלבד; בדוק דינמית בכל פעולה
        self.mongodb_available = MONGODB_AVAILABLE and mongodb_manager.is_connected()
        
        if self.mongodb_available:
            print("✅ משתמש ב-MongoDB לשמירת סיכומים")
            # נסה לשמור סיכום בדיקה
            try:
                test_summary = {
                    "phone_number": "test_connection",
                    "customer_name": "בדיקת חיבור",
                    "summary": "בדיקת חיבור למונגו DB",
                    "timestamp": datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.000Z')
                }
                mongodb_manager.save_summary("test_connection", test_summary)
                # מחק את הבדיקה
                mongodb_manager.delete_summary("test_connection")
                print("✅ MongoDB פועל תקין - בדיקת כתיבה/מחיקה הצליחה")
            except Exception as e:
                print(f"⚠️ בעיה ב-MongoDB: {e}")
                self.mongodb_available = False
        else:
            print("📄 משתמש בקבצי JSON לשמירת סיכומים")
            if not MONGODB_AVAILABLE:
                print("💡 כדי להשתמש ב-MongoDB, הוסף MONGODB_URI למשתני הסביבה")
            elif not mongodb_manager.is_connected():
                print("💡 בדוק את החיבור ל-MongoDB")
    
    def load_summaries(self):
        """טען סיכומים קיימים"""
        if os.path.exists(self.summaries_file):
            try:
                with open(self.summaries_file, "r", encoding="utf-8-sig") as f:
                    return json.load(f)
            except (json.JSONDecodeError, UnicodeDecodeError):
                return {}
        return {}
    
    def save_summaries(self):
        """שמור סיכומים לקובץ JSON (גיבוי)"""
        with open(self.summaries_file, "w", encoding="utf-8-sig") as f:
            json.dump(self.summaries, f, ensure_ascii=False, indent=2)
    
    def add_summary(self, user_id: str, summary: str, conversations: dict, pushname: str = ""):
        """הוסף סיכום חדש עם מידע על תמונות"""
        customer_name = extract_customer_name(user_id, conversations, pushname)
        customer_gender = detect_customer_gender(user_id, conversations)
        
        # ספור תמונות בשיחה לפי תוכן ההודעות
        image_count = 0
        image_urls = []
        for msg in conversations.get(user_id, []):
            if "[תמונה]" in msg.get("content", ""):
                image_count += 1
                # חלץ קישור לתמונה מהתוכן
                content = msg.get("content", "")
                if "🔗 קישור לתמונה:" in content:
                    lines = content.split('\n')
                    for line in lines:
                        if "🔗 קישור לתמונה:" in line:
                            url = line.replace("🔗 קישור לתמונה:", "").strip()
                            if url:
                                image_urls.append(url)
                            break
        
        summary_data = {
            "phone_number": user_id,
            "customer_name": customer_name,
            "gender": customer_gender,
            "summary": summary,
            "timestamp": datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.000Z'),
            "total_messages": len([m for m in conversations.get(user_id, []) if m["role"] in ["user", "assistant"]]),
            "image_count": image_count,
            "image_urls": image_urls
        }
        
        # שמור ב-JSON (גיבוי)
        self.summaries[user_id] = summary_data
        self.save_summaries()
        
        # נסה לשמור ב-MongoDB דינמית בכל פעם (גם אם בתחילת חיי התהליך לא היה חיבור)
        try:
            if MONGODB_AVAILABLE and mongodb_manager.is_connected():
                mongodb_manager.save_summary(user_id, summary_data)
            else:
                # נסה להתחבר מחדש אם לא מחובר
                if MONGODB_AVAILABLE:
                    mongodb_manager.connect()
                    if mongodb_manager.is_connected():
                        mongodb_manager.save_summary(user_id, summary_data)
        except Exception as e:
            print(f"⚠️ שמירה ל-MongoDB נכשלה, נשמר רק ב-JSON. שגיאה: {e}")
        
        print(f"✅ סיכום נשמר עבור {customer_name} ({user_id}) עם {image_count} תמונות")
    
    def get_summary(self, user_id: str):
        """קבל סיכום לפי מזהה משתמש"""
        # נסה MongoDB קודם
        if self.mongodb_available:
            mongo_summary = mongodb_manager.get_summary(user_id)
            if mongo_summary:
                return mongo_summary
        
        # גיבוי ל-JSON
        return self.summaries.get(user_id)
    
    def get_all_summaries(self):
        """קבל את כל הסיכומים"""
        # נסה MongoDB קודם
        if self.mongodb_available:
            mongo_summaries = mongodb_manager.get_all_summaries()
            if mongo_summaries:
                return {summary["phone_number"]: summary for summary in mongo_summaries}
        
        # גיבוי ל-JSON
        return self.summaries
    
    def search_summaries(self, query: str):
        """חפש סיכומים לפי מספר טלפון או שם"""
        # נסה MongoDB קודם
        if self.mongodb_available:
            # חפש לפי מספר טלפון
            phone_results = mongodb_manager.search_by_phone(query)
            if phone_results:
                return phone_results
            
            # חפש לפי שם
            name_results = mongodb_manager.search_by_name(query)
            if name_results:
                return name_results
        
        # גיבוי ל-JSON
        results = {}
        query_lower = query.lower()
        for user_id, summary in self.summaries.items():
            if (query_lower in user_id.lower() or 
                query_lower in summary.get("customer_name", "").lower()):
                results[user_id] = summary
        
        return list(results.values())
    
    def print_summary(self, user_id: str):
        """הדפס סיכום מסודר"""
        summary = self.get_summary(user_id)
        if not summary:
            print(f"❌ לא נמצא סיכום עבור {user_id}")
            return
        
        print("=" * 60)
        print("📋 סיכום שיחה")
        print("=" * 60)
        print(f"📱 מספר טלפון: {summary['phone_number']}")
        print(f"👤 שם לקוח: {summary['customer_name']}")
        print(f"👥 מין: {summary['gender']}")
        print(f"📅 תאריך: {summary['timestamp']}")
        print(f"💬 כמות הודעות: {summary['total_messages']}")
        print("=" * 60)
        print(f"\n{summary['summary']}")
        print("=" * 60)
    
    def print_all_summaries(self):
        """הדפס את כל הסיכומים"""
        summaries = self.get_all_summaries()
        
        if not summaries:
            print("❌ אין סיכומים שמורים")
            return
        
        print(f"📊 סיכומי שיחה - {len(summaries)} לקוחות")
        print("=" * 60)
        
        for user_id, summary in summaries.items():
            print(f"\n📱 {summary['phone_number']}")
            print(f"👤 {summary['customer_name']} ({summary['gender']})")
            print(f"📅 {summary['timestamp']}")
            print(f"💬 {summary['total_messages']} הודעות")
            print("-" * 40)
    
    def export_to_txt(self, filename="all_summaries.txt"):
        """ייצא את כל הסיכומים לקובץ טקסט"""
        summaries = self.get_all_summaries()
        
        with open(filename, "w", encoding="utf-8-sig") as f:
            f.write("📊 סיכומי שיחה - VALUE+ Bot\n")
            f.write("=" * 60 + "\n\n")
            
            for user_id, summary in summaries.items():
                f.write(f"📱 מספר טלפון: {summary['phone_number']}\n")
                f.write(f"👤 שם לקוח: {summary['customer_name']}\n")
                f.write(f"👥 מין: {summary['gender']}\n")
                f.write(f"📅 תאריך: {summary['timestamp']}\n")
                f.write(f"💬 כמות הודעות: {summary['total_messages']}\n")
                f.write("-" * 40 + "\n")
                f.write(f"{summary['summary']}\n")
                f.write("=" * 60 + "\n\n")
        
        print(f"✅ סיכומים יוצאו לקובץ: {filename}")
    
    def get_statistics(self):
        """קבל סטטיסטיקות על הסיכומים"""
        if self.mongodb_available:
            return mongodb_manager.get_statistics()
        
        # גיבוי ל-JSON
        summaries = self.get_all_summaries()
        
        if not summaries:
            return {}
        
        total_customers = len(summaries)
        total_messages = sum(s['total_messages'] for s in summaries.values())
        
        # ספירת מין
        gender_count = {}
        for summary in summaries.values():
            gender = summary['gender']
            gender_count[gender] = gender_count.get(gender, 0) + 1
        
        return {
            "total_customers": total_customers,
            "total_messages": total_messages,
            "avg_messages_per_customer": round(total_messages/total_customers, 1) if total_customers > 0 else 0,
            "gender_distribution": gender_count
        }

# יצירת מופע גלובלי
summaries_manager = ConversationSummaries() 