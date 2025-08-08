from flask import Flask, request
from chatbot import chat_with_gpt
import requests
import os
import json
import base64
import tempfile
from io import BytesIO
from dotenv import load_dotenv
from openai import OpenAI

# טען משתני סביבה
load_dotenv()

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

# התחברות ל־OpenAI עבור תמלול ו-TTS
client = OpenAI(api_key=OPENAI_API_KEY)

app = Flask(__name__)

# פונקציות עזר לטיפול בקבצים
def download_file(file_url):
    """הורד קובץ מ-URL"""
    try:
        print(f"🔄 מנסה להוריד: {file_url}")
        
        # בדוק שהקישור תקין
        if not file_url or not file_url.startswith(('http://', 'https://')):
            print(f"❌ קישור לא תקין: {file_url}")
            return None
        
        # הוסף headers כדי לחקות דפדפן
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(file_url, headers=headers, timeout=60, stream=True)
        response.raise_for_status()
        
        # קרא את התוכן
        content = response.content
        print(f"✅ הורד בהצלחה: {len(content)} bytes")
        print(f"📊 Content-Type: {response.headers.get('content-type', 'unknown')}")
        
        return content
        
    except requests.exceptions.Timeout:
        print(f"❌ timeout בהורדת קובץ: {file_url}")
        return None
    except requests.exceptions.RequestException as e:
        print(f"❌ שגיאה בהורדת קובץ: {e}")
        return None
    except Exception as e:
        print(f"❌ שגיאה לא צפויה בהורדת קובץ: {e}")
        return None

def transcribe_audio(audio_data):
    """תמלל קובץ אודיו באמצעות OpenAI Whisper"""
    try:
        # בדוק שהאודיו לא ריק
        if not audio_data or len(audio_data) < 1000:
            print("⚠️ קובץ אודיו ריק או קטן מדי")
            return None
        
        print(f"🎤 מתמלל אודיו: {len(audio_data)} bytes")
        
        # צור קובץ זמני
        with tempfile.NamedTemporaryFile(delete=False, suffix='.ogg') as temp_file:
            temp_file.write(audio_data)
            temp_file.flush()
            
            # תמלל באמצעות OpenAI
            with open(temp_file.name, 'rb') as audio_file:
                transcript = client.audio.transcriptions.create(
                    model="whisper-1", 
                    file=audio_file,
                    language="he"  # עברית
                )
            
            # מחק קובץ זמני
            os.unlink(temp_file.name)
            
            result = transcript.text.strip()
            print(f"✅ תמלול הושלם: {result}")
            return result
            
    except Exception as e:
        print(f"❌ שגיאה בתמלול: {e}")
        import traceback
        traceback.print_exc()
        return None

