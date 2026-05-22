#!/usr/bin/env python
"""
Simple email test for Fleet Care
Run this AFTER you update your Gmail App Password in settings.py
"""
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vehicleservicemanagement.settings')
django.setup()

from django.core.mail import send_mail
from django.conf import settings

def test_email():
    print("🔍 Testing Fleet Care Email Configuration...")
    print("=" * 50)
    
    # Check current settings
    print(f"EMAIL_HOST: {settings.EMAIL_HOST}")
    print(f"EMAIL_PORT: {settings.EMAIL_PORT}")
    print(f"EMAIL_USE_TLS: {settings.EMAIL_USE_TLS}")
    print(f"EMAIL_HOST_USER: {settings.EMAIL_HOST_USER}")
    
    # Check password length (App Passwords are 16 characters)
    password = settings.EMAIL_HOST_PASSWORD
    password_length = len(password) if password else 0
    print(f"EMAIL_HOST_PASSWORD length: {password_length}")
    
    if password_length < 16:
        print("❌ Password too short! App Passwords must be 16 characters")
        print("🔧 Please update EMAIL_HOST_PASSWORD in settings.py")
        return False
    
    if ' ' in password:
        print("❌ Password contains spaces! Remove all spaces")
        print("🔧 Please update EMAIL_HOST_PASSWORD in settings.py")
        return False
    
    print("✅ Password format looks correct!")
    
    # Try to send email
    try:
        print("\n🔍 Attempting to send test email...")
        send_mail(
            subject='Fleet Care - Email Test',
            message='This is a test email to verify your email configuration is working correctly.',
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[settings.EMAIL_HOST_USER],
            fail_silently=False,
        )
        print("✅ Test email sent successfully!")
        print("📧 Check your inbox at:", settings.EMAIL_HOST_USER)
        return True
        
    except Exception as e:
        print(f"❌ Email test failed: {str(e)}")
        
        if "Authentication" in str(e):
            print("\n🔧 SOLUTION: Authentication failed. Check your App Password.")
        elif "Username and Password not accepted" in str(e):
            print("\n🔧 SOLUTION: Username/password not accepted. Check your App Password.")
        elif "Less secure app access" in str(e):
            print("\n🔧 SOLUTION: Enable 2-Factor Authentication and use App Password.")
        
        return False

if __name__ == '__main__':
    print("🚀 Fleet Care Email Test")
    print("Make sure you've updated EMAIL_HOST_PASSWORD in settings.py first!")
    print()
    
    success = test_email()
    
    if success:
        print("\n🎉 Email configuration is working! You can now send invoices.")
    else:
        print("\n💡 Fix the email configuration and run this script again.") 