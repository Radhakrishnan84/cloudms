from django.shortcuts import render, redirect,get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import user_passes_test
from django.contrib import messages
from apps.core.models import File, Subscription, ActivityLog, Notification, Server
import os
import matplotlib
matplotlib.use('Agg')  # Required for Django
import matplotlib.pyplot as plt
from django.contrib.auth.decorators import login_required
from django.utils.timezone import now
from datetime import timedelta
from django.conf import settings
import base64
from io import BytesIO
import matplotlib.pyplot as plt
from django.db.models import Count, Sum
from django.utils import timezone
from django.contrib.auth.models import User
from django.core.paginator import Paginator
import csv
from django.http import HttpResponse
import io
import base64
import csv
import json
from datetime import datetime
from django.http import HttpResponse, FileResponse, JsonResponse, HttpResponseBadRequest
from django.shortcuts import render
from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.csrf import csrf_exempt
from django.utils.encoding import smart_str
from django.contrib import messages

# Attempt to import PDF libs; provide friendly error if missing
try:
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.pdfgen import canvas
    from reportlab.lib.utils import ImageReader
    from PIL import Image
except Exception as e:
    # We'll still allow the view to load, but PDF export will return an error
    reportlab = None
    Image = None


def generate_chart():
    buffer = BytesIO()
    plt.savefig(buffer, format='png', bbox_inches='tight')
    buffer.seek(0)
    encoded = base64.b64encode(buffer.getvalue()).decode('utf-8')
    plt.close()
    return encoded

def admin_only(view_func):
    return user_passes_test(lambda u: u.is_staff, login_url="login_admin")(view_func)

def login_admin_view(request):
    if request.method == "POST":
        username = request.POST.get("username").strip()
        password = request.POST.get("password").strip()

        user = authenticate(request, username=username, password=password)

        if user is None:
            messages.error(request, "Invalid admin credentials.")
            return redirect("login_admin")

        if not user.is_staff:
            messages.error(request, "Access restricted: Admins only.")
            return redirect("login_admin")

        login(request, user)
        return redirect("admin_dashboard")

    return render(request, "auth/login_admin.html")

# ===============================
#  ADMIN DASHBOARD VIEW (Matplotlib)
# ===============================
@admin_only
def admin_dashboard(request):

    # ------------------------
    # TOP COUNTS
    # ------------------------
    total_users = User.objects.filter(is_staff=False).count()
    total_files = File.objects.count()

    storage_used = File.objects.aggregate(total=Sum("size"))["total"] or 0
    storage_used_tb = round(storage_used / 1024, 2)

    active_servers = 8  # mock (later dynamic)

    # -----------------------------------
    # USER ACTIVITY → LAST 7 DAYS
    # -----------------------------------
    last_7_days = timezone.now() - timedelta(days=7)

    daily_data = (
        File.objects.filter(uploaded_at__gte=last_7_days)
        .extra({'day': "date(uploaded_at)"})
        .values("day")
        .annotate(count=Count("id"))
        .order_by("day")
    )

    activity_labels = [str(d["day"]) for d in daily_data]
    activity_values = [d["count"] for d in daily_data]

    # Create Matplotlib Line Chart
    plt.figure(figsize=(6, 3))
    plt.plot(activity_labels, activity_values, marker='o', color='#7A5CFF')
    plt.fill_between(activity_labels, activity_values, color='#7A5CFF', alpha=0.2)
    plt.title("User Activity (Last 7 Days)")
    plt.ylabel("Uploads")
    plt.grid(alpha=0.2)

    user_activity_chart = generate_chart()

    # -----------------------------------
    # PLAN DISTRIBUTION DONUT
    # -----------------------------------
    plan_data = (
        Subscription.objects.values("plan")
        .annotate(count=Count("id"))
        .order_by("plan")
    )

    plan_labels = [d["plan"] for d in plan_data]
    plan_counts = [d["count"] for d in plan_data]

    # Donut chart
    plt.figure(figsize=(6, 3))
    wedges, texts, autotexts = plt.pie(plan_counts, labels=plan_labels, autopct='%1.1f%%')
    centre_circle = plt.Circle((0, 0), 0.65, fc='white')
    fig = plt.gcf()
    fig.gca().add_artist(centre_circle)
    plt.title("Plan Distribution")

    plan_distribution_chart = generate_chart()

    # -----------------------------------
    # STORAGE GROWTH – LAST 12 MONTHS
    # -----------------------------------
    growth_labels = []
    growth_values = []

    for i in range(11, -1, -1):
        month = timezone.now() - timedelta(days=i * 30)

        used = (
            File.objects.filter(uploaded_at__lte=month)
            .aggregate(total=Sum("size"))["total"]
        ) or 0

        growth_labels.append(month.strftime("%b"))
        growth_values.append(round(used / 1024, 2))  # Convert MB → TB approx

    plt.figure(figsize=(7, 3))
    plt.bar(growth_labels, growth_values, color="#6A5CFF")
    plt.title("Storage Growth (Last 12 Months)")
    plt.ylabel("TB Used")
    plt.grid(alpha=0.2)

    storage_growth_chart = generate_chart()

    # -----------------------------------
    # RECENT ACTIVITY
    # -----------------------------------
    recent_activity = ActivityLog.objects.order_by("-timestamp")[:8]

    # -----------------------------------
    # CONTEXT → TEMPLATE
    # -----------------------------------
    context = {
        # Top Stats
        "total_users": total_users,
        "total_files": total_files,
        "storage_used": storage_used_tb,
        "active_servers": active_servers,

        # Charts
        "user_activity_chart": user_activity_chart,
        "plan_distribution_chart": plan_distribution_chart,
        "storage_growth_chart": storage_growth_chart,

        # Logs
        "recent_activity": recent_activity,
    }

    notifications = Notification.objects.filter(user=request.user, is_read=False).order_by('-created_at')


    return render(request, "adminpanel/dashboard.html", context)