def text_to_speech(text, language="he"):
    """המר טקסט לדיבור באמצעות OpenAI TTS"""
    try:
        # בדוק שהטקסט לא ריק
        if not text or not text.strip():
            print("⚠️ טקסט ריק ל-TTS")
            return None
        
        # הגבל אורך הטקסט (OpenAI מגביל ל-4096 תווים)
        if len(text) > 4000:
            text = text[:4000] + "..."
            print(f"⚠️ טקסט קוצר ל-TTS: {len(text)} תווים")
        
        print(f"🎵 יוצר קול עבור: {text[:100]}...")
        
        response = client.audio.speech.create(
            model="tts-1",
            voice="nova",  # קול נשי
            input=text,
            speed=1.0
        )
        
        print(f"✅ קול נוצר בהצלחה: {len(response.content)} bytes")
        return response.content
        
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
        
        # זיהוי תמונות - בדוק מספר דרכים
        is_image = False
        
        # הדפס את כל המידע לדיבוג
        print(f"🔍 Debug - message_type: '{message_type}'")
        print(f"🔍 Debug - payload keys: {list(payload.keys())}")
        print(f"🔍 Debug - media: {payload.get('media', 'None')}")
        print(f"🔍 Debug - body: {payload.get('body', 'None')}")
        
        # בדוק לפי type
        if message_type == "image":
            is_image = True
            print("🖼️ זוהתה תמונה לפי type='image'")
        elif message_type in ["photo", "picture", "media"]:
            is_image = True
            print("🖼️ זוהתה תמונה לפי type אחר")
        
        # בדוק לפי media URL
        elif payload.get("media"):
            media_url = payload.get("media", "")
            print(f"🔍 בדוק media URL: {media_url}")
            if any(img_type in media_url.lower() for img_type in ["image", "photo", "picture", "jpg", "jpeg", "png", "gif", "webp", "bmp"]):
                is_image = True
                print("🖼️ זוהתה תמונה לפי media URL")
        
        # בדוק לפי body URL (לפעמים התמונה נשלחת ב-body)
        elif payload.get("body") and payload.get("body").startswith("http"):
            body_url = payload.get("body", "")
            print(f"🔍 בדוק body URL: {body_url}")
            if any(img_type in body_url.lower() for img_type in ["image", "photo", "picture", "jpg", "jpeg", "png", "gif", "webp", "bmp"]):
                is_image = True
                print("🖼️ זוהתה תמונה לפי body URL")
        
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
        elif payload.get("media"):
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
        
        if is_audio:
            print("🎤 מטפל בהודעה קולית...")
            return handle_voice_message(payload, sender)
            
        # הודעת טקסט רגילה
        message = payload.get("body", "")
        if not message:
            print("⚠️ הודעה חסרה.")
            send_whatsapp_message(sender, "לא הצלחתי לקרוא את ההודעה. נסה לשלוח אותה שוב.")
            return "Invalid", 400
                
        print(f"📩 הודעת טקסט מ-{sender}: {message}")
        reply = chat_with_gpt(message, user_id=sender)
        print(f"💬 תשובת GPT: {reply}")
        
        # שלח תשובת טקסט רגילה
        send_whatsapp_message(sender, reply)
        
        return "OK", 200

    except Exception as e:
        print(f"❌ שגיאה בטיפול בהודעה: {e}")
        return "Error", 500

def handle_voice_message(payload, sender):
    """טיפול בהודעה קולית"""
    try:
        # קבל URL של קובץ הקול - בדוק מספר מקומות
        audio_url = payload.get("media", "") or payload.get("body", "") or payload.get("url", "")
        if not audio_url:
            print("⚠️ URL של קובץ קול חסר")
            print(f"🔍 Debug - payload keys: {list(payload.keys())}")
            return "Invalid", 400
        
        # הורד את קובץ הקול
        audio_data = download_file(audio_url)
        if not audio_data:
            send_whatsapp_message(sender, "❌ לא הצלחתי להוריד את ההקלטה. נסה שוב.")
            return "Error", 500
        
        # תמלל את הקול
        transcribed_text = transcribe_audio(audio_data)
        if not transcribed_text:
            send_whatsapp_message(sender, "לא הצלחתי לתמלל את ההקלטה. נסה שוב או שלח הודעה בטקסט.")
            return "Error", 500
        
        print(f"🎤 תמלול: {transcribed_text}")
        
        # בדוק שהתמלול לא ריק
        if not transcribed_text.strip():
            send_whatsapp_message(sender, "לא הצלחתי להבין את ההקלטה. נסה לדבר יותר ברור או שלח הודעה בטקסט.")
            return "Error", 500
        
        # עבד את הטקסט המתומלל
        reply = chat_with_gpt(transcribed_text, user_id=sender)
        print(f"💬 תשובת GPT: {reply}")
        
        # יצירת תשובה קולית
        audio_response = text_to_speech(reply)
        if audio_response:
            print("🎵 שולח תשובה קולית...")
            audio_sent = send_whatsapp_audio(sender, audio_response)
            if not audio_sent:
                # אם שליחת האודיו נכשלה, שלח טקסט
                print("⚠️ שליחת אודיו נכשלה, שולח טקסט...")
                send_whatsapp_message(sender, reply)
        else:
            # אם TTS נכשל, שלח טקסט
            print("⚠️ TTS נכשל, שולח טקסט...")
            send_whatsapp_message(sender, reply)
        
        return "OK", 200
        
    except Exception as e:
        print(f"❌ שגיאה בטיפול בהודעה קולית: {e}")
        return "Error", 500

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
            send_whatsapp_message(sender, "לא הצלחתי לקבל את התמונה. נסה לשלוח אותה שוב.")
            return "Invalid", 400
        
        # הורד את התמונה
        print(f"🔄 מוריד תמונה מ: {image_url}")
        image_data = download_file(image_url)
        if not image_data:
            send_whatsapp_message(sender, "לא הצלחתי להוריד את התמונה. נסה לשלוח אותה שוב.")
            return "Error", 500
        
        print(f"✅ הורדתי תמונה: {len(image_data)} bytes")
        
        # בדוק שהתמונה לא ריקה או קטנה מדי
        if len(image_data) < 1000:  # פחות מקילובייט
            print("⚠️ התמונה קטנה מדי או ריקה")
            send_whatsapp_message(sender, "התמונה קטנה מדי או לא תקינה. נסה לשלוח תמונה אחרת.")
            return "Error", 500
        
        # נתח את התמונה
        print("🔍 מנתח תמונה...")
        image_analysis = analyze_image(image_data)
        if not image_analysis or "לא הצלחתי" in image_analysis:
            send_whatsapp_message(sender, "לא הצלחתי לנתח את התמונה. נסה לשלוח אותה שוב או תאר לי מה אתה רוצה.")
            return "Error", 500
        
        print(f"🖼️ ניתוח תמונה: {image_analysis}")
        
        # הכן הודעה עם ניתוח התמונה
        message_to_process = f"[תמונה] {image_analysis}"
        if caption:
            message_to_process += f"\nכיתוב: {caption}"
        
        print(f"📝 הודעה לעיבוד: {message_to_process}")
        
        # עבד את ההודעה
        reply = chat_with_gpt(message_to_process, user_id=sender)
        print(f"💬 תשובת GPT: {reply}")
        
        # שלח תשובת טקסט רגילה
        send_whatsapp_message(sender, reply)
        
        return "OK", 200
        
    except Exception as e:
        print(f"❌ שגיאה בטיפול בתמונה: {e}")
        import traceback
        traceback.print_exc()
        send_whatsapp_message(sender, "אירעה שגיאה בטיפול בתמונה. נסה לשלוח אותה שוב או תאר לי מה אתה רוצה.")
        return "Error", 500

