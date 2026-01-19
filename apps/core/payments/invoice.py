from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from io import BytesIO
from datetime import datetime

def generate_invoice_pdf(user, plan, payment_id, amount):
    """
    Generates invoice PDF and returns bytes.
    """

    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)

    # Header
    c.setFont("Helvetica-Bold", 20)
    c.drawString(50, 750, "CloudSync Invoice")

    # Sub-header
    c.setFont("Helvetica", 12)
    c.drawString(50, 720, f"Invoice Date: {datetime.now().strftime('%d %b %Y')}")
    c.drawString(50, 700, f"Invoice To: {user.first_name} {user.last_name}")
    c.drawString(50, 680, f"Email: {user.email}")

    # Payment details
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, 640, "Payment Details")

    c.setFont("Helvetica", 12)
    c.drawString(50, 620, f"Plan: {plan.name}")
    c.drawString(50, 600, f"Storage: {plan.storage_limit} GB")
    c.drawString(50, 580, f"Price: ₹{amount}")
    c.drawString(50, 560, f"Razorpay Payment ID: {payment_id}")

    # Footer
    c.setFont("Helvetica-Oblique", 10)
    c.drawString(50, 520, "Thank you for choosing CloudSync!")

    c.showPage()
    c.save()

    buffer.seek(0)
    return buffer.getvalue()
