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

# יצירת תיקייה לשמירת שיחות
def save_conversation_to_file(user_id: str):
    folder = "conversations"
    os.makedirs(folder, exist_ok=True)

    filepath = os.path.join(folder, f"{user_id}.txt")
    with open(filepath, "w", encoding="utf-8-sig") as f:
        for msg in conversations[user_id]:
            role = msg["role"].upper()
            content = msg["content"]
            f.write(f"{role}: {content}\n\n")

# סיכום שיחה קצר
def summarize_conversation(user_id: str) -> str:
    history = conversations.get(user_id, [])
    text = "\n".join([f"{msg['role']}: {msg['content']}" for msg in history])

    response = client.chat.completions.create(
        model="gpt-4o",
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
    # שמור בקובץ המקורי
    folder = "conversations"
    os.makedirs(folder, exist_ok=True)
    
    # ייבא הפונקציות מהמודול הנכון
    from conversation_summaries import extract_customer_name, detect_customer_gender
    
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

{summary}

{'='*50}
"""
    
    # שמור הכל לקובץ
    with open(filepath, "w", encoding="utf-8-sig") as f:
        f.write(existing_content + summary_section)
    
    # שמור במערכת הסיכומים החדשה
    try:
        from conversation_summaries import summaries_manager
        summaries_manager.add_summary(user_id, summary, conversations, pushname)
        print(f"✅ סיכום נשמר ב-JSON עבור {customer_name} ({user_id})")
    except Exception as e:
        print(f"⚠️ שגיאה בשמירת סיכום ל-JSON: {e}")
        pass  # אם המערכת לא זמינה, נמשיך בלי

# בדיקה אם לקוח הגיע למגבלה
def is_user_at_limit(user_id: str) -> bool:
    if user_id not in conversations:
        return False
    
    # ספור רק הודעות משתמש וסוכן (לא system)
    user_assistant_messages = [m for m in conversations[user_id] if m["role"] in ["user", "assistant"]]
    return len(user_assistant_messages) >= 50

# בדיקה אם עבר זמן רב מההודעה האחרונה
def is_conversation_timed_out(user_id: str) -> bool:
    if user_id not in last_message_times:
        return False
    
    time_diff = datetime.now() - last_message_times[user_id]
    return time_diff.total_seconds() > 3600  # שעה = 3600 שניות

# עדכון זמן הודעה אחרונה
def update_last_message_time(user_id: str):
    last_message_times[user_id] = datetime.now()

# זיהוי סיום שיחה טבעי
def should_end_conversation_naturally(user_message: str, conversation_history: list) -> bool:
    """בדוק אם השיחה צריכה להסתיים באופן טבעי"""
    user_message_lower = user_message.lower().strip()
    
    # מילות סיום מפורשות - רק ביטויים ברורים מאוד
    ending_phrases = [
        "תודה רבה", "תודה רבה רבה", "שבוע טוב", "חג שמח", "בהצלחה",
        "נדבר", "נהיה בקשר", "אני אחזור אליך", "אני אחשוב על זה",
        "לילה טוב", "יום טוב", "שלום", "ביי", "להתראות",
        "סיימתי", "זהו", "זה הכל", "זהו זה", "זהו זהו"
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
    
    if len(missing_items) == 1:
        return f"אני צריך להבין {missing_items[0]}."
    elif len(missing_items) == 2:
        return f"אני צריך להבין {missing_items[0]} ו{missing_items[1]}."
    else:
        return f"אני צריך להבין עוד כמה דברים: {', '.join(missing_items[:-1])} ו{missing_items[-1]}."

# בדיקה ושיכום שיחות ישנות שלא קיבלו סיכום
def check_and_summarize_old_conversations():
    """בדוק שיחות ישנות שלא קיבלו סיכום ובצע סיכום אוטומטי"""
    current_time = datetime.now()
    
    for user_id, conversation in conversations.items():
        # בדוק אם יש שיחה עם יותר מ-10 הודעות
        user_assistant_messages = [m for m in conversation if m["role"] in ["user", "assistant"]]
        if len(user_assistant_messages) >= 10:
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
                    except Exception as e:
                        print(f"⚠️ שגיאה בסיכום אוטומטי: {e}")
                        pass

# פונקציית שיחה
def chat_with_gpt(user_message: str, user_id: str = "default") -> str:
    # בדוק שיחות ישנות שלא קיבלו סיכום
    check_and_summarize_old_conversations()
    
    # בדיקה אם לקוח הגיע למגבלה
    if is_user_at_limit(user_id):
        return (
            "🚫 הגעת למגבלת 50 הודעות בשיחה הזו.\n"
            "לא תוכל לשלוח הודעות נוספות.\n"
            "מאפיין אתרים מטעמנו יחייג למספר שלך בקרוב"
        )
    
    # בדיקה אם עבר זמן רב מההודעה האחרונה
    if is_conversation_timed_out(user_id):
        summary = summarize_conversation(user_id)
        save_conversation_summary(user_id, summary)
        save_conversation_to_file(user_id)
        return (
            "⏰ עבר זמן רב מההודעה האחרונה שלך.\n"
            "סיכמתי את השיחה שלנו.\n"
            "מאפיין אתרים מטעמנו יחייג למספר שלך בקרוב"
        )
    
    # אם אין שיחה קיימת – צור חדשה
    if user_id not in conversations:
        conversations[user_id] = [{"role": "system", "content": system_prompt}]

    # הוסף הודעת משתמש
    conversations[user_id].append({"role": "user", "content": user_message})
    
    # עדכן זמן הודעה אחרונה
    update_last_message_time(user_id)
    
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
    if total_messages >= 50:
        summary = summarize_conversation(user_id)
        save_conversation_summary(user_id, summary)
        save_conversation_to_file(user_id)
        return (
            "🚫 הגענו למגבלת 50 הודעות בשיחה הזו.\n"
            "לא תוכל לשלוח הודעות נוספות.\n"
            "מאפיין אתרים מטעמנו יחייג למספר שלך בקרוב"
        )

    # שלח ל־GPT
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=conversations[user_id]
    )

    reply = response.choices[0].message.content

    # הוסף תגובת הסוכן להיסטוריה
    conversations[user_id].append({"role": "assistant", "content": reply})

    # שמור את השיחה לקובץ
    save_conversation_to_file(user_id)

    return reply
