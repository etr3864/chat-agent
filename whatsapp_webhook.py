from flask import Flask, request, jsonify
from chatbot import chat_with_gpt
import requests
import os
import json
import base64
# לא צריכים tempfile יותר - משתמשים ב-BytesIO
from io import BytesIO
from dotenv import load_dotenv
from openai import OpenAI
from datetime import datetime
import time
import random
import tempfile
import os
import cloudinary
import cloudinary.uploader
import cloudinary.api
import threading
import schedule

# OpenAI TTS מודל מתקדם
# gpt-4o-mini-tts הוא המודל העדכני ביותר להמרת טקסט לדיבור
# קולות זמינים: alloy, coral, fable, onyx, nova, coral
# איכות קול גבוהה יותר וזמני תגובה קצרים

# טען משתני סביבה
load_dotenv()

# הגדר את Cloudinary
try:
    CLOUDINARY_CLOUD_NAME = os.environ["CLOUDINARY_CLOUD_NAME"]
    CLOUDINARY_API_KEY = os.environ["CLOUDINARY_API_KEY"]
    CLOUDINARY_API_SECRET = os.environ["CLOUDINARY_API_SECRET"]
    
    cloudinary.config(
        cloud_name=CLOUDINARY_CLOUD_NAME,
        api_key=CLOUDINARY_API_KEY,
        api_secret=CLOUDINARY_API_SECRET
    )
    
    print("✅ Cloudinary מוגדר בהצלחה")
    print("✅ CLOUDINARY_CLOUD_NAME:", CLOUDINARY_CLOUD_NAME)
    print("✅ CLOUDINARY_API_KEY:", CLOUDINARY_API_KEY[:5] + "*****")
    print("✅ CLOUDINARY_API_SECRET:", CLOUDINARY_API_SECRET[:5] + "*****")
    
except KeyError as e:
    print(f"❌ שגיאה: משתנה סביבה Cloudinary חסר: {e}")
    print("⚠️ Cloudinary לא יהיה זמין - קבצי אודיו יישלחו כטקסט")
    CLOUDINARY_AVAILABLE = False
else:
    CLOUDINARY_AVAILABLE = True

# מילון לשמירת מצב הבוט לכל משתמש
bot_active_status = {}

# מילון לשמירת זמני הודעות אחרונות לכל משתמש
last_message_times = {}

def is_bot_active(user_id):
    """בדוק אם הבוט פעיל למשתמש מסוים"""
    return bot_active_status.get(user_id, True)  # ברירת מחדל: פעיל

def set_bot_status(user_id, active):
    """הגדר מצב הבוט למשתמש מסוים"""
    bot_active_status[user_id] = active
    print(f"🤖 בוט {'פעיל' if active else 'לא פעיל'} עבור משתמש: {user_id}")

def update_last_message_time(user_id):
    """עדכן זמן הודעה אחרונה למשתמש"""
    last_message_times[user_id] = datetime.now()
    print(f"⏰ זמן הודעה אחרונה עודכן עבור: {user_id}")

def check_and_summarize_old_conversations():
    """בדוק שיחות ישנות שלא קיבלו סיכום ובצע סיכום אוטומטי"""
    try:
        print("🔄 בודק שיחות ישנות לסיכום אוטומטי...")
        
        # ייבא את הפונקציות הנדרשות
        from chatbot import conversations, summarize_conversation, save_conversation_summary, save_conversation_to_file
        
        current_time = datetime.now()
        summarized_count = 0
        
        # בדוק אם יש שיחות
        if not conversations:
            print("ℹ️ אין שיחות לבדיקה")
            return
        
        for user_id, conversation in conversations.items():
            try:
                # בדוק אם יש שיחה עם יותר מ-5 הודעות (הורדתי מ-10 ל-5)
                user_assistant_messages = [m for m in conversation if m["role"] in ["user", "assistant"]]
                if len(user_assistant_messages) >= 5:
                    # בדוק אם עבר זמן רב מההודעה האחרונה (יותר משעה)
                    if user_id in last_message_times:
                        time_diff = current_time - last_message_times[user_id]
                        if time_diff.total_seconds() > 3600:  # שעה
                            # בדוק אם כבר יש סיכום בקובץ ה-JSON
                            try:
                                from conversation_summaries import summaries_manager
                                existing_summary = summaries_manager.get_summary(user_id)
                                if not existing_summary:
                                    print(f"🔄 מבצע סיכום אוטומטי לשיחה ישנה: {user_id}")
                                    summary = summarize_conversation(user_id)
                                    save_conversation_summary(user_id, summary)
                                    save_conversation_to_file(user_id)
                                    summarized_count += 1
                                    print(f"✅ סיכום אוטומטי הושלם עבור: {user_id}")
                            except Exception as e:
                                print(f"⚠️ שגיאה בסיכום אוטומטי עבור {user_id}: {e}")
                                continue
            except Exception as e:
                print(f"⚠️ שגיאה בבדיקת שיחה {user_id}: {e}")
                continue
        
        if summarized_count > 0:
            print(f"✅ סיכום אוטומטי הושלם עבור {summarized_count} שיחות")
        else:
            print("ℹ️ אין שיחות ישנות שדורשות סיכום")
            
    except Exception as e:
        print(f"❌ שגיאה בבדיקת שיחות ישנות: {e}")
        import traceback
        traceback.print_exc()

def run_auto_summary_scheduler():
    """הפעל את מערכת הסיכום האוטומטי"""
    try:
        print("⏰ מפעיל מערכת סיכום אוטומטי...")
        
        # בדוק שיחות ישנות כל 30 דקות
        schedule.every(30).minutes.do(check_and_summarize_old_conversations)
        
        # בדוק שיחות ישנות כל שעה
        schedule.every().hour.do(check_and_summarize_old_conversations)
        
        print("✅ מערכת סיכום אוטומטי הופעלה")
        print("   - בדיקה כל 30 דקות")
        print("   - בדיקה כל שעה")
        
        # הרץ בדיקה מיד בהפעלה
        check_and_summarize_old_conversations()
        
        while True:
            try:
                schedule.run_pending()
                time.sleep(60)  # בדוק כל דקה
            except KeyboardInterrupt:
                print("⏹️ מערכת הסיכום האוטומטי הופסקה")
                break
            except Exception as e:
                print(f"⚠️ שגיאה במערכת הסיכום האוטומטי: {e}")
                time.sleep(60)  # המתן דקה ונסה שוב
                continue
            
    except Exception as e:
        print(f"❌ שגיאה במערכת הסיכום האוטומטי: {e}")
        import traceback
        traceback.print_exc()

def start_auto_summary_thread():
    """הפעל את מערכת הסיכום האוטומטי בthread נפרד"""
    try:
        print("🚀 מפעיל מערכת סיכום אוטומטי...")
        scheduler_thread = threading.Thread(target=run_auto_summary_scheduler, daemon=True)
        scheduler_thread.start()
        print("✅ thread של מערכת הסיכום האוטומטי הופעל")
        
        # המתן קצת כדי לוודא שהמערכת עובדת
        time.sleep(1)
        
        # בדוק אם ה-thread עדיין פעיל
        if scheduler_thread.is_alive():
            print("✅ מערכת הסיכום האוטומטי פועלת בהצלחה")
        else:
            print("⚠️ מערכת הסיכום האוטומטי לא פועלת")
            
    except Exception as e:
        print(f"❌ שגיאה בהפעלת thread של מערכת הסיכום: {e}")
        import traceback
        traceback.print_exc()

