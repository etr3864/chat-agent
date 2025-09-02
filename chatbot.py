import os
from openai import OpenAI
from dotenv import load_dotenv
from datetime import datetime

# טען משתני סביבה
load_dotenv()

# התחברות ל־OpenAI עם המפתח - ללא ברירת מחדל כדי לזהות בעיות
try:
    OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
    print("✅ chatbot.py - OPENAI_API_KEY נטען בהצלחה")
    client = OpenAI(api_key=OPENAI_API_KEY)
except KeyError as e:
    print(f"❌ שגיאה ב-chatbot.py: משתנה סביבה חסר: {e}")
    raise

# שיחות לכל משתמש (לפי מזהה = מספר טלפון)
conversations = {}

# מעקב אחרי זמני הודעות אחרונות
last_message_times = {}

# מעקב אחרי מספר שאלות לכל משתמש
question_count = {}

# מעקב אחרי משתמשים שקיבלו הודעת העברה ליועץ
transferred_to_advisor = {}

# מעקב אחרי משתמשים שהגיעו למגבלת ההודעות וקיבלו הודעה על זה
users_at_message_limit = {}

# בקרה על סיכומי שיחה (מניעת כפילויות והגבלה לסיכום נוסף לאחר המשך)
summary_control = {}

# פונקציה לטעינת הפרומפט מקובץ חיצוני
def load_system_prompt():
    """טען את הפרומפט מקובץ חיצוני"""
    try:
        with open("agent_prompt.txt", "r", encoding="utf-8-sig") as f:
            return f.read().strip()
    except FileNotFoundError:
        print("⚠️ קובץ agent_prompt.txt לא נמצא, משתמש בפרומפט ברירת מחדל")
        return """שם הבוט: יוסי
שפה: עברית
סגנון: אנושי, הומוריסטי, סלנג ישראלי, אנושי
אורך תגובה: 1-2 משפטים קצרים כמו בן אדם אמיתי

🎯 מי אני:
אני ליאון, רובוט חכם מ-VALUE+ שעוזר ליצור דפי נחיתה ברמה גבוהה.
אני מלא בהומור, סלנג ישראלי, ואני מזהה אם מולי בן או בת.

🎭 איך להתנהג:
- שאל שאלה אחת בכל הודעה
- טקסטים קצרים כמו בן אדם אמיתי
- הומור וסלנג ישראלי
- אם שואלים אם אני בוט: "מזה משנה? גם ככה אני פה לעזור 😄"
- התאם את הטון לפי מין (בן/בת)

💰 מה אני מוכר:
דף נחיתה ברמה גבוהה 
מחיר: 800 שקל
קישור לאתר: https://valuepluselanding.com/?utm_source=bot&utm_medium=whatsapp&utm_campaign=leon_bot

📋 מה אני צריך להוציא מהלקוח:
1. שם העסק/המוצר
2. מה המטרה של הדף (מכירה/השארת פרטים/תיאום)
3. איך לפנות אליהם
4. יש לוגו/תמונות?
5. איזה סגנון עיצוב הם אוהבים
6. מה מבדל אותם מאחרים
7. איך הלקוח שלהם צריך להרגיש בדף

🟢 פתיחה:
"היי! מה קורה? 😊 זה ליאון מ-VALUE+. רוצה דף נחיתה מקצועי ב-800 שקל? אפשר לשאול אותך כמה שאלות קצרות?"

🎯 כללי ברזל:
- שאלה אחת בכל הודעה
- טקסטים קצרים
- הומור וסלנג ישראלי
- זיהוי מין והתאמת הטון
- אם שואלים אם בוט - הומור
- מטרה: לאסוף מידע ולסגור מכירה"""
    except Exception as e:
        print(f"❌ שגיאה בטעינת הפרומפט: {e}")
        return "שגיאה בטעינת הפרומפט"

# זהות הסוכן - נטען מהקובץ החיצוני
system_prompt = load_system_prompt()

def reload_system_prompt():
    """רענן את הפרומפט מהקובץ החיצוני"""
    global system_prompt
    system_prompt = load_system_prompt()
    print("✅ הפרומפט רוענן מהקובץ החיצוני")
    return system_prompt

