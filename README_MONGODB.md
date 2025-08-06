# 🚀 מערכת סיכומי שיחה עם MongoDB

## 📋 תיאור
מערכת מתקדמת לניהול סיכומי שיחה עם תמיכה ב-MongoDB ו-JSON כגיבוי.

## 🛠️ התקנה

### 1. התקנת תלויות
```bash
pip install -r requirements.txt
```

### 2. הגדרת משתני סביבה
צור קובץ `.env` בתיקיית הפרויקט עם התוכן הבא:

```env
# OpenAI API Key
OPENAI_API_KEY=your_openai_api_key_here

# UltraMsg WhatsApp API
ULTRA_INSTANCE_ID=your_instance_id_here
ULTRA_TOKEN=your_token_here

# MongoDB Configuration (Optional)
# אם לא מוגדר, המערכת תשתמש בקבצי JSON
MONGODB_URI=mongodb://localhost:27017/
MONGODB_DATABASE=chatbot_db
MONGODB_COLLECTION=conversation_summaries

# MongoDB Atlas (Cloud) Example:
# MONGODB_URI=mongodb+srv://username:password@cluster.mongodb.net/
# MONGODB_DATABASE=chatbot_db
# MONGODB_COLLECTION=conversation_summaries
```

### 3. התקנת MongoDB (אופציונלי)

#### MongoDB מקומי:
```bash
# Windows
# הורד והתקן מ: https://www.mongodb.com/try/download/community

# Linux (Ubuntu)
sudo apt update
sudo apt install mongodb

# macOS
brew install mongodb-community
```

#### MongoDB Atlas (Cloud):
1. היכנס ל-[MongoDB Atlas](https://cloud.mongodb.com/)
2. צור חשבון חינמי
3. צור Cluster חדש
4. קבל את כתובת החיבור
5. הוסף את הכתובת ל-.env

## 🎯 שימוש

### ניהול סיכומים
```bash
python manage_summaries.py
```

### הפעלת הבוט
```bash
python whatsapp_webhook.py
```

## 📊 תכונות

### ✅ MongoDB
- שמירה מהירה וחסכונית
- חיפוש מתקדם
- אינדקסים לביצועים מיטביים
- גיבוי אוטומטי

### ✅ JSON (גיבוי)
- שמירה מקומית
- תאימות מלאה
- גיבוי אוטומטי

### ✅ חיפוש מתקדם
- חיפוש לפי מספר טלפון
- חיפוש לפי שם לקוח
- תוצאות מסודרות

### ✅ סטטיסטיקות
- כמות לקוחות
- כמות הודעות
- התפלגות לפי מין
- ממוצע הודעות ללקוח

## 🔧 הגדרות מתקדמות

### אינדקסים ב-MongoDB
המערכת יוצרת אוטומטית אינדקסים על:
- `phone_number` (ייחודי)
- `customer_name`
- `timestamp`

### גיבוי אוטומטי
המערכת שומרת אוטומטית ב-JSON ו-MongoDB במקביל.

## 🚨 פתרון בעיות

### MongoDB לא מתחבר
1. בדוק שהשירות רץ: `sudo systemctl status mongodb`
2. בדוק כתובת החיבור ב-.env
3. בדוק הרשאות גישה

### שגיאות חיבור
```bash
# בדוק חיבור MongoDB
python manage_summaries.py
# בחר אפשרות 6 - בדוק חיבור MongoDB
```

## 📁 מבנה קבצים
```
Chat agent/
├── mongodb_manager.py      # ניהול MongoDB
├── conversation_summaries.py # ניהול סיכומים
├── manage_summaries.py     # ממשק ניהול
├── chatbot.py             # לוגיקת הבוט
├── whatsapp_webhook.py    # Webhook WhatsApp
├── requirements.txt       # תלויות
└── .env                   # משתני סביבה
```

## 🔄 מיגרציה מ-JSON ל-MongoDB
המערכת תעביר אוטומטית את כל הסיכומים הקיימים ל-MongoDB בעת הפעלה ראשונה.

## 📞 תמיכה
לשאלות ותמיכה, פנה למפתח המערכת. 