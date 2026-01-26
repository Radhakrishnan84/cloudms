from django.shortcuts import render, redirect, get_object_or_404
from django.conf import settings
from django.contrib.auth.decorators import login_required
import razorpay
from .models import PricingPlan
from django.contrib.auth.models import User
from django.contrib.auth import login, authenticate
from django.contrib import messages
from django.http import HttpResponse
from .models import File
from apps.core.utils.helpers import detect_category, file_size_in_mb
from django.db import IntegrityError
from .models import Subscription, Plan
from django.utils import timezone
from datetime import timedelta
from apps.core.utils.payments import razorpay_client
from django.http import JsonResponse
from .models import File, Subscription, Folder, SharedFile, Profile, ActivityLog
from django.core.files.storage import default_storage
from django.core.paginator import Paginator
from django.db.models import Q
from django.views.decorators.csrf import csrf_exempt
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from reportlab.pdfgen import canvas
import io
from django.http import FileResponse
from django.contrib.auth import logout

def home_view(request):
    return render(request, 'core/home.html')


def login_view(request):
    if request.method == "POST":
        return handle_login(request)
    return render(request, "auth/login_user.html")



def handle_login(request):
    login_type = request.POST.get("login_type", "user")
    email = request.POST.get("email")
    password = request.POST.get("password")
    remember = request.POST.get("rememberMe")

    if not email or not password:
        messages.error(request, "Email and password are required.")
        return redirect("login" if login_type == "user" else "admin_login")

    email = email.strip().lower()
    user = authenticate(request, username=email, password=password)

    if user is None:
        messages.error(request, "Invalid email or password.")
        return redirect("login" if login_type == "user" else "admin_login")

    # Admin validation
    if login_type == "admin" and not user.is_staff:
        messages.error(request, "Admin access denied.")
        return redirect("admin_login")

    login(request, user)

    # Remember me feature
    if remember:
        request.session.set_expiry(1209600)
    else:
        request.session.set_expiry(0)

    # Redirect based on login type
    if login_type == "admin":
        return redirect("admin_dashboard")
    return redirect("dashboard")


def signup_view(request):

    if request.method == "POST":
        full_name = request.POST.get("username").strip()
        email = request.POST.get("email").strip().lower()
        p1 = request.POST.get("password1")
        p2 = request.POST.get("password2")

        # Empty field check
        if not full_name or not email or not p1 or not p2:
            messages.error(request, "All fields are required.")
            return redirect("signup")

        # Password match check
        if p1 != p2:
            messages.error(request, "Passwords do not match.")
            return redirect("signup")

        # Existing user check
        if User.objects.filter(username=email).exists():
            messages.error(request, "An account with this email already exists.")
            return redirect("signup")

        # Split name properly
        parts = full_name.split()
        first_name = parts[0]
        last_name = " ".join(parts[1:]) if len(parts) > 1 else ""

        # Create user account
        user = User.objects.create_user(
            username=email,
            email=email,
            password=p1,
            first_name=first_name,
            last_name=last_name
        )

        # Auto-login
        login(request, user)

        messages.success(request, "Account created successfully!")
        return redirect("dashboard")

    return render(request, "auth/signup.html")



# subscription 
def activate_subscription(user, plan_name):
    plan = Plan.objects.get(name=plan_name)

    Subscription.objects.update_or_create(
        user=user,
        defaults={
            "plan": plan.name,
            "storage_limit": plan.storage_limit,
            "start_date": timezone.now(),
            "end_date": timezone.now() + timedelta(days=30)  # monthly
        }
    )
@login_required
def payment_success(request):
    plan_name = request.GET.get("plan")
    activate_subscription(request.user, plan_name)
    return redirect("dashboard")

# dashboard

@login_required
def dashboard_view(request):
    user = request.user

    # -----------------------------
    # 1. Subscription (optional)
    # -----------------------------
    try:
        sub = Subscription.objects.get(user=user)
    except Subscription.DoesNotExist:
        sub = None  # dashboard still loads

    # -----------------------------
    # 2. Files & Storage Calculation
    # -----------------------------
    files = File.objects.filter(user=user)
    storage_used = round(sum(f.size for f in files), 2)

    # If subscription exists → use its storage limit
    if sub:
        storage_total = sub.storage_limit
    else:
        storage_total = 0  # show 0 GB if no plan

    # Prevent zero-division
    if storage_total > 0:
        storage_percent = int((storage_used / storage_total) * 100)
    else:
        storage_percent = 0

    storage_full = sub and storage_used >= storage_total

    # -----------------------------
    # 3. Prepare dashboard data
    # -----------------------------
    context = {
        "sub": sub,
        "storage_used": storage_used,
        "storage_total": storage_total,
        "storage_percent": storage_percent,
        "storage_full": storage_full,
        "recent_files": files.order_by("-uploaded_at")[:6],
    }

    return render(request, "core/dashboard/dashboard.html", context)



