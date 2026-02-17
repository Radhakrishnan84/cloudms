from django.urls import path
from .views import home_view
from . import views

urlpatterns = [
    path('', home_view, name='home'),
    path("login/", views.login_view, name="login"),
    path("signup/", views.signup_view, name="signup"),
    path("dashboard/", views.dashboard_view, name="dashboard"),
    path("upload/", views.upload, name="upload"),
    path("storage-status/", views.storage_status, name="storage_status"),
    path("shared/", views.shared_view, name="shared"),
    path("my-files/", views.my_files_view, name="my_files"),
    path("file/view/<int:file_id>/", views.view_file, name="view_file"),
    path("file/download/<int:file_id>/", views.download_file, name="download_file"),
    path("file/share/<int:file_id>/", views.share_file, name="share_file"),
    path("file/trash/<int:file_id>/", views.trash_file, name="trash_file"),
    path("trash/", views.trash_view, name="trash"),
    path("trash/restore/<int:file_id>/", views.restore_file, name="restore_file"),
    path("trash/delete/<int:file_id>/", views.delete_file_permanently, name="delete_file"),
    path("trash/restore-all/", views.restore_all_files, name="restore_all"),
    path("trash/empty/", views.empty_trash, name="empty_trash"),
    path("settings/", views.settings_view, name="settings"),
    path('pricing/', views.pricing, name='pricing'),
    path("checkout/<str:plan>/", views.checkout_view, name="checkout"),
    path("payment/create-order/", views.create_order, name="create_order"),
    path("payment/verify/", views.verify_payment, name="payment_verify"),
    path("invoice/<str:order_id>/", views.download_invoice, name="download_invoice"),
    path('payment/success/', views.payment_success, name='payment_success'),
    path('no-subscription/', views.no_subscription, name='no_subscription'),
    path('subscription-expired/', views.subscription_expired, name='subscription_expired'),
    path('storage-full/', views.storage_full, name='storage_full'),
]
