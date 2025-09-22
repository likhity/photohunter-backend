from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, PhotoHunt, PhotoHuntCompletion, PhotoValidation, UserProfile


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    """Admin configuration for custom User model"""
    list_display = ['email', 'name', 'is_active', 'created_at']
    list_filter = ['is_active', 'is_staff', 'created_at']
    search_fields = ['email', 'name']
    ordering = ['-created_at']
    
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal info', {'fields': ('name',)}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined', 'created_at')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'name', 'password1', 'password2'),
        }),
    )
    
    readonly_fields = ['created_at']


@admin.register(PhotoHunt)
class PhotoHuntAdmin(admin.ModelAdmin):
    """Admin configuration for PhotoHunt model"""
    list_display = ['name', 'created_by', 'is_user_generated', 'is_active', 'created_at']
    list_filter = ['is_user_generated', 'is_active', 'created_at']
    search_fields = ['name', 'description', 'created_by__email']
    readonly_fields = ['id', 'created_at', 'updated_at']
    
    fieldsets = (
        (None, {'fields': ('id', 'name', 'description')}),
        ('Location', {'fields': ('latitude', 'longitude')}),
        ('Media', {'fields': ('reference_image',)}),
        ('Metadata', {'fields': ('created_by', 'is_user_generated', 'is_active')}),
        ('Timestamps', {'fields': ('created_at', 'updated_at')}),
    )


@admin.register(PhotoHuntCompletion)
class PhotoHuntCompletionAdmin(admin.ModelAdmin):
    """Admin configuration for PhotoHuntCompletion model"""
    list_display = ['user', 'photohunt', 'is_valid', 'validation_score', 'created_at']
    list_filter = ['is_valid', 'created_at']
    search_fields = ['user__email', 'photohunt__name']
    readonly_fields = ['id', 'created_at']
    
    fieldsets = (
        (None, {'fields': ('id', 'user', 'photohunt')}),
        ('Submission', {'fields': ('submitted_image',)}),
        ('Validation', {'fields': ('validation_score', 'is_valid', 'validation_notes')}),
        ('Timestamps', {'fields': ('created_at',)}),
    )


@admin.register(PhotoValidation)
class PhotoValidationAdmin(admin.ModelAdmin):
    """Admin configuration for PhotoValidation model"""
    list_display = ['completion', 'similarity_score', 'confidence_score', 'is_approved', 'created_at']
    list_filter = ['is_approved', 'created_at']
    search_fields = ['completion__user__email', 'completion__photohunt__name']
    readonly_fields = ['id', 'created_at']
    
    fieldsets = (
        (None, {'fields': ('id', 'completion')}),
        ('Images', {'fields': ('reference_image_url', 'submitted_image_url')}),
        ('Scores', {'fields': ('similarity_score', 'confidence_score', 'is_approved')}),
        ('AI Response', {'fields': ('validation_prompt', 'ai_response')}),
        ('Timestamps', {'fields': ('created_at',)}),
    )


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    """Admin configuration for UserProfile model"""
    list_display = ['user', 'total_completions', 'total_created', 'created_at']
    list_filter = ['created_at']
    search_fields = ['user__email', 'user__name']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        (None, {'fields': ('user',)}),
        ('Profile', {'fields': ('bio', 'avatar')}),
        ('Stats', {'fields': ('total_completions', 'total_created')}),
        ('Timestamps', {'fields': ('created_at', 'updated_at')}),
    )