# ---------------------------------------------------------
# Storage Calculation (used by all pages)
# ---------------------------------------------------------
def calculate_storage(user):
    try:
        sub = Subscription.objects.get(user=user)
    except Subscription.DoesNotExist:
        return None, 0, 0, 0, False

    files = File.objects.filter(user=user)
    storage_used = round(sum(f.size for f in files), 2)  # MB or GB based on your units
    storage_total = sub.storage_limit
    storage_percent = int((storage_used / storage_total) * 100) if storage_total > 0 else 0
    storage_full = storage_used >= storage_total

    return sub, storage_used, storage_total, storage_percent, storage_full


# ---------------------------------------------------------
# UPLOAD PAGE
# ---------------------------------------------------------
@login_required
def upload(request):
    user = request.user

    # subscription check
    try:
        sub = Subscription.objects.get(user=user)
    except Subscription.DoesNotExist:
        return redirect("no_subscription")

    if not sub.is_active():
        return redirect("subscription_expired")

    # ------------- File Upload POST --------------
    if request.method == "POST":
        file = request.FILES.get("file")
        folder_id = request.POST.get("folder")

        if not file:
            return JsonResponse({"error": "No file uploaded"}, status=400)

        # check storage limit
        size_mb = round(file.size / (1024 * 1024), 2)
        _, used, total, _, _ = calculate_storage(user)

        if used + size_mb > total:
            return JsonResponse({"error": "Storage limit reached! Upgrade your plan."}, status=403)

        # folder
        folder = Folder.objects.get(id=folder_id, user=user) if folder_id else None

        File.objects.create(
            user=user,
            file=file,
            name=file.name,
            size=size_mb,
            folder=folder
        )

        return JsonResponse({"success": True})

    # ---------------- STORAGE INFO ----------------
    sub, storage_used, storage_total, storage_percent, storage_full = calculate_storage(user)

    folders = Folder.objects.filter(user=user)

    context = {
        "folders": folders,
        "sub": sub,
        "storage_used": storage_used,
        "storage_total": storage_total,
        "storage_percent": storage_percent,
        "storage_full": storage_full,
    }

    return render(request, "core/dashboard/upload.html", context)


# ---------------------------------------------------------
# SHARED FILES PAGE
# ---------------------------------------------------------
@login_required
def shared_view(request):
    user = request.user

    shared_by_you = SharedFile.objects.filter(owner=user)
    shared_with_you = SharedFile.objects.filter(shared_with=user)

    total_shared = shared_by_you.count() + shared_with_you.count()

    # include storage card data
    sub, storage_used, storage_total, storage_percent, storage_full = calculate_storage(user)

    context = {
        "shared_by_you": shared_by_you,
        "shared_with_you": shared_with_you,
        "total_shared": total_shared,

        # storage card
        "sub": sub,
        "storage_used": storage_used,
        "storage_total": storage_total,
        "storage_percent": storage_percent,
        "storage_full": storage_full,
    }

    return render(request, "core/dashboard/shared.html", context)


# ---------------------------------------------------------
# MY FILES PAGE
# ---------------------------------------------------------
@login_required
def my_files_view(request):
    user = request.user
    files = File.objects.filter(user=user, is_deleted=False).order_by("-uploaded_at")

    # storage card info
    sub, storage_used, storage_total, storage_percent, storage_full = calculate_storage(user)

    context = {
        "files": files,

        # storage card
        "sub": sub,
        "storage_used": storage_used,
        "storage_total": storage_total,
        "storage_percent": storage_percent,
        "storage_full": storage_full,
    }

    return render(request, "core/dashboard/my_files.html", context)


