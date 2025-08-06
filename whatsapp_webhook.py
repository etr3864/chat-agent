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

INSTANCE_ID = os.getenv("ULTRA_INSTANCE_ID", "instance137396")
TOKEN = os.getenv("ULTRA_TOKEN", "co579fjbu34budjt")

# התחברות ל־OpenAI עבור תמלול ו-TTS
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

app = Flask(__name__)

# פונקציות עזר לטיפול בקבצים
def download_file(file_url):
    """הורד קובץ מ-URL"""
    try:
        print(f"🔄 מנסה להוריד: {file_url}")
        response = requests.get(file_url, timeout=30)
        response.raise_for_status()
        print(f"✅ הורד בהצלחה: {len(response.content)} bytes")
        return response.content
    except Exception as e:
        print(f"❌ שגיאה בהורדת קובץ: {e}")
        return None

def transcribe_audio(audio_data):
    """תמלל קובץ אודיו באמצעות OpenAI Whisper"""
    try:
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
            
            return transcript.text
            
    except Exception as e:
        print(f"❌ שגיאה בתמלול: {e}")
        return None

def text_to_speech(text, language="he"):
    """המר טקסט לדיבור באמצעות OpenAI TTS"""
    try:
        response = client.audio.speech.create(
            model="tts-1",
            voice="nova",  # קול נשי
            input=text,
            speed=1.0
        )
        
        return response.content
        
    except Exception as e:
        print(f"❌ שגיאה ב-TTS: {e}")
        return None

def analyze_image(image_data):
    """נתח תמונה באמצעות OpenAI Vision"""
    try:
        print(f"🔍 מנתח תמונה: {len(image_data)} bytes")
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
                            "text": "תאר מה אתה רואה בתמונה הזו בעברית. אם זה קשור לעסק או למוצר, תן פרטים רלוונטיים ליצירת דף נחיתה."
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
            max_tokens=500
        )
        
        result = response.choices[0].message.content
        print(f"✅ קיבלתי תשובה מ-OpenAI: {len(result)} characters")
        return result
        
    except Exception as e:
        print(f"❌ שגיאה בניתוח תמונה: {e}")
        return None

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
        print(f"🔍 Debug - payload: {payload}")
        
        # if message_type == "ptt":  # הודעה קולית - מבוטל זמנית
        #     print("🎤 התקבלה הודעה קולית")
        #     return handle_voice_message(payload, sender)
            
        if message_type == "image":  # תמונה
            print("🖼️ התקבלה תמונה")
            return handle_image_message(payload, sender)
            
        # בדוק אם יש media URL - לפעמים תמונות מגיעות עם type אחר
        elif payload.get("media") and ("image" in payload.get("media", "").lower() or message_type in ["photo", "picture"]):
            print("🖼️ זוהתה תמונה לפי media URL")
            return handle_image_message(payload, sender)
            
        else:  # הודעת טקסט רגילה
            message = payload.get("body", "")
            if not message:
                print("⚠️ הודעה חסרה.")
                return "Invalid", 400
                
            print(f"📩 הודעת טקסט מ-{sender}: {message}")
            reply = chat_with_gpt(message, user_id=sender)
            print(f"💬 תשובת GPT: {reply}")
            
            # שלח תשובת טקסט רגילה (TTS מבוטל זמנית)
            send_whatsapp_message(sender, reply)
            
            return "OK", 200

    except Exception as e:
        print(f"❌ שגיאה בטיפול בהודעה: {e}")
        return "Error", 500

def handle_voice_message(payload, sender):
    """טיפול בהודעה קולית"""
    try:
        # קבל URL של קובץ הקול
        audio_url = payload.get("body", "")
        if not audio_url:
            print("⚠️ URL של קובץ קול חסר")
            return "Invalid", 400
        
        # הורד את קובץ הקול
        audio_data = download_file(audio_url)
        if not audio_data:
            send_whatsapp_message(sender, "❌ לא הצלחתי להוריד את ההקלטה. נסה שוב.")
            return "Error", 500
        
        # תמלל את הקול
        transcribed_text = transcribe_audio(audio_data)
        if not transcribed_text:
            send_whatsapp_message(sender, "❌ לא הצלחתי לתמלל את ההקלטה. נסה שוב.")
            return "Error", 500
        
        print(f"🎤 תמלול: {transcribed_text}")
        
        # עבד את הטקסט המתומלל
        reply = chat_with_gpt(transcribed_text, user_id=sender)
        print(f"💬 תשובת GPT: {reply}")
        
        # יצירת תשובה קולית
        audio_response = text_to_speech(reply)
        if audio_response:
            send_whatsapp_audio(sender, audio_response)
        else:
            # אם TTS נכשל, שלח טקסט
            send_whatsapp_message(sender, reply)
        
        return "OK", 200
        
    except Exception as e:
        print(f"❌ שגיאה בטיפול בהודעה קולית: {e}")
        return "Error", 500

def handle_image_message(payload, sender):
    """טיפול בתמונה"""
    try:
        # קבל URL של התמונה - צריך לחפש גם ב-media וגם ב-body
        image_url = payload.get("media", "") or payload.get("body", "")
        caption = payload.get("caption", "")
        
        print(f"🔍 Debug - payload keys: {list(payload.keys())}")
        print(f"🔍 Debug - image_url: {image_url}")
        print(f"🔍 Debug - caption: {caption}")
        
        if not image_url:
            print("⚠️ URL של תמונה חסר")
            return "Invalid", 400
        
        # הורד את התמונה
        image_data = download_file(image_url)
        if not image_data:
            send_whatsapp_message(sender, "❌ לא הצלחתי להוריד את התמונה. נסה שוב.")
            return "Error", 500
        
        # נתח את התמונה
        image_analysis = analyze_image(image_data)
        if not image_analysis:
            send_whatsapp_message(sender, "❌ לא הצלחתי לנתח את התמונה. נסה שוב.")
            return "Error", 500
        
        print(f"🖼️ ניתוח תמונה: {image_analysis}")
        
        # הכן הודעה עם ניתוח התמונה
        message_to_process = f"[תמונה] {image_analysis}"
        if caption:
            message_to_process += f"\nכיתוב: {caption}"
        
        # עבד את ההודעה
        reply = chat_with_gpt(message_to_process, user_id=sender)
        print(f"💬 תשובת GPT: {reply}")
        
        # שלח תשובת טקסט רגילה (TTS מבוטל זמנית)
        send_whatsapp_message(sender, reply)
        
        return "OK", 200
        
    except Exception as e:
        print(f"❌ שגיאה בטיפול בתמונה: {e}")
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
            
            # מחק קובץ זמני
            os.unlink(temp_file.name)
            
    except Exception as e:
        print(f"❌ שגיאה בשליחת הודעה קולית: {e}")
        # אם נכשל, נסה לשלוח כטקסט
        send_whatsapp_message(to, "❌ לא הצלחתי לשלוח תשובה קולית. אענה בטקסט.")

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
