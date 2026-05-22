# 🔧 **Fix Fleet Care Email Issue**

## ❌ **Current Problem:**
- Email sending is failing with "Failed to send 2 invoice(s)" error
- Gmail is rejecting the login credentials
- You're using a regular password instead of an App Password

## ✅ **Solution: Get Gmail App Password**

### **Step 1: Enable 2-Factor Authentication**
1. Go to: https://myaccount.google.com/security
2. Sign in with: `fleetcare09@gmail.com`
3. Enable **"2-Step Verification"** (2-Factor Authentication)

### **Step 2: Generate App Password**
1. In the same Security section, find **"App passwords"**
2. Click **"App passwords"**
3. Select **"Mail"** as the app
4. Click **"Generate"**
5. Copy the **16-character password** (like `abcd efgh ijkl mnop`)

### **Step 3: Update Your Settings**
**File**: `vehicleservicemanagement/settings.py`

**Change this line:**
```python
EMAIL_HOST_PASSWORD = 'Fleetcare@123'  # ❌ Regular password
```

**To this (use your generated App Password):**
```python
EMAIL_HOST_PASSWORD = 'abcd efgh ijkl mnop'  # ✅ App Password
```

**Important:**
- Remove all spaces from the App Password
- Use exactly 16 characters
- Do NOT use your regular Gmail password

## 🧪 **Test After Fix:**
1. **Save the settings.py file**
2. **Try sending an invoice** from the customer dashboard
3. **Check the console** for detailed error messages

## 🎯 **Why This Happens:**
- **Google no longer allows** regular passwords for SMTP
- **App Passwords are required** for security
- **2-Factor Authentication must be enabled** to generate App Passwords

## 📧 **After Fix:**
- ✅ Invoices will send successfully via email
- ✅ Custom recipient emails will work
- ✅ Bulk email functionality will work
- ✅ Professional email system fully operational

---

**Need Help?** Check the console output for specific error messages after attempting to send an email. 