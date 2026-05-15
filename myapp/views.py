from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from .models import Note, Category, Profile
from django.core.mail import send_mail
from django.conf import settings
import random

# --- Auth Views ---

def register(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        
        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists")
            return redirect('register')
        
        user = User.objects.create_user(username=username, email=email, password=password)
        profile = Profile.objects.create(user=user)
        otp = profile.generate_otp()
        
        # Send Email
        subject = 'Your OTP for Notes App Verification'
        message = f'Hi {username}, your OTP is {otp}.'
        email_from = settings.EMAIL_HOST_USER
        recipient_list = [email]
        try:
            send_mail(subject, message, email_from, recipient_list)
        except Exception as e:
            print(e) # Log error
            
        request.session['unverified_user_id'] = user.id
        return redirect('verify_otp')
        
    return render(request, 'auth/register.html')

def verify_otp(request):
    user_id = request.session.get('unverified_user_id')
    if not user_id:
        return redirect('register')
        
    user = get_object_or_404(User, id=user_id)
    profile = user.profile
    
    if request.method == 'POST':
        otp_entered = request.POST.get('otp')
        if profile.otp == otp_entered:
            profile.is_verified = True
            profile.otp = None
            profile.save()
            login(request, user)
            del request.session['unverified_user_id']
            messages.success(request, "Account verified and logged in!")
            return redirect('index')
        else:
            messages.error(request, "Invalid OTP")
            
    return render(request, 'auth/verify_otp.html')

def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            # Ensure Profile exists (for superusers created via CLI)
            profile, created = Profile.objects.get_or_create(user=user)
            if created and user.is_superuser:
                profile.is_verified = True
                profile.is_approved = True
                profile.save()

            if user.profile.is_verified:
                if user.is_superuser or user.profile.is_approved:
                    login(request, user)
                    return redirect('index')
                else:
                    messages.warning(request, "Account pending admin approval.")
                    return redirect('login')
            else:
                request.session['unverified_user_id'] = user.id
                # Resend OTP
                otp = user.profile.generate_otp()
                send_mail('Verify your account', f'Your OTP is {otp}', settings.EMAIL_HOST_USER, [user.email])
                return redirect('verify_otp')
        else:
            messages.error(request, "Invalid username or password")
            
    return render(request, 'auth/login.html')

def forgot_password(request):
    if request.method == 'POST':
        identifier = request.POST.get('identifier')
        # Check if identifier is email or username
        user = User.objects.filter(Q(email=identifier) | Q(username=identifier)).first()
        
        if user:
            # Ensure Profile exists
            profile, _ = Profile.objects.get_or_create(user=user)
            otp = profile.generate_otp()
            
            # Send Email
            subject = 'Password Reset OTP'
            message = f'Hi {user.username},\n\nYour OTP for password reset is {otp}. If you did not request this, please ignore this email.'
            try:
                send_mail(subject, message, settings.EMAIL_HOST_USER, [user.email])
            except Exception as e:
                print("Email sending failed:", e)
                
            request.session['reset_user_id'] = user.id
            messages.success(request, f"OTP sent to {user.email}")
            return redirect('verify_reset_otp')
        else:
            messages.error(request, "No account found with that username or email.")
            
    return render(request, 'auth/forgot_password.html')

def verify_reset_otp(request):
    user_id = request.session.get('reset_user_id')
    if not user_id:
        return redirect('forgot_password')
        
    user = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        otp_entered = request.POST.get('otp')
        if user.profile.otp == otp_entered:
            # Valid OTP, clear it and allow reset
            user.profile.otp = None
            user.profile.save()
            request.session['can_reset_password'] = True
            return redirect('reset_password')
        else:
            messages.error(request, "Invalid OTP.")
            
    return render(request, 'auth/verify_reset_otp.html')

def reset_password(request):
    user_id = request.session.get('reset_user_id')
    can_reset = request.session.get('can_reset_password')
    
    if not user_id or not can_reset:
        return redirect('forgot_password')
        
    user = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')
        
        if new_password == confirm_password:
            user.set_password(new_password)
            user.save()
            
            # Clear session variables
            del request.session['reset_user_id']
            del request.session['can_reset_password']
            
            messages.success(request, "Password successfully reset. You can now login.")
            return redirect('login')
        else:
            messages.error(request, "Passwords do not match.")
            
    return render(request, 'auth/reset_password.html')

@login_required
def logout_view(request):
    logout(request)
    return redirect('login')

@login_required
def profile(request):
    notes_count = Note.objects.filter(user=request.user).count()
    fav_count = Note.objects.filter(user=request.user, is_favorite=True).count()
    return render(request, 'auth/profile.html', {
        'notes_count': notes_count,
        'fav_count': fav_count
    })

# --- Notes CRUD ---

@login_required
def index(request):
    query = request.GET.get('q', '')
    cat_id = request.GET.get('category', '')
    show_favs = request.GET.get('favorites', False)
    
    notes = Note.objects.filter(user=request.user).order_by('-updated_at')
    
    if query:
        notes = notes.filter(Q(title__icontains=query) | Q(content__icontains=query))
    
    if cat_id:
        notes = notes.filter(category_id=cat_id)
        
    if show_favs:
        notes = notes.filter(is_favorite=True)
        
    categories = Category.objects.filter(user=request.user)
    
    context = {
        'notes': notes,
        'categories': categories,
        'search_query': query,
        'selected_cat': cat_id,
        'show_favs': show_favs
    }
    return render(request, 'index.html', context)

@login_required
def add_note(request):
    if request.method == 'POST':
        title = request.POST.get('title')
        content = request.POST.get('content')
        category_id = request.POST.get('category')
        is_favorite = request.POST.get('is_favorite') == 'on'
        file = request.FILES.get('file')
        
        category = None
        if category_id:
            category = get_object_or_404(Category, id=category_id, user=request.user)
            
        Note.objects.create(
            user=request.user,
            title=title,
            content=content,
            category=category,
            is_favorite=is_favorite,
            file=file
        )
        messages.success(request, "Note created!")
        return redirect('index')
        
    categories = Category.objects.filter(user=request.user)
    return render(request, 'notes/add_note.html', {'categories': categories})

@login_required
def edit_note(request, pk):
    note = get_object_or_404(Note, pk=pk, user=request.user)
    if request.method == 'POST':
        note.title = request.POST.get('title')
        note.content = request.POST.get('content')
        category_id = request.POST.get('category')
        note.is_favorite = request.POST.get('is_favorite') == 'on'
        
        if request.FILES.get('file'):
            note.file = request.FILES.get('file')
            
        if category_id:
            note.category = get_object_or_404(Category, id=category_id, user=request.user)
        else:
            note.category = None
            
        note.save()
        messages.success(request, "Note updated!")
        return redirect('index')
        
    categories = Category.objects.filter(user=request.user)
    return render(request, 'notes/edit_note.html', {'note': note, 'categories': categories})

@login_required
def delete_note(request, pk):
    if request.user.is_superuser:
        note = get_object_or_404(Note, pk=pk)
        note.delete()
        messages.success(request, "Note deleted by admin!")
        return redirect('custom_admin_notes')
    else:
        note = get_object_or_404(Note, pk=pk, user=request.user)
        note.delete()
        messages.success(request, "Note deleted!")
        return redirect('index')

@login_required
def toggle_favorite(request, pk):
    note = get_object_or_404(Note, pk=pk, user=request.user)
    note.is_favorite = not note.is_favorite
    note.save()
    return redirect('index')

@login_required
def remove_attachment(request, pk):
    note = get_object_or_404(Note, pk=pk, user=request.user)
    if note.file:
        note.file.delete()
        note.file = None
        note.save()
        messages.success(request, "Attachment removed!")
    return redirect('edit_note', pk=pk)

@login_required
def note_detail(request, pk):
    note = get_object_or_404(Note, pk=pk, user=request.user)
    return render(request, 'notes/note_detail.html', {'note': note})

@login_required
def category_list(request):
    categories = Category.objects.filter(user=request.user)
    return render(request, 'notes/category_list.html', {'categories': categories})

@login_required
def delete_category(request, pk):
    category = get_object_or_404(Category, pk=pk, user=request.user)
    category.delete()
    messages.success(request, "Category deleted!")
    return redirect('category_list')

# --- Category CRUD ---

@login_required
def add_category(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        color = request.POST.get('color', '#3498db')
        Category.objects.create(user=request.user, name=name, color=color)
        messages.success(request, "Category added!")
    return redirect('index')

# --- Custom Admin Views ---
from django.contrib.admin.views.decorators import staff_member_required

@staff_member_required
def custom_admin_dashboard(request):
    users_count = User.objects.count()
    notes_count = Note.objects.count()
    pending_users = Profile.objects.filter(is_approved=False, is_verified=True).count()
    return render(request, 'admin/dashboard.html', {
        'users_count': users_count,
        'notes_count': notes_count,
        'pending_users': pending_users
    })

@staff_member_required
def custom_admin_users(request):
    profiles = Profile.objects.select_related('user').all().order_by('-user__date_joined')
    return render(request, 'admin/users.html', {'profiles': profiles})

@staff_member_required
def custom_admin_approve_user(request, pk):
    profile = get_object_or_404(Profile, user_id=pk)
    profile.is_approved = True
    profile.save()
    messages.success(request, f"User {profile.user.username} approved.")
    return redirect('custom_admin_users')

@staff_member_required
def custom_admin_decline_user(request, pk):
    user = get_object_or_404(User, id=pk)
    if not user.is_superuser:
        user.delete()
        messages.success(request, "User declined and deleted.")
    return redirect('custom_admin_users')

@staff_member_required
def custom_admin_notes(request):
    notes = Note.objects.all().order_by('-created_at')
    return render(request, 'admin/notes.html', {'notes': notes})

@login_required
def contact_view(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        message = request.POST.get('message')
        # In a real application, you might send an email here
        messages.success(request, f"Thank you {name}, your message has been received!")
        return redirect('contact')
    return render(request, 'contact.html')

def about_view(request):
    return render(request, 'about.html')

def faq_view(request):
    return render(request, 'faq.html')

def home_view(request):
    if request.user.is_authenticated:
        return redirect('index')
    return render(request, 'home.html')
