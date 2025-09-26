from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
import uuid


class User(AbstractUser):
    """Custom user model extending Django's AbstractUser"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=255)
    created_at = models.DateTimeField(default=timezone.now)
    
    # Override username to use email instead
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'name']
    
    class Meta:
        db_table = 'users'
    
    def __str__(self):
        return self.email


class PhotoHunt(models.Model):
    """PhotoHunt model representing a scavenger hunt location"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    description = models.TextField()
    latitude = models.DecimalField(max_digits=20, decimal_places=15)
    longitude = models.DecimalField(max_digits=20, decimal_places=15)
    reference_image = models.URLField(max_length=500, null=True, blank=True)  # S3 URL
    difficulty = models.FloatField(null=True, blank=True, help_text="Difficulty level out of 5")
    hint = models.TextField(blank=True, help_text="Optional hint for the photo hunt")
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_photohunts')
    is_user_generated = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'photohunts'
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name


class PhotoHuntCompletion(models.Model):
    """Tracks when a user completes a PhotoHunt"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='completions')
    photohunt = models.ForeignKey(PhotoHunt, on_delete=models.CASCADE, related_name='completions')
    submitted_image = models.URLField(max_length=500)  # S3 URL of user's photo
    validation_score = models.FloatField(null=True, blank=True)  # AI validation score
    is_valid = models.BooleanField(default=False)
    validation_notes = models.TextField(blank=True)  # AI feedback
    created_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        db_table = 'photohunt_completions'
        unique_together = ['user', 'photohunt']  # User can only complete each hunt once
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.email} - {self.photohunt.name}"


class PhotoValidation(models.Model):
    """Stores AI validation results for photo submissions"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    completion = models.OneToOneField(PhotoHuntCompletion, on_delete=models.CASCADE, related_name='validation')
    reference_image_url = models.URLField(max_length=500)
    submitted_image_url = models.URLField(max_length=500)
    similarity_score = models.FloatField()  # 0-1 score
    confidence_score = models.FloatField()  # AI confidence in the result
    validation_prompt = models.TextField()  # Prompt used for validation
    ai_response = models.TextField()  # Raw AI response
    is_approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        db_table = 'photo_validations'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Validation for {self.completion.user.email} - {self.completion.photohunt.name}"


class UserProfile(models.Model):
    """Extended user profile information"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    bio = models.TextField(blank=True)
    avatar = models.URLField(max_length=500, blank=True)  # S3 URL
    total_completions = models.PositiveIntegerField(default=0)
    total_created = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'user_profiles'
    
    def __str__(self):
        return f"Profile for {self.user.email}"