@admin_only
def admin_users(request):
    users_list = []

    for u in User.objects.all():

        # Subscription
        sub = Subscription.objects.filter(user=u).first()
        plan = sub.plan if sub else "Free"
        storage_limit = sub.storage_limit if sub else 5

        # Storage used
        files = File.objects.filter(user=u)
        used_storage = round(sum(f.size for f in files), 2)

        users_list.append({
            "id": u.id,
            "first_name": u.first_name,
            "last_name": u.last_name,
            "email": u.email,
            "plan": plan,
            "storage_limit": storage_limit,
            "used_storage": used_storage,
            "status": "Active" if u.is_active else "Suspended",
            "date_joined": u.date_joined,
            "profile": u.profile if hasattr(u, "profile") else None
        })

    paginator = Paginator(users_list, 8)
    page = request.GET.get("page")
    users = paginator.get_page(page)

    return render(request, "adminpanel/users.html", {
        "users": users
    })

@admin_only
def admin_user_view(request, user_id):
    user_obj = User.objects.get(id=user_id)

    return render(request, "adminpanel/users/view_user.html", {
        "u": user_obj
    })

@admin_only
def admin_add_user(request):
    if request.method == "POST":
        first = request.POST.get("first_name")
        last = request.POST.get("last_name")
        email = request.POST.get("email").lower()
        password = request.POST.get("password")
        plan = request.POST.get("plan")

        if User.objects.filter(email=email).exists():
            messages.error(request, "Email already exists.")
            return redirect("admin_add_user")

        user = User.objects.create_user(
            username=email, 
            email=email,
            first_name=first,
            last_name=last,
            password=password
        )

        # Create subscription
        Subscription.objects.create(
            user=user,
            plan=plan,
            storage_limit=50 if plan == "Free" else 
                           200 if plan == "Basic" else 
                           500 if plan == "Pro" else 2000
        )

        messages.success(request, "User created successfully.")
        return redirect("admin_users")

    return render(request, "adminpanel/users/add_user.html")
@admin_only
def admin_user_edit(request, user_id):
    u = User.objects.get(id=user_id)
    sub = Subscription.objects.filter(user=u).first()

    if request.method == "POST":
        u.first_name = request.POST["first_name"]
        u.last_name = request.POST["last_name"]
        u.email = request.POST["email"]

        u.username = u.email
        u.save()

        if sub:
            sub.plan = request.POST["plan"]
            sub.save()

        messages.success(request, "User updated successfully!")
        return redirect("admin_users")

    return render(request, "adminpanel/users/edit_user.html", {
        "u": u,
        "sub": sub
    })


@admin_only
def admin_user_suspend(request, user_id):
    u = User.objects.get(id=user_id)
    u.is_active = False
    u.save()

    messages.info(request, "User has been suspended.")
    return redirect("admin_users")

@admin_only
def admin_user_activate(request, user_id):
    u = User.objects.get(id=user_id)
    u.is_active = True
    u.save()

    messages.success(request, "User activated.")
    return redirect("admin_users")

