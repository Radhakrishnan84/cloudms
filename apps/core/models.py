from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta

class PricingPlan:
    PLANS = {
        "free": {
            "amount": 0,
            "name": "Free Plan"
        },
        "pro": {
            "amount": 499,
            "name": "Pro Plan"
        },
        "premium": {
            "amount": 999,
            "name": "premium plan"
        }
    }

#dashboard

class UserFile(models.Model):
    CATEGORY_CHOICES = [
        ("document", "Document"),
        ("image", "Image"),
        ("video", "Video"),
        ("other", "Other"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    file = models.FileField(upload_to="uploads/")
    size = models.FloatField()  # stored in MB
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
    

class Subscription(models.Model):

    PLAN_CHOICES = [
        ("FREE", "Free"),
        ("PRO", "Pro"),
        ("PREMIUM", "Premium"),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    plan = models.CharField(max_length=20, choices=PLAN_CHOICES)
    storage_limit = models.IntegerField(default=5)   # GB
    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField(null=True, blank=True)

    def is_active(self):
        if self.end_date is None:
            return True
        return self.end_date > timezone.now()

    def days_left(self):
        if self.end_date:
            return (self.end_date - timezone.now()).days
        return None

    def __str__(self):
        return f"{self.user.username} – {self.plan}"


# Admin setup

class Plan(models.Model):
    name = models.CharField(max_length=20)
    price = models.FloatField()
    storage_limit = models.IntegerField()  # in GB
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name

class File(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    folder = models.ForeignKey("Folder", on_delete=models.SET_NULL, null=True, blank=True)
    file = models.FileField(upload_to="uploads/")
    name = models.CharField(max_length=255)
    size = models.FloatField()  # MB
    category = models.CharField(max_length=20, default="other")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    # Soft delete fields
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)

    def expires_in_days(self):
        if not self.deleted_at:
            return None
        expire_date = self.deleted_at + timedelta(days=30)
        return (expire_date - timezone.now()).days

    def is_expired(self):
        return self.expires_in_days() <= 0

class Folder(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
    
class SharedFile(models.Model):
    file = models.ForeignKey(File, on_delete=models.CASCADE)
    owner = models.ForeignKey(User, related_name="shared_by_you", on_delete=models.CASCADE)
    shared_with = models.ForeignKey(User, related_name="shared_with_you", on_delete=models.CASCADE)
    shared_at = models.DateTimeField(auto_now_add=True)

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    photo = models.ImageField(upload_to='profile_photos/', null=True, blank=True)

    first_name = models.CharField(max_length=100, null=True, blank=True)
    last_name = models.CharField(max_length=100, null=True, blank=True)
    phone = models.CharField(max_length=20, null=True, blank=True)

    dark_mode = models.BooleanField(default=False)
    email_notify = models.BooleanField(default=True)
    autosync = models.BooleanField(default=False)

    def __str__(self):
        return self.user.username


class ActivityLog(models.Model):
    ACTIVITY_TYPES = [
        ("UPLOAD", "File Uploaded"),
        ("DELETE", "File Deleted"),
        ("RESTORE", "File Restored"),
        ("SHARE", "File Shared"),
        ("LOGIN", "User Login"),
        ("SUBSCRIPTION", "Subscription Updated"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    activity_type = models.CharField(max_length=20, choices=ACTIVITY_TYPES)
    action = models.CharField(max_length=255)
    timestamp = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.user.username} - {self.activity_type}"

class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    message = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    def __str__(self):
        return self.message
    

class Server(models.Model):
    name = models.CharField(max_length=100)
    location = models.CharField(max_length=100)

    cpu = models.IntegerField(default=0)
    memory = models.IntegerField(default=0)
    storage = models.IntegerField(default=0)
    uptime = models.FloatField(default=99.8)

    status = models.CharField(max_length=20, default="Active")  
    color = models.CharField(max_length=20, default="#e8d7ff")

    def __str__(self):
        return self.name








