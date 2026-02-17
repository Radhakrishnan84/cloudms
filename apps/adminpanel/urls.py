from django.urls import path
from . import views

urlpatterns = [
    path("admin-login/", views.login_admin_view, name="login_admin"),
    path("logout/", views.logout_admin, name="logout_admin"),
    path("admin-dashboard/",views.admin_dashboard, name="admin_dashboard"),
    path("users/", views.admin_users, name="admin_users"),

    # --- User Actions ---
    path('users/view/<int:user_id>/', views.admin_user_view, name='admin_user_view'),
    path('users/edit/<int:user_id>/', views.admin_user_edit, name='admin_user_edit'),
    path('users/suspend/<int:user_id>/', views.admin_user_suspend, name='admin_user_suspend'),
    path('users/activate/<int:user_id>/', views.admin_user_activate, name='admin_user_activate'),
    path('users/delete/<int:user_id>/', views.admin_user_delete, name='admin_user_delete'),

    # Add + Export
    path("users/add/", views.admin_add_user, name="admin_add_user"),
    path("users/export/", views.admin_export_users, name="admin_export_users"),

    #Files
    path("files/", views.admin_files_view, name="admin_files"),
    path("files/add/", views.admin_add_file, name="admin_add_file"),
    path("files/export/", views.admin_export_files, name="admin_export_files"),

    path("subscriptions/", views.admin_subscriptions, name="admin_subscriptions"),

    #server
    path("servers/", views.admin_servers, name="admin_servers"),
    path("servers/add/", views.admin_add_server, name="admin_add_server"),
    path("servers/<int:server_id>/view/", views.admin_view_server, name="admin_view_server"),
    path("servers/<int:server_id>/edit/", views.admin_edit_server, name="admin_edit_server"),

    path('adminpanel/reports/', views.admin_reports_view, name='admin_reports'),
    path('adminpanel/reports/export_csv/', views.admin_reports_export_csv, name='admin_reports_export_csv'),
    path('adminpanel/reports/export_pdf/', views.admin_reports_export_pdf, name='admin_reports_export_pdf'),

    path("settings/", views.admin_settings, name="admin_settings"),
path("settings/platform/update/", views.admin_update_platform, name="admin_update_platform"),
path("settings/storage/update/", views.admin_update_storage_limits, name="admin_update_storage_limits"),
path("settings/features/update/", views.admin_update_features, name="admin_update_features"),
path("settings/security/update/", views.admin_update_security, name="admin_update_security"),
path("settings/maintenance/update/", views.admin_update_maintenance, name="admin_update_maintenance"),


]
