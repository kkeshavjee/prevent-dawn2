"""
Gmail OAuth2 Email Service.
Sends emails using Gmail API with OAuth2 authentication.
"""
import os
import base64
import pickle
from pathlib import Path
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# OAuth2 scopes for Gmail
SCOPES = [
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.readonly'
]

# Path to store credentials
CREDENTIALS_DIR = Path(__file__).parent / 'credentials'
TOKEN_PATH = CREDENTIALS_DIR / 'gmail_token.pickle'
CLIENT_SECRET_PATH = CREDENTIALS_DIR / 'client_secret.json'


class GmailOAuthService:
    """Service for sending emails via Gmail OAuth2."""
    
    def __init__(self):
        self.service = None
        self.sender_email = None
        self._initialized = False
    
    def is_configured(self) -> bool:
        """Check if Gmail OAuth is configured."""
        return CLIENT_SECRET_PATH.exists()
    
    def is_authenticated(self) -> bool:
        """Check if we have valid credentials."""
        if TOKEN_PATH.exists():
            try:
                with open(TOKEN_PATH, 'rb') as token:
                    creds = pickle.load(token)
                return creds and creds.valid
            except:
                return False
        return False
    
    def initialize(self) -> bool:
        """
        Initialize the Gmail service.
        Returns True if successful.
        """
        if self._initialized and self.service:
            return True
        
        if not self.is_configured():
            print("[Gmail OAuth] Not configured - client_secret.json not found")
            return False
        
        creds = None
        
        # Load existing token
        if TOKEN_PATH.exists():
            try:
                with open(TOKEN_PATH, 'rb') as token:
                    creds = pickle.load(token)
            except Exception as e:
                print(f"[Gmail OAuth] Error loading token: {e}")
        
        # Refresh or get new credentials
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                # Save refreshed token
                with open(TOKEN_PATH, 'wb') as token:
                    pickle.dump(creds, token)
            except Exception as e:
                print(f"[Gmail OAuth] Error refreshing token: {e}")
                creds = None
        
        if not creds or not creds.valid:
            print("[Gmail OAuth] No valid credentials. Run setup_gmail_oauth.py first.")
            return False
        
        try:
            self.service = build('gmail', 'v1', credentials=creds)
            # Get sender email
            profile = self.service.users().getProfile(userId='me').execute()
            self.sender_email = profile.get('emailAddress')
            self._initialized = True
            print(f"[Gmail OAuth] Initialized for {self.sender_email}")
            return True
        except HttpError as e:
            print(f"[Gmail OAuth] Error initializing: {e}")
            return False
    
    def create_message(self, to: str, subject: str, body_text: str, body_html: str = None) -> dict:
        """Create a message for the Gmail API."""
        message = MIMEMultipart('alternative')
        message['to'] = to
        message['from'] = self.sender_email
        message['subject'] = subject
        
        # Attach text version
        message.attach(MIMEText(body_text, 'plain'))
        
        # Attach HTML version if provided
        if body_html:
            message.attach(MIMEText(body_html, 'html'))
        
        # Encode the message
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
        return {'raw': raw}
    
    async def send_email(self, to: str, subject: str, body_text: str, body_html: str = None) -> bool:
        """
        Send an email via Gmail API.
        Returns True if successful.
        """
        if not self.initialize():
            return False
        
        try:
            message = self.create_message(to, subject, body_text, body_html)
            self.service.users().messages().send(userId='me', body=message).execute()
            print(f"[Gmail OAuth] Email sent to {to}")
            return True
        except HttpError as e:
            print(f"[Gmail OAuth] Error sending email: {e}")
            return False
    
    async def send_otp_email(self, to: str, otp: str, purpose: str = "verification") -> bool:
        """Send an OTP email with nice formatting."""
        subject_map = {
            "verification": "Verify your PREVENT Dawn account",
            "mfa": "Your PREVENT Dawn login code",
            "password_reset": "Reset your PREVENT Dawn password"
        }
        subject = subject_map.get(purpose, "Your PREVENT Dawn code")
        
        text_body = f"Your PREVENT Dawn verification code is: {otp}\n\nThis code expires in 10 minutes."
        
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
                            padding: 20px; text-align: center; letter-spacing: 8px; margin: 20px 0; border-radius: 8px;">
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
        
        return await self.send_email(to, subject, text_body, html_body)


# Global instance
gmail_service = GmailOAuthService()