@admin_only
def admin_user_delete(request, user_id):
    u = User.objects.get(id=user_id)
    u.delete()
    messages.warning(request, "User deleted permanently.")
    return redirect("admin_users")


@admin_only
def admin_export_users(request):
    users = User.objects.all()

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = "attachment; filename=cloudsync_users.csv"

    writer = csv.writer(response)
    writer.writerow(["First Name", "Last Name", "Email", "Plan", "Storage Used", "Joined"])

    for u in users:
        sub = Subscription.objects.filter(user=u).first()
        plan = sub.plan if sub else "Free"
        used = u.profile.used_storage if hasattr(u, "profile") else 0

        writer.writerow([u.first_name, u.last_name, u.email, plan, used, u.date_joined])

    return response



@admin_only
def admin_subscriptions(request):
    subs = Subscription.objects.select_related("user")
    return render(request, "adminpanel/subscriptions.html", {"subs": subs})

# apps/adminpanel/views.py

from django.contrib.auth.decorators import login_required, user_passes_test
from apps.core.models import File

def is_admin(user):
    return user.is_staff

@login_required
@user_passes_test(is_admin)
def admin_files_view(request):
    files = (
        File.objects
        .select_related("user")
        .filter(is_deleted=False)
        .order_by("-uploaded_at")
    )

    return render(request, "adminpanel/files.html", {
        "files": files
    })


@admin_only
def admin_add_file(request):
    if request.method == "POST":
        uploaded = request.FILES["file"]
        name = uploaded.name

        File.objects.create(
            user=request.user,
            file=uploaded,
            name=name,
            file_type=name.split(".")[-1],
            size_mb=uploaded.size / (1024 * 1024),
            category="document",
        )

        return redirect("admin_files")

    return render(request, "adminpanel/files/add_file.html")

@admin_only
def admin_export_files(request):
    """Exports all files into a CSV download."""

    # Create HTTP Response with CSV headers
    response = HttpResponse(
        content_type='text/csv',
        headers={'Content-Disposition': 'attachment; filename="cloudsync_files_export.csv"'},
    )

    writer = csv.writer(response)
    
    # CSV Header Row
    writer.writerow([
        "File Name",
        "Type",
        "Size (MB)",
        "Owner",
        "Uploaded At",
        "Category",
    ])

    # Query all files
    files = File.objects.all().order_by('-uploaded_at')

    # Write file data
    for f in files:
        writer.writerow([
            f.name,
            f.file_type,
            f.size_mb,
            f.user.email,
            timezone.localtime(f.uploaded_at).strftime("%Y-%m-%d %I:%M %p"),
            f.category,
        ])

    return response

@admin_only
def admin_servers(request):
    servers = Server.objects.all().order_by('id')
    return render(request, "adminpanel/servers.html", {"servers": servers})


# --------------------------
# ADD SERVER
# --------------------------
@admin_only
def admin_add_server(request):
    if request.method == "POST":
        Server.objects.create(
            name=request.POST['name'],
            location=request.POST['location'],
            cpu=request.POST['cpu'],
            memory=request.POST['memory'],
            storage=request.POST['storage'],
            uptime=request.POST['uptime'],
            status=request.POST['status'],
            color=request.POST['color'],
        )
        return redirect("admin_servers")

    return render(request, "adminpanel/servers/add_server.html")


# --------------------------
# VIEW SERVER
# --------------------------
@admin_only
def admin_view_server(request, server_id):
    server = get_object_or_404(Server, id=server_id)
    return render(request, "adminpanel/servers/view_server.html", {"server": server})


# --------------------------
# EDIT SERVER
# --------------------------
@admin_only
def admin_edit_server(request, server_id):
    server = get_object_or_404(Server, id=server_id)

    if request.method == "POST":
        server.name = request.POST['name']
        server.location = request.POST['location']
        server.cpu = request.POST['cpu']
        server.memory = request.POST['memory']
        server.storage = request.POST['storage']
        server.uptime = request.POST['uptime']
        server.status = request.POST['status']
        server.color = request.POST['color']
        server.save()

        return redirect("admin_servers")

    return render(request, "adminpanel/servers/edit_server.html", {"server": server})


