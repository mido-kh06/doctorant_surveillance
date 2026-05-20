import sys
import os

# Set Python path to project directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import send_registration_summary

if __name__ == '__main__':
    email = "khayamedmehdi@gmail.com"
    print(f"Starting daily registration summary script for email: {email}...")
    success = send_registration_summary(email)
    if success:
        print("Daily summary email sent successfully.")
    else:
        print("Failed to send daily summary email. Please check your SMTP settings.")
