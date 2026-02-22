import os
import json
import requests

class AlertBot:
    def __init__(self, config_path=None):
        if config_path is None:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            config_path = os.path.join(script_dir, 'ai_config.json')
            
        with open(config_path, 'r') as f:
            self.config = json.load(f)
            
        self.telegram_token = self.config.get('telegram_bot_token', '')
        self.telegram_chat_id = self.config.get('telegram_chat_id', '')

    def send_high_score_alert(self, role, company, match_score, apply_link):
        """Sends an alert for highly scored jobs."""
        
        message = (
            f"🚨 TOP TIER MATCH 🚨\n\n"
            f"💼 Role: {role}\n"
            f"🏢 Company: {company}\n"
            f"⭐ AI Score: {match_score}/100\n\n"
            f"🔗 Link: {apply_link}\n\n"
            f"🚀 Dive into your Job Tracker Dashboard to generate your PDF resume!"
        )

        # If true credentials exist, use the standard Telegram Bot API.
        if self.telegram_token and self.telegram_chat_id:
            url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
            payload = {"chat_id": self.telegram_chat_id, "text": message}
            try:
                response = requests.post(url, json=payload)
                if response.status_code == 200:
                    print("   📱 Telegram alert sent successfully!")
                    return True
            except Exception as e:
                print(f"   ⚠️ Could not send Telegram alert: {e}")
        else:
            print(f"   📱 [MOCK ALERT NOT DUE TO MISSING KEYS in ai_config.json]:\n{message}")
            
        return False

if __name__ == "__main__":
    bot = AlertBot()
    bot.send_high_score_alert("Sr. Software Engineer", "Microsoft", 95, "https://careers.microsoft.com/fake")