def _build_summary_document(user_id: str, summary_text: str) -> dict:
    from datetime import datetime
    try:
        from conversation_summaries import extract_customer_name as _extract_customer_name, detect_customer_gender as _detect_customer_gender
    except Exception:
        # Fallbacks if helpers are not available for any reason
        def _extract_customer_name(*_args, **_kwargs): return ""
        def _detect_customer_gender(*_args, **_kwargs): return "לא ידוע"

    msgs = conversations.get(user_id, [])
    total_user_msgs = len([m for m in msgs if m.get("role") == "user"])
    safe_summary = (summary_text or "").strip()

    # נסה לקרוא לפי החתימות הקיימות בקובץ conversation_summaries.py
    try:
        pushname = customer_pushnames.get(user_id, "")
        customer_name = _extract_customer_name(user_id, conversations, pushname)
    except TypeError:
        customer_name = _extract_customer_name(user_id)

    try:
        gender = _detect_customer_gender(user_id, conversations)
    except TypeError:
        gender = _detect_customer_gender(user_id)

    return {
        "phone_number": user_id,
        "customer_name": customer_name,
        "gender": gender,
        "summary": safe_summary,
        "timestamp": datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.000Z'),
        "total_messages": total_user_msgs,
    }

def ensure_system_prompt_for_user(user_id: str) -> None:
    """ודא שהיסטוריית השיחה למשתמש מתחילה בהודעת system עם ה-agent prompt."""
    if user_id not in conversations or not conversations[user_id]:
        conversations[user_id] = [{"role": "system", "content": system_prompt}]
        return
    first_message = conversations[user_id][0]
    if first_message.get("role") != "system":
        conversations[user_id].insert(0, {"role": "system", "content": system_prompt})

# יצירת תיקייה לשמירת שיחות
def save_conversation_to_file(user_id: str):
    folder = "conversations"
    os.makedirs(folder, exist_ok=True)

    filepath = os.path.join(folder, f"{user_id}.txt")
    with open(filepath, "w", encoding="utf-8-sig") as f:
        for msg in conversations[user_id]:
            role = msg["role"].upper()
            content = msg["content"]
            
            # בדוק אם זו הודעת תמונה
            if "[תמונה]" in content and "🔗 קישור לתמונה:" in content:
                f.write(f"{role}: {content}\n\n")
            else:
                f.write(f"{role}: {content}\n\n")
    
    # שמור גם בפורמט JSON לטעינה קלה יותר
    save_conversation_to_json(user_id)

def save_conversation_to_json(user_id: str):
    """שמור שיחה בפורמט JSON לטעינה קלה יותר"""
    try:
        import json
        folder = "conversations"
        os.makedirs(folder, exist_ok=True)
        
        json_filepath = os.path.join(folder, f"{user_id}.json")
        conversation_data = {
            "user_id": user_id,
            "last_updated": datetime.now().isoformat(),
            "messages": conversations.get(user_id, []),
            "question_count": question_count.get(user_id, 0)
        }
        
        with open(json_filepath, "w", encoding="utf-8-sig") as f:
            json.dump(conversation_data, f, ensure_ascii=False, indent=2)
            
        print(f"💾 שיחה נשמרה ל-JSON: {user_id}")
        
    except Exception as e:
        print(f"⚠️ שגיאה בשמירת שיחה ל-JSON: {e}")

def load_conversation_from_json(user_id: str) -> bool:
    """טען שיחה מקובץ JSON"""
    try:
        import json
        folder = "conversations"
        json_filepath = os.path.join(folder, f"{user_id}.json")
        
        if not os.path.exists(json_filepath):
            return False
            
        with open(json_filepath, "r", encoding="utf-8-sig") as f:
            conversation_data = json.load(f)
        
        # טען את השיחה
        conversations[user_id] = conversation_data.get("messages", [])
        question_count[user_id] = conversation_data.get("question_count", 0)
        
        print(f"📂 שיחה נטענה מ-JSON: {user_id} ({len(conversations[user_id])} הודעות, {question_count[user_id]} שאלות)")
        return True
        
    except Exception as e:
        print(f"⚠️ שגיאה בטעינת שיחה מ-JSON: {e}")
        return False