# ---------------------------------------------------------
# TRASH PAGE
# ---------------------------------------------------------
@login_required
def trash_view(request):
    user = request.user

    trashed_files = File.objects.filter(
        user=user,
        is_deleted=True
    ).order_by("-deleted_at")

    total_items = trashed_files.count()
    total_size = round(sum(f.size for f in trashed_files), 2)

    expiring_soon = trashed_files.filter(
        deleted_at__lte=timezone.now() - timedelta(days=18)
    ).count()

    paginator = Paginator(trashed_files, 10)
    page = request.GET.get("page")
    files = paginator.get_page(page)

    # storage card
    sub, storage_used, storage_total, storage_percent, storage_full = calculate_storage(user)

    context = {
        "files": files,
        "total_items": total_items,
        "total_size": total_size,
        "expiring_soon": expiring_soon,

        # storage card
        "sub": sub,
        "storage_used": storage_used,
        "storage_total": storage_total,
        "storage_percent": storage_percent,
        "storage_full": storage_full,
    }

    return render(request, "core/dashboard/trash.html", context)


# ---------------------------------------------------------
# RESTORE FILE
# ---------------------------------------------------------
@login_required
def restore_file(request, file_id):
    file = File.objects.get(id=file_id, user=request.user)
    file.is_deleted = False
    file.deleted_at = None
    file.save()
    return redirect("trash")


# ---------------------------------------------------------
# DELETE PERMANENTLY
# ---------------------------------------------------------
@login_required
def delete_permanently(request, file_id):
    file = File.objects.get(id=file_id, user=request.user)
    file.delete()
    return redirect("trash")


# ---------------------------------------------------------
# EMPTY TRASH
# ---------------------------------------------------------
@login_required
def empty_trash(request):
    File.objects.filter(user=request.user, is_deleted=True).delete()
    return redirect("trash")


@login_required
def settings_view(request):
    user = request.user

    # ---- Get or Create Profile ----
    profile, created = Profile.objects.get_or_create(user=user)

    # ---- Get Subscription ----
    try:
        sub = Subscription.objects.get(user=user)
    except Subscription.DoesNotExist:
        sub = None

    # ---- Calculate storage usage ----
    files = File.objects.filter(user=user)
    storage_used = round(sum(f.size for f in files), 2)  # in GB
    storage_total = sub.storage_limit if sub else 0
    storage_percent = int((storage_used / storage_total) * 100) if storage_total else 0

    # ---- FORM SUBMISSION ----
    if request.method == "POST":

        # -------------------- Profile Photo Upload --------------------
        if "upload_photo" in request.POST:
            if "photo" in request.FILES:
                # delete previous photo if exists
                if profile.photo:
                    try:
                        default_storage.delete(profile.photo.path)
                    except:
                        pass

                profile.photo = request.FILES["photo"]
                profile.save()
                messages.success(request, "Profile photo updated successfully!")
            return redirect("settings")

        # -------------------- Remove Photo --------------------
        if "remove_photo" in request.POST:
            if profile.photo:
                try:
                    default_storage.delete(profile.photo.path)
                except:
                    pass
            profile.photo = None
            profile.save()
            messages.success(request, "Profile photo removed successfully!")
            return redirect("settings")

        # -------------------- Save Profile Info --------------------
        if "save_profile" in request.POST:
            profile.first_name = request.POST.get("first_name")
            profile.last_name = request.POST.get("last_name")
            profile.phone = request.POST.get("phone")
            user.email = request.POST.get("email")

            profile.save()
            user.save()

            messages.success(request, "Profile details updated successfully!")
            return redirect("settings")

        # -------------------- Preferences --------------------
        if "preferences" in request.POST:
            dark_mode = request.POST.get("dark_mode") == "on"
            email_notify = request.POST.get("email_notify") == "on"
            autosync = request.POST.get("autosync") == "on"

            profile.dark_mode = dark_mode
            profile.email_notify = email_notify
            profile.autosync = autosync
            profile.save()

            messages.success(request, "Preferences updated!")
            return redirect("settings")

    # ---- RENDER PAGE ----
    return render(request, "core/dashboard/settings.html", {
        "profile": profile,
        "subscription": sub,
        "storage_used": storage_used,
        "storage_total": storage_total,
        "storage_percent": storage_percent,
    })

from django.contrib.auth.decorators import user_passes_test

def superuser_required(view_func):
    return user_passes_test(lambda user: user.is_superuser)(view_func)


