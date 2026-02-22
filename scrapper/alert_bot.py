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
            
        self.whatsapp_phone = self.config.get('whatsapp_phone', '')
        self.twilio_sid = self.config.get('twilio_sid', '')
        self.twilio_token = self.config.get('twilio_token', '')

    def send_high_score_alert(self, role, company, match_score, apply_link):
        """Sends an alert for highly scored jobs over WhatsApp via Twilio."""
        
        message = (
            f"🚨 TOP TIER MATCH 🚨\n\n"
            f"💼 Role: {role}\n"
            f"🏢 Company: {company}\n"
            f"⭐ AI Score: {match_score}/100\n\n"
            f"🔗 Link: {apply_link}\n\n"
            f"🚀 Dive into your Dashboard to generate your PDF resume!"
        )

        if self.whatsapp_phone and self.twilio_sid and self.twilio_token:
            url = f"https://api.twilio.com/2010-04-01/Accounts/{self.twilio_sid}/Messages.json"
            
            # Format phone numbers (Twilio requires 'whatsapp:+91...' format)
            to_number = f"whatsapp:+{self.whatsapp_phone}" if not self.whatsapp_phone.startswith('+') else f"whatsapp:{self.whatsapp_phone}"
            from_number = "whatsapp:+14155238886"  # Official Twilio Sandbox Number
            
            payload = {
                "From": from_number,
                "To": to_number,
                "Body": message
            }
            
            try:
                response = requests.post(url, data=payload, auth=(self.twilio_sid, self.twilio_token))
                if response.status_code in [200, 201]:
                    print("   📱 WhatsApp alert sent successfully via Twilio!")
                    return True
                else:
                    print(f"   ⚠️ Twilio API Error: {response.text}")
            except Exception as e:
                print(f"   ⚠️ Could not send WhatsApp alert: {e}")
        else:
            print(f"   📱 [MOCK WHATSAPP ALERT NOT DEPLOYED DUE TO MISSING TWILIO KEYS]:\n{message}")
            
        return False

if __name__ == "__main__":
    bot = AlertBot()
    bot.send_high_score_alert("Sr. Software Engineer", "Microsoft", 95, "https://careers.microsoft.com/fake")