def should_continue_existing_conversation(user_id: str) -> bool:
    """בדוק אם צריך להמשיך שיחה קיימת"""
    # אם יש שיחה פעילה בזיכרון - המשך אותה
    if user_id in conversations and len(conversations[user_id]) > 1:
        return True
    
    # נסה לטעון שיחה מהקובץ
    if load_conversation_from_json(user_id):
        # בדוק אם השיחה לא ישנה מדי (יותר מ-24 שעות)
        try:
            folder = "conversations"
            json_filepath = os.path.join(folder, f"{user_id}.json")
            
            if os.path.exists(json_filepath):
                # בדוק מתי הקובץ עודכן לאחרונה
                import time
                file_time = os.path.getmtime(json_filepath)
                current_time = time.time()
                hours_since_update = (current_time - file_time) / 3600
                
                # הבוט יזכור שיחות לנצח - ללא הגבלת זמן
                print(f"🔄 ממשיך שיחה קיימת: {user_id} (עודכנה לפני {hours_since_update:.1f} שעות)")
                return True
        except Exception as e:
            print(f"⚠️ שגיאה בבדיקת זמן קובץ: {e}")
    
    return False

# סיכום שיחה קצר
def summarize_conversation(user_id: str) -> str:
    history = conversations.get(user_id, [])
    text = "\n".join([f"{msg['role']}: {msg['content']}" for msg in history])

    response = client.chat.completions.create(
        model="gpt-5-chat-latest",
        messages=[
            {"role": "system", "content": """אתה מומחה לניתוח שיחות מכירה של VALUE+. סכם את השיחה הזו בצורה מפורטת ומקצועית.

📋 מה לסכם (חובה לבדוק את כולם):
1. **שם העסק/המוצר** - מה בדיוק הם עושים?
2. **מטרת הדף** - מה הם רוצים שהלקוחות שלהם יעשו? (מכירה/השארת פרטים/תיאום)
3. **פרטי קשר** - איך לפנות אליהם?
4. **חומרים קיימים** - יש לוגו/תמונות?
5. **סגנון עיצוב** - מודרני, קלאסי, צבעוני?
6. **יתרון תחרותי** - מה מבדל אותם מאחרים?
7. **רגש בדף** - איך הלקוח שלהם צריך להרגיש?
8. **פרופיל לקוחות** - גיל, מגדר, תחומי עניין?

🎯 הנחיות ליועץ:
- איך לגשת ללקוח (פסיכולוגית)
- מה הדגשים החשובים
- איזה סוג לקוח זה (חם/חם-חם/קר)
- מה המחיר שהם צריכים להציע (800 שקל)
- איך להתגבר על התנגדויות

📊 סיכום קצר:
- סטטוס: [חם/חם-חם/קר]
- סיכוי מכירה: [גבוה/בינוני/נמוך]
- זמן צפוי לסגירה: [מיד/שבוע/חודש]
- מחיר מומלץ: [800 שקל]

⚠️ חשוב: אם חסר מידע על אחד מהנושאים, ציין זאת בבירור.
השתמש בעברית ברורה ומקצועית."""},
            {"role": "user", "content": text}
        ]
    )

    return response.choices[0].message.content.strip()

# הפונקציות לחילוץ שם ומין עברו ל-conversation_summaries.py

# משתנה גלובלי לשמירת שמות מ-UltraMsg
customer_pushnames = {}

def set_customer_pushname(user_id: str, pushname: str):
    """שמור שם לקוח מ-UltraMsg"""
    if pushname and pushname.strip():
        customer_pushnames[user_id] = pushname.strip()

