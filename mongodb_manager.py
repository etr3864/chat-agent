#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ניהול MongoDB עבור סיכומי שיחה
"""

import os
from datetime import datetime
from typing import Dict, List, Optional
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from dotenv import load_dotenv

# טען משתני סביבה
load_dotenv()

class MongoDBManager:
    def __init__(self):
        """אתחול חיבור ל-MongoDB"""
        self.client = None
        self.db = None
        self.collection = None
        self.connect()
    
    def connect(self):
        """התחבר ל-MongoDB"""
        try:
            # נסה לקבל את כתובת ה-MongoDB ממשתנה סביבה
            mongo_uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017/")
            database_name = os.getenv("MONGODB_DATABASE", "chatbot_db")
            collection_name = os.getenv("MONGODB_COLLECTION", "conversation_summaries")
            
            print(f"🔗 מתחבר ל-MongoDB: {mongo_uri}")
            self.client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
            
            # בדוק חיבור
            self.client.admin.command('ping')
            print("✅ חיבור ל-MongoDB הצליח")
            
            self.db = self.client[database_name]
            self.collection = self.db[collection_name]
            
            # צור אינדקסים לשיפור ביצועים
            self._create_indexes()
            
        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            print(f"❌ שגיאה בהתחברות ל-MongoDB: {e}")
            print("⚠️ המערכת תמשיך לעבוד עם קבצי JSON")
            self.client = None
            self.db = None
            self.collection = None
    
    def _create_indexes(self):
        """צור אינדקסים לשיפור ביצועים"""
        try:
            # אינדקס על מספר טלפון
            self.collection.create_index("phone_number", unique=True)
            # אינדקס על שם לקוח
            self.collection.create_index("customer_name")
            # אינדקס על תאריך
            self.collection.create_index("timestamp")
            print("✅ אינדקסים נוצרו בהצלחה")
        except Exception as e:
            print(f"⚠️ שגיאה ביצירת אינדקסים: {e}")
    
    def is_connected(self) -> bool:
        """בדוק אם יש חיבור ל-MongoDB"""
        return self.client is not None and self.db is not None
    
    def save_summary(self, user_id: str, summary_data: Dict) -> bool:
        """שמור סיכום שיחה ב-MongoDB"""
        if not self.is_connected():
            print("❌ אין חיבור ל-MongoDB")
            return False
        
        try:
            # הוסף תאריך עדכון בפורמט UTC ISO 8601 עם דיוק של שניות
            from datetime import datetime, timezone
            summary_data["updated_at"] = datetime.now(timezone.utc).isoformat(timespec='seconds') + "Z"
            
            # עדכן או הוסף מסמך חדש
            result = self.collection.update_one(
                {"phone_number": user_id},
                {"$set": summary_data},
                upsert=True
            )
            
            if result.upserted_id:
                print(f"✅ סיכום חדש נשמר ב-MongoDB עבור {user_id}")
            else:
                print(f"✅ סיכום עודכן ב-MongoDB עבור {user_id}")
            
            return True
            
        except Exception as e:
            print(f"❌ שגיאה בשמירת סיכום ב-MongoDB: {e}")
            return False
    
    def get_summary(self, user_id: str) -> Optional[Dict]:
        """קבל סיכום שיחה לפי מספר טלפון"""
        if not self.is_connected():
            print("❌ אין חיבור ל-MongoDB")
            return None
        
        try:
            summary = self.collection.find_one({"phone_number": user_id})
            return summary
        except Exception as e:
            print(f"❌ שגיאה בקבלת סיכום מ-MongoDB: {e}")
            return None
    
    def get_all_summaries(self) -> List[Dict]:
        """קבל את כל סיכומי השיחה"""
        if not self.is_connected():
            print("❌ אין חיבור ל-MongoDB")
            return []
        
        try:
            summaries = list(self.collection.find({}, {"_id": 0}).sort("timestamp", -1))
            return summaries
        except Exception as e:
            print(f"❌ שגיאה בקבלת כל הסיכומים מ-MongoDB: {e}")
            return []
    
    def search_by_phone(self, phone_number: str) -> List[Dict]:
        """חפש סיכומים לפי מספר טלפון"""
        if not self.is_connected():
            print("❌ אין חיבור ל-MongoDB")
            return []
        
        try:
            # חפש מספר טלפון חלקי
            summaries = list(self.collection.find(
                {"phone_number": {"$regex": phone_number, "$options": "i"}},
                {"_id": 0}
            ).sort("timestamp", -1))
            return summaries
        except Exception as e:
            print(f"❌ שגיאה בחיפוש ב-MongoDB: {e}")
            return []
    
    def search_by_name(self, customer_name: str) -> List[Dict]:
        """חפש סיכומים לפי שם לקוח"""
        if not self.is_connected():
            print("❌ אין חיבור ל-MongoDB")
            return []
        
        try:
            summaries = list(self.collection.find(
                {"customer_name": {"$regex": customer_name, "$options": "i"}},
                {"_id": 0}
            ).sort("timestamp", -1))
            return summaries
        except Exception as e:
            print(f"❌ שגיאה בחיפוש ב-MongoDB: {e}")
            return []
    
    def get_statistics(self) -> Dict:
        """קבל סטטיסטיקות על הסיכומים"""
        if not self.is_connected():
            print("❌ אין חיבור ל-MongoDB")
            return {}
        
        try:
            total_customers = self.collection.count_documents({})
            
            # ספירת לפי מין
            gender_pipeline = [
                {"$group": {"_id": "$gender", "count": {"$sum": 1}}}
            ]
            gender_stats = list(self.collection.aggregate(gender_pipeline))
            
            # ממוצע הודעות
            avg_messages = self.collection.aggregate([
                {"$group": {"_id": None, "avg": {"$avg": "$total_messages"}}}
            ])
            avg_messages_result = list(avg_messages)
            avg_messages_count = avg_messages_result[0]["avg"] if avg_messages_result else 0
            
            # סה"כ הודעות
            total_messages = self.collection.aggregate([
                {"$group": {"_id": None, "total": {"$sum": "$total_messages"}}}
            ])
            total_messages_result = list(total_messages)
            total_messages_count = total_messages_result[0]["total"] if total_messages_result else 0
            
            return {
                "total_customers": total_customers,
                "total_messages": total_messages_count,
                "avg_messages_per_customer": round(avg_messages_count, 1),
                "gender_distribution": {item["_id"]: item["count"] for item in gender_stats}
            }
            
        except Exception as e:
            print(f"❌ שגיאה בקבלת סטטיסטיקות מ-MongoDB: {e}")
            return {}
    
    def delete_summary(self, user_id: str) -> bool:
        """מחק סיכום שיחה"""
        if not self.is_connected():
            print("❌ אין חיבור ל-MongoDB")
            return False
        
        try:
            result = self.collection.delete_one({"phone_number": user_id})
            if result.deleted_count > 0:
                print(f"✅ סיכום נמחק בהצלחה עבור {user_id}")
                return True
            else:
                print(f"❌ לא נמצא סיכום למחיקה עבור {user_id}")
                return False
        except Exception as e:
            print(f"❌ שגיאה במחיקת סיכום מ-MongoDB: {e}")
            return False
    
    def close_connection(self):
        """סגור חיבור ל-MongoDB"""
        if self.client:
            self.client.close()
            print("🔌 חיבור ל-MongoDB נסגר")

# יצירת מופע גלובלי
mongodb_manager = MongoDBManager() 