def handle_admin_commands(message, sender):
    """טיפול בפקודות מנהל לשליטה בבוט"""
    message_lower = message.lower().strip()
    
    # פקודה לעצירת הבוט
    if message_lower in ["עצור", "עצור בוט", "stop", "stop bot", "הפסק", "הפסק בוט"]:
        set_bot_status(sender, False)
        return "🛑 הבוט הופסק עבורך. עכשיו אתה יכול לשלוח הודעות ידניות.\n\nכדי להחזיר את הבוט, שלח: 'מעכשיו ההתכתבות שלך תמשיך עם הבוט'"
    
    # פקודה להפעלת הבוט
    elif message_lower == "מעכשיו ההתכתבות שלך תמשיך עם הבוט":
        set_bot_status(sender, True)
        return "✅ הבוט הופעל מחדש! עכשיו אני אענה על כל ההודעות שלך."
    
    # פקודה לבדיקת סטטוס
    elif message_lower in ["סטטוס", "status", "מה המצב"]:
        status = "פעיל" if is_bot_active(sender) else "לא פעיל"
        return f"📊 מצב הבוט עבורך: {status}"
    
    # פקודה לעזרה
    elif message_lower in ["עזרה", "help", "מה אני יכול לעשות"]:
        return """🤖 פקודות זמינות:

🛑 עצור/עצור בוט - עצור את הבוט
✅ מעכשיו ההתכתבות שלך תמשיך עם הבוט - הפעל את הבוט
📊 סטטוס - בדוק מצב הבוט
❓ עזרה - הצג הודעה זו

כשהבוט לא פעיל, אתה יכול לשלוח הודעות ידניות ללא הפרעה."""
    
    # פקודות מנהל מתקדמות (רק למנהל הראשי)
    if sender == "972523006544" or sender == "0523006544":
        # צפייה בסיכומים
        if message_lower in ["סיכומים", "summaries"]:
            try:
                from conversation_summaries import summaries_manager
                summaries = summaries_manager.get_all_summaries()
                if summaries:
                    summary_text = "📋 סיכומי שיחות:\n\n"
                    for i, summary in enumerate(summaries[:10], 1):  # רק 10 הראשונים
                        summary_text += f"{i}. {summary.get('customer_name', 'לא ידוע')} - {summary.get('phone_number', '')}\n"
                        summary_text += f"   {summary.get('summary', '')[:100]}...\n\n"
                    if len(summaries) > 10:
                        summary_text += f"...ועוד {len(summaries) - 10} סיכומים"
                    return summary_text
                else:
                    return "📋 אין סיכומים זמינים כרגע"
            except Exception as e:
                return f"❌ שגיאה בטעינת סיכומים: {e}"
        
        # חיפוש שיחה
        elif message_lower.startswith("חפש "):
            search_term = message_lower[5:].strip()
            try:
                from conversation_summaries import summaries_manager
                results = summaries_manager.search_summaries(search_term)
                if results:
                    result_text = f"🔍 תוצאות חיפוש עבור '{search_term}':\n\n"
                    for i, result in enumerate(results[:5], 1):
                        result_text += f"{i}. {result.get('customer_name', 'לא ידוע')} - {result.get('phone_number', '')}\n"
                        result_text += f"   {result.get('summary', '')[:100]}...\n\n"
                    return result_text
                else:
                    return f"🔍 לא נמצאו תוצאות עבור '{search_term}'"
            except Exception as e:
                return f"❌ שגיאה בחיפוש: {e}"
        
        # סטטיסטיקות
        elif message_lower in ["סטטיסטיקות", "stats", "statistics"]:
            try:
                from conversation_summaries import summaries_manager
                stats = summaries_manager.get_statistics()
                if stats:
                    stats_text = "📊 סטטיסטיקות שיחות:\n\n"
                    stats_text += f"📈 סה\"כ שיחות: {stats.get('total_conversations', 0)}\n"
                    stats_text += f"📅 שיחות היום: {stats.get('conversations_today', 0)}\n"
                    stats_text += f"📅 שיחות השבוע: {stats.get('conversations_this_week', 0)}\n"
                    stats_text += f"📅 שיחות החודש: {stats.get('conversations_this_month', 0)}\n"
                    return stats_text
                else:
                    return "📊 אין סטטיסטיקות זמינות כרגע"
            except Exception as e:
                return f"❌ שגיאה בטעינת סטטיסטיקות: {e}"
        
        # ייצוא נתונים
        elif message_lower in ["ייצא", "export"]:
            try:
                from conversation_summaries import summaries_manager
                filename = summaries_manager.export_to_txt()
                return f"📤 נתונים יוצאו לקובץ: {filename}"
            except Exception as e:
                return f"❌ שגיאה בייצוא: {e}"
        
        # בדיקת בוט
        elif message_lower.startswith("בדוק בוט "):
            phone = message_lower[10:].strip()
            if not phone.startswith("972"):
                phone = "972" + phone.lstrip("0")
            status = "פעיל" if is_bot_active(phone) else "לא פעיל"
            return f"🤖 מצב הבוט עבור {phone}: {status}"
        
        # עצירת בוט
        elif message_lower.startswith("עצור בוט "):
            phone = message_lower[10:].strip()
            if not phone.startswith("972"):
                phone = "972" + phone.lstrip("0")
            set_bot_status(phone, False)
            return f"🛑 הבוט הופסק עבור {phone}"
        
        # הפעלת בוט
        elif message_lower.startswith("הפעל בוט "):
            phone = message_lower[10:].strip()
            if not phone.startswith("972"):
                phone = "972" + phone.lstrip("0")
            set_bot_status(phone, True)
            return f"✅ הבוט הופעל עבור {phone}"
        
        # בדיקת בריאות המערכת הקולית
        elif message_lower in ["בדוק קול", "voice health", "voice status", "מערכת קול"]:
            try:
                health = check_voice_system_health()
                health_text = "🎤 בדיקת בריאות המערכת הקולית:\n\n"
                
                for key, status in health.items():
                    if key != "error":
                        health_text += f"{key}: {status}\n"
                
                if "error" in health:
                    health_text += f"\n❌ שגיאה: {health['error']}"
                
                return health_text
            except Exception as e:
                return f"❌ שגיאה בבדיקת בריאות המערכת: {e}"
        
        # סטטיסטיקות מערכת קולית
        elif message_lower in ["סטט קול", "voice stats", "voice statistics", "סטטיסטיקות קול"]:
            try:
                stats = get_voice_system_stats()
                stats_text = "🎤 סטטיסטיקות מערכת קולית:\n\n"
                
                if "error" not in stats:
                    stats_text += f"📅 זמן: {stats.get('timestamp', 'לא ידוע')}\n"
                    stats_text += f"🤖 משתמשים פעילים: {stats.get('bot_active_users', 0)}\n"
                    stats_text += f"⏸️ משתמשים לא פעילים: {stats.get('bot_inactive_users', 0)}\n"
                    stats_text += f"👥 סה\"כ משתמשים: {stats.get('total_registered_users', 0)}\n"
                    
                    # הוסף סטטוס בריאות
                    health = stats.get('system_health', {})
                    if health and "error" not in health:
                        stats_text += "\n🔍 סטטוס בריאות:\n"
                        for key, status in health.items():
                            if key != "error":
                                stats_text += f"   {key}: {status}\n"
                else:
                    stats_text += f"❌ שגיאה: {stats['error']}"
                
                return stats_text
            except Exception as e:
                return f"❌ שגיאה באיסוף סטטיסטיקות קול: {e}"
        
        # בדיקת בוט למשתמש ספציפי
        elif message_lower.startswith("בדוק בוט "):
            try:
                phone_number = message_lower[11:].strip()
                if phone_number:
                    # הוסף קידומת אם חסרה
                    if not phone_number.startswith("972"):
                        if phone_number.startswith("0"):
                            phone_number = "972" + phone_number[1:]
                        else:
                            phone_number = "972" + phone_number
                    
                    is_active = is_bot_active(phone_number)
                    status = "פעיל" if is_active else "לא פעיל"
                    return f"🤖 סטטוס בוט עבור {phone_number}: {status}"
                else:
                    return "❌ אנא ציין מספר טלפון לבדיקה"
            except Exception as e:
                return f"❌ שגיאה בבדיקת בוט: {e}"
        
        # עצירת בוט למשתמש ספציפי
        elif message_lower.startswith("עצור בוט "):
            try:
                phone_number = message_lower[11:].strip()
                if phone_number:
                    # הוסף קידומת אם חסרה
                    if not phone_number.startswith("972"):
                        if phone_number.startswith("0"):
                            phone_number = "972" + phone_number[1:]
                        else:
                            phone_number = "972" + phone_number
                    
                    set_bot_status(phone_number, False)
                    return f"🛑 הבוט הופסק עבור {phone_number}"
                else:
                    return "❌ אנא ציין מספר טלפון לעצירה"
            except Exception as e:
                return f"❌ שגיאה בעצירת בוט: {e}"
        
        # הפעלת בוט למשתמש ספציפי
        elif message_lower.startswith("הפעל בוט "):
            try:
                phone_number = message_lower[11:].strip()
                if phone_number:
                    # הוסף קידומת אם חסרה
                    if not phone_number.startswith("972"):
                        if phone_number.startswith("0"):
                            phone_number = "972" + phone_number[1:]
                        else:
                            phone_number = "972" + phone_number
                    
                    set_bot_status(phone_number, True)
                    return f"✅ הבוט הופעל עבור {phone_number}"
                else:
                    return "❌ אנא ציין מספר טלפון להפעלה"
            except Exception as e:
                return f"❌ שגיאה בהפעלת בוט: {e}"
    
    return None  # לא זוהו פקודות מנהל

# טען משתני סביבה - ללא ברירת מחדל כדי לזהות בעיות
try:
    INSTANCE_ID = os.environ["ULTRA_INSTANCE_ID"]
    TOKEN = os.environ["ULTRA_TOKEN"]
    OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
    
    print("✅ INSTANCE_ID:", INSTANCE_ID)
    print("✅ TOKEN prefix:", TOKEN[:5] + "*****")
    print("✅ OPENAI_API_KEY prefix:", OPENAI_API_KEY[:10] + "*****")
    
except KeyError as e:
    print(f"❌ שגיאה: משתנה סביבה חסר: {e}")
    raise

# מפתח ElevenLabs ל-TTS
try:
    ELEVEN_API_KEY = os.environ["ELEVEN_API_KEY"]
    print("✅ ELEVEN_API_KEY prefix:", ELEVEN_API_KEY[:10] + "*****")
except KeyError as e:
    print(f"❌ שגיאה: משתנה סביבה חסר: {e}")
    raise

# הגדרות קבועות ל-ElevenLabs TTS
ELEVEN_VOICE_ID = "cgSgspJ2msm6clMCkdW9"  # Jessica
ELEVEN_MODEL_ID = "eleven_multilingual_v3"

# התחברות ל־OpenAI עבור תמלול ו-TTS
client = OpenAI(api_key=OPENAI_API_KEY)

app = Flask(__name__)

# פונקציות עזר לטיפול בקבצים
def upload_audio_to_cloudinary(audio_bytes, filename="audio.mp3"):
    """העלה קובץ אודיו ל-Cloudinary ומחזיר את ה-URL"""
    try:
        if not CLOUDINARY_AVAILABLE:
            print("❌ Cloudinary לא זמין")
            return None
        
        if not audio_bytes or len(audio_bytes) < 1000:
            print("⚠️ קובץ אודיו ריק או קטן מדי")
            return None
        
        print(f"☁️ מעלה אודיו ל-Cloudinary: {len(audio_bytes)} bytes")
        print(f"☁️ שם קובץ: {filename}")
        
        # המר את ה-bytes לקובץ זמני
        from io import BytesIO
        audio_file = BytesIO(audio_bytes)
        audio_file.name = filename
        
        # הגדרות מיטביות ל-Cloudinary
        upload_options = {
            "resource_type": "video",  # Cloudinary מטפל באודיו תחת resource_type="video"
            "format": "mp3",
            "folder": "whatsapp_audio",
            "public_id": f"audio_{int(time.time())}_{random.randint(1000, 9999)}",
            "overwrite": False,
            "audio_codec": "mp3",
            "bit_rate": "128k",  # איכות טובה לקבצי WhatsApp
            "channels": "stereo"
        }
        
        print(f"☁️ העלאה עם הגדרות: {upload_options}")
        
        # העלה ל-Cloudinary
        result = cloudinary.uploader.upload(
            audio_file,
            **upload_options
        )
        
        audio_url = result.get("secure_url")
        if audio_url:
            print(f"✅ אודיו הועלה בהצלחה ל-Cloudinary: {audio_url}")
            print(f"📊 פרטי העלאה: {result.get('format', 'unknown')} - {result.get('bytes', 0)} bytes")
            return audio_url
        else:
            print("❌ לא קיבלתי URL מ-Cloudinary")
            print(f"🔍 תגובה מלאה: {result}")
            return None
            
    except Exception as e:
        print(f"❌ שגיאה בהעלאת אודיו ל-Cloudinary: {e}")
        import traceback
        traceback.print_exc()
        return None