# שמירת סיכום שיחה עם פרטי לקוח
def save_conversation_summary(user_id: str, summary: str):
    # בדיקת טקסט החשוד כתשובת בוט ולא סיכום אמיתי
    safe_summary_text = (summary or "").strip()
    suspicious_reply_like = False
    try:
        # רק סינון טקסטים קצרים מדי או ריקים - לא נסנן תוכן לפי מילים
        if len(safe_summary_text) < 50:  # הגדלנו את הסף מ-20 ל-50
            suspicious_reply_like = True
            print(f"[save_conversation_summary] SKIP - summary too short: {len(safe_summary_text)} chars")
        # הסרנו את הסינון לפי מילים ואימוג'ים כדי לאפשר סיכומים אמיתיים
    except Exception:
        pass
    if suspicious_reply_like:
        print("[save_conversation_summary] SKIP suspicious reply-like text")
        return

    summary_data = _build_summary_document(user_id, summary)
    print(f"[save_conversation_summary] saving for {user_id}: {len(summary_data.get('summary',''))} chars")

    # בקרת כפילויות: הגבל סיכום לשיחה לפעם אחת, ועוד פעם אחת בלבד אם הייתה המשכיות מצד הלקוח
    from conversation_summaries import summaries_manager, extract_customer_name, detect_customer_gender

    # ספירת הודעות משתמש עדכנית
    current_user_msg_count = len([m for m in conversations.get(user_id, []) if m.get("role") == "user"])

    # אתחל/טען מצב עבור המשתמש
    state = summary_control.get(user_id)
    if state is None:
        try:
            existing = summaries_manager.get_summary(user_id)
        except Exception:
            existing = None
        if existing:
            existing_count = existing.get("summary_count", 1)
            prev_user_count = existing.get("user_message_count", current_user_msg_count)
            summary_control[user_id] = {"count": existing_count, "user_msg_count_at_last": prev_user_count}
        else:
            summary_control[user_id] = {"count": 0, "user_msg_count_at_last": 0}
        state = summary_control[user_id]

    # כללים: לא יותר מ-2 סיכומים. השני רק אם נוספו הודעות משתמש מאז הסיכום הקודם
    if state.get("count", 0) >= 2:
        print(f"⛔ דילוג על סיכום: כבר נשלחו 2 סיכומים עבור {user_id}")
        return
    if state.get("count", 0) == 1 and current_user_msg_count <= state.get("user_msg_count_at_last", 0):
        print(f"⛔ דילוג על סיכום: אין המשך שיחה מאז הסיכום האחרון עבור {user_id}")
        return

    # שמור בקובץ המקורי
    folder = "conversations"
    os.makedirs(folder, exist_ok=True)

    # חלץ פרטי לקוח (כולל שם מ-UltraMsg)
    pushname = customer_pushnames.get(user_id, "")
    customer_name = extract_customer_name(user_id, conversations, pushname)
    customer_gender = detect_customer_gender(user_id, conversations)

    # קרא את הקובץ הקיים אם יש
    filepath = os.path.join(folder, f"{user_id}.txt")
    existing_content = ""
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8-sig") as f:
                existing_content = f.read()
        except UnicodeDecodeError:
            # אם יש בעיה עם הקידוד, ננסה קידוד אחר
            with open(filepath, "r", encoding="utf-8") as f:
                existing_content = f.read()

    # הוסף סיכום עם פרטי לקוח
    summary_section = f"""
{'='*50}
📋 סיכום שיחה
{'='*50}
📱 מספר טלפון: {user_id}
👤 שם לקוח: {customer_name}
👥 מין: {customer_gender}
📅 תאריך: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
{'='*50}

{summary_data.get('summary','')}

{'='*50}
"""

    # שמור הכל לקובץ
    with open(filepath, "w", encoding="utf-8-sig") as f:
        f.write(existing_content + summary_section)

    # שמור במסד הנתונים (MongoDB) עם מסמך יציב שמכיל תמיד "summary"
    try:
        from mongodb_manager import mongodb_manager
        try:
            mongo_saved = mongodb_manager.save_summary(user_id, summary_data)
        except Exception as e:
            mongo_saved = False
            print(f"⚠️ שמירה ל-MongoDB נכשלה: {e}")
        if mongo_saved:
            print(f"[save_conversation_summary] saved OK for {user_id}")
    except Exception as e:
        print(f"⚠️ טעינת mongodb_manager נכשלה: {e}")

    # שמור במערכת הסיכומים (תעד user_message_count ו-summary_count)
    try:
        # ודא שהמחרוזת שנשמרת במערכות הנלוות היא זו מתוך summary_data
        summaries_manager.add_summary(user_id, summary_data.get('summary',''), conversations, pushname)
        # עדכן מצב בקרת סיכומים
        summary_control[user_id]["count"] = state.get("count", 0) + 1
        summary_control[user_id]["user_msg_count_at_last"] = current_user_msg_count
        print(f"✅ סיכום נשמר עבור {customer_name} ({user_id})")
        # לוג הצלחה עם מספר התווים בסיכום
        try:
            print(f"[save_conversation_summary] saved OK ({len(summary_data.get('summary',''))} chars)")
        except Exception:
            print("[save_conversation_summary] saved OK")
    except Exception as e:
        print(f"⚠️ שגיאה בשמירת סיכום: {e}")
        return

