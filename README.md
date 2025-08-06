# 🤖 VALUE+ WhatsApp Bot

## 📋 תיאור
בוט WhatsApp חכם מבוסס על OpenAI GPT עם תמיכה בסיכומי שיחה מתקדמים ב-MongoDB.

## ✨ תכונות עיקריות

### 🤖 בוט חכם
- תגובות טבעיות בעברית
- זיהוי מין המשתמש
- הומור וסלנג ישראלי
- תמיכה בתמונות ואודיו

### 📊 ניהול סיכומים מתקדם
- **MongoDB** - שמירה מהירה וחסכונית
- **JSON** - גיבוי אוטומטי
- חיפוש מתקדם לפי טלפון ושם
- סטטיסטיקות מפורטות

### 🔍 חיפוש וניתוח
- חיפוש לפי מספר טלפון
- חיפוש לפי שם לקוח
- סטטיסטיקות לפי מין
- ייצוא לקובץ טקסט

## 🚀 התקנה מהירה

### 1. התקנת תלויות
```bash
pip install -r requirements.txt
```

### 2. הגדרת משתני סביבה
צור קובץ `.env`:
```env
# OpenAI API
OPENAI_API_KEY=your_openai_api_key_here

# UltraMsg WhatsApp
ULTRA_INSTANCE_ID=your_instance_id_here
ULTRA_TOKEN=your_token_here

# MongoDB (אופציונלי)
MONGODB_URI=mongodb://localhost:27017/
MONGODB_DATABASE=chatbot_db
MONGODB_COLLECTION=conversation_summaries
```

### 3. הפעלת המערכת
```bash
# הפעלת הבוט
python whatsapp_webhook.py

# ניהול סיכומים
python manage_summaries.py

# בדיקת MongoDB
python test_mongodb.py
```

## 📁 מבנה הפרויקט

```
Chat agent/
├── 🤖 whatsapp_webhook.py      # Webhook WhatsApp
├── 🧠 chatbot.py              # לוגיקת הבוט
├── 📊 conversation_summaries.py # ניהול סיכומים
├── 🗄️ mongodb_manager.py      # ניהול MongoDB
├── 🛠️ manage_summaries.py     # ממשק ניהול
├── 🔄 migrate_to_mongodb.py   # מיגרציה
├── 🧪 test_mongodb.py         # בדיקות
├── 📋 requirements.txt        # תלויות
├── 📖 README.md              # תיעוד כללי
├── 📖 README_MONGODB.md      # תיעוד MongoDB
└── 🚫 .gitignore             # קבצים להתעלמות
```

## 🎯 שימוש

### ניהול סיכומים
```bash
python manage_summaries.py
```

**אפשרויות:**
1. הצג את כל הסיכומים
2. חפש לפי מספר טלפון
3. חפש לפי שם לקוח
4. ייצא לקובץ טקסט
5. הצג סטטיסטיקות
6. בדוק חיבור MongoDB

### בדיקת MongoDB
```bash
python test_mongodb.py
```

**בדיקות:**
- חיבור MongoDB
- פעולות סיכום
- פונקציונליות חיפוש
- יצירת סיכום בדיקה

### מיגרציה מ-JSON ל-MongoDB
```bash
python migrate_to_mongodb.py
```

## 🔧 הגדרות מתקדמות

### MongoDB Atlas (Cloud)
```env
MONGODB_URI=mongodb+srv://username:password@cluster.mongodb.net/
MONGODB_DATABASE=chatbot_db
MONGODB_COLLECTION=conversation_summaries
```

### אינדקסים אוטומטיים
המערכת יוצרת אוטומטית אינדקסים על:
- `phone_number` (ייחודי)
- `customer_name`
- `timestamp`

## 📊 סטטיסטיקות

המערכת מספקת:
- כמות לקוחות
- כמות הודעות
- ממוצע הודעות ללקוח
- התפלגות לפי מין
- תאריכי שיחה

## 🚨 פתרון בעיות

### MongoDB לא מתחבר
1. בדוק שהשירות רץ
2. בדוק כתובת החיבור ב-.env
3. הרץ `python test_mongodb.py`

### שגיאות חיבור
```bash
# בדוק חיבור
python manage_summaries.py
# בחר אפשרות 6
```

### גיבוי אוטומטי
המערכת שומרת אוטומטית ב-JSON ו-MongoDB במקביל.

## 🔄 מיגרציה

המערכת תעביר אוטומטית את כל הסיכומים הקיימים ל-MongoDB בעת הפעלה ראשונה.

## 📞 תמיכה

לשאלות ותמיכה:
- בדוק את `README_MONGODB.md` לפרטים על MongoDB
- הרץ `python test_mongodb.py` לבדיקות
- השתמש ב-`python manage_summaries.py` לניהול

## 🎉 יתרונות המערכת

### ✅ MongoDB
- ביצועים מהירים
- חיפוש מתקדם
- אינדקסים אוטומטיים
- גיבוי ענן

### ✅ JSON (גיבוי)
- שמירה מקומית
- תאימות מלאה
- גיבוי אוטומטי

### ✅ חיפוש מתקדם
- חיפוש לפי טלפון
- חיפוש לפי שם
- תוצאות מסודרות

### ✅ ניהול נוח
- ממשק ידידותי
- סטטיסטיקות מפורטות
- ייצוא לקובץ 