def send_whatsapp_message(to, message):
    """שלח הודעת טקסט"""
    url = f"https://api.ultramsg.com/{INSTANCE_ID}/messages/chat"
    payload = {
        "token": TOKEN,
        "to": to,
        "body": message
    }
    response = requests.post(url, data=payload)
    print("📤 הודעת טקסט נשלחה:", response.text)

def send_whatsapp_audio(to, audio_data):
    """שלח הודעה קולית"""
    try:
        # בדוק שהאודיו לא ריק
        if not audio_data or len(audio_data) < 1000:
            print("⚠️ קובץ אודיו ריק או קטן מדי לשליחה")
            return False
        
        print(f"🎵 שולח הודעה קולית: {len(audio_data)} bytes")
        
        # צור קובץ זמני לאודיו
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as temp_file:
            temp_file.write(audio_data)
            temp_file.flush()
            
            # שלח את קובץ האודיו
            url = f"https://api.ultramsg.com/{INSTANCE_ID}/messages/audio"
            
            with open(temp_file.name, 'rb') as audio_file:
                files = {'audio': audio_file}
                data = {
                    'token': TOKEN,
                    'to': to
                }
                
                response = requests.post(url, files=files, data=data)
                print("🎵 הודעה קולית נשלחה:", response.text)
                
                # בדוק אם השליחה הצליחה
                if response.status_code == 200:
                    print("✅ הודעה קולית נשלחה בהצלחה")
                    return True
                else:
                    print(f"⚠️ שגיאה בשליחת הודעה קולית: {response.status_code}")
                    return False
            
            # מחק קובץ זמני
            os.unlink(temp_file.name)
            
    except Exception as e:
        print(f"❌ שגיאה בשליחת הודעה קולית: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    print(f"🚀 השרת מתחיל על פורט: {port}")
    print(f"🌍 מצב: {'Production' if os.environ.get('FLASK_ENV') == 'production' else 'Development'}")
    
    # הגדר מצב production
    app.config['ENV'] = 'production'
    app.config['DEBUG'] = False
    
    app.run(host="0.0.0.0", port=port)