# בדיקה אם לקוח הגיע למגבלה
def is_user_at_limit(user_id: str) -> bool:
    if user_id not in conversations:
        return False
    
    # ספור רק הודעות משתמש וסוכן (לא system)
    user_assistant_messages = [m for m in conversations[user_id] if m["role"] in ["user", "assistant"]]
    return len(user_assistant_messages) >= 100

# בדיקה אם עבר זמן רב מההודעה האחרונה
# פונקציה זו עברה ל-whatsapp_webhook.py
def is_conversation_timed_out(user_id: str) -> bool:
    # פונקציה זו עברה ל-whatsapp_webhook.py
    return False

# עדכון זמן הודעה אחרונה
# פונקציה זו עברה ל-whatsapp_webhook.py
def update_last_message_time(user_id: str):
    # פונקציה זו עברה ל-whatsapp_webhook.py
    pass

# זיהוי סיום שיחה טבעי
def should_end_conversation_naturally(user_message: str, conversation_history: list) -> bool:
    """בדוק אם השיחה צריכה להסתיים באופן טבעי"""
    user_message_lower = user_message.lower().strip()
    
    # מילות סיום מפורשות - רק ביטויים ברורים מאוד
    ending_phrases = [
     " ביי"
    ]
    
    # בדוק אם יש ביטוי סיום מפורש
    for phrase in ending_phrases:
        if phrase in user_message_lower:
            return True
    
    # בדוק אם השיחה ארוכה מאוד (יותר מ-40 הודעות) ויש סימנים של סיום
    if len(conversation_history) > 40:
        # אם המשתמש נותן תשובות קצרות מאוד ברציפות
        short_responses = ["כן", "לא", "אוקיי", "בסדר", "בטח"]
        if user_message_lower in short_responses:
            # בדוק אם היו 4 תשובות קצרות ברציפות (במקום 3)
            recent_user_messages = [
                msg["content"].lower().strip() 
                for msg in conversation_history[-8:] 
                if msg["role"] == "user"
            ]
            if len(recent_user_messages) >= 4 and all(
                msg in short_responses or len(msg) < 5 
                for msg in recent_user_messages[-4:]
            ):
                return True
    
    return False

# בדיקה אם השיחה נעצרה פתאום - מבוטל זמנית
def should_end_conversation_abruptly(user_message: str, conversation_history: list) -> bool:
    """בדוק אם השיחה נעצרה פתאום ויש לבצע סיכום - מבוטל זמנית"""
    # מבוטל זמנית כדי למנוע סגירת שיחות מיותרות
    return False

def has_enough_business_info(conversation_history: list) -> bool:
    """בדוק אם יש מספיק מידע על העסק כדי להתקדם למכירה"""
    # נדרש לפחות 6 הודעות משתמש כדי לאסוף מידע בסיסי
    user_messages = [msg for msg in conversation_history if msg["role"] == "user"]
    if len(user_messages) < 6:
        return False
    
    # בדוק אם השיחה מכילה מידע על העסק
    conversation_text = " ".join([msg["content"].lower() for msg in conversation_history])
    
    # מילות מפתח שמעידות על מידע עסקי
    business_keywords = [
        "עסק", "מוצר", "שירות", "חברה", "חנות", "מטרה", "מכירה", 
        "לקוחות", "לוגו", "תמונות", "עיצוב", "סגנון", "מבדיל", "תחושה"
    ]
    
    # צריך לפחות 3 מילות מפתח שונות
    found_keywords = sum(1 for keyword in business_keywords if keyword in conversation_text)
    
    return found_keywords >= 3

def should_proceed_to_sale(conversation_history: list) -> bool:
    """בדוק אם אפשר להתקדם למכירה"""
    # צריך מספיק מידע על העסק
    if not has_enough_business_info(conversation_history):
        return False
    
    # בדוק אם המשתמש הביע עניין או מוכנות
    recent_messages = conversation_history[-4:]  # 4 ההודעות האחרונות
    user_messages = [msg["content"].lower() for msg in recent_messages if msg["role"] == "user"]
    
    # מילות שמעידות על מוכנות
    readiness_phrases = [
        "אני מעוניין", "אני רוצה", "אני מוכן", "בוא נתקדם", "אוקיי", "בסדר",
        "אני אקנה", "אני אתחיל", "בואו נתחיל", "אני מסכים", "זה נשמע טוב"
    ]
    
    for message in user_messages:
        for phrase in readiness_phrases:
            if phrase in message:
                return True
    
    return False

