import os
from io import BytesIO
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from django.core.mail import EmailMessage
from django.conf import settings
from django.template.loader import render_to_string
from django.http import HttpResponse
from .models import Request, Customer
from datetime import datetime

def generate_invoice_pdf(request_id):
    """
    Generate a PDF invoice for a specific service request
    """
    try:
        # Get the service request
        service_request = Request.objects.get(id=request_id)
        customer = service_request.customer
        
        # Create the PDF document
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        elements = []
        
        # Get styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            alignment=TA_CENTER,
            textColor=colors.darkblue
        )
        
        subtitle_style = ParagraphStyle(
            'CustomSubtitle',
            parent=styles['Heading2'],
            fontSize=16,
            spaceAfter=20,
            alignment=TA_CENTER,
            textColor=colors.darkblue
        )
        
        normal_style = styles['Normal']
        
        # Add company header
        elements.append(Paragraph("FLEET CARE", title_style))
        elements.append(Paragraph("Professional Vehicle Services", subtitle_style))
        elements.append(Spacer(1, 20))
        
        # Add invoice details
        elements.append(Paragraph(f"<b>INVOICE</b>", styles['Heading2']))
        elements.append(Spacer(1, 10))
        
        # Invoice info table
        invoice_data = [
            ['Invoice Number:', f'INV-{service_request.id:06d}'],
            ['Invoice Date:', datetime.now().strftime('%B %d, %Y')],
            ['Service Date:', service_request.date.strftime('%B %d, %Y')],
        ]
        
        invoice_table = Table(invoice_data, colWidths=[2*inch, 3*inch])
        invoice_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(invoice_table)
        elements.append(Spacer(1, 20))
        
        # Customer information
        elements.append(Paragraph("<b>Customer Information</b>", styles['Heading3']))
        customer_data = [
            ['Name:', f"{customer.user.first_name} {customer.user.last_name}"],
            ['Email:', customer.user.email],
            ['Mobile:', customer.mobile],
            ['Address:', customer.address],
        ]
        
        customer_table = Table(customer_data, colWidths=[1.5*inch, 4*inch])
        customer_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(customer_table)
        elements.append(Spacer(1, 20))
        
        # Service details
        elements.append(Paragraph("<b>Service Details</b>", styles['Heading3']))
        service_data = [
            ['Vehicle Name:', service_request.vehicle_name],
            ['Vehicle Number:', str(service_request.vehicle_no)],
            ['Vehicle Brand:', service_request.vehicle_brand],
            ['Vehicle Model:', service_request.vehicle_model],
            ['Category:', service_request.category],
            ['Problem Description:', service_request.problem_description],
        ]
        
        service_table = Table(service_data, colWidths=[2*inch, 3.5*inch])
        service_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(service_table)
        elements.append(Spacer(1, 20))
        
        # Cost breakdown
        elements.append(Paragraph("<b>Cost Breakdown</b>", styles['Heading3']))
        cost_data = [
            ['Service Cost:', f"₹{service_request.cost}"],
            ['Total Amount:', f"₹{service_request.cost}"],
        ]
        
        cost_table = Table(cost_data, colWidths=[2*inch, 3.5*inch])
        cost_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 12),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('BACKGROUND', (0, 1), (1, 1), colors.lightgrey),
        ]))
        elements.append(cost_table)
        elements.append(Spacer(1, 30))
        
        # Terms and conditions
        elements.append(Paragraph("<b>Terms & Conditions</b>", styles['Heading3']))
        terms = [
            "• Payment is due upon receipt of this invoice",
            "• All services are guaranteed for 30 days",
            "• For any queries, please contact our support team",
            "• Thank you for choosing Fleet Care!"
        ]
        
        for term in terms:
            elements.append(Paragraph(term, normal_style))
        
        # Build the PDF
        doc.build(elements)
        buffer.seek(0)
        
        return buffer
        
    except Exception as e:
        print(f"Error generating PDF: {str(e)}")
        return None