@staff_member_required
def admin_reports_view(request):
    """
    Render the reports page. In real app replace the sample lists below with real DB queries.
    """
    # Example monthly labels and values (match your screenshot layout)
    perf_labels = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug"]
    perf_values = [50000, 60000, 75000, 90000, 120000, 150000, 180000, 230000]

    # Weekly example
    week_labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    week_uploads = [2000, 2100, 3600, 2400, 2200, 3700, 2900]
    week_downloads = [1500, 2400, 2700, 3000, 3900, 4200, 4800]

    context = {
        "perf_labels": json.dumps(perf_labels),
        "perf_values": json.dumps(perf_values),
        "week_labels": json.dumps(week_labels),
        "week_uploads": json.dumps(week_uploads),
        "week_downloads": json.dumps(week_downloads),
    }
    return render(request, "adminpanel/reports.html", context)


@staff_member_required
def admin_reports_export_csv(request):
    """
    Return a CSV file for the reports.
    Uses the same test data as the view above — replace with real queries.
    """
    perf_labels = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug"]
    perf_values = [50000, 60000, 75000, 90000, 120000, 150000, 180000, 230000]

    # Create CSV in memory
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["Month", "Users"])
    for m, v in zip(perf_labels, perf_values):
        writer.writerow([m, v])

    buffer.seek(0)
    resp = HttpResponse(buffer.getvalue(), content_type="text/csv")
    resp['Content-Disposition'] = 'attachment; filename="performance_report.csv"'
    return resp


@csrf_exempt  # JS sends JSON; we use X-CSRFToken header; @csrf_exempt is used to allow token checks — staff_member_required still applies below
@staff_member_required
def admin_reports_export_pdf(request):
    """
    Accepts JSON POST with base64 images and returns a PDF file embedding them.
    Expected POST JSON:
      {
        "title":"Reports & Analytics",
        "perf_image":"data:image/png;base64,...",
        "week_image":"data:image/png;base64,...",
        "meta": { ... }
      }
    """
    if request.method != "POST":
        return HttpResponseBadRequest("Only POST allowed")

    if 'reportlab' not in globals() or Image is None:
        return HttpResponseBadRequest("PDF generation libraries not installed. Install reportlab and pillow.")

    try:
        payload = json.loads(request.body.decode('utf-8'))
    except Exception as e:
        return HttpResponseBadRequest("Invalid JSON payload: " + str(e))

    perf_b64 = payload.get("perf_image")
    week_b64 = payload.get("week_image")
    title = payload.get("title", "Reports")
    meta = payload.get("meta", {})

    # Helper to extract bytes from dataURL
    def _from_data_url(data_url):
        if not data_url:
            return None
        if "," in data_url:
            header, b64 = data_url.split(",", 1)
        else:
            b64 = data_url
        return base64.b64decode(b64)

    perf_bytes = _from_data_url(perf_b64)
    week_bytes = _from_data_url(week_b64)

    # Create PDF
    out = io.BytesIO()
    # Portrait A4
    page_w, page_h = A4  # A4 in points (595x842)
    pdf = canvas.Canvas(out, pagesize=A4)

    # Title
    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawString(40, page_h - 50, title)
    pdf.setFont("Helvetica", 10)
    pdf.drawString(40, page_h - 68, "Generated: " + meta.get("generated_at", datetime.utcnow().isoformat()))

    y_cursor = page_h - 100

    # Add perf image (scale to width-with-margin)
    if perf_bytes:
        try:
            pil = Image.open(io.BytesIO(perf_bytes)).convert("RGB")
            # compute width to fit leaving margins
            max_w = page_w - 80
            aspect = pil.height / pil.width
            new_w = max_w
            new_h = new_w * aspect
            img_reader = ImageReader(pil)
            pdf.drawImage(img_reader, 40, y_cursor - new_h, width=new_w, height=new_h)
            y_cursor = y_cursor - new_h - 30
        except Exception as e:
            # skip image on failure
            pdf.setFont("Helvetica-Oblique", 10)
            pdf.drawString(40, y_cursor, "Error embedding performance image: " + str(e))
            y_cursor -= 20

    # Add weekly chart on same page if there's space, otherwise new page
    if week_bytes:
        try:
            pil2 = Image.open(io.BytesIO(week_bytes)).convert("RGB")
            max_w = page_w - 80
            aspect2 = pil2.height / pil2.width
            new_w2 = max_w
            new_h2 = new_w2 * aspect2

            if y_cursor - new_h2 < 80:
                pdf.showPage()
                y_cursor = page_h - 80
            pdf.drawImage(ImageReader(pil2), 40, y_cursor - new_h2, width=new_w2, height=new_h2)
            y_cursor = y_cursor - new_h2 - 20
        except Exception as e:
            pdf.setFont("Helvetica-Oblique", 10)
            pdf.drawString(40, y_cursor, "Error embedding weekly image: " + str(e))
            y_cursor -= 16

    # Footer and finish
    pdf.setFont("Helvetica", 8)
    pdf.drawString(40, 18, "CloudSync Reports - Generated by admin: %s" % request.user.get_username())
    pdf.showPage()
    pdf.save()
    out.seek(0)

    return FileResponse(out, as_attachment=True, filename="reports.pdf")


