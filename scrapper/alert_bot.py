import os
import json
import requests
import urllib.parse

class AlertBot:
    def __init__(self, config_path=None):
        if config_path is None:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            config_path = os.path.join(script_dir, 'ai_config.json')
            
        with open(config_path, 'r') as f:
            self.config = json.load(f)
            
        self.whatsapp_phone = self.config.get('whatsapp_phone', '')
        self.whatsapp_api_key = self.config.get('whatsapp_api_key', '')

    def send_high_score_alert(self, role, company, match_score, apply_link):
        """Sends an alert for highly scored jobs over WhatsApp."""
        
        message = (
            f"🚨 TOP TIER MATCH 🚨\n\n"
            f"💼 Role: {role}\n"
            f"🏢 Company: {company}\n"
            f"⭐ AI Score: {match_score}/100\n\n"
            f"🔗 Link: {apply_link}\n\n"
            f"🚀 Dive into your Job Tracker Dashboard to generate your PDF resume!"
        )

        encoded_message = urllib.parse.quote(message)

        if self.whatsapp_phone and self.whatsapp_api_key:
            url = f"https://api.callmebot.com/whatsapp.php?phone={self.whatsapp_phone}&text={encoded_message}&apikey={self.whatsapp_api_key}"
            try:
                response = requests.get(url)
                if response.status_code == 200:
                    print("   📱 WhatsApp alert sent successfully!")
                    return True
                else:
                    print(f"   ⚠️ WhatsApp API Error: {response.text}")
            except Exception as e:
                print(f"   ⚠️ Could not send WhatsApp alert: {e}")
        else:
            print(f"   📱 [MOCK WHATSAPP ALERT NOT DEPLOYED DUE TO MISSING KEYS in ai_config.json]:\n{message}")
            
        return False

if __name__ == "__main__":
    bot = AlertBot()
    bot.send_high_score_alert("Sr. Software Engineer", "Microsoft", 95, "https://careers.microsoft.com/fake")

