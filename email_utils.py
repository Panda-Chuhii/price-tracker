import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from itsdangerous import URLSafeTimedSerializer

SENDER_EMAIL = os.environ.get('SENDER_EMAIL', 'pricetrack28152gmail.com')
SENDER_PASSWORD = os.environ.get('SENDER_PASSWORD', 'xvsevhrhzcdvhxmt')
SECRET_KEY = os.environ.get('SECRET_KEY', 'your-secret-key-change-this')

serializer = URLSafeTimedSerializer(SECRET_KEY)

def send_email(to_email, subject, body):
    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = SENDER_EMAIL
    msg['To'] = to_email
    msg.attach(MIMEText(body, 'html'))
    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(msg)
        print(f"[Email sent] to {to_email}")
        return True
    except Exception as e:
        print(f"[Email error] {e}")
        return False

def send_verification_email(user_email, base_url):
    token = serializer.dumps(user_email, salt='email-verify')
    link = f"{base_url}/verify-email/{token}"
    body = f"""
    <div style="font-family:sans-serif;max-width:500px;margin:auto;padding:32px;background:#f0f4ff;border-radius:16px">
      <h2 style="color:#4f46e5">Verify your email</h2>
      <p style="color:#374151">Thanks for registering on PriceTracker! Click the button below to verify your email address.</p>
      <a href="{link}" style="display:inline-block;padding:12px 24px;background:linear-gradient(135deg,#6366f1,#ec4899);color:white;border-radius:8px;text-decoration:none;font-weight:700;margin:16px 0">Verify Email</a>
      <p style="color:#9ca3af;font-size:13px">This link expires in 1 hour. If you didn't register, ignore this email.</p>
    </div>
    """
    return send_email(user_email, "Verify your PriceTracker email", body)

def send_reset_email(user_email, base_url):
    token = serializer.dumps(user_email, salt='password-reset')
    link = f"{base_url}/reset-password/{token}"
    body = f"""
    <div style="font-family:sans-serif;max-width:500px;margin:auto;padding:32px;background:#f0f4ff;border-radius:16px">
      <h2 style="color:#4f46e5">Reset your password</h2>
      <p style="color:#374151">We received a request to reset your password. Click the button below to set a new one.</p>
      <a href="{link}" style="display:inline-block;padding:12px 24px;background:linear-gradient(135deg,#6366f1,#ec4899);color:white;border-radius:8px;text-decoration:none;font-weight:700;margin:16px 0">Reset Password</a>
      <p style="color:#9ca3af;font-size:13px">This link expires in 1 hour. If you didn't request this, ignore this email.</p>
    </div>
    """
    return send_email(user_email, "Reset your PriceTracker password", body)

def verify_token(token, salt, expiry=3600):
    try:
        email = serializer.loads(token, salt=salt, max_age=expiry)
        return email
    except Exception:
        return None