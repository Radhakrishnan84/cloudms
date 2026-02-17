from django.core.mail import EmailMessage
from django.conf import settings


def send_invoice_email(user, invoice_pdf, order_id):
    subject = "CloudSync – Payment Successful & Invoice"
    body = f"""
Hello {user.first_name or user.username},

Thank you for subscribing to CloudSync 🎉

Your payment was successful.
Order ID: {order_id}

Please find your invoice attached as a PDF.

Regards,
CloudSync Team
"""

    email = EmailMessage(
        subject=subject,
        body=body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[user.email],
    )

    email.attach(
        filename=f"CloudSync_Invoice_{order_id}.pdf",
        content=invoice_pdf.getvalue(),
        mimetype="application/pdf"
    )

    email.send(fail_silently=False)