def admin_settings(request):
    context = {
        "platform": {
            "name": "CloudSync",
            "support_email": "support@cloudsync.com",
            "max_file_size": 100
        },
        "plans": {
            "free": 5,
            "basic": 10,
            "pro": 100,
            "enterprise": 2
        },
        "features": {
            "file_sharing": True,
            "public_links": True,
            "versioning": False,
            "registration": True
        },
        "security": {
            "two_factor": False,
            "password_complexity": False,
            "session_timeout": 30
        },
        "maintenance": {
            "enabled": False,
            "message": ""
        }
    }
    return render(request, "adminpanel/settings.html", context)


# Temporary in-memory storage (replace with DB later)
SETTINGS_DATA = {
    "platform": {
        "name": "CloudSync",
        "support_email": "support@cloudsync.com",
        "max_file_size": 100,
    },
    "plans": {
        "free": 5,
        "basic": 10,
        "pro": 100,
        "enterprise": 2,
    },
    "features": {
        "file_sharing": True,
        "public_links": True,
        "versioning": False,
        "registration": True,
    },
    "security": {
        "two_factor": False,
        "password_complexity": False,
        "session_timeout": 30,
    },
    "maintenance": {
        "enabled": False,
        "message": "",
    }
}


# ============================
# MAIN SETTINGS PAGE
# ============================
def admin_settings(request):
    return render(request, "adminpanel/settings.html", SETTINGS_DATA)


# ============================
# UPDATE PLATFORM SETTINGS
# ============================
def admin_update_platform(request):
    if request.method == "POST":
        SETTINGS_DATA["platform"]["name"] = request.POST.get("platform_name", "")
        SETTINGS_DATA["platform"]["support_email"] = request.POST.get("support_email", "")
        SETTINGS_DATA["platform"]["max_file_size"] = int(request.POST.get("max_file_size", 100))

        messages.success(request, "Platform settings updated successfully!")
    return redirect("admin_settings")


# ============================
# UPDATE STORAGE LIMITS
# ============================
def admin_update_storage_limits(request):
    if request.method == "POST":
        SETTINGS_DATA["plans"]["free"] = int(request.POST.get("free", 5))
        SETTINGS_DATA["plans"]["basic"] = int(request.POST.get("basic", 10))
        SETTINGS_DATA["plans"]["pro"] = int(request.POST.get("pro", 100))
        SETTINGS_DATA["plans"]["enterprise"] = int(request.POST.get("enterprise", 2))

        messages.success(request, "Storage plan limits updated successfully!")
    return redirect("admin_settings")


# ============================
# UPDATE FEATURE TOGGLES
# ============================
def admin_update_features(request):
    if request.method == "POST":
        SETTINGS_DATA["features"]["file_sharing"] = "file_sharing" in request.POST
        SETTINGS_DATA["features"]["public_links"] = "public_links" in request.POST
        SETTINGS_DATA["features"]["versioning"] = "versioning" in request.POST
        SETTINGS_DATA["features"]["registration"] = "registration" in request.POST

        messages.success(request, "Feature toggles updated successfully!")
    return redirect("admin_settings")


# ============================
# UPDATE SECURITY SETTINGS
# ============================
def admin_update_security(request):
    if request.method == "POST":
        SETTINGS_DATA["security"]["two_factor"] = "two_factor" in request.POST
        SETTINGS_DATA["security"]["password_complexity"] = "password_complexity" in request.POST
        SETTINGS_DATA["security"]["session_timeout"] = int(request.POST.get("session_timeout", 30))

        messages.success(request, "Security settings updated!")
    return redirect("admin_settings")


# ============================
# UPDATE MAINTENANCE MODE
# ============================
def admin_update_maintenance(request):
    if request.method == "POST":
        SETTINGS_DATA["maintenance"]["enabled"] = "maintenance" in request.POST
        SETTINGS_DATA["maintenance"]["message"] = request.POST.get("message", "")

        messages.success(request, "Maintenance settings updated!")
    return redirect("admin_settings")



def logout_admin(request):
    logout(request)
    return redirect("login_admin")
