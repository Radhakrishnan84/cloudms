from django.shortcuts import render, redirect, get_object_or_404
from django.conf import settings
from django.contrib.auth.decorators import login_required
import razorpay
from .models import PricingPlan
from django.contrib.auth.models import User
from django.contrib.auth import login, authenticate
from django.contrib import messages
from django.http import HttpResponseForbidden
from django.http import HttpResponseRedirect
from django.http import Http404
from .models import File
from apps.core.utils.helpers import detect_category, file_size_in_mb
from django.db import IntegrityError
from .models import Subscription, Plan
from django.utils import timezone
from django.http import HttpResponse
from datetime import datetime
from datetime import timedelta
from apps.core.utils.payments import razorpay_client
from django.http import JsonResponse
from .models import UserFile, Subscription, Folder, SharedFile, Profile, ActivityLog, File
from cloudinary.uploader import upload as cloudinary_upload
from django.core.files.storage import default_storage
from django.core.paginator import Paginator
from django.db.models import Sum
from django.views.decorators.csrf import csrf_exempt
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from reportlab.pdfgen import canvas
import io
import os
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
    next_url = request.POST.get("next")

    if not email or not password:
        messages.error(request, "Email and password are required.")
        return redirect("login")

    email = email.strip().lower()

    # 🔐 Authenticate
    user = authenticate(request, username=email, password=password)

    if user is None:
        messages.error(request, "Invalid email or password.")
        return redirect("login")

    # 🚫 Admin access check
    if login_type == "admin" and not user.is_staff:
        messages.error(request, "Admin access denied.")
        return redirect("login")

    # ✅ Login
    login(request, user)

    # ⏳ Remember me
    if remember:
        request.session.set_expiry(60 * 60 * 24 * 14)  # 14 days
    else:
        request.session.set_expiry(0)  # browser close

    # 🔁 Redirect
    if next_url:
        return redirect(next_url)

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




@login_required
def dashboard_view(request):
    user = request.user

    # ---------------- SUBSCRIPTION CHECK ----------------
    try:
        sub = Subscription.objects.get(user=user)
    except Subscription.DoesNotExist:
        return redirect("no_subscription")

    # ---------------- CATEGORY STATS ----------------
    def category_stats(cat):
        qs = UserFile.objects.filter(user=user, category=cat)
        count = qs.count()
        size = qs.aggregate(total=Sum("size"))["total"] or 0
        return count, round(size / 1024, 2)  # MB → GB

    doc_count, doc_size = category_stats("document")
    img_count, img_size = category_stats("image")
    vid_count, vid_size = category_stats("video")
    oth_count, oth_size = category_stats("other")

    # ---------------- RECENT FILES ----------------
    recent_files = (
        UserFile.objects
        .filter(user=user)
        .order_by("-uploaded_at")[:6]
    )

    # ---------------- STORAGE CARD ----------------
    sub, storage_used, storage_total, storage_percent, storage_full = calculate_storage(user)

    context = {
        # category cards
        "doc_count": doc_count,
        "doc_size": doc_size,
        "img_count": img_count,
        "img_size": img_size,
        "vid_count": vid_count,
        "vid_size": vid_size,
        "oth_count": oth_count,
        "oth_size": oth_size,

        # recent files
        "recent_files": recent_files,

        # storage card
        "sub": sub,
        "storage_used": storage_used,
        "storage_total": storage_total,
        "storage_percent": storage_percent,
        "storage_full": storage_full,
    }

    return render(request, "core/dashboard/dashboard.html", context)


    



# ---------------------------------------------------------
# Storage Calculation (used by all pages)
# ---------------------------------------------------------
def calculate_storage(user):
    sub = Subscription.objects.filter(user=user).first()
    if not sub:
        return None, 0, 0, 0, False

    files = UserFile.objects.filter(user=user)
    storage_used = round(sum(f.size for f in files), 2)
    storage_total = sub.storage_limit
    storage_percent = int((storage_used / storage_total) * 100) if storage_total else 0
    storage_full = storage_used >= storage_total

    return sub, storage_used, storage_total, storage_percent, storage_full


# ---------------- STORAGE STATUS API ----------------
@login_required
def storage_status(request):
    _, used, total, percent, _ = calculate_storage(request.user)
    return JsonResponse({
        "used": used,
        "total": total,
        "percent": percent
    })


