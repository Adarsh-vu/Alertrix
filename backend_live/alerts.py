import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

EMAIL_CONFIG = {
    'smtp_server': os.getenv('SMTP_SERVER', 'smtp.gmail.com'),
    'smtp_port': int(os.getenv('SMTP_PORT', 587)),
    'sender_email': os.getenv('arshcrx@gmail.com', ''),
    'sender_password': os.getenv('Arsh@9023', ''),
    'enabled': False 
}

# Check if email is configured
if EMAIL_CONFIG['sender_email'] and EMAIL_CONFIG['sender_password']:
    EMAIL_CONFIG['enabled'] = True
    print("✅ Email alerts enabled")
else:
    print("⚠️ Email alerts disabled. Set ALERT_EMAIL and ALERT_EMAIL_PASSWORD env vars to enable.")


class AlertManager:
    """Manages all alert notifications"""
    
    def __init__(self):
        self.last_alert_time = {}
        self.cooldown_seconds = 30  # Minimum time between alerts
        self.alert_history = []
        self.max_history = 100
    
    def can_send_alert(self, source_id: str) -> bool:
        """Check if enough time has passed since last alert"""
        now = datetime.now()
        if source_id not in self.last_alert_time:
            return True
        elapsed = (now - self.last_alert_time[source_id]).total_seconds()
        return elapsed >= self.cooldown_seconds
    
    def record_alert(self, source_id: str, score: float, status: str):
        """Record that an alert was sent"""
        now = datetime.now()
        self.last_alert_time[source_id] = now
        
        alert_record = {
            'timestamp': now.isoformat(),
            'source_id': source_id,
            'score': score,
            'status': status
        }
        self.alert_history.append(alert_record)
        
        # Trim history if too long
        if len(self.alert_history) > self.max_history:
            self.alert_history = self.alert_history[-self.max_history:]
    
    def send_email_alert(self, recipient_email: str, source_id: str, score: float, camera_name: str = None):

        if not EMAIL_CONFIG['enabled']:
            return {'success': False, 'error': 'Email not configured'}
        
        if not self.can_send_alert(source_id):
            return {'success': False, 'error': 'Alert cooldown active'}
        
        try:
            # Determine threat level
            if score > 0.70:
                threat_level = "🔴 CRITICAL"
                subject = f"🚨 CRITICAL ALERT: Anomaly Detected - {camera_name or source_id}"
            elif score > 0.45:
                threat_level = "🟠 WARNING"
                subject = f"⚠️ WARNING: Potential Anomaly - {camera_name or source_id}"
            else:
                return {'success': False, 'error': 'Score below alert threshold'}
            
            # Create email content
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body {{ font-family: 'Segoe UI', sans-serif; background: #f1f5f9; padding: 20px; }}
                    .container {{ max-width: 600px; margin: 0 auto; background: white; border-radius: 16px; overflow: hidden; box-shadow: 0 4px 20px rgba(0,0,0,0.1); }}
                    .header {{ background: linear-gradient(135deg, #14b8a6, #0d9488); color: white; padding: 24px; text-align: center; }}
                    .header h1 {{ margin: 0; font-size: 28px; }}
                    .content {{ padding: 24px; }}
                    .alert-badge {{ display: inline-block; padding: 8px 16px; border-radius: 8px; font-weight: bold; font-size: 18px; 
                        {'background: #fee2e2; color: #dc2626;' if score > 0.70 else 'background: #fff7ed; color: #c2410c;'} }}
                    .details {{ background: #f8fafc; border-radius: 12px; padding: 16px; margin: 16px 0; }}
                    .detail-row {{ display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #e2e8f0; }}
                    .detail-row:last-child {{ border-bottom: none; }}
                    .score {{ font-size: 48px; font-weight: bold; text-align: center; 
                        {'color: #dc2626;' if score > 0.70 else 'color: #c2410c;'} }}
                    .footer {{ background: #f8fafc; padding: 16px; text-align: center; color: #64748b; font-size: 12px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>🛡️ Alertrix AI</h1>
                        <p style="margin: 8px 0 0; opacity: 0.9;">Anomaly Detection Alert</p>
                    </div>
                    <div class="content">
                        <div style="text-align: center; margin-bottom: 16px;">
                            <span class="alert-badge">{threat_level}</span>
                        </div>
                        <div class="score">{int(score * 100)}%</div>
                        <p style="text-align: center; color: #64748b;">Threat Score</p>
                        
                        <div class="details">
                            <div class="detail-row">
                                <span><strong>Camera:</strong></span>
                                <span>{camera_name or source_id}</span>
                            </div>
                            <div class="detail-row">
                                <span><strong>Time:</strong></span>
                                <span>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</span>
                            </div>
                            <div class="detail-row">
                                <span><strong>Status:</strong></span>
                                <span>{threat_level}</span>
                            </div>
                        </div>
                        
                        <p style="text-align: center; margin-top: 16px;">
                            <strong>Action Required:</strong> Please review the live feed immediately.
                        </p>
                    </div>
                    <div class="footer">
                        Alertrix AI Security System | This is an automated alert
                    </div>
                </div>
            </body>
            </html>
            """
            
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = EMAIL_CONFIG['sender_email']
            msg['To'] = recipient_email
            
            # Attach HTML content
            msg.attach(MIMEText(html_content, 'html'))
            
            # Send email
            with smtplib.SMTP(EMAIL_CONFIG['smtp_server'], EMAIL_CONFIG['smtp_port']) as server:
                server.starttls()
                server.login(EMAIL_CONFIG['sender_email'], EMAIL_CONFIG['sender_password'])
                server.sendmail(EMAIL_CONFIG['sender_email'], recipient_email, msg.as_string())
            
            # Record the alert
            self.record_alert(source_id, score, threat_level)
            
            print(f"📧 Email alert sent to {recipient_email} for {source_id} (score: {score:.2f})")
            return {'success': True, 'message': 'Email sent successfully'}
            
        except Exception as e:
            print(f"❌ Email alert failed: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_alert_history(self, limit: int = 50):
        """Get recent alert history"""
        return self.alert_history[-limit:]
    
    def get_voice_alert_text(self, score: float, camera_name: str = None) -> str:
        """
        Generate text for browser voice alerts (Text-to-Speech)
        Called from frontend via API
        """
        if score > 0.70:
            return f"Critical alert! Anomaly detected on {camera_name or 'camera'}. Threat score {int(score * 100)} percent. Immediate attention required."
        elif score > 0.45:
            return f"Warning. Potential anomaly detected on {camera_name or 'camera'}. Threat score {int(score * 100)} percent. Please investigate."
        return ""


# Global alert manager instance
alert_manager = AlertManager()


def get_alert_manager():
    """Get the global alert manager instance"""
    return alert_manager