def get_next_action_message(conversation_history: list) -> str:
    """קבל הודעה מתאימה לשלב הבא בשיחה"""
    
    # בדוק אם יש מספיק מידע על העסק
    if not has_enough_business_info(conversation_history):
        # חסר מידע - המשך לאסוף
        missing_info = get_missing_business_info(conversation_history)
        return f"אני רוצה לוודא שאני מבין בדיוק מה אתה צריך. {missing_info}"
    
    # יש מספיק מידע - בדוק אם אפשר להתקדם למכירה
    if should_proceed_to_sale(conversation_history):
        return "מעולה! יש לי תמונה ברורה של מה שאתה צריך. בואו נסגור את זה?"
    
    # יש מידע אבל הלקוח לא מוכן - המשך לבנות אמון
    return "אני רואה שיש לך עסק מעניין. בואו נדבר קצת יותר על איך הדף הזה יעזור לך להשיג את המטרות שלך."

def get_missing_business_info(conversation_history: list) -> str:
    """קבל הודעה על מה חסר מידע"""
    conversation_text = " ".join([msg["content"].lower() for msg in conversation_history])
    
    missing_items = []
    
    if "עסק" not in conversation_text and "מוצר" not in conversation_text and "שירות" not in conversation_text:
        missing_items.append("מה בדיוק העסק שלך עושה")
    
    if "מטרה" not in conversation_text and "מכירה" not in conversation_text:
        missing_items.append("מה המטרה של הדף - מה אתה רוצה שהלקוחות יעשו")
    
    if "לוגו" not in conversation_text and "תמונות" not in conversation_text:
        missing_items.append("איזה חומרים יש לך כבר - לוגו, תמונות")
    
    if "עיצוב" not in conversation_text and "סגנון" not in conversation_text:
        missing_items.append("איזה סגנון עיצוב אתה אוהב")
    
    if "מבדיל" not in conversation_text and "יתרון" not in conversation_text:
        missing_items.append("מה מבדל אותך מהמתחרים")
    
    if "לקוחות" not in conversation_text and "גיל" not in conversation_text:
        missing_items.append("מי הלקוחות שלך - גיל, מגדר, תחומי עניין")
    
    if len(missing_items) == 0:
        return "מעולה! יש לי את כל המידע שאני צריך על העסק שלך."
    elif len(missing_items) == 1:
        return f"אני צריך להבין {missing_items[0]}."
    elif len(missing_items) == 2:
        return f"אני צריך להבין {missing_items[0]} ו{missing_items[1]}."
    else:
        return f"אני צריך להבין עוד כמה דברים: {', '.join(missing_items[:-1])} ו{missing_items[-1]}."

def count_questions_in_reply(reply: str) -> int:
    """ספור כמה שאלות יש בתגובה של הבוט"""
    question_marks = reply.count('?')
    question_words = ['איך', 'מה', 'איפה', 'מתי', 'למה', 'מי', 'כמה', 'איזה', 'האם']
    
    # ספור שאלות לפי מילות שאלה
    words = reply.split()
    question_word_count = sum(1 for word in words if any(q_word in word for q_word in question_words))
    
    # החזר את המקסימום בין סימני שאלה למילות שאלה
    return max(question_marks, question_word_count)

def should_transfer_to_advisor(user_id: str) -> bool:
    """בדוק אם צריך להעביר ליועץ - מינימום 5 הודעות משתמש + שעה ללא הודעות"""
    # בדוק אם כבר הועבר ליועץ
    if user_id in transferred_to_advisor:
        return False
    
    if user_id not in conversations:
        return False
    
    # ספור הודעות משתמש
    user_messages = [m for m in conversations[user_id] if m["role"] == "user"]
    if len(user_messages) < 5:
        return False
    
    # בדוק אם עבר יותר משעה מההודעה האחרונה
    from whatsapp_webhook import last_message_times
    from datetime import datetime, timedelta
    
    if user_id not in last_message_times:
        return False
    
    time_since_last_message = datetime.now() - last_message_times[user_id]
    if time_since_last_message < timedelta(hours=1):
        return False
    
    return True

