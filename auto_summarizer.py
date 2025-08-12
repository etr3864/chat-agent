import os
import time
import threading
from datetime import datetime, timedelta
from chatbot import conversations, last_message_times, summarize_conversation, save_conversation_summary, save_conversation_to_file

class AutoSummarizer:
    """מערכת לסיכום אוטומטי של שיחות ישנות"""
    
    def __init__(self, check_interval=300):  # בדיקה כל 5 דקות
        self.check_interval = check_interval
        self.running = False
        self.thread = None
        self.summarized_conversations = set()  # מעקב אחרי שיחות שכבר סוכמו
        
    def start(self):
        """התחל את המערכת האוטומטית"""
        if self.running:
            print("⚠️ מערכת הסיכום האוטומטי כבר רצה")
            return
            
        self.running = True
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()
        print("✅ מערכת הסיכום האוטומטי הופעלה")
        
    def stop(self):
        """עצור את המערכת האוטומטית"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        print("🛑 מערכת הסיכום האוטומטי הופסקה")
        
    def _run_loop(self):
        """לולאה ראשית לבדיקת שיחות ישנות"""
        while self.running:
            try:
                self._check_old_conversations()
                time.sleep(self.check_interval)
            except Exception as e:
                print(f"❌ שגיאה בלולאת הסיכום האוטומטי: {e}")
                time.sleep(60)  # המתן דקה במקרה של שגיאה
                
    def _check_old_conversations(self):
        """בדוק שיחות ישנות שלא קיבלו סיכום"""
        current_time = datetime.now()
        print(f"🔍 בודק שיחות ישנות... ({len(conversations)} שיחות פעילות)")
        
        for user_id, conversation in conversations.items():
            try:
                # דלג אם כבר סוכמה
                if user_id in self.summarized_conversations:
                    continue
                    
                # בדוק אם יש שיחה עם יותר מ-5 הודעות (לפחות שיחה משמעותית)
                user_assistant_messages = [
                    m for m in conversation 
                    if m["role"] in ["user", "assistant"]
                ]
                
                if len(user_assistant_messages) < 5:
                    continue
                    
                # בדוק אם עבר זמן רב מההודעה האחרונה (שעה)
                if user_id in last_message_times:
                    time_diff = current_time - last_message_times[user_id]
                    if time_diff.total_seconds() > 3600:  # שעה = 3600 שניות
                        print(f"⏰ שיחה ישנה זוהתה: {user_id} (עברו {time_diff.total_seconds()/3600:.1f} שעות)")
                        
                        # בדוק אם כבר יש סיכום במערכת הסיכומים
                        if not self._has_existing_summary(user_id):
                            print(f"📝 מבצע סיכום אוטומטי לשיחה ישנה: {user_id}")
                            self._summarize_conversation(user_id)
                        else:
                            print(f"✅ שיחה {user_id} כבר סוכמה בעבר")
                            self.summarized_conversations.add(user_id)
                            
            except Exception as e:
                print(f"❌ שגיאה בבדיקת שיחה {user_id}: {e}")
                continue
                
    def _has_existing_summary(self, user_id):
        """בדוק אם כבר יש סיכום לשיחה זו"""
        try:
            # בדוק אם יש קובץ סיכום
            summary_file = f"conversations/{user_id}.txt"
            if os.path.exists(summary_file):
                with open(summary_file, "r", encoding="utf-8-sig") as f:
                    content = f.read()
                    if "📋 סיכום שיחה" in content:
                        return True
                        
            # בדוק במערכת הסיכומים החדשה
            try:
                from conversation_summaries import summaries_manager
                existing_summary = summaries_manager.get_summary(user_id)
                return existing_summary is not None
            except:
                pass
                
            return False
            
        except Exception as e:
            print(f"⚠️ שגיאה בבדיקת סיכום קיים: {e}")
            return False
            
    def _summarize_conversation(self, user_id):
        """בצע סיכום לשיחה ישנה"""
        try:
            print(f"📝 מתחיל סיכום אוטומטי לשיחה: {user_id}")
            
            # צור סיכום
            summary = summarize_conversation(user_id)
            if not summary:
                print(f"⚠️ לא הצלחתי ליצור סיכום לשיחה: {user_id}")
                return
                
            # שמור את הסיכום
            save_conversation_summary(user_id, summary)
            save_conversation_to_file(user_id)
            
            # סמן כסוכמה
            self.summarized_conversations.add(user_id)
            
            print(f"✅ סיכום אוטומטי הושלם עבור: {user_id}")
            
        except Exception as e:
            print(f"❌ שגיאה בסיכום אוטומטי: {e}")
            
    def force_summarize_all(self):
        """בצע סיכום כפוי לכל השיחות הישנות"""
        print("🔄 מבצע סיכום כפוי לכל השיחות הישנות...")
        current_time = datetime.now()
        
        for user_id, conversation in conversations.items():
            try:
                # בדוק אם יש שיחה עם יותר מ-5 הודעות
                user_assistant_messages = [
                    m for m in conversation 
                    if m["role"] in ["user", "assistant"]
                ]
                
                if len(user_assistant_messages) < 5:
                    continue
                    
                # בדוק אם עבר זמן רב מההודעה האחרונה (שעה)
                if user_id in last_message_times:
                    time_diff = current_time - last_message_times[user_id]
                    if time_diff.total_seconds() > 3600:  # שעה
                        print(f"⏰ מבצע סיכום כפוי לשיחה ישנה: {user_id}")
                        self._summarize_conversation(user_id)
                        
            except Exception as e:
                print(f"❌ שגיאה בסיכום כפוי: {e}")
                continue
                
        print("✅ סיכום כפוי הושלם")
        
    def get_status(self):
        """קבל סטטוס המערכת"""
        return {
            "running": self.running,
            "check_interval": self.check_interval,
            "total_conversations": len(conversations),
            "summarized_conversations": len(self.summarized_conversations),
            "active_conversations": len(conversations) - len(self.summarized_conversations)
        }

# יצירת מופע גלובלי
auto_summarizer = AutoSummarizer()

def start_auto_summarizer():
    """התחל את מערכת הסיכום האוטומטי"""
    auto_summarizer.start()
    
def stop_auto_summarizer():
    """עצור את מערכת הסיכום האוטומטי"""
    auto_summarizer.stop()
    
def get_auto_summarizer_status():
    """קבל סטטוס מערכת הסיכום האוטומטי"""
    return auto_summarizer.get_status()
    
def force_summarize_all():
    """בצע סיכום כפוי לכל השיחות הישנות"""
    auto_summarizer.force_summarize_all()

if __name__ == "__main__":
    # בדיקה פשוטה
    print("🔍 בדיקת מערכת הסיכום האוטומטי...")
    print(f"📊 סטטוס: {get_auto_summarizer_status()}")
    
    # התחל את המערכת
    start_auto_summarizer()
    
    try:
        # הרץ למשך דקה לבדיקה
        print("⏱️ הרצה למשך דקה לבדיקה...")
        time.sleep(60)
    except KeyboardInterrupt:
        print("\n🛑 עצירה ידנית...")
    finally:
        stop_auto_summarizer()
        print("✅ בדיקה הושלמה")
