"""
Gmail OAuth2 Setup Script.

Run this script once to authenticate with Gmail and store credentials.
After running, emails can be sent without user interaction.

Usage:
    python setup_gmail_oauth.py

Prerequisites:
1. Download client_secret.json from Google Cloud Console
2. Place it in backend/auth/credentials/client_secret.json
"""
import os
import sys
import pickle
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Include both send and readonly scopes
SCOPES = [
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.readonly'
]
CREDENTIALS_DIR = Path(__file__).parent / 'credentials'
TOKEN_PATH = CREDENTIALS_DIR / 'gmail_token.pickle'
CLIENT_SECRET_PATH = CREDENTIALS_DIR / 'client_secret.json'


def setup_gmail_oauth():
    """Run the OAuth flow and save credentials."""
    print("=" * 60)
    print("Gmail OAuth2 Setup for PREVENT Dawn")
    print("=" * 60)
    
    # Ensure credentials directory exists
    CREDENTIALS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Check for client_secret.json
    if not CLIENT_SECRET_PATH.exists():
        print("\n❌ ERROR: client_secret.json not found!")
        print("\nTo set up Gmail OAuth2:")
        print("1. Go to https://console.cloud.google.com/apis/credentials")
        print("2. Create a new project (or select existing)")
        print("3. Enable the Gmail API:")
        print("   - Go to 'APIs & Services' > 'Library'")
        print("   - Search for 'Gmail API' and enable it")
        print("4. Create OAuth credentials:")
        print("   - Go to 'APIs & Services' > 'Credentials'")
        print("   - Click 'Create Credentials' > 'OAuth client ID'")
        print("   - Select 'Desktop app' as application type")
        print("   - Download the JSON file")
        print(f"5. Rename it to 'client_secret.json' and place it in:")
        print(f"   {CLIENT_SECRET_PATH}")
        print("\n6. Run this script again.")
        return False
    
    print("\n✓ Found client_secret.json")
    print("\nStarting OAuth flow...")
    print("A browser window will open for you to authorize the app.\n")
    
    try:
        # Run the OAuth flow
        flow = InstalledAppFlow.from_client_secrets_file(
            str(CLIENT_SECRET_PATH), 
            SCOPES
        )
        creds = flow.run_local_server(port=8085)
        
        # Save the credentials
        with open(TOKEN_PATH, 'wb') as token:
            pickle.dump(creds, token)
        
        print("\n✓ Authentication successful!")
        
        # Test the connection
        service = build('gmail', 'v1', credentials=creds)
        profile = service.users().getProfile(userId='me').execute()
        email = profile.get('emailAddress')
        
        print(f"\n✓ Connected to Gmail account: {email}")
        print(f"\n✓ Credentials saved to: {TOKEN_PATH}")
        print("\n" + "=" * 60)
        print("Setup complete! You can now send emails via Gmail OAuth2.")
        print("Restart the backend server to enable email sending.")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error during OAuth flow: {e}")
        return False


if __name__ == "__main__":
    setup_gmail_oauth()
