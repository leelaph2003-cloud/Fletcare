# Fleet Care - Invoice & Email Setup Guide

## Overview
This guide explains how to set up the PDF invoice generation and email functionality for the Fleet Care system.

## Features Implemented

### 1. PDF Invoice Generation
- Professional PDF invoices with company branding
- Complete service details and cost breakdown
- Customer information and terms & conditions
- Automatic invoice numbering (INV-000001, INV-000002, etc.)

### 2. Email Functionality
- Automatic invoice delivery via email
- HTML email templates with professional design
- PDF attachments for easy access
- Bulk email functionality for multiple invoices

### 3. Automatic Invoice Generation
- Invoices are automatically generated when mechanics mark services as "Repairing Done" or "Released"
- Manual invoice generation and email sending options
- Individual and bulk invoice operations

## Setup Instructions

### 1. Install Required Packages
```bash
pip install reportlab Pillow
```

### 2. Configure Email Settings
Update the following settings in `vehicleservicemanagement/settings.py`:

```python
# Email Configuration
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_USE_TLS = True
EMAIL_PORT = 587
EMAIL_HOST_USER = 'your-email@gmail.com'  # Replace with your Gmail
EMAIL_HOST_PASSWORD = 'your-app-password'  # Replace with your app password
EMAIL_RECEIVING_USER = ['your-email@gmail.com']
```

### 3. Gmail App Password Setup
1. Go to your Google Account settings
2. Enable 2-Factor Authentication
3. Generate an App Password for "Mail"
4. Use this App Password in EMAIL_HOST_PASSWORD

### 4. Test Email Configuration
1. Start the Django server
2. Go to the customer invoice page
3. Try sending an invoice via email
4. Check your email for the invoice

## Usage

### For Customers
1. **View Invoices**: Go to Customer Dashboard → Invoice
2. **Download PDF**: Click the "PDF" button for any service request
3. **Receive via Email**: Click the "Email" button to receive invoice via email
4. **Bulk Email**: Use "Send All Invoices via Email" to receive all invoices at once

### For Mechanics
1. **Update Service Status**: When completing work, update status to "Repairing Done" or "Released"
2. **Automatic Invoice**: Invoice is automatically generated and sent to customer
3. **Status Tracking**: Monitor service progress through the dashboard

### For Admins
1. **Monitor Invoices**: View all generated invoices in the admin panel
2. **Email Configuration**: Ensure email settings are properly configured
3. **System Maintenance**: Monitor email delivery and PDF generation

## File Structure
```
vehicle/
├── invoice_utils.py          # PDF generation and email functions
├── views.py                  # Updated views with invoice functionality
└── templates/
    └── vehicle/
        ├── customer_invoice.html      # Updated invoice display
        └── email/
            └── invoice_email.html     # Email template

vehicleservicemanagement/
└── urls.py                  # New URL patterns for invoice functions
```

## URL Patterns Added
- `/customer-invoice-pdf/<id>` - Download PDF invoice
- `/customer-invoice-email/<id>` - Send invoice via email
- `/customer-invoice-bulk-email` - Send all invoices via email

## Troubleshooting

### Common Issues

1. **Email Not Sending**
   - Check Gmail app password configuration
   - Verify EMAIL_HOST_USER and EMAIL_HOST_PASSWORD
   - Check Gmail security settings

2. **PDF Generation Fails**
   - Ensure reportlab is installed: `pip install reportlab`
   - Check file permissions in the project directory

3. **Template Errors**
   - Verify email template exists at `templates/vehicle/email/invoice_email.html`
   - Check Django template syntax

### Error Messages
- "Email configuration not set up" - Update email settings in settings.py
- "Failed to generate PDF" - Check reportlab installation
- "Failed to send email" - Verify email configuration

## Security Considerations
- Email passwords should be stored securely (use environment variables)
- PDF generation is restricted to authenticated customers
- Email addresses are validated before sending

## Future Enhancements
- Invoice customization options
- Multiple email templates
- Invoice payment integration
- Digital signature support
- Invoice archiving system

## Support
For technical support or questions about the invoice system, please contact the development team. 