# ---------------- UPLOAD VIEW ----------------
@login_required
def upload(request):
    user = request.user

    try:
        sub = Subscription.objects.get(user=user)
    except Subscription.DoesNotExist:
        return redirect("no_subscription")

    if not sub.is_active():
        return redirect("subscription_expired")

    if request.method == "POST":
        uploaded_file = request.FILES.get("file")
        folder_id = request.POST.get("folder")

        if not uploaded_file:
            return JsonResponse({"error": "No file uploaded"}, status=400)

        size_mb = round(uploaded_file.size / (1024 * 1024), 2)
        _, used, total, _, _ = calculate_storage(user)

        if used + size_mb > total:
            return JsonResponse({"error": "Storage limit reached"}, status=403)

        # -------- CATEGORY AUTO-DETECTION --------
        ext = uploaded_file.name.split(".")[-1].lower()

        if ext in ["jpg", "jpeg", "png", "gif", "webp"]:
            category = "image"
            system_folder = "images"
        elif ext in ["mp4", "avi", "mov", "mkv"]:
            category = "video"
            system_folder = "videos"
        else:
            category = "document"
            system_folder = "documents"

        # -------- OPTIONAL USER FOLDER (SAFE) --------
        folder = None
        if folder_id:
            folder = Folder.objects.filter(
                id=int(folder_id),
                user=user
            ).first()

        # -------- SAFE FILE PATH --------
        uploaded_file.name = (
            f"cloudsync/{user.id}/{system_folder}/{uploaded_file.name}"
        )

        UserFile.objects.create(
            user=user,
            name=uploaded_file.name.split("/")[-1],
            file=uploaded_file,
            size=size_mb,
            category=category,
            folder=folder
        )

        return JsonResponse({"success": True})

    # GET
    sub, used, total, percent, full = calculate_storage(user)
    folders = Folder.objects.filter(user=user)

    return render(request, "core/dashboard/upload.html", {
        "folders": folders,
        "sub": sub,
        "storage_used": used,
        "storage_total": total,
        "storage_percent": percent,
        "storage_full": full,
    })



# ---------------------------------------------------------
# SHARED FILES PAGE
# ---------------------------------------------------------
@login_required
def shared_view(request):
    user = request.user

    shared_by_you = SharedFile.objects.filter(owner=user)
    shared_with_you = SharedFile.objects.filter(shared_with=user)

    total_shared = shared_by_you.count() + shared_with_you.count()

    sub, used, total, percent, full = calculate_storage(user)

    return render(request, "core/dashboard/shared.html", {
        "shared_by_you": shared_by_you,
        "shared_with_you": shared_with_you,
        "total_shared": total_shared,
        "sub": sub,
        "storage_used": used,
        "storage_total": total,
        "storage_percent": percent,
        "storage_full": full,
    })


# ---------------------------------------------------------
# MY FILES PAGE
# ---------------------------------------------------------
@login_required
def my_files_view(request):
    user = request.user

    # optional filters
    search = request.GET.get("q", "")
    folder_id = request.GET.get("folder")

    files = UserFile.objects.filter(
        user=user,
        is_deleted=False
    )

    # 🔍 Search
    if search:
        files = files.filter(name__icontains=search)

    # 📂 Folder filter
    if folder_id:
        files = files.filter(folder_id=folder_id)

    files = files.order_by("-uploaded_at")

    # 💾 Storage card
    sub, used, total, percent, full = calculate_storage(user)

    return render(request, "core/dashboard/my_files.html", {
        "files": files,
        "sub": sub,
        "storage_used": used,
        "storage_total": total,
        "storage_percent": percent,
        "storage_full": full,
        "search_query": search,
        "active_folder": folder_id,
    })




# ---------------------------------------------------------
# TRASH PAGE
# ---------------------------------------------------------

@login_required
def trash_view(request):
    user = request.user
    now = timezone.now()

    deleted_files = UserFile.objects.filter(
        user=user,
        is_deleted=True
    ).order_by("-deleted_at")

    enriched_files = []
    total_size = 0
    expiring_soon = 0

    for f in deleted_files:
        deleted_at = f.deleted_at or now
        days_deleted = (now - deleted_at).days
        expires_in = max(0, 30 - days_deleted)

        if expires_in <= 5:
            expiring_soon += 1

        total_size += f.size

        enriched_files.append({
            "id": f.id,
            "name": f.name,
            "size": f.size,
            "type": f.category.title(),
            "deleted_ago": f"{days_deleted} days",
            "expires_in": expires_in,
            "icon": (
                "files-card.png" if f.category == "document" else
                "img-card.png" if f.category == "image" else
                "video-card.png" if f.category == "video" else
                "others-card.png"
            )
        })

    sub, used, total, percent, full = calculate_storage(user)

    return render(request, "core/dashboard/trash.html", {
        "deleted_files": enriched_files,
        "total_items": len(enriched_files),
        "total_size": round(total_size / 1024, 2),
        "expiring_soon": expiring_soon,
        "page_count": len(enriched_files),
        "sub": sub,
        "storage_used": used,
        "storage_total": total,
        "storage_percent": percent,
        "storage_full": full,
    })
@login_required
def view_file(request, file_id):
    file = get_object_or_404(UserFile, id=file_id)

    allowed = (
        file.user == request.user or
        SharedFile.objects.filter(file=file, shared_with=request.user).exists()
    )

    if not allowed:
        return HttpResponseForbidden("Access denied")

    return redirect(file.file)


@login_required
def download_file(request, file_id):
    file = get_object_or_404(UserFile, id=file_id, user=request.user)

    response = redirect(file.file)
    response["Content-Disposition"] = f'attachment; filename="{file.name}"'
    return response