def download_file(file_url):
    """הורד קובץ מ-URL"""
    try:
        print(f"🔄 מתחיל הורדת קובץ מ: {file_url}")
        
        # בדוק שהקישור תקין
        if not file_url or not file_url.strip():
            print(f"❌ קישור חסר או ריק")
            return None
        
        if not file_url.startswith(('http://', 'https://')):
            print(f"❌ קישור לא תקין: {file_url}")
            return None
        
        print(f"🔗 קישור תקין, מתחיל הורדה...")
        
        # הוסף headers כדי לחקות דפדפן
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': '*/*',
            'Accept-Language': 'he-IL,he;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive'
        }
        
        print(f"📥 שולח בקשת GET עם timeout של 60 שניות...")
        response = requests.get(file_url, headers=headers, timeout=60, stream=True)
        
        # בדוק את קוד התגובה
        print(f"📊 קוד תגובה: {response.status_code}")
        print(f"📊 Content-Type: {response.headers.get('content-type', 'unknown')}")
        print(f"📊 Content-Length: {response.headers.get('content-length', 'unknown')}")
        
        response.raise_for_status()
        
        # קרא את התוכן
        print(f"📖 קורא תוכן הקובץ...")
        content = response.content
        
        if not content:
            print("❌ תוכן הקובץ ריק")
            return None
        
        print(f"✅ קובץ הורד בהצלחה: {len(content)} bytes")
        print(f"📊 גודל סופי: {len(content)} bytes")
        
        # בדיקה נוספת - וודא שהקובץ לא ריק
        if len(content) < 100:
            print(f"⚠️ קובץ קטן מדי: {len(content)} bytes")
            return None
        
        return content
        
    except requests.exceptions.Timeout:
        print(f"❌ timeout בהורדת קובץ: {file_url}")
        return None
    except requests.exceptions.RequestException as e:
        print(f"❌ שגיאה בהורדת קובץ: {e}")
        return None
    except Exception as e:
        print(f"❌ שגיאה לא צפויה בהורדת קובץ: {e}")
        import traceback
        traceback.print_exc()
        return None

def transcribe_audio(audio_data):
    """תמלל קובץ אודיו באמצעות OpenAI Whisper"""
    try:
        # בדוק שהאודיו לא ריק
        if not audio_data or len(audio_data) < 1000:
            print("⚠️ קובץ אודיו ריק או קטן מדי")
            return None
        
        print(f"🎤 מתמלל אודיו: {len(audio_data)} bytes")
        
        # השתמש ב-BytesIO במקום קובץ זמני
        from io import BytesIO
        audio_file = BytesIO(audio_data)
        audio_file.name = "audio.ogg"
        
        # תמלל באמצעות OpenAI
        transcript = client.audio.transcriptions.create(
            model="whisper-1", 
            file=audio_file,
            language="he"  # עברית
        )
        
        result = transcript.text.strip()
        print(f"✅ תמלול הושלם: {result}")
        return result
            
    except Exception as e:
        print(f"❌ שגיאה בתמלול: {e}")
        import traceback
        traceback.print_exc()
        return None

def text_to_speech(text, language="he"):
    """המר טקסט לדיבור באמצעות ElevenLabs TTS (MP3 bytes)"""
    try:
        # בדוק שהטקסט לא ריק
        if not text or not text.strip():
            print("⚠️ טקסט ריק ל-TTS")
            return None

        # הגבל אורך הטקסט לשמירה על זמן תגובה וגודל קובץ
        if len(text) > 4000:
            text = text[:4000] + "..."
            print(f"⚠️ טקסט קוצר ל-TTS: {len(text)} תווים")

        print(f"🎵 יוצר קול עבור: {text[:100]}... (ElevenLabs)")

        url = f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVEN_VOICE_ID}"
        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": ELEVEN_API_KEY,
        }
        body = {
            "text": text,
            "voice_settings": {
                "stability": 0.4,
                "similarity_boost": 0.8,
                "style": 0.5,
                "use_speaker_boost": True,
            },
        }

        resp = requests.post(url, headers=headers, data=json.dumps(body))
        if resp.status_code != 200:
            print(f"❌ שגיאה מ-ElevenLabs TTS: {resp.status_code} {resp.text}")
            return None

        audio_bytes = resp.content
        print(f"✅ קול נוצר בהצלחה: {len(audio_bytes)} bytes")
        return audio_bytes

    except Exception as e:
        print(f"❌ שגיאה ב-TTS: {e}")
        import traceback
        traceback.print_exc()
        return None

def analyze_image(image_data):
    """נתח תמונה באמצעות OpenAI Vision"""
    try:
        print(f"🔍 מנתח תמונה: {len(image_data)} bytes")
        
        # בדוק שהתמונה לא ריקה
        if not image_data or len(image_data) == 0:
            print("❌ התמונה ריקה")
            return "התמונה ריקה או לא תקינה"
        
        # בדוק שהתמונה לא קטנה מדי
        if len(image_data) < 1000:
            print("❌ התמונה קטנה מדי")
            return "התמונה קטנה מדי לניתוח"
        
        # המר לbase64
        base64_image = base64.b64encode(image_data).decode('utf-8')
        print(f"🔍 Base64 הומר: {len(base64_image)} characters")
        
        print("🤖 שולח ל-OpenAI Vision...")
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "תאר מה אתה רואה בתמונה הזו בעברית בצורה מפורטת. אם זה קשור לעסק, לוגו, מוצר או שירות, תן פרטים רלוונטיים ליצירת דף נחיתה. תאר את הצבעים, הטקסטים, הסגנון והתחושה הכללית. אם יש טקסט בתמונה, תעתיק אותו בדיוק."
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}",
                                "detail": "high"
                            }
                        }
                    ]
                }
            ],
            max_tokens=1500,
            temperature=0.2
        )
        
        result = response.choices[0].message.content
        print(f"✅ קיבלתי תשובה מ-OpenAI: {len(result)} characters")
        return result
        
    except Exception as e:
        print(f"❌ שגיאה בניתוח תמונה: {e}")
        import traceback
        traceback.print_exc()
        return f"לא הצלחתי לנתח את התמונה: {str(e)}"

# פונקציות חדשות לטיפול בהודעות קוליות משודרגות
def transcribe_voice_message(file_url):
    """תמלל הודעה קולית באמצעות OpenAI Whisper"""
    try:
        print(f"🎤 מתחיל תמלול הודעה קולית מ: {file_url}")
        
        # בדוק שהקישור תקין
        if not file_url or not file_url.strip():
            print("❌ קישור קובץ קול חסר או ריק")
            return None
        
        if not file_url.startswith(('http://', 'https://')):
            print(f"❌ קישור לא תקין: {file_url}")
            return None
        
        # 1. הורד את קובץ האודיו
        print("🔄 מוריד קובץ אודיו...")
        audio_data = download_file(file_url)
        if not audio_data:
            print("❌ לא הצלחתי להוריד את קובץ האודיו")
            return None
        
        # 2. בדוק שהאודיו לא ריק
        if len(audio_data) < 1000:
            print(f"⚠️ קובץ אודיו ריק או קטן מדי: {len(audio_data)} bytes")
            return None
        
        print(f"✅ קובץ אודיו הורד בהצלחה: {len(audio_data)} bytes")
        
        # 3. תמלול באמצעות OpenAI Whisper
        print("🎤 מתחיל תמלול עם Whisper...")
        from io import BytesIO
        audio_file = BytesIO(audio_data)
        audio_file.name = "voice.ogg"  # שם הקובץ לזיהוי סוג הקובץ
        
        # תמלול באמצעות OpenAI Whisper
        transcript = client.audio.transcriptions.create(
            model="whisper-1", 
            file=audio_file,
            language="he"  # עברית
        )
        
        result = transcript.text.strip()
        
        if not result:
            print("⚠️ התמלול החזיר טקסט ריק")
            return None
        
        print(f"✅ תמלול הושלם בהצלחה: {result}")
        print(f"📊 אורך הטקסט: {len(result)} תווים")
        
        return result
            
    except Exception as e:
        print(f"❌ שגיאה בתמלול הודעה קולית: {e}")
        import traceback
        traceback.print_exc()
        return None

def create_tts_audio_coral(text, voice="coral"):
    """צור אודיו באמצעות OpenAI gpt-4o-mini-tts (voice=alloy) - מחזיר bytes של MP3"""
    try:
        print("🎵 מתחיל יצירת אודיו עם OpenAI gpt-4o-mini-tts (voice=alloy)...")

        # בדוק שהטקסט לא ריק
        if not text or not text.strip():
            print("⚠️ טקסט ריק ל-TTS")
            return None

        # הגבל אורך הטקסט
        original_length = len(text)
        if original_length > 4000:
            text = text[:4000] + "..."
            print(f"⚠️ טקסט קוצר ל-TTS: {original_length} -> {len(text)} תווים")

        print(f"🎵 יוצר קול עבור: {text[:100]}... (OpenAI)")
        print(f"📊 אורך הטקסט הסופי: {len(text)} תווים")

        # השתמש ב-OpenAI TTS עם הזרמה לקובץ זמני ואז קריאה כ-bytes
        temp_path = None
        try:
            import tempfile
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
            temp_path = tmp.name
            tmp.close()

            # שימוש בלקוח OpenAI שכבר מאותחל עם מפתח מהסביבה
            with client.audio.speech.with_streaming_response.create(
                model="gpt-4o-mini-tts",
                voice="alloy",
                input=text
            ) as response:
                response.stream_to_file(temp_path)

            # קרא את ה-MP3 כ-bytes
            with open(temp_path, "rb") as f:
                audio_bytes = f.read()
        finally:
            if temp_path:
                try:
                    os.unlink(temp_path)
                except Exception:
                    pass

        if not audio_bytes:
            print("❌ OpenAI החזיר אודיו ריק")
            return None

        print(f"✅ קול נוצר בהצלחה: {len(audio_bytes)} bytes")
        print(f"📊 גודל קובץ MP3: {len(audio_bytes)} bytes")

        # בדיקה נוספת - וודא שהאודיו לא ריק
        if len(audio_bytes) < 1000:
            print(f"⚠️ קובץ אודיו קטן מדי: {len(audio_bytes)} bytes")
            return None

        # בדיקה - וודא שהאודיו לא גדול מדי (WhatsApp מגביל ל-16MB)
        if len(audio_bytes) > 16 * 1024 * 1024:
            print(f"⚠️ קובץ אודיו גדול מדי: {len(audio_bytes)} bytes (מעל 16MB)")
            # נסה לקצר את הטקסט
            shortened_text = text[:2000] + "..."
            print(f"🔄 מנסה עם טקסט מקוצר: {len(shortened_text)} תווים")
            return create_tts_audio_coral(shortened_text)

        print(f"🎵 קובץ MP3 מוכן לשליחה: {len(audio_bytes)} bytes")

        # מחזיר את ה-bytes ישירות - ללא שינוי לוגיקה קיימת
        return audio_bytes

    except Exception as e:
        print(f"❌ שגיאה ב-TTS (OpenAI): {e}")
        import traceback
        traceback.print_exc()
        return None

def send_audio_via_ultramsg(to, audio_bytes, caption=""):
    """שלח אודיו דרך UltraMsg API ישירות מה-bytes - ללא שמירת קובץ זמני"""
    try:
        if not audio_bytes:
            print("❌ נתוני אודיו חסרים")
            return False
        
        print(f"🎵 שולח אודיו דרך UltraMsg ל: {to}")
        
        # שלח את האודיו עם token כפרמטר GET
        url = f"https://api.ultramsg.com/{INSTANCE_ID}/messages/audio"
        
        # הוסף את הטוקן כפרמטר GET
        params = {
            'token': TOKEN
        }
        
        # שלח את ה-bytes ישירות עם BytesIO
        from io import BytesIO
        audio_file = BytesIO(audio_bytes)
        audio_file.name = "audio.mp3"  # שם הקובץ לזיהוי סוג הקובץ
        
        # שלח את הפרמטרים ב-data ולא ב-files
        files = {'audio': ('audio.mp3', audio_file, 'audio/mpeg')}
        data = {
            'to': to,
            'caption': caption
        }
        
        print(f"🎵 שולח עם פרמטרים: to={to}, caption={caption}")
        print(f"🎵 URL עם token: {url}?token={TOKEN[:5]}*****")
        print(f"🎵 גודל אודיו: {len(audio_bytes)} bytes")
        
        # נסה לשלוח עם multipart/form-data
        response = requests.post(url, files=files, data=data, params=params)
        print(f"🎵 תגובת UltraMsg API: {response.status_code}")
        print(f"🎵 תוכן תגובה: {response.text}")
        
        # בדוק אם השליחה הצליחה
        if response.status_code == 200:
            try:
                response_json = response.json()
                if "error" in response_json:
                    print(f"❌ שגיאת UltraMsg API: {response_json['error']}")
                    # נסה לשלוח עם פורמט אחר
                    print("🔄 מנסה פורמט אחר...")
                    return send_audio_via_ultramsg_alternative(to, audio_bytes, caption)
                else:
                    print("✅ אודיו נשלח בהצלחה דרך UltraMsg")
                    return True
            except Exception as e:
                print(f"⚠️ לא הצלחתי לפרסר JSON: {e}")
                # אם התגובה היא 200 אבל לא JSON תקין, נניח שהשליחה הצליחה
                print("✅ אודיו נשלח בהצלחה (תגובה לא JSON)")
                return True
        else:
            print(f"❌ שגיאה בשליחת אודיו: {response.status_code}")
            # נסה פורמט אחר
            print("🔄 מנסה פורמט אחר...")
            return send_audio_via_ultramsg_alternative(to, audio_bytes, caption)
            
    except Exception as e:
        print(f"❌ שגיאה בשליחת אודיו דרך UltraMsg: {e}")
        import traceback
        traceback.print_exc()
        # נסה פורמט אחר
        print("🔄 מנסה פורמט אחר...")
        return send_audio_via_ultramsg_alternative(to, audio_bytes, caption)

def send_audio_via_ultramsg_alternative(to, audio_bytes, caption=""):
    """שלח אודיו עם פורמט חלופי"""
    try:
        print(f"🎵 מנסה פורמט חלופי לשליחת אודיו...")
        
        url = f"https://api.ultramsg.com/{INSTANCE_ID}/messages/audio"
        params = {'token': TOKEN}
        
        # נסה עם פורמט אחר - שלח את האודיו כ-bytes ישירות
        from io import BytesIO
        audio_file = BytesIO(audio_bytes)
        audio_file.name = "audio.mp3"
        
        # נסה עם פורמט multipart/form-data שונה
        files = {'audio': audio_file}
        data = {
            'to': to,
            'caption': caption
        }
        
        response = requests.post(url, files=files, data=data, params=params)
        print(f"🎵 תגובת UltraMsg API (פורמט חלופי): {response.status_code}")
        print(f"🎵 תוכן תגובה: {response.text}")
        
        if response.status_code == 200:
            try:
                response_json = response.json()
                if "error" not in response_json:
                    print("✅ אודיו נשלח בהצלחה עם הפורמט החלופי")
                    return True
            except:
                print("✅ אודיו נשלח בהצלחה עם הפורמט החלופי")
                return True
        
        return False
        
    except Exception as e:
        print(f"❌ שגיאה בפורמט החלופי: {e}")
        return False

def send_audio_via_ultramsg_fixed(to, audio_bytes, caption=""):
    """שלח אודיו עם פורמט מתוקן - פותר את בעיית הפרמטרים החסרים"""
    try:
        print(f"🎵 שולח אודיו עם פורמט מתוקן ל: {to}")
        
        url = f"https://api.ultramsg.com/{INSTANCE_ID}/messages/audio"
        
        # שלח את הטוקן כפרמטר GET
        params = {
            'token': TOKEN
        }
        
        # שלח את האודיו עם BytesIO
        from io import BytesIO
        audio_file = BytesIO(audio_bytes)
        audio_file.name = "audio.mp3"
        
        # שלח את הפרמטרים הנדרשים ב-data
        data = {
            'to': to,
            'caption': caption
        }
        
        # שלח את האודיו ב-files עם MIME type נכון
        files = {
            'audio': ('audio.mp3', audio_file, 'audio/mpeg')
        }
        
        print(f"🎵 שולח עם פרמטרים: to={to}, caption={caption}")
        print(f"🎵 גודל אודיו: {len(audio_bytes)} bytes")
        print(f"🎵 URL: {url}")
        print(f"🎵 Token: {TOKEN[:5]}*****")
        
        # שלח את הבקשה עם headers מותאמים
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive'
        }
        
        # שלח את הבקשה
        response = requests.post(url, files=files, data=data, params=params, headers=headers)
        print(f"🎵 תגובת UltraMsg API: {response.status_code}")
        print(f"🎵 תוכן תגובה: {response.text}")
        
        # בדוק את התגובה
        if response.status_code == 200:
            try:
                response_json = response.json()
                if "error" in response_json:
                    print(f"❌ שגיאת UltraMsg API: {response_json['error']}")
                    return False
                else:
                    print("✅ אודיו נשלח בהצלחה!")
                    return True
            except Exception as e:
                print(f"⚠️ לא הצלחתי לפרסר JSON: {e}")
                # אם התגובה היא 200, נניח שהשליחה הצליחה
                print("✅ אודיו נשלח בהצלחה!")
                return True
        else:
            print(f"❌ שגיאה בשליחת אודיו: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ שגיאה בשליחת אודיו: {e}")
        import traceback
        traceback.print_exc()
        return False

def send_audio_via_ultramsg_simple(to, audio_bytes, caption=""):
    """שלח אודיו עם פורמט פשוט יותר - נסיון לפתור בעיות API"""
    try:
        print(f"🎵 שולח אודיו עם פורמט פשוט ל: {to}")
        
        url = f"https://api.ultramsg.com/{INSTANCE_ID}/messages/audio"
        
        # שלח את הטוקן כפרמטר GET
        params = {
            'token': TOKEN
        }
        
        # שלח את האודיו עם BytesIO
        from io import BytesIO
        audio_file = BytesIO(audio_bytes)
        audio_file.name = "audio.mp3"
        
        # נסה עם פורמט פשוט יותר
        files = {
            'audio': ('audio.mp3', audio_file, 'audio/mpeg')
        }
        
        # שלח את הפרמטרים הנדרשים ב-data
        data = {
            'to': to,
            'caption': caption
        }
        
        print(f"🎵 שולח עם פרמטרים: to={to}, caption={caption}")
        print(f"🎵 גודל אודיו: {len(audio_bytes)} bytes")
        
        # שלח את הבקשה
        response = requests.post(url, files=files, data=data, params=params)
        print(f"🎵 תגובת UltraMsg API: {response.status_code}")
        print(f"🎵 תוכן תגובה: {response.text}")
        
        # בדוק את התגובה
        if response.status_code == 200:
            try:
                response_json = response.json()
                if "error" in response_json:
                    print(f"❌ שגיאת UltraMsg API: {response_json['error']}")
                    return False
                else:
                    print("✅ אודיו נשלח בהצלחה!")
                    return True
            except Exception as e:
                print(f"⚠️ לא הצלחתי לפרסר JSON: {e}")
                # אם התגובה היא 200, נניח שהשליחה הצליחה
                print("✅ אודיו נשלח בהצלחה!")
                return True
        else:
            print(f"❌ שגיאה בשליחת אודיו: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ שגיאה בשליחת אודיו: {e}")
        import traceback
        traceback.print_exc()
        return False

def send_audio_via_ultramsg_documentation(to, audio_bytes, caption=""):
    """שלח אודיו לפי התיעוד הרשמי של UltraMsg API"""
    try:
        print(f"🎵 שולח אודיו לפי התיעוד הרשמי ל: {to}")
        
        url = f"https://api.ultramsg.com/{INSTANCE_ID}/messages/audio"
        
        # שלח את הטוקן כפרמטר GET
        params = {
            'token': TOKEN
        }
        
        # שלח את האודיו עם BytesIO
        from io import BytesIO
        audio_file = BytesIO(audio_bytes)
        audio_file.name = "audio.mp3"
        
        # נסה עם פורמט לפי התיעוד - אולי הבעיה היא בסדר הפרמטרים
        files = {
            'audio': ('audio.mp3', audio_file, 'audio/mpeg')
        }
        
        # שלח את הפרמטרים הנדרשים ב-data
        data = {
            'to': to,
            'caption': caption
        }
        
        print(f"🎵 שולח עם פרמטרים: to={to}, caption={caption}")
        print(f"🎵 גודל אודיו: {len(audio_bytes)} bytes")
        print(f"🎵 URL: {url}")
        print(f"🎵 Token: {TOKEN[:5]}*****")
        
        # שלח את הבקשה
        response = requests.post(url, files=files, data=data, params=params)
        print(f"🎵 תגובת UltraMsg API: {response.status_code}")
        print(f"🎵 תוכן תגובה: {response.text}")
        
        # בדוק את התגובה
        if response.status_code == 200:
            try:
                response_json = response.json()
                if "error" in response_json:
                    print(f"❌ שגיאת UltraMsg API: {response_json['error']}")
                    return False
                else:
                    print("✅ אודיו נשלח בהצלחה!")
                    return True
            except Exception as e:
                print(f"⚠️ לא הצלחתי לפרסר JSON: {e}")
                # אם התגובה היא 200, נניח שהשליחה הצליחה
                print("✅ אודיו נשלח בהצלחה!")
                return True
        else:
            print(f"❌ שגיאה בשליחת אודיו: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ שגיאה בשליחת אודיו: {e}")
        import traceback
        traceback.print_exc()
        return False

def send_audio_via_ultramsg_recorald(to, audio_bytes, caption=""):
    """שלח אודיו עם סדר פרמטרים שונה - אולי הבעיה היא בסדר"""
    try:
        print(f"🎵 שולח אודיו עם סדר פרמטרים שונה ל: {to}")
        
        url = f"https://api.ultramsg.com/{INSTANCE_ID}/messages/audio"
        
        # שלח את הטוקן כפרמטר GET
        params = {
            'token': TOKEN
        }
        
        # שלח את האודיו עם BytesIO
        from io import BytesIO
        audio_file = BytesIO(audio_bytes)
        audio_file.name = "audio.mp3"
        
        # נסה עם סדר פרמטרים שונה - אולי הבעיה היא בסדר
        files = {
            'audio': ('audio.mp3', audio_file, 'audio/mpeg')
        }
        
        # שלח את הפרמטרים הנדרשים ב-data
        data = {
            'caption': caption,
            'to': to
        }
        
        print(f"🎵 שולח עם פרמטרים: caption={caption}, to={to}")
        print(f"🎵 גודל אודיו: {len(audio_bytes)} bytes")
        
        # שלח את הבקשה
        response = requests.post(url, files=files, data=data, params=params)
        print(f"🎵 תגובת UltraMsg API: {response.status_code}")
        print(f"🎵 תוכן תגובה: {response.text}")
        
        # בדוק את התגובה
        if response.status_code == 200:
            try:
                response_json = response.json()
                if "error" in response_json:
                    print(f"❌ שגיאת UltraMsg API: {response_json['error']}")
                    return False
                else:
                    print("✅ אודיו נשלח בהצלחה!")
                    return True
            except Exception as e:
                print(f"⚠️ לא הצלחתי לפרסר JSON: {e}")
                # אם התגובה היא 200, נניח שהשליחה הצליחה
                print("✅ אודיו נשלח בהצלחה!")
                return True
        else:
            print(f"❌ שגיאה בשליחת אודיו: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ שגיאה בשליחת אודיו: {e}")
        import traceback
        traceback.print_exc()
        return False

def send_audio_via_ultramsg_form_data(to, audio_bytes, caption=""):
    """שלח אודיו עם פורמט form-data שונה - אולי הבעיה היא בפורמט"""
    try:
        print(f"🎵 שולח אודיו עם פורמט form-data שונה ל: {to}")
        
        url = f"https://api.ultramsg.com/{INSTANCE_ID}/messages/audio"
        
        # שלח את הטוקן כפרמטר GET
        params = {
            'token': TOKEN
        }
        
        # שלח את האודיו עם BytesIO
        from io import BytesIO
        audio_file = BytesIO(audio_bytes)
        audio_file.name = "audio.mp3"
        
        # נסה עם פורמט form-data שונה
        files = {
            'audio': ('audio.mp3', audio_file, 'audio/mpeg')
        }
        
        # שלח את הפרמטרים הנדרשים ב-data
        data = {
            'to': to,
            'caption': caption
        }
        
        print(f"🎵 שולח עם פרמטרים: to={to}, caption={caption}")
        print(f"🎵 גודל אודיו: {len(audio_bytes)} bytes")
        
        # שלח את הבקשה עם headers מותאמים
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive'
        }
        
        # שלח את הבקשה
        response = requests.post(url, files=files, data=data, params=params, headers=headers)
        print(f"🎵 תגובת UltraMsg API: {response.status_code}")
        print(f"🎵 תוכן תגובה: {response.text}")
        
        # בדוק את התגובה
        if response.status_code == 200:
            try:
                response_json = response.json()
                if "error" in response_json:
                    print(f"❌ שגיאת UltraMsg API: {response_json['error']}")
                    return False
                else:
                    print("✅ אודיו נשלח בהצלחה!")
                    return True
            except Exception as e:
                print(f"⚠️ לא הצלחתי לפרסר JSON: {e}")
                # אם התגובה היא 200, נניח שהשליחה הצליחה
                print("✅ אודיו נשלח בהצלחה!")
                return True
        else:
            print(f"❌ שגיאה בשליחת אודיו: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ שגיאה בשליחת אודיו: {e}")
        import traceback
        traceback.print_exc()
        return False

def send_audio_via_ultramsg_json(to, audio_bytes, caption=""):
    """שלח אודיו עם פורמט JSON - אולי הבעיה היא בפורמט של הבקשה"""
    try:
        print(f"🎵 שולח אודיו עם פורמט JSON ל: {to}")
        
        url = f"https://api.ultramsg.com/{INSTANCE_ID}/messages/audio"
        
        # שלח את הטוקן כפרמטר GET
        params = {
            'token': TOKEN
        }
        
        # שלח את האודיו עם BytesIO
        from io import BytesIO
        audio_file = BytesIO(audio_bytes)
        audio_file.name = "audio.mp3"
        
        # נסה עם פורמט JSON - אולי הבעיה היא בפורמט של הבקשה
        files = {
            'audio': ('audio.mp3', audio_file, 'audio/mpeg')
        }
        
        # שלח את הפרמטרים הנדרשים ב-data
        data = {
            'to': to,
            'caption': caption
        }
        
        print(f"🎵 שולח עם פרמטרים: to={to}, caption={caption}")
        print(f"🎵 גודל אודיו: {len(audio_bytes)} bytes")
        
        # שלח את הבקשה עם headers מותאמים
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Content-Type': 'multipart/form-data'
        }
        
        # שלח את הבקשה
        response = requests.post(url, files=files, data=data, params=params, headers=headers)
        print(f"🎵 תגובת UltraMsg API: {response.status_code}")
        print(f"🎵 תוכן תגובה: {response.text}")
        
        # בדוק את התגובה
        if response.status_code == 200:
            try:
                response_json = response.json()
                if "error" in response_json:
                    print(f"❌ שגיאת UltraMsg API: {response_json['error']}")
                    return False
                else:
                    print("✅ אודיו נשלח בהצלחה!")
                    return True
            except Exception as e:
                print(f"⚠️ לא הצלחתי לפרסר JSON: {e}")
                # אם התגובה היא 200, נניח שהשליחה הצליחה
                print("✅ אודיו נשלח בהצלחה!")
                return True
        else:
            print(f"❌ שגיאה בשליחת אודיו: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ שגיאה בשליחת אודיו: {e}")
        import traceback
        traceback.print_exc()
        return False

def send_audio_via_ultramsg_final(to, audio_bytes, caption=""):
    """שלח אודיו עם פורמט סופי - נסיון אחרון לפתור את הבעיה"""
    try:
        print(f"🎵 שולח אודיו עם פורמט סופי ל: {to}")
        
        url = f"https://api.ultramsg.com/{INSTANCE_ID}/messages/audio"
        
        # שלח את הטוקן כפרמטר GET
        params = {
            'token': TOKEN
        }
        
        # שלח את האודיו עם BytesIO
        from io import BytesIO
        audio_file = BytesIO(audio_bytes)
        audio_file.name = "audio.mp3"
        
        # נסה עם פורמט סופי - אולי הבעיה היא בפורמט של הבקשה
        files = {
            'audio': ('audio.mp3', audio_file, 'audio/mpeg')
        }
        
        # שלח את הפרמטרים הנדרשים ב-data
        data = {
            'to': to,
            'caption': caption
        }
        
        print(f"🎵 שולח עם פרמטרים: to={to}, caption={caption}")
        print(f"🎵 גודל אודיו: {len(audio_bytes)} bytes")
        
        # שלח את הבקשה עם headers מותאמים
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive'
        }
        
        # שלח את הבקשה
        response = requests.post(url, files=files, data=data, params=params, headers=headers)
        print(f"🎵 תגובת UltraMsg API: {response.status_code}")
        print(f"🎵 תוכן תגובה: {response.text}")
        
        # בדוק את התגובה
        if response.status_code == 200:
            try:
                response_json = response.json()
                if "error" in response_json:
                    print(f"❌ שגיאת UltraMsg API: {response_json['error']}")
                    return False
                else:
                    print("✅ אודיו נשלח בהצלחה!")
                    return True
            except Exception as e:
                print(f"⚠️ לא הצלחתי לפרסר JSON: {e}")
                # אם התגובה היא 200, נניח שהשליחה הצליחה
                print("✅ אודיו נשלח בהצלחה!")
                return True
        else:
            print(f"❌ שגיאה בשליחת אודיו: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ שגיאה בשליחת אודיו: {e}")
        import traceback
        traceback.print_exc()
        return False

def calculate_smart_delay(message_length: int, message_type: str = "text") -> float:
    """חישוב עיכוב חכם אך מקוצר מעט כדי לשפר מהירות תגובה"""
    base_delay = 0.6  # היה 1.0

    if message_type == "image":
        base_delay = 1.2  # היה 2.0
    elif message_type == "audio":
        base_delay = 2.0  # היה 3.0

    # עיכוב לפי אורך ההודעה (מקוצר בכ~35%)
    if message_length < 10:
        delay = base_delay + random.uniform(0.3, 0.9)
    elif message_length < 50:
        delay = base_delay + random.uniform(0.6, 1.5)
    elif message_length < 150:
        delay = base_delay + random.uniform(1.2, 2.4)
    elif message_length < 300:
        delay = base_delay + random.uniform(1.8, 3.6)
    else:
        delay = base_delay + random.uniform(2.4, 4.8)

    # רנדומיות קטנה
    delay += random.uniform(-0.3, 0.3)

    # רף מינימלי מעט נמוך יותר
    delay = max(0.3, delay)

    print(f"⏱️ עיכוב חכם: {delay:.2f} שניות (אורך: {message_length}, סוג: {message_type})")
    return delay

@app.route("/")
def healthcheck():
    """בדיקת בריאות לשרת - נדרש עבור Render"""
    return "🚀 WhatsApp Chat Agent Server is alive ✅", 200

@app.route('/webhook', methods=['POST'])
def whatsapp_webhook():
    data = request.get_json()
    print("🔍 JSON מלא שהתקבל:")
    print(data)

    try:
        payload = data.get("data", {})
        sender = payload.get("from", "")
        sender_name = payload.get("pushname", "")  # שם השולח מ-UltraMsg
        
        if not sender:
            print("⚠️ שולח חסר.")
            # חישוב עיכוב חכם לפני שליחת הודעת שגיאה
            delay = calculate_smart_delay(30, "text")  # הודעת שגיאה קצרה
            print(f"⏱️ ממתין {delay:.2f} שניות לפני שליחת הודעת שגיאה...")
            time.sleep(delay)
            return "Invalid", 400
            
        if sender_name:
            print(f"📝 שם שולח: {sender_name}")
            # שמור את השם ב-chatbot
            from chatbot import set_customer_pushname
            set_customer_pushname(sender, sender_name)

        # בדוק סוג ההודעה
        message_type = payload.get("type", "")
        
        print(f"🔍 Debug - message_type: '{message_type}'")
        print(f"🔍 Debug - payload keys: {list(payload.keys())}")
        
        # זיהוי תמונות משופר - בדוק מספר דרכים
        is_image = False
        
        # הדפס את כל המידע לדיבוג
        print(f"🔍 Debug - message_type: '{message_type}'")
        print(f"🔍 Debug - payload keys: {list(payload.keys())}")
        print(f"🔍 Debug - media: {payload.get('media', 'None')}")
        print(f"🔍 Debug - body: {payload.get('body', 'None')}")
        print(f"🔍 Debug - mimetype: {payload.get('mimetype', 'None')}")
        
        # בדיקה ראשונית לפי type
        if message_type == "image":
            is_image = True
            print("🖼️ זוהתה תמונה לפי type='image'")
        
        # בדיקה לפי mimetype
        elif payload.get("mimetype"):
            mimetype = payload.get("mimetype", "").lower()
            if mimetype.startswith("image/"):
                is_image = True
                print(f"🖼️ זוהתה תמונה לפי mimetype: {mimetype}")
        
        # בדיקה לפי media URL
        elif payload.get("media"):
            media_url = payload.get("media", "").lower()
            print(f"🔍 בדוק media URL: {media_url}")
            
            # בדוק לפי מילות מפתח
            if any(img_type in media_url for img_type in ["image", "photo", "picture"]):
                is_image = True
                print("🖼️ זוהתה תמונה לפי מילות מפתח ב-URL")
            
            # בדוק לפי סיומות קובץ
            elif any(media_url.endswith(ext) for ext in [".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".tiff", ".svg"]):
                is_image = True
                print("🖼️ זוהתה תמונה לפי סיומת קובץ")
            
            # בדוק לפי פרמטרים ב-URL
            elif any(param in media_url for param in ["type=image", "format=image", "content=image"]):
                is_image = True
                print("🖼️ זוהתה תמונה לפי פרמטרים ב-URL")
        
        # בדיקה לפי body URL (לפעמים התמונה נשלחת ב-body)
        elif payload.get("body") and payload.get("body").startswith("http"):
            body_url = payload.get("body", "").lower()
            print(f"🔍 בדוק body URL: {body_url}")
            
            # בדוק לפי מילות מפתח
            if any(img_type in body_url for img_type in ["image", "photo", "picture"]):
                is_image = True
                print("🖼️ זוהתה תמונה לפי מילות מפתח ב-body URL")
            
            # בדוק לפי סיומות קובץ
            elif any(body_url.endswith(ext) for ext in [".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".tiff", ".svg"]):
                is_image = True
                print("🖼️ זוהתה תמונה לפי סיומת קובץ ב-body URL")
        
        # בדיקה נוספת - אם יש media URL עם סיומת תמונה
        if not is_image and payload.get("media"):
            media_url = payload.get("media", "").lower()
            if any(media_url.endswith(ext) for ext in [".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".tiff", ".svg"]):
                is_image = True
                print("🖼️ זוהתה תמונה לפי סיומת קובץ נוספת")
        
        # בדיקה אחרונה - אם יש פרמטרים נוספים שמעידים על תמונה
        if not is_image:
            # בדוק אם יש פרמטרים נוספים שמעידים על תמונה
            additional_keys = ["image_url", "photo_url", "picture_url", "img_url"]
            for key in additional_keys:
                if payload.get(key):
                    is_image = True
                    print(f"🖼️ זוהתה תמונה לפי פרמטר נוסף: {key}")
                    break
        
        if is_image:
            print("🖼️ מטפל בתמונה...")
            return handle_image_message(payload, sender)
            
        # בדוק הודעות קוליות
        is_audio = False
        
        # בדוק לפי type
        if message_type in ["ptt", "audio", "voice"]:
            is_audio = True
            print("🎤 זוהתה הודעה קולית לפי type")
        
        # בדוק לפי media URL
        elif payload.get("media") and payload.get("media").strip():
            media_url = payload.get("media", "")
            if any(audio_type in media_url.lower() for audio_type in ["audio", "voice", "ogg", "mp3", "wav", "m4a"]):
                is_audio = True
                print("🎤 זוהתה הודעה קולית לפי media URL")
        
        # בדוק לפי body URL
        elif payload.get("body") and payload.get("body").startswith("http"):
            body_url = payload.get("body", "")
            if any(audio_type in body_url.lower() for audio_type in ["audio", "voice", "ogg", "mp3", "wav", "m4a"]):
                is_audio = True
                print("🎤 זוהתה הודעה קולית לפי body URL")
        
        # בדיקה נוספת - אם יש media URL עם סיומת אודיו
        if not is_audio and payload.get("media"):
            media_url = payload.get("media", "")
            if any(media_url.lower().endswith(ext) for ext in [".ogg", ".mp3", ".wav", ".m4a", ".aac"]):
                is_audio = True
                print("🎤 זוהתה הודעה קולית לפי סיומת קובץ")
        
        # בדיקה נוספת - אם יש טקסט רגיל, זה לא הודעה קולית
        # אל תדרוס זיהוי אודיו שכבר נקבע (למשל לפי type/media)
        if (not is_audio) and payload.get("body") and not payload.get("body").startswith("http"):
            print("📝 זוהתה הודעת טקסט רגילה")
            is_audio = False
        
        if is_audio:
            print("🎤 מטפל בהודעה קולית...")
            return handle_voice_message(payload, sender)
            
        # הודעת טקסט רגילה
        message = payload.get("body", "")
        if not message:
            print("⚠️ הודעה חסרה.")
            # חישוב עיכוב חכם לפני שליחת הודעת שגיאה
            delay = calculate_smart_delay(50, "text")  # הודעת שגיאה בינונית
            print(f"⏱️ ממתין {delay:.2f} שניות לפני שליחת הודעת שגיאה...")
            time.sleep(delay)
            send_whatsapp_message(sender, "לא הצלחתי לקרוא את ההודעה. נסה לשלוח אותה שוב.")
            return "Invalid", 400
                
        print(f"📩 הודעת טקסט מ-{sender}: {message}")
        
        # עדכן זמן הודעה אחרונה
        update_last_message_time(sender)
        
        # בדוק אם זו פקודת מנהל
        admin_reply = handle_admin_commands(message, sender)
        if admin_reply:
            print(f"⚙️ פקודת מנהל זוהתה: {message}")
            # חישוב עיכוב חכם לפני שליחת תשובת מנהל
            delay = calculate_smart_delay(len(admin_reply), "text")
            print(f"⏱️ ממתין {delay:.2f} שניות לפני שליחת תשובת מנהל...")
            time.sleep(delay)
            send_whatsapp_message(sender, admin_reply)
            return "OK", 200
        
        # טיפול מיוחד למנהל - מספר 0523006544
        if sender == "972523006544" or sender == "0523006544":
            print(f"👑 מנהל זוהה: {sender}")
            admin_menu = """👑 שלום מנהל! ברוך הבא לתפריט הניהול

📊 מה תרצה לעשות?

1️⃣ **צפייה בסיכומים** - שלח "סיכומים"
2️⃣ **חיפוש שיחה** - שלח "חפש [שם/מספר]"
3️⃣ **סטטיסטיקות** - שלח "סטטיסטיקות"
4️⃣ **ייצוא נתונים** - שלח "ייצא"
5️⃣ **בדיקת בוט** - שלח "בדוק בוט [מספר]"
6️⃣ **עצירת בוט** - שלח "עצור בוט [מספר]"
7️⃣ **הפעלת בוט** - שלח "הפעל בוט [מספר]"

💡 דוגמאות:
- "חפש יוסי"
- "בדוק בוט 972123456789"
- "עצור בוט 972123456789"

איזה פעולה תרצה לבצע?"""
            send_whatsapp_message(sender, admin_menu)
            return "OK", 200
        
        # בדוק אם הבוט פעיל למשתמש זה
        if not is_bot_active(sender):
            print(f"🤖 בוט לא פעיל עבור {sender}, לא מעבד הודעה")
            return "OK", 200  # לא שולח תשובה, אבל מקבל את ההודעה
        
        # הבוט פעיל - עבד את ההודעה
        print(f"🤖 מעבד הודעה עם GPT...")
        reply = chat_with_gpt(message, user_id=sender)
        print(f"💬 תשובת GPT: {reply}")
        
        # חישוב עיכוב חכם לפי אורך ההודעה
        delay = calculate_smart_delay(len(message), "text")
        print(f"⏱️ ממתין {delay:.2f} שניות לפני שליחת תשובה...")
        time.sleep(delay)
        
        # שלח תשובת טקסט רגילה
        send_whatsapp_message(sender, reply)
        
        return "OK", 200

    except Exception as e:
        print(f"❌ שגיאה בטיפול בהודעה: {e}")
        return "Error", 500

def handle_voice_message(payload, sender):
    """טיפול בהודעה קולית - משודרג עם TTS nova, Cloudinary ו-UltraMsg"""
    try:
        print(f"🎤 מתחיל טיפול בהודעה קולית מ: {sender}")
        print(f"🔍 Debug - payload keys: {list(payload.keys())}")
        print(f"🔍 Debug - media: '{payload.get('media', '')}'")
        print(f"🔍 Debug - body: '{payload.get('body', '')}'")
        print(f"🔍 Debug - type: '{payload.get('type', '')}'")
        
        # קבל URL של קובץ הקול - בדוק מספר מקומות
        audio_url = payload.get("media", "") or payload.get("body", "") or payload.get("url", "")
        if not audio_url or not audio_url.strip():
            print("⚠️ URL של קובץ קול חסר או ריק")
            print(f"🔍 Debug - payload keys: {list(payload.keys())}")
            print(f"🔍 Debug - media: '{payload.get('media', '')}'")
            print(f"🔍 Debug - body: '{payload.get('body', '')}'")
            print(f"🔍 Debug - url: '{payload.get('url', '')}'")
            return "Invalid", 400
        
        print(f"🎤 קובץ קול זוהה: {audio_url}")
        
        # 1. תמלל את ההודעה הקולית באמצעות OpenAI Whisper
        print("🎤 מתחיל תמלול...")
        transcribed_text = transcribe_voice_message(audio_url)
        if not transcribed_text:
            print("❌ תמלול נכשל, שולח הודעת טקסט...")
            # חישוב עיכוב חכם לפני שליחת הודעת שגיאה
            delay = calculate_smart_delay(50, "text")  # הודעת שגיאה בינונית
            print(f"⏱️ ממתין {delay:.2f} שניות לפני שליחת הודעת שגיאה...")
            time.sleep(delay)
            send_whatsapp_message(sender, "לא הצלחתי לתמלל את ההקלטה. נסה לדבר יותר ברור או שלח הודעה בטקסט.")
            return "Error", 500
        
        print(f"✅ תמלול הושלם: {transcribed_text}")
        
        # עדכן זמן הודעה אחרונה
        update_last_message_time(sender)
        
        # 2. בדוק אם הבוט פעיל למשתמש זה
        if not is_bot_active(sender):
            print(f"🤖 בוט לא פעיל עבור {sender}, לא מעבד הודעה קולית")
            send_whatsapp_message(sender, "הבוט לא פעיל כרגע. שלח 'מעכשיו ההתכתבות שלך תמשיך עם הבוט' כדי להפעיל אותו.")
            return "OK", 200
        
        # 3. עבד את הטקסט המתומלל עם GPT
        print("🤖 מעבד עם GPT...")
        reply = chat_with_gpt(transcribed_text, user_id=sender)
        print(f"💬 תשובת GPT: {reply}")
        
        # חישוב עיכוב חכם לפי אורך ההודעה הקולית
        delay = calculate_smart_delay(len(transcribed_text), "audio")
        print(f"⏱️ ממתין {delay:.2f} שניות לפני יצירת תגובה קולית...")
        time.sleep(delay)
        
        # 4. צור תגובה קולית עם OpenAI TTS קול coral (גברי)
        print("🎵 יוצר תגובה קולית עם קול coral (גברי)...")
        audio_bytes = None
        try:
            audio_bytes = create_tts_audio_coral(reply)
        except Exception as e:
            print(f"❌ שגיאה ביצירת אודיו: {e}")
            import traceback
            traceback.print_exc()
        
        if not audio_bytes:
            print("❌ יצירת אודיו נכשלה, שולח טקסט...")
            # חישוב עיכוב חכם לפני שליחת טקסט
            delay = calculate_smart_delay(len(reply), "text")
            print(f"⏱️ ממתין {delay:.2f} שניות לפני שליחת תשובה בטקסט...")
            time.sleep(delay)
            send_whatsapp_message(sender, reply)
            return "OK", 200
        
        # 5. שלח את האודיו דרך UltraMsg עם מספר שיטות
        print("📤 שולח אודיו דרך UltraMsg...")
        print(f"📤 גודל אודיו: {len(audio_bytes)} bytes")
        audio_sent = False
        
        # רשימת הפונקציות לנסות בסדר עדיפות (עם Cloudinary)
        send_functions = [
            ("send_audio_via_ultramsg_official", send_audio_via_ultramsg_official),
            ("send_audio_via_ultramsg_url", send_audio_via_ultramsg_url),
            ("send_audio_via_ultramsg_base64", send_audio_via_ultramsg_base64),
            ("send_audio_via_ultramsg_fixed", send_audio_via_ultramsg_fixed),
            ("send_audio_via_ultramsg_simple", send_audio_via_ultramsg_simple),
            ("send_audio_via_ultramsg_alternative", send_audio_via_ultramsg_alternative),
            ("send_audio_via_ultramsg_documentation", send_audio_via_ultramsg_documentation),
            ("send_audio_via_ultramsg_recorald", send_audio_via_ultramsg_recorald),
            ("send_audio_via_ultramsg_form_data", send_audio_via_ultramsg_form_data),
            ("send_audio_via_ultramsg_json", send_audio_via_ultramsg_json)
        ]
        
        for func_name, func in send_functions:
            try:
                print(f"🔄 מנסה עם {func_name}...")
                audio_sent = func(sender, audio_bytes, caption="תגובה קולית")
                if audio_sent:
                    print(f"✅ אודיו נשלח בהצלחה עם {func_name}!")
                    break
                else:
                    print(f"⚠️ {func_name} נכשל")
            except Exception as e:
                print(f"❌ שגיאה עם {func_name}: {e}")
                continue
        
        if not audio_sent:
            print("⚠️ כל השיטות נכשלו, שולח טקסט...")
            # חישוב עיכוב חכם לפני שליחת טקסט
            delay = calculate_smart_delay(len(reply), "text")
            print(f"⏱️ ממתין {delay:.2f} שניות לפני שליחת תשובה בטקסט...")
            time.sleep(delay)
            send_whatsapp_message(sender, reply)
        else:
            print("🎉 הודעה קולית נשלחה בהצלחה!")
        
        return "OK", 200
        
    except Exception as e:
        print(f"❌ שגיאה בטיפול בהודעה קולית: {e}")
        import traceback
        traceback.print_exc()
        
        # במקום לחזור הודעת שגיאה, נחזור תשובה בטקסט
        try:
            print("🔄 מנסה לחזור תשובה בטקסט במקום אודיו...")
            # חישוב עיכוב חכם לפני שליחת טקסט
            delay = calculate_smart_delay(len(reply) if 'reply' in locals() else 100, "text")
            print(f"⏱️ ממתין {delay:.2f} שניות לפני שליחת תשובה בטקסט...")
            time.sleep(delay)
            
            # נסה לשלוח את התשובה המקורית או הודעת ברירת מחדל
            if 'reply' in locals() and reply:
                send_whatsapp_message(sender, reply)
            else:
                send_whatsapp_message(sender, "אני מתנצל, לא הצלחתי לעבד את ההודעה הקולית. נסה לשלוח אותה שוב או שלח הודעה בטקסט.")
        except Exception as fallback_error:
            print(f"❌ שגיאה גם בשליחת טקסט: {fallback_error}")
        
        return "OK", 200  # נחזור OK במקום Error

def handle_image_message(payload, sender):
    """טיפול בתמונה"""
    try:
        print(f"🔍 Debug - payload keys: {list(payload.keys())}")
        
        # קבל URL של התמונה - צריך לחפש גם ב-media וגם ב-body וגם ב-url
        image_url = payload.get("media", "") or payload.get("body", "") or payload.get("url", "")
        caption = payload.get("caption", "")
        
        print(f"🔍 Debug - image_url: {image_url}")
        print(f"🔍 Debug - caption: {caption}")
        
        if not image_url:
            print("⚠️ URL של תמונה חסר")
            # חישוב עיכוב חכם לפני שליחת הודעת שגיאה
            delay = calculate_smart_delay(50, "text")  # הודעת שגיאה בינונית
            print(f"⏱️ ממתין {delay:.2f} שניות לפני שליחת הודעת שגיאה...")
            time.sleep(delay)
            send_whatsapp_message(sender, "לא הצלחתי לקבל את התמונה. נסה לשלוח אותה שוב.")
            return "Invalid", 400
        
        # הורד את התמונה
        print(f"🔄 מוריד תמונה מ: {image_url}")
        image_data = download_file(image_url)
        if not image_data:
            # חישוב עיכוב חכם לפני שליחת הודעת שגיאה
            delay = calculate_smart_delay(50, "text")  # הודעת שגיאה בינונית
            print(f"⏱️ ממתין {delay:.2f} שניות לפני שליחת הודעת שגיאה...")
            time.sleep(delay)
            send_whatsapp_message(sender, "לא הצלחתי להוריד את התמונה. נסה לשלוח אותה שוב.")
            return "Error", 500
        
        print(f"✅ הורדתי תמונה: {len(image_data)} bytes")
        
        # בדוק שהתמונה לא ריקה או קטנה מדי
        if len(image_data) < 1000:  # פחות מקילובייט
            print("⚠️ התמונה קטנה מדי או ריקה")
            # חישוב עיכוב חכם לפני שליחת הודעת שגיאה
            delay = calculate_smart_delay(60, "text")  # הודעת שגיאה בינונית
            print(f"⏱️ ממתין {delay:.2f} שניות לפני שליחת הודעת שגיאה...")
            time.sleep(delay)
            send_whatsapp_message(sender, "התמונה קטנה מדי או לא תקינה. נסה לשלוח תמונה אחרת.")
            return "Error", 500
        
        # נתח את התמונה
        print("🔍 מנתח תמונה...")
        image_analysis = analyze_image(image_data)
        if not image_analysis or "לא הצלחתי" in image_analysis:
            # חישוב עיכוב חכם לפני שליחת הודעת שגיאה
            delay = calculate_smart_delay(70, "text")  # הודעת שגיאה בינונית
            print(f"⏱️ ממתין {delay:.2f} שניות לפני שליחת הודעת שגיאה...")
            time.sleep(delay)
            send_whatsapp_message(sender, "לא הצלחתי לנתח את התמונה. נסה לשלוח אותה שוב או תאר לי מה אתה רוצה.")
            return "Error", 500
        
        print(f"🖼️ ניתוח תמונה: {image_analysis}")
        
        # הוסף את התמונה למערכת השיחות עם מידע נוסף
        from chatbot import conversations
        if sender not in conversations:
            conversations[sender] = [{"role": "system", "content": "system_prompt"}]
        
        # שמור את התמונה כחלק מהשיחה עם מידע נוסף
        image_message = f"[תמונה] {image_analysis}"
        if caption:
            image_message += f"\nכיתוב: {caption}"
        image_message += f"\n🔗 קישור לתמונה: {image_url}"
        
        conversations[sender].append({"role": "user", "content": image_message})
        
        # הכן הודעה עם ניתוח התמונה
        message_to_process = f"[תמונה] {image_analysis}"
        if caption:
            message_to_process += f"\nכיתוב: {caption}"
        
        print(f"📝 הודעה לעיבוד: {message_to_process}")
        
        # עדכן זמן הודעה אחרונה
        update_last_message_time(sender)
        
        # עבד את ההודעה
        reply = chat_with_gpt(message_to_process, user_id=sender)
        print(f"💬 תשובת GPT: {reply}")
        
        # חישוב עיכוב חכם לפי אורך ההודעה וסוג התמונה
        delay = calculate_smart_delay(len(message_to_process), "image")
        print(f"⏱️ ממתין {delay:.2f} שניות לפני שליחת תשובה לתמונה...")
        time.sleep(delay)
        
        # שלח תשובת טקסט רגילה
        send_whatsapp_message(sender, reply)
        
        return "OK", 200
        
    except Exception as e:
        print(f"❌ שגיאה בטיפול בתמונה: {e}")
        import traceback
        traceback.print_exc()
        # חישוב עיכוב חכם לפני שליחת הודעת שגיאה
        delay = calculate_smart_delay(80, "text")  # הודעת שגיאה ארוכה
        print(f"⏱️ ממתין {delay:.2f} שניות לפני שליחת הודעת שגיאה...")
        time.sleep(delay)
        send_whatsapp_message(sender, "אירעה שגיאה בטיפול בתמונה. נסה לשלוח אותה שוב או תאר לי מה אתה רוצה.")
        return "Error", 500

def send_whatsapp_message(to, message):
    """שלח הודעת טקסט"""
    url = f"https://api.ultramsg.com/{INSTANCE_ID}/messages/chat"
    
    # הוסף את הטוקן כפרמטר GET
    params = {
        'token': TOKEN
    }
    
    payload = {
        "to": to,
        "body": message
    }
    
    response = requests.post(url, data=payload, params=params)
    print("📤 הודעת טקסט נשלחה:", response.text)

def send_whatsapp_audio(to, audio_data):
    """שלח הודעה קולית - ללא קבצים זמניים"""
    try:
        # בדוק שהאודיו לא ריק
        if not audio_data or len(audio_data) < 1000:
            print("⚠️ קובץ אודיו ריק או קטן מדי לשליחה")
            return False
        
        print(f"🎵 שולח הודעה קולית: {len(audio_data)} bytes")
        
        # שלח את האודיו ישירות עם BytesIO
        from io import BytesIO
        audio_file = BytesIO(audio_data)
        audio_file.name = "audio.mp3"
        
        # שלח את קובץ האודיו עם token כפרמטר GET
        url = f"https://api.ultramsg.com/{INSTANCE_ID}/messages/audio"
        
        # הוסף את הטוקן כפרמטר GET
        params = {
            'token': TOKEN
        }
        
        # שלח את האודיו עם MIME type נכון
        files = {
            'audio': ('audio.mp3', audio_file, 'audio/mpeg')
        }
        
        # שלח את הפרמטרים הנדרשים ב-data
        data = {
            'to': to
        }
        
        response = requests.post(url, files=files, data=data, params=params)
        print("🎵 תגובת API:", response.text)
        
        # בדוק אם השליחה הצליחה
        if response.status_code == 200:
            # בדוק שהתגובה לא מכילה שגיאה
            try:
                response_json = response.json()
                if "error" in response_json:
                    print(f"❌ שגיאת API: {response_json['error']}")
                    return False
            except:
                pass
            
            print("✅ הודעה קולית נשלחה בהצלחה")
            return True
        else:
            print(f"⚠️ שגיאה בשליחת הודעה קולית: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ שגיאה בשליחת הודעה קולית: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_voice_system_health():
    """בדוק את בריאות המערכת הקולית"""
    try:
        print("🔍 בודק בריאות המערכת הקולית...")
        
        # בדוק משתני סביבה
        openai_key = os.environ.get("OPENAI_API_KEY")
        instance_id = os.environ.get("ULTRA_INSTANCE_ID")  # תיקנתי את השם
        token = os.environ.get("ULTRA_TOKEN")  # תיקנתי את השם
        
        # בדוק Cloudinary
        cloudinary_cloud_name = os.environ.get("CLOUDINARY_CLOUD_NAME")
        cloudinary_api_key = os.environ.get("CLOUDINARY_API_KEY")
        cloudinary_api_secret = os.environ.get("CLOUDINARY_API_SECRET")
        
        health_status = {
            "openai_api_key": "✅" if openai_key else "❌",
            "ultramsg_instance_id": "✅" if instance_id else "❌", 
            "ultramsg_token": "✅" if token else "❌",
            "cloudinary_cloud_name": "✅" if cloudinary_cloud_name else "❌",
            "cloudinary_api_key": "✅" if cloudinary_api_key else "❌",
            "cloudinary_api_secret": "✅" if cloudinary_api_secret else "❌",
            "openai_client": "✅" if 'client' in globals() else "❌",
            "cloudinary_available": "✅" if CLOUDINARY_AVAILABLE else "❌"
        }
        
        print("📊 סטטוס משתני סביבה:")
        for key, status in health_status.items():
            print(f"   {key}: {status}")
        
        # בדוק חיבור ל-OpenAI
        if openai_key and 'client' in globals():
            try:
                print("🔗 בודק חיבור ל-OpenAI...")
                # בדיקה פשוטה - נסה לקבל רשימת מודלים
                models = client.models.list()
                print("✅ חיבור ל-OpenAI תקין")
                health_status["openai_connection"] = "✅"
            except Exception as e:
                print(f"❌ שגיאה בחיבור ל-OpenAI: {e}")
                health_status["openai_connection"] = "❌"
        else:
            health_status["openai_connection"] = "⚠️ לא נבדק"
        
        # בדוק חיבור ל-UltraMsg
        if instance_id and token:
            try:
                print("🔗 בודק חיבור ל-UltraMsg...")
                test_url = f"https://api.ultramsg.com/{instance_id}/instance/me"
                test_params = {'token': token}
                response = requests.get(test_url, params=test_params, timeout=10)
                if response.status_code == 200:
                    print("✅ חיבור ל-UltraMsg תקין")
                    health_status["ultramsg_connection"] = "✅"
                else:
                    print(f"⚠️ תגובה לא תקינה מ-UltraMsg: {response.status_code}")
                    health_status["ultramsg_connection"] = "⚠️"
            except Exception as e:
                print(f"❌ שגיאה בחיבור ל-UltraMsg: {e}")
                health_status["ultramsg_connection"] = "❌"
        else:
            health_status["ultramsg_connection"] = "⚠️ לא נבדק"
        
        # בדוק חיבור ל-Cloudinary
        if CLOUDINARY_AVAILABLE and cloudinary_cloud_name and cloudinary_api_key and cloudinary_api_secret:
            try:
                print("🔗 בודק חיבור ל-Cloudinary...")
                # בדיקה פשוטה - נסה לקבל מידע על הענן
                cloudinary_info = cloudinary.api.ping()
                if cloudinary_info.get("status") == "ok":
                    print("✅ חיבור ל-Cloudinary תקין")
                    health_status["cloudinary_connection"] = "✅"
                else:
                    print(f"⚠️ תגובה לא תקינה מ-Cloudinary: {cloudinary_info}")
                    health_status["cloudinary_connection"] = "⚠️"
            except Exception as e:
                print(f"❌ שגיאה בחיבור ל-Cloudinary: {e}")
                health_status["cloudinary_connection"] = "❌"
        else:
            health_status["cloudinary_connection"] = "⚠️ לא נבדק"
        
        return health_status
        
    except Exception as e:
        print(f"❌ שגיאה בבדיקת בריאות המערכת: {e}")
        return {"error": str(e)}

def get_voice_system_stats():
    """קבל סטטיסטיקות על המערכת הקולית"""
    try:
        print("📊 אוסף סטטיסטיקות מערכת קולית...")
        
        stats = {
            "timestamp": datetime.now().isoformat(),
            "bot_active_users": len([uid for uid, status in bot_active_status.items() if status]),
            "bot_inactive_users": len([uid for uid, status in bot_active_status.items() if not status]),
            "total_registered_users": len(bot_active_status),
            "system_health": check_voice_system_health()
        }
        
        print("✅ סטטיסטיקות נאספו בהצלחה")
        return stats
        
    except Exception as e:
        print(f"❌ שגיאה באיסוף סטטיסטיקות: {e}")
        return {"error": str(e)}

def send_audio_via_ultramsg_base64(to, audio_bytes, caption=""):
    """שלח אודיו עם פורמט base64 - פתרון חלופי לבעיית הפרמטרים"""
    try:
        print(f"🎵 שולח אודיו עם פורמט base64 ל: {to}")
        
        url = f"https://api.ultramsg.com/{INSTANCE_ID}/messages/audio"
        
        # שלח את הטוקן כפרמטר GET
        params = {
            'token': TOKEN
        }
        
        # המר את האודיו ל-base64
        import base64
        audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')
        
        # שלח את הבקשה עם JSON
        payload = {
            "to": to,
            "audio": audio_base64,
            "caption": caption
        }
        
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json'
        }
        
        print(f"🎵 שולח עם פרמטרים: to={to}, caption={caption}")
        print(f"🎵 גודל אודיו: {len(audio_bytes)} bytes")
        print(f"🎵 גודל base64: {len(audio_base64)} characters")
        print(f"🎵 URL: {url}")
        print(f"🎵 Token: {TOKEN[:5]}*****")
        
        # שלח את הבקשה
        response = requests.post(url, json=payload, params=params, headers=headers)
        print(f"🎵 תגובת UltraMsg API: {response.status_code}")
        print(f"🎵 תוכן תגובה: {response.text}")
        
        # בדוק את התגובה
        if response.status_code == 200:
            try:
                response_json = response.json()
                if "error" in response_json:
                    print(f"❌ שגיאת UltraMsg API: {response_json['error']}")
                    return False
                else:
                    print("✅ אודיו נשלח בהצלחה עם base64!")
                    return True
            except Exception as e:
                print(f"⚠️ לא הצלחתי לפרסר JSON: {e}")
                # אם התגובה היא 200, נניח שהשליחה הצליחה
                print("✅ אודיו נשלח בהצלחה!")
                return True
        else:
            print(f"❌ שגיאה בשליחת אודיו: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ שגיאה בשליחת אודיו: {e}")
        import traceback
        traceback.print_exc()
        return False

def send_audio_via_ultramsg_url(to, audio_url, caption=""):
    """שלח אודיו עם URL של קובץ - פתרון חלופי לבעיית הפרמטרים"""
    try:
        print(f"🎵 שולח אודיו עם URL של קובץ ל: {to}")
        print(f"🎵 URL של האודיו: {audio_url}")
        print(f"🎵 כותרת: {caption}")
        
        url = f"https://api.ultramsg.com/{INSTANCE_ID}/messages/audio"
        
        # שלח את הטוקן כפרמטר GET
        params = {
            'token': TOKEN
        }
        
        # שלח את הבקשה עם URL של קובץ
        payload = {
            "to": to,
            "audio": audio_url,
            "caption": caption
        }
        
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json'
        }
        
        print(f"🎵 שולח עם payload: {payload}")
        print(f"🎵 URL: {url}")
        print(f"🎵 Token: {TOKEN[:5]}*****")
        
        # שלח את הבקשה
        response = requests.post(url, json=payload, params=params, headers=headers)
        print(f"🎵 תגובת UltraMsg API: {response.status_code}")
        print(f"🎵 תוכן תגובה: {response.text}")
        
        # בדוק את התגובה
        if response.status_code == 200:
            try:
                response_json = response.json()
                if "error" in response_json:
                    print(f"❌ שגיאת UltraMsg API: {response_json['error']}")
                    return False
                else:
                    print("✅ אודיו נשלח בהצלחה עם URL של קובץ!")
                    return True
            except Exception as e:
                print(f"⚠️ לא הצלחתי לפרסר JSON: {e}")
                # אם התגובה היא 200, נניח שהשליחה הצליחה
                print("✅ אודיו נשלח בהצלחה!")
                return True
        else:
            print(f"❌ שגיאה בשליחת אודיו: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ שגיאה בשליחת אודיו עם URL: {e}")
        import traceback
        traceback.print_exc()
        return False

def send_audio_via_ultramsg_official(to, audio_bytes, caption=""):
    """שלח אודיו לפי התיעוד הרשמי של UltraMsg API - פורמט מדויק עם Cloudinary"""
    try:
        print(f"🎵 שולח אודיו לפי התיעוד הרשמי ל: {to}")
        print(f"🎵 גודל אודיו: {len(audio_bytes)} bytes")
        print(f"🎵 כותרת: {caption}")
        
        # קודם כל, העלה את האודיו ל-Cloudinary
        if CLOUDINARY_AVAILABLE:
            print("☁️ מעלה אודיו ל-Cloudinary...")
            cloudinary_url = upload_audio_to_cloudinary(audio_bytes, "audio.mp3")
            if cloudinary_url:
                print(f"✅ אודיו הועלה ל-Cloudinary: {cloudinary_url}")
                
                # שלח את ה-URL של Cloudinary ל-ULTRAmsg
                print("📤 שולח URL של Cloudinary ל-ULTRAmsg...")
                return send_audio_via_ultramsg_url(to, cloudinary_url, caption)
            else:
                print("⚠️ העלאה ל-Cloudinary נכשלה, מנסה לשלוח ישירות...")
        else:
            print("⚠️ Cloudinary לא זמין, מנסה לשלוח ישירות...")
        
        # אם Cloudinary לא עובד, נסה לשלוח ישירות
        print("📤 מנסה לשלוח אודיו ישירות ל-ULTRAmsg...")
        url = f"https://api.ultramsg.com/{INSTANCE_ID}/messages/audio"
        
        # שלח את הטוקן כפרמטר GET
        params = {
            'token': TOKEN
        }
        
        # שלח את האודיו עם BytesIO
        from io import BytesIO
        audio_file = BytesIO(audio_bytes)
        audio_file.name = "audio.mp3"
        
        # שלח את הפרמטרים הנדרשים ב-data
        data = {
            'to': to,
            'caption': caption
        }
        
        # שלח את האודיו ב-files עם MIME type נכון
        files = {
            'audio': ('audio.mp3', audio_file, 'audio/mpeg')
        }
        
        print(f"🎵 שולח עם פרמטרים: to={to}, caption={caption}")
        print(f"🎵 גודל אודיו: {len(audio_bytes)} bytes")
        print(f"🎵 URL: {url}")
        print(f"🎵 Token: {TOKEN[:5]}*****")
        
        # שלח את הבקשה עם headers מותאמים בדיוק לתיעוד
        headers = {
            'User-Agent': 'UltraMsg-Client/1.0',
            'Accept': 'application/json',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive'
        }
        
        # שלח את הבקשה
        response = requests.post(url, files=files, data=data, params=params, headers=headers)
        print(f"🎵 תגובת UltraMsg API: {response.status_code}")
        print(f"🎵 תוכן תגובה: {response.text}")
        
        # בדוק את התגובה
        if response.status_code == 200:
            try:
                response_json = response.json()
                if "error" in response_json:
                    print(f"❌ שגיאת UltraMsg API: {response_json['error']}")
                    return False
                else:
                    print("✅ אודיו נשלח בהצלחה לפי התיעוד הרשמי!")
                    return True
            except Exception as e:
                print(f"⚠️ לא הצלחתי לפרסר JSON: {e}")
                # אם התגובה היא 200, נניח שהשליחה הצליחה
                print("✅ אודיו נשלח בהצלחה!")
                return True
        else:
            print(f"❌ שגיאה בשליחת אודיו: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ שגיאה בשליחת אודיו: {e}")
        import traceback
        traceback.print_exc()
        return False

@app.route("/health")
def health_check():
    """בדיקת בריאות המערכת"""
    try:
        health_status = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "ultramsg": {
                "instance_id": INSTANCE_ID[:5] + "*****" if INSTANCE_ID else "❌",
                "token": TOKEN[:5] + "*****" if TOKEN else "❌"
            },
            "openai": {
                "api_key": OPENAI_API_KEY[:10] + "*****" if OPENAI_API_KEY else "❌"
            },
            "cloudinary": {
                "cloud_name": CLOUDINARY_CLOUD_NAME[:5] + "*****" if CLOUDINARY_AVAILABLE and CLOUDINARY_CLOUD_NAME else "❌",
                "api_key": CLOUDINARY_API_KEY[:5] + "*****" if CLOUDINARY_AVAILABLE and CLOUDINARY_API_KEY else "❌",
                "available": CLOUDINARY_AVAILABLE
            }
        }
        
        # בדוק חיבור ל-UltraMsg
        try:
            test_url = f"https://api.ultramsg.com/{INSTANCE_ID}/instance/me"
            params = {'token': TOKEN}
            response = requests.get(test_url, params=params, timeout=10)
            if response.status_code == 200:
                health_status["ultramsg"]["connection"] = "✅"
            else:
                health_status["ultramsg"]["connection"] = f"⚠️ {response.status_code}"
        except Exception as e:
            health_status["ultramsg"]["connection"] = f"❌ {str(e)}"
        
        # בדוק חיבור ל-Cloudinary
        if CLOUDINARY_AVAILABLE:
            try:
                cloudinary_info = cloudinary.api.ping()
                if cloudinary_info.get("status") == "ok":
                    health_status["cloudinary"]["connection"] = "✅"
                else:
                    health_status["cloudinary"]["connection"] = f"⚠️ {cloudinary_info.get('status', 'unknown')}"
            except Exception as e:
                health_status["cloudinary"]["connection"] = f"❌ {str(e)}"
        else:
            health_status["cloudinary"]["connection"] = "⚠️ לא זמין"
        
        return jsonify(health_status), 200
        
    except Exception as e:
        return jsonify({"status": "unhealthy", "error": str(e)}), 500

@app.route("/test_ultramsg")
def test_ultramsg_api():
    """בדוק את ה-API של UltraMsg עם פרמטרים שונים"""
    try:
        test_results = {}
        
        # בדוק את התיעוד של ה-API
        try:
            doc_url = f"https://api.ultramsg.com/{INSTANCE_ID}/instance/me"
            params = {'token': TOKEN}
            response = requests.get(doc_url, params=params, timeout=10)
            test_results["instance_info"] = {
                "status_code": response.status_code,
                "response": response.text[:200] + "..." if len(response.text) > 200 else response.text
            }
        except Exception as e:
            test_results["instance_info"] = {"error": str(e)}
        
        # בדוק את התיעוד של ה-API
        try:
            doc_url = "https://docs.ultramsg.com/api/send/audio"
            response = requests.get(doc_url, timeout=10)
            test_results["documentation"] = {
                "status_code": response.status_code,
                "available": response.status_code == 200
            }
        except Exception as e:
            test_results["documentation"] = {"error": str(e)}
        
        return jsonify(test_results), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def test_ultramsg_audio_format():
    """בדוק את הפורמט הנכון של ה-API של UltraMsg לשליחת אודיו"""
    try:
        print("🔍 בודק את הפורמט הנכון של UltraMsg API...")
        
        # בדוק את התיעוד הרשמי
        try:
            doc_url = "https://docs.ultramsg.com/api/send/audio"
            response = requests.get(doc_url, timeout=10)
            if response.status_code == 200:
                print("✅ תיעוד UltraMsg זמין")
                # חפש מידע על פורמט הבקשה
                content = response.text.lower()
                if "multipart/form-data" in content:
                    print("📋 API מצפה ל-multipart/form-data")
                if "json" in content:
                    print("📋 API תומך ב-JSON")
                if "base64" in content:
                    print("📋 API תומך ב-base64")
            else:
                print(f"⚠️ תיעוד UltraMsg לא זמין: {response.status_code}")
        except Exception as e:
            print(f"❌ לא הצלחתי לגשת לתיעוד: {e}")
        
        # בדוק את ה-instance
        try:
            test_url = f"https://api.ultramsg.com/{INSTANCE_ID}/instance/me"
            params = {'token': TOKEN}
            response = requests.get(test_url, params=params, timeout=10)
            if response.status_code == 200:
                print("✅ חיבור ל-UltraMsg תקין")
                print(f"📊 תגובה: {response.text[:100]}...")
            else:
                print(f"⚠️ חיבור ל-UltraMsg לא תקין: {response.status_code}")
        except Exception as e:
            print(f"❌ שגיאה בחיבור ל-UltraMsg: {e}")
            
    except Exception as e:
        print(f"❌ שגיאה בבדיקת הפורמט: {e}")

def test_ultramsg_api_format():
    """בדוק את הפורמט הנכון של UltraMsg API עם בקשה ריקה"""
    try:
        print("🔍 בודק את הפורמט הנכון של UltraMsg API...")
        
        # בדוק עם בקשה ריקה כדי לראות איזה שגיאה מקבלים
        test_url = f"https://api.ultramsg.com/{INSTANCE_ID}/messages/audio"
        params = {'token': TOKEN}
        
        # נסה עם בקשה ריקה
        response = requests.post(test_url, params=params, timeout=10)
        print(f"📊 תגובה לבקשה ריקה: {response.status_code}")
        print(f"📊 תוכן תגובה: {response.text}")
        
        # נסה עם JSON ריק
        headers = {'Content-Type': 'application/json'}
        response = requests.post(test_url, json={}, params=params, headers=headers, timeout=10)
        print(f"📊 תגובה ל-JSON ריק: {response.status_code}")
        print(f"📊 תוכן תגובה: {response.text}")
        
        # נסה עם multipart/form-data ריק
        response = requests.post(test_url, params=params, timeout=10)
        print(f"📊 תגובה ל-multipart ריק: {response.status_code}")
        print(f"📊 תוכן תגובה: {response.text}")
        
    except Exception as e:
        print(f"❌ שגיאה בבדיקת הפורמט: {e}")

def test_ultramsg_api_parameters():
    """בדוק את הפורמט הנכון של UltraMsg API עם פרמטרים חלקיים"""
    try:
        print("🔍 בודק את הפרמטרים הנדרשים של UltraMsg API...")
        
        # בדוק עם פרמטר 'to' בלבד
        test_url = f"https://api.ultramsg.com/{INSTANCE_ID}/messages/audio"
        params = {'token': TOKEN}
        data = {'to': '972527044505@c.us'}
        
        response = requests.post(test_url, data=data, params=params, timeout=10)
        print(f"📊 תגובה עם 'to' בלבד: {response.status_code}")
        print(f"📊 תוכן תגובה: {response.text}")
        
        # בדוק עם פרמטר 'audio' בלבד (קובץ ריק)
        from io import BytesIO
        empty_audio = BytesIO(b"")
        empty_audio.name = "empty.mp3"
        files = {'audio': ('empty.mp3', empty_audio, 'audio/mpeg')}
        
        response = requests.post(test_url, files=files, params=params, timeout=10)
        print(f"📊 תגובה עם 'audio' בלבד: {response.status_code}")
        print(f"📊 תוכן תגובה: {response.text}")
        
        # בדוק עם שני הפרמטרים
        data = {'to': '972527044505@c.us'}
        response = requests.post(test_url, files=files, data=data, params=params, timeout=10)
        print(f"📊 תגובה עם שני הפרמטרים: {response.status_code}")
        print(f"📊 תוכן תגובה: {response.text}")
        
    except Exception as e:
        print(f"❌ שגיאה בבדיקת הפרמטרים: {e}")

if __name__ == '__main__':
    # בדוק את הפורמט הנכון של UltraMsg API
    test_ultramsg_audio_format()
    test_ultramsg_api_format()
    test_ultramsg_api_parameters()
    
    # הפעל את מערכת הסיכום האוטומטי
    start_auto_summary_thread()
    
    port = int(os.environ.get("PORT", 5000))
    print(f"🚀 מפעיל שרת על פורט {port}")
    app.run(host='0.0.0.0', port=port, debug=True)
