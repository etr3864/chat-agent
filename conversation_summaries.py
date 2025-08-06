#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ניהול סיכומי שיחה נפרדים
"""

import os
import json
from datetime import datetime

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
        """שמור סיכומים לקובץ"""
        with open(self.summaries_file, "w", encoding="utf-8-sig") as f:
            json.dump(self.summaries, f, ensure_ascii=False, indent=2)
    
    def add_summary(self, user_id: str, summary: str, conversations: dict, pushname: str = ""):
        """הוסף סיכום חדש"""
        customer_name = extract_customer_name(user_id, conversations, pushname)
        customer_gender = detect_customer_gender(user_id, conversations)
        
        summary_data = {
            "phone_number": user_id,
            "customer_name": customer_name,
            "gender": customer_gender,
            "summary": summary,
            "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "total_messages": len([m for m in conversations.get(user_id, []) if m["role"] in ["user", "assistant"]])
        }
        
        self.summaries[user_id] = summary_data
        self.save_summaries()
        
        print(f"✅ סיכום נשמר עבור {customer_name} ({user_id})")
    
    def get_summary(self, user_id: str):
        """קבל סיכום לפי מזהה משתמש"""
        return self.summaries.get(user_id)
    
    def get_all_summaries(self):
        """קבל את כל הסיכומים"""
        return self.summaries
    
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
        if not self.summaries:
            print("❌ אין סיכומים שמורים")
            return
        
        print(f"📊 סיכומי שיחה - {len(self.summaries)} לקוחות")
        print("=" * 60)
        
        for user_id, summary in self.summaries.items():
            print(f"\n📱 {summary['phone_number']}")
            print(f"👤 {summary['customer_name']} ({summary['gender']})")
            print(f"📅 {summary['timestamp']}")
            print(f"💬 {summary['total_messages']} הודעות")
            print("-" * 40)
    
    def export_to_txt(self, filename="all_summaries.txt"):
        """ייצא את כל הסיכומים לקובץ טקסט"""
        with open(filename, "w", encoding="utf-8-sig") as f:
            f.write("📊 סיכומי שיחה - VALUE+ Bot\n")
            f.write("=" * 60 + "\n\n")
            
            for user_id, summary in self.summaries.items():
                f.write(f"📱 מספר טלפון: {summary['phone_number']}\n")
                f.write(f"👤 שם לקוח: {summary['customer_name']}\n")
                f.write(f"👥 מין: {summary['gender']}\n")
                f.write(f"📅 תאריך: {summary['timestamp']}\n")
                f.write(f"💬 כמות הודעות: {summary['total_messages']}\n")
                f.write("-" * 40 + "\n")
                f.write(f"{summary['summary']}\n")
                f.write("=" * 60 + "\n\n")
        
        print(f"✅ סיכומים יוצאו לקובץ: {filename}")

# יצירת מופע גלובלי
summaries_manager = ConversationSummaries() 