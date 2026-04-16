"""
MFA (Multi-Factor Authentication) service.
Supports Email (Gmail OAuth2 or SMTP) and SMS (Twilio) OTP delivery.
"""
from datetime import datetime
from typing import Optional, Tuple
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from sqlalchemy.orm import Session

from .models import User, OTPRecord
from .security import generate_otp, hash_otp, verify_otp, get_otp_expiry

# Gmail OAuth (preferred)
try:
    from .gmail_oauth import gmail_service
    GMAIL_OAUTH_AVAILABLE = True
except ImportError:
    gmail_service = None
    GMAIL_OAUTH_AVAILABLE = False

# Email configuration (fallback SMTP)
EMAIL_ENABLED = os.getenv("EMAIL_ENABLED", "false").lower() == "true"
EMAIL_FROM = os.getenv("EMAIL_FROM", "noreply@preventdawn.health")

# Gmail SMTP configuration (fallback)
GMAIL_ADDRESS = os.getenv("GMAIL_ADDRESS")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
GMAIL_SMTP_ENABLED = bool(GMAIL_ADDRESS and GMAIL_APP_PASSWORD)

# SMS configuration (Twilio)
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")
SMS_ENABLED = bool(TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN and TWILIO_PHONE_NUMBER)


class MFAService:
    """Service for handling Multi-Factor Authentication."""

    def __init__(self, db: Session):
        self.db = db

    def generate_and_save_otp(
        self, 
        user: User, 
        otp_type: str = "mfa"
    ) -> str:
        """
        Generate an OTP, save it to database, and return the plain code.
        otp_type can be: "mfa", "verification", "password_reset"
        """
        # Invalidate any existing OTPs for this user and type
        self.db.query(OTPRecord).filter(
            OTPRecord.user_id == user.id,
            OTPRecord.otp_type == otp_type,
            OTPRecord.used == False
        ).update({"used": True})
        
        # Generate new OTP
        plain_otp = generate_otp()
        hashed = hash_otp(plain_otp)
        
        otp_record = OTPRecord(
            user_id=user.id,
            code=hashed,
            otp_type=otp_type,
            expires_at=get_otp_expiry()
        )
        self.db.add(otp_record)
        self.db.commit()
        
        return plain_otp

    def verify_user_otp(
        self, 
        user: User, 
        plain_otp: str, 
        otp_type: str = "mfa"
    ) -> Tuple[bool, str]:
        """
        Verify an OTP for a user.
        Returns (success, message).
        """
        # Find the latest valid OTP
        otp_record = self.db.query(OTPRecord).filter(
            OTPRecord.user_id == user.id,
            OTPRecord.otp_type == otp_type,
            OTPRecord.used == False,
            OTPRecord.expires_at > datetime.utcnow()
        ).order_by(OTPRecord.created_at.desc()).first()
        
        if not otp_record:
            return False, "No valid OTP found or OTP expired"
        
        # Check attempts (max 3)
        attempts = int(otp_record.attempts)
        if attempts >= 3:
            otp_record.used = True
            self.db.commit()
            return False, "Too many attempts. Please request a new code."
        
        # Verify
        if verify_otp(plain_otp, otp_record.code):
            otp_record.used = True
            otp_record.used_at = datetime.utcnow()
            self.db.commit()
            return True, "OTP verified successfully"
        else:
            otp_record.attempts = str(attempts + 1)
            self.db.commit()
            return False, f"Invalid OTP. {2 - attempts} attempts remaining."

    async def send_otp_email(
        self, 
        email: str, 
        otp: str, 
        purpose: str = "verification"
    ) -> bool:
        """
        Send OTP via email.
        Tries Gmail OAuth first, then SMTP fallback, then dev mode.
        Returns True if sent successfully.
        """
        # Try Gmail OAuth first (preferred)
        if GMAIL_OAUTH_AVAILABLE and gmail_service.is_configured():
            if gmail_service.is_authenticated() or gmail_service.initialize():
                result = await gmail_service.send_otp_email(email, otp, purpose)
                if result:
                    return True
                print("[MFA] Gmail OAuth failed, trying fallback...")
        
        # Try Gmail SMTP (fallback)
        if GMAIL_SMTP_ENABLED:
            try:
                return await self._send_via_smtp(email, otp, purpose)
            except Exception as e:
                print(f"[MFA] SMTP fallback failed: {e}")
        
        # Development mode - log the OTP
        print(f"[DEV] Email OTP for {email}: {otp} (purpose: {purpose})")
        return True

    async def _send_via_smtp(self, email: str, otp: str, purpose: str) -> bool:
        """Send email via Gmail SMTP."""
        subject_map = {
            "verification": "Verify your PREVENT Dawn account",
            "mfa": "Your PREVENT Dawn login code",
            "password_reset": "Reset your PREVENT Dawn password"
        }
        subject = subject_map.get(purpose, "Your PREVENT Dawn code")
        
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = GMAIL_ADDRESS
        msg["To"] = email
        
        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: linear-gradient(135deg, #10b981, #059669); padding: 30px; text-align: center;">
                <h1 style="color: white; margin: 0;">🍏 PREVENT Dawn</h1>
            </div>
            <div style="padding: 30px; background: #f9fafb;">
                <h2 style="color: #111827;">Your Verification Code</h2>
                <p style="color: #6b7280;">Use the code below to {purpose.replace('_', ' ')}:</p>
                <div style="background: #10b981; color: white; font-size: 32px; font-weight: bold; 
                            padding: 20px; text-align: center; letter-spacing: 8px; margin: 20px 0;">
                    {otp}
                </div>
                <p style="color: #6b7280; font-size: 14px;">
                    This code expires in <strong>10 minutes</strong>.<br>
                    If you didn't request this code, please ignore this email.
                </p>
            </div>
            <div style="background: #1f2937; color: #9ca3af; padding: 20px; text-align: center; font-size: 12px;">
                PREVENT Dawn - Your Diabetes Prevention Partner
            </div>
        </body>
        </html>
        """
        text_body = f"Your PREVENT Dawn verification code is: {otp}\n\nThis code expires in 10 minutes."
        
        msg.attach(MIMEText(text_body, "plain"))
        msg.attach(MIMEText(html_body, "html"))
        
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
            server.sendmail(GMAIL_ADDRESS, email, msg.as_string())
        
        print(f"[EMAIL] Sent OTP to {email} via Gmail SMTP")
        return True

    async def send_otp_sms(
        self, 
        phone_number: str, 
        otp: str
    ) -> bool:
        """
        Send OTP via SMS using Twilio.
        Returns True if sent successfully.
        """
        if SMS_ENABLED:
            try:
                from twilio.rest import Client
                
                client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
                message = client.messages.create(
                    body=f"Your PREVENT Dawn verification code is: {otp}. Valid for 10 minutes.",
                    from_=TWILIO_PHONE_NUMBER,
                    to=phone_number
                )
                print(f"[SMS] Sent to {phone_number}, SID: {message.sid}")
                return True
            except Exception as e:
                print(f"[ERROR] Failed to send SMS: {e}")
        
        # Development mode - log the OTP
        print(f"[DEV] SMS OTP for {phone_number}: {otp}")
        return True

    async def send_otp(
        self, 
        user: User, 
        otp: str, 
        otp_type: str = "mfa"
    ) -> bool:
        """
        Send OTP using user's preferred MFA method.
        """
        method = user.mfa_method or "email"
        
        if method == "sms" and user.phone_number:
            return await self.send_otp_sms(user.phone_number, otp)
        else:
            return await self.send_otp_email(user.email, otp, otp_type)

    async def send_physician_invite_email(
        self,
        email: str,
        invite_code: str,
        physician_name: str = None,
        expires_at: str = None
    ) -> bool:
        """
        Send physician invite code email.
        """
        name_display = physician_name or "Healthcare Provider"
        
        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: linear-gradient(135deg, #10b981, #059669); padding: 30px; text-align: center;">
                <h1 style="color: white; margin: 0;">🍏 PREVENT Dawn</h1>
                <p style="color: rgba(255,255,255,0.8); margin: 10px 0 0 0;">Physician Registration Invitation</p>
            </div>
            <div style="padding: 30px; background: #f9fafb;">
                <h2 style="color: #111827;">Welcome, {name_display}!</h2>
                <p style="color: #6b7280;">
                    You have been invited to join PREVENT Dawn as a healthcare provider. 
                    Use the code below when registering on our platform:
                </p>
                <div style="background: #10b981; color: white; font-size: 28px; font-weight: bold; 
                            padding: 20px; text-align: center; letter-spacing: 6px; margin: 20px 0; 
                            border-radius: 8px; font-family: monospace;">
                    {invite_code}
                </div>
                <p style="color: #6b7280; font-size: 14px;">
                    <strong>Important:</strong>
                    <ul>
                        <li>Register at <a href="http://localhost:8080/register">PREVENT Dawn Registration</a></li>
                        <li>Select "Physician" as your role</li>
                        <li>Enter this invite code when prompted</li>
                        <li>Use this email address ({email}) to register</li>
                    </ul>
                </p>
                {f'<p style="color: #ef4444; font-size: 14px;">⚠️ This code expires on {expires_at}</p>' if expires_at else ''}
            </div>
            <div style="background: #1f2937; color: #9ca3af; padding: 20px; text-align: center; font-size: 12px;">
                PREVENT Dawn - Your Diabetes Prevention Partner<br>
                <span style="color: #6b7280;">This is an automated message. Please do not reply.</span>
            </div>
        </body>
        </html>
        """
        
        # Try Gmail OAuth first
        if GMAIL_OAUTH_AVAILABLE and gmail_service:
            if gmail_service.is_authenticated() or gmail_service.initialize():
                # Construct plain text version
                text_body = f"""
Welcome to PREVENT Dawn!

You have been invited to join as a healthcare provider.

Your invite code: {invite_code}

Register at: http://localhost:8080/register
- Select "Physician" as your role
- Enter your invite code
- Use this email address ({email}) to register

{f'This code expires on {expires_at}' if expires_at else ''}
                """
                result = await gmail_service.send_email(
                    to=email,
                    subject="Your PREVENT Dawn Physician Registration Invite",
                    body_text=text_body,
                    body_html=html_body
                )
                if result:
                    print(f"[EMAIL] Sent physician invite to {email} via Gmail OAuth")
                    return True
        
        # Try Gmail SMTP
        if GMAIL_SMTP_ENABLED:
            try:
                msg = MIMEMultipart("alternative")
                msg["Subject"] = "Your PREVENT Dawn Physician Registration Invite"
                msg["From"] = GMAIL_ADDRESS
                msg["To"] = email
                
                text_body = f"""
Welcome to PREVENT Dawn!

You have been invited to join as a healthcare provider.

Your invite code: {invite_code}

Register at: http://localhost:8080/register
- Select "Physician" as your role
- Enter your invite code
- Use this email address ({email}) to register

{f'This code expires on {expires_at}' if expires_at else ''}
                """
                
                msg.attach(MIMEText(text_body, "plain"))
                msg.attach(MIMEText(html_body, "html"))
                
                with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                    server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
                    server.sendmail(GMAIL_ADDRESS, email, msg.as_string())
                
                print(f"[EMAIL] Sent physician invite to {email} via Gmail SMTP")
                return True
            except Exception as e:
                print(f"[ERROR] Failed to send invite email via SMTP: {e}")
        
        # Development mode - log the invite
        print(f"[DEV] Physician invite for {email}: Code={invite_code}")
        return True  # Return true in dev mode
