import os
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from django.core.mail import EmailMessage
from django.conf import settings
from django.template.loader import render_to_string
from .models import Request, Customer
from datetime import datetime


def generate_invoice_pdf(request_id):
    try:
        service_request = Request.objects.get(id=request_id)
        customer = service_request.customer

        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        elements = []
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle('CustomTitle', parent=styles['Heading1'], fontSize=24, spaceAfter=30, alignment=TA_CENTER, textColor=colors.darkblue)
        subtitle_style = ParagraphStyle('CustomSubtitle', parent=styles['Heading2'], fontSize=16, spaceAfter=20, alignment=TA_CENTER, textColor=colors.darkblue)

        elements.append(Paragraph("FLEET CARE", title_style))
        elements.append(Paragraph("Professional Vehicle Services", subtitle_style))
        elements.append(Spacer(1, 20))
        elements.append(Paragraph("<b>INVOICE</b>", styles['Heading2']))
        elements.append(Spacer(1, 10))

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

        elements.append(Paragraph("<b>Cost Breakdown</b>", styles['Heading3']))
        # FIX: handle null cost gracefully
        cost_value = service_request.cost or 0
        cost_data = [
            ['Service Cost:', f'\u20b9{cost_value}'],
            ['Total Amount:', f'\u20b9{cost_value}'],
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

        elements.append(Paragraph("<b>Terms & Conditions</b>", styles['Heading3']))
        for term in [
            "• Payment is due upon receipt of this invoice",
            "• All services are guaranteed for 30 days",
            "• For queries, please contact our support team",
            "• Thank you for choosing Fleet Care!",
        ]:
            elements.append(Paragraph(term, styles['Normal']))

        doc.build(elements)
        buffer.seek(0)
        return buffer

    except Exception as e:
        print(f"Error generating PDF: {str(e)}")
        return None


def send_invoice_email(customer_email, customer_name, request_id, pdf_buffer):
    try:
        if not settings.EMAIL_HOST_USER:
            return False, "EMAIL_HOST_USER not configured in settings."
        if not settings.EMAIL_HOST_PASSWORD:
            return False, "EMAIL_HOST_PASSWORD not configured in settings."

        subject = f"Fleet Care - Service Invoice #{request_id:06d}"

        # FIX: correct template path — file is at templates/vehicle/invoice_email.html
        html_message = render_to_string('vehicle/invoice_email.html', {
            'customer_name': customer_name,
            'request_id': request_id,
            'invoice_number': f'INV-{request_id:06d}',
            'date': datetime.now().strftime('%B %d, %Y'),
        })

        email = EmailMessage(
            subject=subject,
            body=html_message,
            from_email=settings.EMAIL_HOST_USER,
            to=[customer_email]
        )
        pdf_buffer.seek(0)
        email.attach(f'invoice_{request_id:06d}.pdf', pdf_buffer.read(), 'application/pdf')
        email.content_subtype = "html"
        email.send()
        return True, "Email sent successfully"

    except Exception as e:
        error_msg = str(e)
        if "Authentication" in error_msg or "Username and Password not accepted" in error_msg:
            return False, "Email authentication failed. Check your Gmail App Password in settings."
        return False, f"Email sending failed: {error_msg}"


def generate_and_send_invoice(request_id):
    try:
        pdf_buffer = generate_invoice_pdf(request_id)
        if not pdf_buffer:
            return False, "Failed to generate PDF"
        service_request = Request.objects.get(id=request_id)
        customer_email = service_request.customer.user.email
        customer_name = f"{service_request.customer.user.first_name} {service_request.customer.user.last_name}"
        return send_invoice_email(customer_email, customer_name, request_id, pdf_buffer)
    except Exception as e:
        return False, f"Error: {str(e)}"


def generate_and_send_invoice_custom_email(request_id, recipient_email):
    try:
        pdf_buffer = generate_invoice_pdf(request_id)
        if not pdf_buffer:
            return False, "Failed to generate PDF"
        service_request = Request.objects.get(id=request_id)
        customer_name = f"{service_request.customer.user.first_name} {service_request.customer.user.last_name}"
        return send_invoice_email(recipient_email, customer_name, request_id, pdf_buffer)
    except Exception as e:
        return False, f"Error: {str(e)}"