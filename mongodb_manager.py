#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ניהול MongoDB עבור סיכומי שיחה - גרסה משופרת עם בדיקות
"""

import os
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError, DuplicateKeyError
from bson import ObjectId
from dotenv import load_dotenv

# טען משתני סביבה
load_dotenv()

class MongoDBManager:
    def __init__(self):
        """אתחול חיבור ל-MongoDB"""
        self.client = None
        self.db = None
        self.collection = None
        self.connection_tested = False
        self.connect()
    
    def connect(self):
        """התחבר ל-MongoDB עם בדיקות מקיפות"""
        try:
            # בדוק אם משתני הסביבה קיימים
            mongo_uri = os.getenv("MONGODB_URI")
            database_name = os.getenv("MONGODB_DATABASE", "chatbot_db")
            collection_name = os.getenv("MONGODB_COLLECTION", "conversation_summaries")
            
            print("🔍 בודק הגדרות MongoDB...")
            print(f"📊 MONGODB_URI: {'✅ מוגדר' if mongo_uri else '❌ לא מוגדר'}")
            print(f"📊 Database: {database_name}")
            print(f"📊 Collection: {collection_name}")
            
            if not mongo_uri:
                print("⚠️ MONGODB_URI לא מוגדר במשתני הסביבה")
                print("⚠️ המערכת תמשיך לעבוד עם קבצי JSON")
                print("💡 להגדרת MongoDB, הוסף MONGODB_URI למשתני הסביבה")
                print("💡 דוגמה: MONGODB_URI=mongodb+srv://user:pass@cluster.mongodb.net/")
                self._set_disconnected()
                return
            
            # הסתר סיסמה בלוג
            safe_uri = self._mask_password(mongo_uri)
            print(f"🔗 מתחבר ל-MongoDB: {safe_uri}")
            
            # הגדרות חיבור משופרות
            self.client = MongoClient(
                mongo_uri, 
                serverSelectionTimeoutMS=15000,  # 15 שניות
                connectTimeoutMS=15000,
                socketTimeoutMS=15000,
                retryWrites=True,
                maxPoolSize=10,
                minPoolSize=1
            )
            
            # בדוק חיבור עם פרטים
            print("🔄 בודק חיבור למונגו DB...")
            ping_result = self.client.admin.command('ping')
            print(f"✅ חיבור ל-MongoDB הצליח! Ping: {ping_result}")
            
            self.db = self.client[database_name]
            self.collection = self.db[collection_name]
            
            # צור אינדקסים לשיפור ביצועים
            self._create_indexes()
            
            # בדיקת כתיבה/קריאה
            self._test_connection()
            
            print("🎉 MongoDB מוכן לשימוש!")
            
        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            print(f"❌ שגיאה בהתחברות ל-MongoDB: {e}")
            print("⚠️ המערכת תמשיך לעבוד עם קבצי JSON")
            print("💡 בדוק את MONGODB_URI במשתני הסביבה")
            print("💡 וודא שהשרת פועל ונגיש")
            self._set_disconnected()
        except Exception as e:
            print(f"❌ שגיאה כללית בחיבור ל-MongoDB: {e}")
            print("⚠️ המערכת תמשיך לעבוד עם קבצי JSON")
            self._set_disconnected()
    
    def _mask_password(self, uri: str) -> str:
        """הסתר סיסמה ב-URI לצורך הלוג"""
        try:
            if "://" in uri and "@" in uri:
                protocol, rest = uri.split("://", 1)
                if "@" in rest:
                    credentials, host = rest.split("@", 1)
                    if ":" in credentials:
                        user, password = credentials.split(":", 1)
                        return f"{protocol}://{user}:***@{host}"
            return uri[:30] + "..."
        except:
            return uri[:30] + "..."
    
    def _set_disconnected(self):
        """הגדר מצב לא מחובר"""
        self.client = None
        self.db = None
        self.collection = None
        self.connection_tested = False
    
    def _test_connection(self):
        """בדוק שניתן לכתוב ולקרוא מהמונגו"""
        try:
            print("🧪 מבצע בדיקת כתיבה/קריאה...")
            
            test_key = "__test_connection__"
            test_doc = {
                "phone_number": test_key,
                "customer_name": "בדיקת חיבור",
                "summary": "בדיקת חיבור למונגו DB",
                "timestamp": datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.000Z'),
                "test": True
            }
            
            # כתיבה באמצעות upsert כדי למנוע DuplicateKeyError אם המסמך קיים
            self.collection.update_one(
                {"phone_number": test_key},
                {"$set": test_doc, "$setOnInsert": {"created_at": self._now_iso_utc()}},
                upsert=True
            )
            print("✅ כתיבה/עדכון (upsert) הצליחה")
            
            # נסה לקרוא
            found_doc = self.collection.find_one({"phone_number": test_key})
            if found_doc:
                print("✅ קריאה הצליחה")
            else:
                print("⚠️ בעיה בקריאה")
                return False
            
            # מחק את המסמך לניקיון
            self.collection.delete_one({"phone_number": test_key})
            print("✅ מחיקה הצליחה")
            
            self.connection_tested = True
            print("🎯 בדיקת MongoDB הושלמה בהצלחה!")
            return True
            
        except Exception as e:
            print(f"❌ שגיאה בבדיקת החיבור: {e}")
            self.connection_tested = False
            return False
    
    def _create_indexes(self):
        """צור אינדקסים לשיפור ביצועים"""
        try:
            print("📊 יוצר אינדקסים...")
            
            # אינדקס על מספר טלפון (ייחודי)
            try:
                self.collection.create_index("phone_number", unique=True)
                print("✅ אינדקס phone_number נוצר")
            except Exception as e:
                print(f"⚠️ אינדקס phone_number כבר קיים או שגיאה: {e}")
            
            # אינדקס על שם לקוח
            self.collection.create_index("customer_name")
            print("✅ אינדקס customer_name נוצר")
            
            # אינדקס על תאריך
            self.collection.create_index("timestamp")
            print("✅ אינדקס timestamp נוצר")
            
            # אינדקס על שדה notified למניעת כפילויות
            self.collection.create_index("notified")
            print("✅ אינדקס notified נוצר")
            
            print("✅ כל האינדקסים נוצרו בהצלחה")
            
        except Exception as e:
            print(f"⚠️ שגיאה ביצירת אינדקסים: {e}")
    
    def is_connected(self) -> bool:
        """בדוק אם יש חיבור ל-MongoDB"""
        # השוואה מפורשת ל-None כדי להימנע מ-Boolean evaluation על אובייקטי PyMongo
        if self.client is None or self.db is None or self.collection is None:
            return False
        
        try:
            # בדיקה מהירה
            self.client.admin.command('ping')
            return True
        except:
            return False
    
    def save_summary(self, user_id: str, summary_data: Dict) -> bool:
        """שמור סיכום שיחה ב-MongoDB עם לוגים מפורטים"""
        if not self.is_connected():
            print("❌ אין חיבור ל-MongoDB - לא ניתן לשמור")
            return False
        
        try:
            print(f"💾 שומר סיכום ב-MongoDB עבור {user_id}...")
            
            # הוסף את מספר הטלפון למסמך
            summary_data["phone_number"] = user_id
            summary_data["updated_at"] = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.000Z')
            
            # השתמש בפונקציה החדשה למניעת כפילויות
            self.upsert_lead_with_notified(summary_data)
            
            print(f"✅ סיכום נשמר/עודכן ב-MongoDB עבור {user_id}")
            print(f"📊 פרטי סיכום: {summary_data.get('customer_name', 'לא ידוע')} - {len(summary_data.get('summary', ''))} תווים")
            return True
            
        except Exception as e:
            print(f"❌ שגיאה בשמירת סיכום ב-MongoDB: {e}")
            print(f"📄 הסיכום יישמר בקובץ JSON כגיבוי")
            return False
    
    def get_connection_status(self) -> Dict:
        """קבל מידע מפורט על מצב החיבור"""
        status = {
            "connected": self.is_connected(),
            "client_exists": self.client is not None,
            "db_exists": self.db is not None,
            "collection_exists": self.collection is not None,
            "connection_tested": self.connection_tested,
            "mongodb_uri_configured": bool(os.getenv("MONGODB_URI")),
            "database_name": os.getenv("MONGODB_DATABASE", "chatbot_db"),
            "collection_name": os.getenv("MONGODB_COLLECTION", "conversation_summaries"),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if self.is_connected():
            try:
                # נסה לקבל סטטיסטיקות
                stats = self.get_statistics()
                status["statistics"] = stats
                
                # בדוק כמה מסמכים יש
                count = self.collection.count_documents({})
                status["document_count"] = count
                
            except Exception as e:
                status["statistics_error"] = str(e)
        
        return status

    def _now_iso_utc(self) -> str:
        """ISO 8601 UTC with Z (e.g. 2025-08-10T12:34:56.000Z)."""
        return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    
    def upsert_lead_with_notified(self, doc: Dict[str, Any]) -> None:
        """יוצר/מעדכן ליד לפי phone_number"""
        if not isinstance(doc, dict):
            raise ValueError("doc must be a dict")

        key = doc.get("phone_number")
        if not key:
            raise ValueError("doc must include 'phone_number' to upsert")

        now = self._now_iso_utc()
        set_fields: Dict[str, Any] = dict(doc)
        set_fields["updated_at"] = now

        self.collection.update_one(
            {"phone_number": key},
            {
                "$setOnInsert": {"notified": False, "created_at": now},
                "$set": set_fields
            },
            upsert=True
        )
    
    def mark_lead_notified(self, doc_id: Union[str, ObjectId]) -> None:
        """מסמן במסמך שקיימת הודעה/התראה שכבר יצאה"""
        oid = ObjectId(doc_id) if isinstance(doc_id, str) else doc_id
        self.collection.update_one(
            {"_id": oid},
            {"$set": {"notified": True, "notified_at": self._now_iso_utc()}}
        )
    
    def get_unnotified_leads(self) -> List[Dict]:
        """קבל את כל הלידים שעדיין לא נשלחה להם התראה"""
        if not self.is_connected():
            print("❌ אין חיבור ל-MongoDB")
            return []
        
        try:
            unnotified_leads = list(self.collection.find(
                {"notified": {"$ne": True}},
                {"_id": 1, "phone_number": 1, "customer_name": 1, "summary": 1, "timestamp": 1, "notified": 1}
            ).sort("timestamp", -1))
            return unnotified_leads
        except Exception as e:
            print(f"❌ שגיאה בקבלת לידים שלא נשלחה להם התראה: {e}")
            return []
    
    def get_summary(self, user_id: str) -> Optional[Dict]:
        """קבל סיכום שיחה לפי מספר טלפון"""
        if not self.is_connected():
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
            return []
        
        try:
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
        if self.client is not None:
            self.client.close()
            print("🔌 חיבור ל-MongoDB נסגר")

# יצירת מופע גלובלי
print("🚀 מאתחל MongoDB Manager...")
mongodb_manager = MongoDBManager() 