@login_required
def share_file(request, file_id):
    file = get_object_or_404(UserFile, id=file_id, user=request.user)

    if request.method == "POST":
        username = request.POST.get("username")
        shared_with = User.objects.filter(username=username).first()

        if not shared_with:
            messages.error(request, "User not found")
            return redirect("my_files")

        SharedFile.objects.get_or_create(
            owner=request.user,
            shared_with=shared_with,
            file=file
        )

        messages.success(request, "File shared successfully")
        return redirect("shared")

    return render(request, "core/dashboard/shared.html", {"file": file})


@login_required
def trash_file(request, file_id):
    files = UserFile.objects.get(id=file_id, user=request.user, is_deleted=False)
    files.is_deleted = True
    files.deleted_at = timezone.now()
    files.save(update_fields=["is_deleted", "deleted_at"])
    return redirect("my_files")


# ---------------------------------------------------------
# RESTORE FILE
# ---------------------------------------------------------
@login_required
def restore_file(request, file_id):
    file = get_object_or_404(UserFile, id=file_id, user=request.user)
    file.is_deleted = False
    file.deleted_at = None
    file.save()
    return redirect("trash")

@login_required
def delete_file_permanently(request, file_id):
    file = get_object_or_404(UserFile, id=file_id, user=request.user)
    file.delete()
    return redirect("trash")

@login_required
def restore_all_files(request):
    UserFile.objects.filter(
        user=request.user,
        is_deleted=True
    ).update(is_deleted=False, deleted_at=None)
    return redirect("trash")


@login_required
def empty_trash(request):
    UserFile.objects.filter(
        user=request.user,
        is_deleted=True
    ).delete()
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
    files = UserFile.objects.filter(user=user)
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


razorpay_client = razorpay.Client(
    auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
)

@login_required
@csrf_exempt
def create_order(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid request"}, status=400)

    plan = request.POST.get("plan")
    amount = int(float(request.POST.get("amount")) * 100)  # paise

    order = razorpay_client.order.create({
        "amount": amount,
        "currency": "INR",
        "payment_capture": 1
    })

    return JsonResponse({
        "order_id": order["id"],
        "amount": order["amount"],
        "key": settings.RAZORPAY_KEY_ID
    })


import hmac
import hashlib

@login_required
@csrf_exempt
def verify_payment(request):
    if request.method != "POST":
        return JsonResponse({"status": "failed"}, status=400)

    payment_id = request.POST.get("razorpay_payment_id")
    order_id = request.POST.get("razorpay_order_id")
    signature = request.POST.get("razorpay_signature")
    plan = request.POST.get("plan")

    body = f"{order_id}|{payment_id}"

    expected_signature = hmac.new(
        settings.RAZORPAY_KEY_SECRET.encode(),
        body.encode(),
        hashlib.sha256
    ).hexdigest()

    if expected_signature != signature:
        return JsonResponse({"status": "failed"})

    # ------------------------------
    # ✅ ACTIVATE SUBSCRIPTION
    # ------------------------------
    sub, _ = Subscription.objects.get_or_create(user=request.user)

    if plan == "pro":
        sub.plan = "PRO"
        sub.storage_limit = 100
        sub.end_date = timezone.now() + timezone.timedelta(days=30)
        amount = 499
    elif plan == "premium":
        sub.plan = "PREMIUM"
        sub.storage_limit = 1000
        sub.end_date = timezone.now() + timezone.timedelta(days=30)
        amount = 999
    else:
        amount = 0

    sub.save()

    # ==============================
    # 🔥 STORE DATA FOR INVOICE
    # ==============================
    request.session["razorpay_order_id"] = order_id
    request.session["razorpay_payment_id"] = payment_id
    request.session["plan"] = plan
    request.session["amount"] = amount

    return JsonResponse({"status": "success"})


from .utils.invoice import generate_invoice_pdf
from .utils.email import send_invoice_email

@login_required
def download_invoice(request, order_id):
    payment_id = request.GET.get("payment")
    plan = request.GET.get("plan")
    amount = request.GET.get("amount")

    pdf_buffer = generate_invoice_pdf(
        user=request.user,
        order_id=order_id,
        payment_id=payment_id,
        plan=plan,
        amount= amount,
    )

    response = HttpResponse(pdf_buffer, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="Invoice_{order_id}.pdf"'

    return response



@login_required
def payment_success(request):
    user = request.user

    order_id = request.session.get("razorpay_order_id")
    payment_id = request.session.get("razorpay_payment_id")
    plan = request.session.get("plan")
    amount = request.session.get("amount")

    # 🔥 Generate Invoice PDF
    invoice_pdf = generate_invoice_pdf(
        user=user,
        order_id=order_id,
        payment_id=payment_id,
        plan=plan,
        amount=amount
    )

    # 📧 SEND EMAIL WITH PDF
    send_invoice_email(user, invoice_pdf, order_id)

    return render(request, "core/payment_success.html", {
        "order_id": order_id,
        "payment_id": payment_id,
        "plan": plan,
        "amount": amount,
    })
    


def logout_view(request):
    logout(request)
    messages.success(request, "Logged out successfully.")
    return redirect("home")