# בדיקה ושיכום שיחות ישנות שלא קיבלו סיכום
# פונקציה זו עברה ל-whatsapp_webhook.py כדי לעבוד עם מערכת הטיימר האוטומטי
def check_and_summarize_old_conversations():
    """בדוק שיחות ישנות שלא קיבלו סיכום ובצע סיכום אוטומטי"""
    # פונקציה זו עברה ל-whatsapp_webhook.py
    # היא תופעל אוטומטית כל 30 דקות ושעה
    pass

# פונקציית שיחה
def is_greeting_message(message: str) -> bool:
    """בדוק אם זו הודעת פתיחה עם שלום"""
    message_lower = message.lower().strip()
    greetings = ['היי', 'הי', 'שלום לך', 'שלום לכם', 'שלום עליכם', 'מה נשמע', 'מה קורה']
    # בדוק אם ההודעה מתחילה עם ברכה או מכילה רק ברכה
    for greeting in greetings:
        if message_lower.startswith(greeting) or message_lower == greeting:
            return True
    
    return False



def chat_with_gpt(user_message: str, user_id: str = "default") -> str:
    # בדיקת שיחות ישנות נעשית אוטומטית ב-whatsapp_webhook.py
    # כל 30 דקות ושעה
    # ודא שפרומפט המערכת קיים בראש ההיסטוריה
    ensure_system_prompt_for_user(user_id)
    
    # בדוק אם המשתמש הועבר ליועץ ורוצה להמשיך השיחה
    if user_id in transferred_to_advisor:
        # אפשר למשתמש להמשיך השיחה - הסר את הסימון
        del transferred_to_advisor[user_id]
        
        # הוסף הודעה שמאשרת המשך השיחה
        if user_id not in conversations:
            conversations[user_id] = [{"role": "system", "content": system_prompt}]
        
        conversations[user_id].append({"role": "user", "content": user_message})
        continue_response = "אוקיי, אני כאן להמשיך לעזור לך! מה עוד אתה רוצה לדעת על דף הנחיתה?"
        conversations[user_id].append({"role": "assistant", "content": continue_response})
        save_conversation_to_file(user_id)
        return continue_response
    
    # בדיקה אם לקוח הגיע למגבלה
    if is_user_at_limit(user_id):
        # בדוק אם המשתמש כבר קיבל הודעה על המגבלה
        if user_id in users_at_message_limit:
            # המשתמש כבר קיבל הודעה - לא נחזיר כלום (הבוט לא יענה)
            print(f"🚫 משתמש {user_id} הגיע למגבלה וכבר קיבל הודעה - לא עונה")
            return None  # לא נחזיר תגובה
        else:
            # זו הפעם הראשונה - נשלח הודעה ונסמן שהוא קיבל אותה
            users_at_message_limit[user_id] = datetime.now()
            print(f"🚫 משתמש {user_id} הגיע למגבלה - שולח הודעה יחידה")
            return (
                "🚫 הגעת למגבלת 100 הודעות בשיחה הזו.\n"
                "אני מעביר אותך למענה אנושי שיוכל לעזור לך הלאה.\n"
                "מאפיין אתרים מטעמנו יחייג למספר שלך בקרוב"
            )
    
    # בדוק אם צריך להמשיך שיחה קיימת או להתחיל חדשה
    is_new_conversation = user_id not in conversations
    
    if is_new_conversation:
        # נסה להמשיך שיחה קיימת מהקובץ
        if should_continue_existing_conversation(user_id):
            ensure_system_prompt_for_user(user_id)
            # השיחה נטענה - תן הודעה שמתאימה להמשך השיחה
            if is_greeting_message(user_message):
                # אם הלקוח מתחיל עם שלום אבל יש שיחה קיימת - תן לGPT לטפל בזה
                conversations[user_id].append({"role": "user", "content": user_message})
                
                # שלח ל-GPT לקבלת תגובה מותאמת אישית במקום טמפלייט קבוע
                response = client.chat.completions.create(
                    model="gpt-5-chat-latest",
                    messages=conversations[user_id]
                )
                
                personalized_response = response.choices[0].message.content
                conversations[user_id].append({"role": "assistant", "content": personalized_response})
                save_conversation_to_file(user_id)
                return personalized_response
        else:
            # התחל שיחה חדשה
            conversations[user_id] = [{"role": "system", "content": system_prompt}]
            
            # בשיחה חדשה, תמיד שלח את ההודעה הראשונה ל-GPT לתגובה מותאמת
            conversations[user_id].append({"role": "user", "content": user_message})
            
            # שלח ל-GPT לקבלת תגובה מותאמת אישית להודעה הראשונה
            response = client.chat.completions.create(
                model="gpt-5-chat-latest",
                messages=conversations[user_id]
            )
            
            personalized_response = response.choices[0].message.content
            conversations[user_id].append({"role": "assistant", "content": personalized_response})
            save_conversation_to_file(user_id)
            return personalized_response

    # הוסף הודעת משתמש
    ensure_system_prompt_for_user(user_id)
    conversations[user_id].append({"role": "user", "content": user_message})
    
    # עדכון זמן הודעה אחרונה נעשה ב-whatsapp_webhook.py
    
    # בדוק אם השיחה צריכה להסתיים באופן טבעי
    if should_end_conversation_naturally(user_message, conversations[user_id]):
        # בדוק אם יש מספיק מידע על העסק
        if has_enough_business_info(conversations[user_id]):
            summary = summarize_conversation(user_id)
            save_conversation_summary(user_id, summary)
            save_conversation_to_file(user_id)
            
            # הודעת סיום מקצועית רק כשיש מספיק מידע
            return (
                "אני אכין עבורך שאלון אפיון ואפתח בקשה למתכנת ולמעצב שלנו ואחזור אליך בקרוב.\n\n"
                "תודה על הזמן! אם יש שאלות או שינויים, פשוט תכתוב לי"
            )
        else:
            # אם אין מספיק מידע, אל תסיים את השיחה - תן הודעה מתאימה
            return get_next_action_message(conversations[user_id])
    
    # בדוק אם השיחה נעצרה פתאום
    if should_end_conversation_abruptly(user_message, conversations[user_id]):
        summary = summarize_conversation(user_id)
        save_conversation_summary(user_id, summary)
        save_conversation_to_file(user_id)
        
        # הודעת סיום מקצועית
        return (
            "אני אכין לך שאלון אפיון ואפתח בשבילך פנייה לאחד המתכנתים שלנו ואחזור אליך בקרוב.\n\n"
            "תודה על הזמן! אם יש שאלות או שינויים, פשוט תכתוב לי"
        )

    # בדיקה אם עברנו את מגבלת ההודעות
    total_messages = len([m for m in conversations[user_id] if m["role"] in ["user", "assistant"]])
    if total_messages >= 100:
        summary = summarize_conversation(user_id)
        save_conversation_summary(user_id, summary)
        save_conversation_to_file(user_id)
        return (
            "🚫 הגענו למגבלת 100 הודעות בשיחה הזו.\n"
            "אני מעביר אותך למענה אנושי שיוכל לעזור לך הלאה.\n"
            "מאפיין אתרים מטעמנו יחייג למספר שלך בקרוב"
        )

    # בדוק אם צריך להעביר ליועץ
    if should_transfer_to_advisor(user_id):
        # סמן שהמשתמש הועבר ליועץ
        transferred_to_advisor[user_id] = datetime.now()
        
        # צור סיכום שיחה לפני ההעברה
        summary = summarize_conversation(user_id)
        save_conversation_summary(user_id, summary)
        save_conversation_to_file(user_id)
        
        return (
            "אספתי מספיק מידע כדי להתחיל לעבוד על הדף שלך.\n\n"
            "אני מעביר אותך עכשיו ליועץ מטעמנו שיכין לך הצעה מותאמת אישית ויסביר לך בדיוק איך הדף יעבוד עבור העסק שלך.\n\n"
            "היועץ שלנו יחזור אליך תוך מספר שעות. תודה על הסבלנות!"
        )

    # שלח ל־GPT
    response = client.chat.completions.create(
        model="gpt-5-chat-latest",
        messages=conversations[user_id]
    )

    reply = response.choices[0].message.content

    # ספור שאלות בתגובה של הבוט ועדכן מונה
    questions_in_reply = count_questions_in_reply(reply)
    if questions_in_reply > 0:
        if user_id not in question_count:
            question_count[user_id] = 0
        question_count[user_id] += questions_in_reply
        print(f"🔢 ספרתי {questions_in_reply} שאלות עבור {user_id}. סה\"כ: {question_count[user_id]}")

    # הוסף תגובת הסוכן להיסטוריה
    conversations[user_id].append({"role": "assistant", "content": reply})

    # שמור את השיחה לקובץ
    save_conversation_to_file(user_id)

    return reply