def send_invoice_email(customer_email, customer_name, request_id, pdf_buffer):
    """
    Send invoice email with PDF attachment
    """
    try:
        print(f"🔍 Starting email send for request {request_id} to {customer_email}")
        
        # Check if email is properly configured
        if not settings.EMAIL_HOST_USER or settings.EMAIL_HOST_USER == 'from@gmail.com':
            print(f"❌ EMAIL_HOST_USER not configured: {settings.EMAIL_HOST_USER}")
            return False, "Email configuration not set up. Please configure EMAIL_HOST_USER in settings.py"
        
        if not settings.EMAIL_HOST_PASSWORD or settings.EMAIL_HOST_PASSWORD == 'xyz':
            print(f"❌ EMAIL_HOST_PASSWORD not configured: {settings.EMAIL_HOST_PASSWORD}")
            return False, "Email configuration not set up. Please configure EMAIL_HOST_PASSWORD in settings.py"
        
        # Check if the current password looks like a regular password (not an App Password)
        if len(settings.EMAIL_HOST_PASSWORD) < 16 or ' ' in settings.EMAIL_HOST_PASSWORD:
            print(f"❌ EMAIL_HOST_PASSWORD appears to be a regular password, not an App Password")
            return False, "Email configuration error: You need to use a Gmail App Password, not your regular password. Please check the settings.py file for instructions."
        
        print(f"✅ Email config looks good: {settings.EMAIL_HOST_USER}")
        
        subject = f"Fleet Care - Service Invoice #{request_id:06d}"
        
        # HTML email template
        html_message = render_to_string('vehicle/email/invoice_email.html', {
            'customer_name': customer_name,
            'request_id': request_id,
            'invoice_number': f'INV-{request_id:06d}',
            'date': datetime.now().strftime('%B %d, %Y'),
        })
        
        print(f"✅ HTML template rendered successfully")
        
        # Create email message
        email = EmailMessage(
            subject=subject,
            body=html_message,
            from_email=settings.EMAIL_HOST_USER,
            to=[customer_email]
        )
        
        # Attach PDF
        pdf_buffer.seek(0)
        email.attach(
            f'invoice_{request_id:06d}.pdf',
            pdf_buffer.read(),
            'application/pdf'
        )
        
        print(f"✅ PDF attached successfully")
        
        # Send email
        email.content_subtype = "html"
        print(f"🔍 Attempting to send email...")
        email.send()
        
        print(f"✅ Email sent successfully!")
        return True, "Email sent successfully"
        
    except Exception as e:
        print(f"❌ Error sending email: {str(e)}")
        print(f"❌ Error type: {type(e)}")
        
        # Provide specific error messages for common issues
        error_msg = str(e)
        if "Authentication" in error_msg or "Username and Password not accepted" in error_msg:
            return False, "Email authentication failed. Please check your Gmail App Password in settings.py. You need to enable 2-Factor Authentication and generate an App Password."
        elif "Less secure app access" in error_msg:
            return False, "Gmail blocked the login. You need to enable 2-Factor Authentication and use an App Password instead of your regular password."
        else:
            return False, f"Email sending failed: {error_msg}"

def generate_and_send_invoice(request_id):
    """
    Generate PDF invoice and send via email
    """
    try:
        # Generate PDF
        pdf_buffer = generate_invoice_pdf(request_id)
        if not pdf_buffer:
            return False, "Failed to generate PDF"
        
        # Get customer details
        service_request = Request.objects.get(id=request_id)
        customer_email = service_request.customer.user.email
        customer_name = f"{service_request.customer.user.first_name} {service_request.customer.user.last_name}"
        
        # Send email
        email_sent, email_status = send_invoice_email(customer_email, customer_name, request_id, pdf_buffer)
        
        if email_sent:
            return True, "Invoice generated and sent successfully"
        else:
            return False, f"Failed to send email: {email_status}"
            
    except Exception as e:
        return False, f"Error: {str(e)}" 

def generate_and_send_invoice_custom_email(request_id, recipient_email):
    """
    Generate PDF invoice and send via email to custom recipient
    """
    try:
        # Generate PDF
        pdf_buffer = generate_invoice_pdf(request_id)
        if not pdf_buffer:
            return False, "Failed to generate PDF"
        
        # Get customer details for the email content
        service_request = Request.objects.get(id=request_id)
        customer_name = f"{service_request.customer.user.first_name} {service_request.customer.user.last_name}"
        
        # Send email to custom recipient
        email_sent, email_status = send_invoice_email(recipient_email, customer_name, request_id, pdf_buffer)
        
        if email_sent:
            return True, "Invoice generated and sent successfully"
        else:
            return False, f"Failed to send email: {email_status}"
            
    except Exception as e:
        return False, f"Error: {str(e)}" 