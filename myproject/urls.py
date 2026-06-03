from django.contrib import admin
from django.urls import path
from myapp import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('django-admin/', admin.site.urls), # Kept as a fallback
    
    # Custom Admin
    path('admin/', views.custom_admin_dashboard, name='custom_admin_dashboard'),
    path('admin/users/', views.custom_admin_users, name='custom_admin_users'),
    path('admin/notes/', views.custom_admin_notes, name='custom_admin_notes'),
    path('admin/approve/<int:pk>/', views.custom_admin_approve_user, name='custom_admin_approve_user'),
    path('admin/decline/<int:pk>/', views.custom_admin_decline_user, name='custom_admin_decline_user'),
    path('admin-login/', views.admin_login_view, name='admin_login'),
    
    # Auth
    path('register/', views.register, name='register'),
    path('verify-otp/', views.verify_otp, name='verify_otp'),
    path('resend-otp/', views.resend_otp, name='resend_otp'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile, name='profile'),
    
    # Password Reset
    path('forgot-password/', views.forgot_password, name='forgot_password'),
    path('verify-reset-otp/', views.verify_reset_otp, name='verify_reset_otp'),
    path('reset-password/', views.reset_password, name='reset_password'),
    
    # Notes / Main App
    path('', views.home_view, name='home'),
    path('dashboard/', views.index, name='index'),
    path('note/<int:pk>/', views.note_detail, name='note_detail'),
    path('add-note/', views.add_note, name='add_note'),
    path('edit-note/<int:pk>/', views.edit_note, name='edit_note'),
    path('remove-attachment/<int:pk>/', views.remove_attachment, name='remove_attachment'),
    path('delete-note/<int:pk>/', views.delete_note, name='delete_note'),
    path('toggle-favorite/<int:pk>/', views.toggle_favorite, name='toggle_favorite'),
    
    # Category
    path('categories/', views.category_list, name='category_list'),
    path('delete-category/<int:pk>/', views.delete_category, name='delete_category'),
    path('add-category/', views.add_category, name='add_category'),
    
    # Contact & Info
    path('contact/', views.contact_view, name='contact'),
    path('about/', views.about_view, name='about'),
    path('faq/', views.faq_view, name='faq'),
    
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
