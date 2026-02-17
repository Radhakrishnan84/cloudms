from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor, black, grey
from reportlab.lib.units import cm
from io import BytesIO
from datetime import datetime


PRIMARY = HexColor("#4f46e5")   # CloudSync Purple
LIGHT_GRAY = HexColor("#f3f4f6")


def generate_invoice_pdf(user, order_id, payment_id, plan, amount):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # ==============================
    # HEADER BAR
    # ==============================
    c.setFillColor(PRIMARY)
    c.rect(0, height - 90, width, 90, fill=1)

    c.setFillColor("white")
    c.setFont("Helvetica-Bold", 22)
    c.drawString(40, height - 55, "CloudSync")

    c.setFont("Helvetica", 11)
    c.drawString(40, height - 75, "Secure Cloud Storage Platform")

    # ==============================
    # INVOICE META
    # ==============================
    c.setFillColor(black)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(40, height - 120, "INVOICE")

    c.setFont("Helvetica", 10)
    c.drawRightString(width - 40, height - 120, f"Invoice #: {order_id}")
    c.drawRightString(width - 40, height - 135, f"Payment ID: {payment_id}")
    c.drawRightString(
        width - 40,
        height - 150,
        f"Date: {datetime.now().strftime('%d %b %Y')}"
    )

    # ==============================
    # BILL TO BOX
    # ==============================
    c.setFillColor(LIGHT_GRAY)
    c.rect(40, height - 230, width - 80, 70, fill=1, stroke=0)

    c.setFillColor(black)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(55, height - 190, "Billed To")

    c.setFont("Helvetica", 10)
    c.drawString(55, height - 205, user.get_full_name() or user.username)
    c.drawString(55, height - 220, user.email)

    # ==============================
    # TABLE HEADER
    # ==============================
    table_y = height - 280

    c.setFillColor(PRIMARY)
    c.rect(40, table_y, width - 80, 30, fill=1)

    c.setFillColor("white")
    c.setFont("Helvetica-Bold", 10)
    c.drawString(55, table_y + 10, "Description")
    c.drawString(300, table_y + 10, "Plan")
    c.drawRightString(width - 55, table_y + 10, "Amount")

    # ==============================
    # TABLE ROW
    # ==============================
    row_y = table_y - 35

    c.setFillColor(black)
    c.setFont("Helvetica", 10)
    c.drawString(55, row_y, "Cloud Storage Subscription")
    c.drawString(300, row_y, plan.upper())
    c.drawRightString(width - 55, row_y, f"₹ {amount}")

    # Divider
    c.setStrokeColor(grey)
    c.line(40, row_y - 15, width - 40, row_y - 15)

    # ==============================
    # TOTAL BOX
    # ==============================
    total_y = row_y - 60

    c.setFont("Helvetica-Bold", 12)
    c.drawRightString(width - 150, total_y, "Total Paid")
    c.setFillColor(PRIMARY)
    c.drawRightString(width - 55, total_y, f"₹ {amount}")

    # ==============================
    # PAYMENT STATUS
    # ==============================
    c.setFillColor(LIGHT_GRAY)
    c.rect(40, total_y - 50, width - 80, 40, fill=1, stroke=0)

    c.setFillColor(black)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(55, total_y - 25, "Payment Status:")
    c.setFillColor(HexColor("#16a34a"))
    c.drawString(160, total_y - 25, "PAID")

    # ==============================
    # FOOTER
    # ==============================
    c.setFillColor(grey)
    c.setFont("Helvetica", 9)
    c.drawCentredString(
        width / 2,
        60,
        "Thank you for choosing CloudSync"
    )

    c.drawCentredString(
        width / 2,
        45,
        "This is a system generated invoice and does not require signature."
    )

    c.drawCentredString(
        width / 2,
        30,
        "support@cloudsync.com | www.cloudsync.com"
    )

    c.showPage()
    c.save()

    buffer.seek(0)
    return buffer
