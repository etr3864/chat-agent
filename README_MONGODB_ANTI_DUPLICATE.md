# מניעת כפילויות ב-MongoDB - מדריך שימוש

## סקירה כללית

הקוד שודרג כדי למנוע שליחה כפולה של הודעות לוואטסאפ באמצעות MongoDB. המערכת עכשיו:

1. **מוסיפה שדה `notified`** לכל מסמך חדש עם ערך ברירת מחדל `false`
2. **שומרת זמנים ב-UTC ISO 8601** עם `Z` בסוף
3. **לא מוחקת שדות קיימים** בעדכון מסמכים
4. **מספקת פונקציות** לסימון הודעות שנשלחו

## פונקציות חדשות

### 1. `upsert_lead_with_notified(doc)`

יוצר או מעדכן ליד לפי `phone_number`:

```python
from mongodb_manager import mongodb_manager

lead_data = {
    "phone_number": "972501234567",
    "customer_name": "ישראל ישראלי",
    "summary": "לקוח מתעניין במוצר X",
    "timestamp": "2025-08-10T12:00:00.000Z"
}

# יצירה/עדכון עם notified=false אוטומטי
mongodb_manager.upsert_lead_with_notified(lead_data)
```

**תכונות:**
- ✅ לא מוחק שדות קיימים
- ✅ מוסיף `notified: false` במסמך חדש
- ✅ מוסיף `created_at` במסמך חדש
- ✅ מעדכן `updated_at` תמיד
- ✅ שומר זמנים ב-UTC ISO 8601

### 2. `mark_lead_notified(doc_id)`

מסמן ליד שהודעה נשלחה אליו:

```python
# לאחר שליחה מוצלחת ב-n8n
mongodb_manager.mark_lead_notified("507f1f77bcf86cd799439011")
```

**תוצאה:**
```json
{
  "notified": true,
  "notified_at": "2025-08-10T12:34:56.789Z"
}
```

### 3. `get_unnotified_leads()`

מחזיר לידים שעדיין לא נשלחה להם התראה:

```python
unnotified = mongodb_manager.get_unnotified_leads()
for lead in unnotified:
    print(f"ליד: {lead['customer_name']} - {lead['phone_number']}")
```

## שימוש ב-n8n

### שלב 1: בדיקת הודעה נשלחה

**IF Node:**
- **Value 1:** `{{ $json["notified"] }}`
- **Operator:** `is not equal to`
- **Value 2:** `true` (בוליאני, בלי גרשיים)

### שלב 2: שליחת הודעה לוואטסאפ

**HTTP Request Node** - שליחה לוואטסאפ (כבר קיים)

### שלב 3: סימון הודעה נשלחה

**MongoDB Update One Node:**
- **Query:**
  ```json
  { "_id": { "$oid": "{{$json["_id"]["$oid"]}}" } }
  ```
- **Update:**
  ```json
  {
    "$set": {
      "notified": true,
      "notified_at": "{{$now.toISOString()}}"
    }
  }
  ```
- **Upsert:** Off

## מבנה מסמך MongoDB

### מסמך חדש:
```json
{
  "_id": ObjectId("..."),
  "phone_number": "972501234567",
  "customer_name": "ישראל ישראלי",
  "summary": "לקוח מתעניין במוצר X",
  "timestamp": "2025-08-10T12:00:00.000Z",
  "notified": false,
  "created_at": "2025-08-10T12:00:00.000Z",
  "updated_at": "2025-08-10T12:00:00.000Z"
}
```

### לאחר שליחת הודעה:
```json
{
  "_id": ObjectId("..."),
  "phone_number": "972501234567",
  "customer_name": "ישראל ישראלי",
  "summary": "לקוח מתעניין במוצר X",
  "timestamp": "2025-08-10T12:00:00.000Z",
  "notified": true,
  "notified_at": "2025-08-10T12:34:56.789Z",
  "created_at": "2025-08-10T12:00:00.000Z",
  "updated_at": "2025-08-10T12:00:00.000Z"
}
```

## אינדקסים חדשים

המערכת יוצרת אוטומטית אינדקס על שדה `notified` לשיפור ביצועים:

```python
# אינדקס על שדה notified למניעת כפילויות
self.collection.create_index("notified")
```

## דוגמה מלאה

```python
from mongodb_manager import mongodb_manager

def process_new_lead():
    """עיבוד ליד חדש"""
    
    # 1. צור ליד חדש
    lead_data = {
        "phone_number": "972501234567",
        "customer_name": "ישראל ישראלי",
        "summary": "לקוח מתעניין במוצר X",
        "timestamp": "2025-08-10T12:00:00.000Z"
    }
    
    mongodb_manager.upsert_lead_with_notified(lead_data)
    print("✅ ליד נוצר עם notified=false")
    
    # 2. בדוק לידים שלא נשלחה להם התראה
    unnotified = mongodb_manager.get_unnotified_leads()
    print(f"📊 {len(unnotified)} לידים ממתינים לשליחה")
    
    # 3. לאחר שליחה מוצלחת ב-n8n
    if unnotified:
        first_lead = unnotified[0]
        mongodb_manager.mark_lead_notified(first_lead["_id"])
        print(f"✅ ליד {first_lead['_id']} סומן כשהודעה נשלחה")

if __name__ == "__main__":
    process_new_lead()
```

## בדיקת הקוד

הרץ את קובץ הדוגמה:

```bash
python example_usage.py
```

## יתרונות המערכת החדשה

1. **מניעת כפילויות** - הודעות נשלחות רק פעם אחת
2. **שמירת היסטוריה** - כל השדות נשמרים, לא נמחקים
3. **זמנים מדויקים** - UTC ISO 8601 עם Z
4. **ביצועים משופרים** - אינדקסים על שדות חשובים
5. **גמישות** - עובד עם n8n וכל מערכת אחרת

## הערות חשובות

- **אל תסמנו `notified=true`** מתוך הקוד - זה ייעשה אחרי שליחה מוצלחת
- **השתמשו ב-`upsert_lead_with_notified`** במקום `insertOne` ישיר
- **כל הזמנים נשמרים ב-UTC** - אין צורך להמיר
- **המערכת לא מוחקת שדות** - רק מוסיפה/מעדכנת