@superuser_required
def admin_dashboard(request):

    total_users = User.objects.count()
    total_files = File.objects.count()

    storage_used = round(sum(f.size for f in File.objects.all()) / 1024, 2)  # TB approx
    active_servers = 8  # Just a placeholder

    recent_activity = ActivityLog.objects.order_by("-timestamp")[:8]

    context = {
        "total_users": total_users,
        "total_files": total_files,
        "storage_used": storage_used,
        "active_servers": active_servers,
        "recent_activity": recent_activity,
    }

    return render(request, "admin/dashboard.html", context)


def no_subscription(request):
    return render(request, "core/subscription/no_subscription.html")

def subscription_expired(request):
    return render(request, "core/subscription/subscription_expired.html")

def storage_full(request):
    return render(request, "core/subscription/storage_full.html")

@login_required
def pricing(request):
    return render(request, "core/subscription/pricing.html")

@login_required
def checkout_view(request, plan):
    user = request.user

    PLAN_DATA = {
        "free": {"name": "FREE", "storage": 5, "duration": None, "amount": 0},
        "pro": {"name": "PRO", "storage": 50, "duration": 30, "amount": 499},
        "premium": {"name": "PREMIUM", "storage": 200, "duration": 30, "amount": 999},
    }

    if plan not in PLAN_DATA:
        messages.error(request, "Invalid plan selected.")
        return redirect("pricing")

    plan_info = PLAN_DATA[plan]

    # FREE PLAN → auto activate
    if plan_info["amount"] == 0:
        sub, _ = Subscription.objects.get_or_create(user=user)
        sub.plan = plan_info["name"]
        sub.storage_limit = plan_info["storage"]
        sub.start_date = timezone.now()
        sub.end_date = None
        sub.save()

        messages.success(request, "FREE plan activated!")
        return redirect("dashboard")

    return render(request, "core/subscription/checkout.html", {
        "plan": plan,
        "amount": plan_info["amount"],
        "plan_data": plan_info,
        "razorpay_key": settings.RAZORPAY_KEY_ID
    })


@login_required
@csrf_exempt
def create_order(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid request"}, status=400)

    plan = request.POST.get("plan")
    amount = int(float(request.POST.get("amount")) * 100)

    client = razorpay.Client(
        auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
    )

    order = client.order.create({
        "amount": amount,
        "currency": "INR",
        "payment_capture": 1
    })

    return JsonResponse({"order": order})



@login_required
@csrf_exempt
def verify_payment(request):
    if request.method != "POST":
        return JsonResponse({"status": "failed"})

    data = request.POST

    client = razorpay.Client(
        auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
    )

    try:
        client.utility.verify_payment_signature({
            "razorpay_order_id": data["razorpay_order_id"],
            "razorpay_payment_id": data["razorpay_payment_id"],
            "razorpay_signature": data["razorpay_signature"]
        })
    except razorpay.errors.SignatureVerificationError:
        return JsonResponse({"status": "failed"})

    # Activate subscription
    PLAN_DATA = {
        "pro": {"name": "PRO", "storage": 50},
        "premium": {"name": "PREMIUM", "storage": 200},
    }

    plan = data.get("plan")
    plan_info = PLAN_DATA.get(plan)

    sub, _ = Subscription.objects.get_or_create(user=request.user)
    sub.plan = plan_info["name"]
    sub.storage_limit = plan_info["storage"]
    sub.start_date = timezone.now()
    sub.end_date = timezone.now() + timezone.timedelta(days=30)
    sub.save()

    # Email receipt
    # send_mail(
    #     subject="CloudSync Payment Successful",
    #     message=f"Your {sub.plan} plan is activated.",
    #     from_email=settings.DEFAULT_FROM_EMAIL,
    #     recipient_list=[request.user.email],
    #     fail_silently=True
    # )

    return JsonResponse({"status": "success"})


    
def download_invoice(request, order_id):
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer)

    p.drawString(100, 800, f"Invoice for Order: {order_id}")
    p.drawString(100, 780, f"User: {request.user.email}")
    p.drawString(100, 760, "Thank you for your purchase!")

    p.showPage()
    p.save()

    buffer.seek(0)
    return FileResponse(buffer, as_attachment=True, filename="invoice.pdf")



def logout_view(request):
    logout(request)
    messages.success(request, "Logged out successfully.")
    return redirect("home")


