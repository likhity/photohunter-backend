from rest_framework import serializers
from django.contrib.auth import authenticate
from .models import User, PhotoHunt, PhotoHuntCompletion, PhotoValidation, UserProfile


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model"""
    class Meta:
        model = User
        fields = ['id', 'email', 'name', 'created_at']
        read_only_fields = ['id', 'created_at']


class UserRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for user registration"""
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True)
    
    class Meta:
        model = User
        fields = ['email', 'name', 'password', 'password_confirm']
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError("Passwords don't match")
        return attrs
    
    def create(self, validated_data):
        validated_data.pop('password_confirm')
        user = User.objects.create_user(
            username=validated_data['email'],  # Use email as username
            email=validated_data['email'],
            name=validated_data['name'],
            password=validated_data['password']
        )
        # Create user profile
        UserProfile.objects.create(user=user)
        return user


class UserLoginSerializer(serializers.Serializer):
    """Serializer for user login"""
    email = serializers.EmailField()
    password = serializers.CharField()
    
    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')
        
        if email and password:
            user = authenticate(username=email, password=password)
            if not user:
                raise serializers.ValidationError('Invalid email or password')
            if not user.is_active:
                raise serializers.ValidationError('User account is disabled')
            attrs['user'] = user
        else:
            raise serializers.ValidationError('Must include email and password')
        
        return attrs


class PhotoHuntSerializer(serializers.ModelSerializer):
    """Serializer for PhotoHunt model"""
    created_by_name = serializers.CharField(source='created_by.name', read_only=True)
    created_by_avatar = serializers.SerializerMethodField()  # Creator's avatar with signed URL
    hunted = serializers.SerializerMethodField()
    reference_image = serializers.SerializerMethodField()  # Override to return signed URL
    latitude = serializers.FloatField()
    longitude = serializers.FloatField()
    
    class Meta:
        model = PhotoHunt
        fields = [
            'id', 'name', 'description', 'latitude', 'longitude', 
            'reference_image', 'difficulty', 'hint', 'created_by', 'created_by_name', 'created_by_avatar',
            'is_user_generated', 'is_active', 'created_at', 'updated_at',
            'hunted'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'hunted']
    
    def get_hunted(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return PhotoHuntCompletion.objects.filter(
                user=request.user, 
                photohunt=obj
            ).exists()
        return False
    
    def get_reference_image(self, obj):
        """Return signed URL for S3 reference images or absolute URL for local files"""
        if not obj.reference_image:
            return None
            
        # If it's an S3 URL, generate a presigned URL
        if obj.reference_image.startswith('http://') or obj.reference_image.startswith('https://'):
            try:
                from .services.s3_service import S3Service
                s3_service = S3Service()
                key = s3_service.extract_key_from_url(obj.reference_image)
                if key:
                    # Generate presigned URL with 1 hour expiration
                    return s3_service.generate_presigned_get_url(key, expiration=3600)
            except Exception:
                # Fallback to original URL if presigning fails
                pass
        
        # For local files, build absolute URL
        request = self.context.get('request')
        if request and not obj.reference_image.startswith('http'):
            return request.build_absolute_uri(obj.reference_image)
        
        # Return original URL as fallback
        return obj.reference_image
    
    def get_created_by_avatar(self, obj):
        """Return signed URL for creator's avatar or None if no avatar"""
        try:
            # Get the creator's profile
            profile = obj.created_by.profile
            if not profile.avatar:
                return None
                
            # If it's an S3 URL, generate a presigned URL
            if profile.avatar.startswith('http://') or profile.avatar.startswith('https://'):
                try:
                    from .services.s3_service import S3Service
                    s3_service = S3Service()
                    key = s3_service.extract_key_from_url(profile.avatar)
                    if key:
                        # Generate presigned URL with 1 hour expiration
                        return s3_service.generate_presigned_get_url(key, expiration=3600)
                except Exception:
                    # Fallback to original URL if presigning fails
                    pass
            
            # For local files, build absolute URL
            request = self.context.get('request')
            if request and not profile.avatar.startswith('http'):
                return request.build_absolute_uri(profile.avatar)
            
            # Return original URL as fallback
            return profile.avatar
            
        except (AttributeError, UserProfile.DoesNotExist):
            # Return None if user has no profile or avatar
            return None


class PhotoHuntCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating PhotoHunt with file upload support"""
    reference_image_file = serializers.ImageField(required=False, write_only=True)
    reference_image = serializers.URLField(required=False, write_only=True)
    # Support both field names for frontend compatibility
    lat = serializers.DecimalField(max_digits=20, decimal_places=15, write_only=True, required=False)
    long = serializers.DecimalField(max_digits=20, decimal_places=15, write_only=True, required=False)
    difficulty = serializers.FloatField(required=False, min_value=0, max_value=5)
    hint = serializers.CharField(required=False, allow_blank=True)
    
    class Meta:
        model = PhotoHunt
        fields = ['name', 'description', 'lat', 'long', 'difficulty', 'hint', 'reference_image', 'reference_image_file']
    
    def validate(self, attrs):
        # Map lat/long to latitude/longitude if provided
        if 'lat' in attrs and attrs['lat'] is not None:
            attrs['latitude'] = attrs.pop('lat')
        if 'long' in attrs and attrs['long'] is not None:
            attrs['longitude'] = attrs.pop('long')
        
        # Handle reference image validation - only validate if image-related fields are provided
        has_file = 'reference_image_file' in attrs and attrs['reference_image_file'] is not None
        has_url = 'reference_image' in attrs and attrs['reference_image'] is not None and attrs['reference_image'] != 'Present'
        
        # If reference_image is "Present", it means the frontend is indicating a file should be uploaded
        # but the actual file is in reference_image_file
        if 'reference_image' in attrs and attrs['reference_image'] == 'Present':
            attrs.pop('reference_image')  # Remove the "Present" string
            has_url = False
        
        # If no file and no valid URL, but we have a "Present" indicator, that's okay
        # The frontend should be sending the file via reference_image_file
        if not has_file and not has_url:
            # Check if this is a multipart request with a file
            if hasattr(self.context.get('request'), 'FILES') and 'reference_image_file' in self.context['request'].FILES:
                has_file = True
                attrs['reference_image_file'] = self.context['request'].FILES['reference_image_file']
        
        # Only require reference image for CREATE operations, not UPDATE operations
        # For updates, we only validate if image fields are provided
        is_update = self.instance is not None
        image_fields_provided = has_file or has_url or 'reference_image' in attrs or 'reference_image_file' in attrs
        
        if not is_update:
            # This is a CREATE operation - validate required fields
            if not has_file and not has_url:
                raise serializers.ValidationError("Either reference_image_file or reference_image must be provided")
            
            # Ensure coordinates are provided for creation
            if 'latitude' not in attrs and 'lat' not in attrs:
                raise serializers.ValidationError("Latitude (lat) is required for creating PhotoHunts")
            if 'longitude' not in attrs and 'long' not in attrs:
                raise serializers.ValidationError("Longitude (long) is required for creating PhotoHunts")
        
        if has_file and has_url:
            raise serializers.ValidationError("Provide either reference_image_file or reference_image, not both")
        
        return attrs
    
    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        
        # Handle file upload - upload to S3 and get URL
        if 'reference_image_file' in validated_data:
            file_obj = validated_data.pop('reference_image_file')
            # Get file extension
            file_extension = file_obj.name.split('.')[-1].lower()
            if file_extension not in ['jpg', 'jpeg', 'png', 'gif', 'webp']:
                raise serializers.ValidationError("Unsupported file format. Please use JPG, PNG, GIF, or WebP.")
            
            # Read file bytes once so we can safely retry and/or fall back to local storage
            import io
            try:
                if hasattr(file_obj, 'seek'):
                    file_obj.seek(0)
            except Exception:
                pass
            file_bytes = file_obj.read()
            if file_bytes is None:
                file_bytes = b''
            s3_buffer = io.BytesIO(file_bytes)

            # Upload to S3
            from .services.s3_service import S3Service
            s3_service = S3Service()
            try:
                # Ensure buffer is at start before upload
                try:
                    s3_buffer.seek(0)
                except Exception:
                    s3_buffer = io.BytesIO(file_bytes)
                s3_url = s3_service.upload_file(s3_buffer, folder='photohunts', file_extension=file_extension)
                validated_data['reference_image'] = s3_url
            except Exception as e:
                # Fallback to local storage for development
                import os
                import uuid
                from django.conf import settings
                
                # Create media directory if it doesn't exist
                media_dir = os.path.join(settings.MEDIA_ROOT, 'photohunts')
                os.makedirs(media_dir, exist_ok=True)
                
                # Generate unique filename
                filename = f"{uuid.uuid4()}.{file_extension}"
                file_path = os.path.join(media_dir, filename)
                
                # Save file locally
                try:
                    with open(file_path, 'wb') as f:
                        f.write(file_bytes)
                except Exception as write_err:
                    raise serializers.ValidationError(
                        { 'non_field_errors': [f'Failed to persist image locally: {str(write_err)}'] }
                    )
                
                # Create URL for local file
                local_url = f"{settings.MEDIA_URL}photohunts/{filename}"
                validated_data['reference_image'] = local_url
        try:
            return super().create(validated_data)
        except Exception as e:
            # Surface clean error to client; check server logs for full traceback
            raise serializers.ValidationError({
                'non_field_errors': [f'Failed to create PhotoHunt: {str(e)}']
            })


class PhotoHuntCompletionSerializer(serializers.ModelSerializer):
    """Serializer for PhotoHuntCompletion model"""
    photohunt_name = serializers.CharField(source='photohunt.name', read_only=True)
    user_name = serializers.CharField(source='user.name', read_only=True)
    submitted_image = serializers.SerializerMethodField()  # Override to return signed URL
    
    class Meta:
        model = PhotoHuntCompletion
        fields = [
            'id', 'user', 'user_name', 'photohunt', 'photohunt_name',
            'submitted_image', 'validation_score', 'is_valid', 
            'validation_notes', 'created_at'
        ]
        read_only_fields = ['id', 'user', 'created_at']
    
    def get_submitted_image(self, obj):
        """Return signed URL for S3 submitted images or absolute URL for local files"""
        if not obj.submitted_image:
            return None
            
        # If it's an S3 URL, generate a presigned URL
        if obj.submitted_image.startswith('http://') or obj.submitted_image.startswith('https://'):
            try:
                from .services.s3_service import S3Service
                s3_service = S3Service()
                key = s3_service.extract_key_from_url(obj.submitted_image)
                if key:
                    # Generate presigned URL with 1 hour expiration
                    return s3_service.generate_presigned_get_url(key, expiration=3600)
            except Exception:
                # Fallback to original URL if presigning fails
                pass
        
        # For local files, build absolute URL
        request = self.context.get('request')
        if request and not obj.submitted_image.startswith('http'):
            return request.build_absolute_uri(obj.submitted_image)
        
        # Return original URL as fallback
        return obj.submitted_image


class PhotoValidationSerializer(serializers.ModelSerializer):
    """Serializer for PhotoValidation model"""
    class Meta:
        model = PhotoValidation
        fields = [
            'id', 'completion', 'reference_image_url', 'submitted_image_url',
            'similarity_score', 'confidence_score', 'validation_prompt',
            'ai_response', 'is_approved', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer for UserProfile model with nested user fields"""
    user = UserSerializer(read_only=True)
    name = serializers.CharField(source='user.name', required=False)
    avatar_file = serializers.ImageField(required=False, write_only=True)
    avatar = serializers.SerializerMethodField()  # Override to return signed URL
    
    class Meta:
        model = UserProfile
        fields = [
            'user', 'name', 'bio', 'avatar', 'avatar_file', 'total_completions', 
            'total_created', 'created_at', 'updated_at'
        ]
        read_only_fields = ['total_completions', 'total_created', 'created_at', 'updated_at']
    
    def get_avatar(self, obj):
        """Return signed URL for S3 avatars or absolute URL for local files"""
        if not obj.avatar:
            return None
            
        # If it's an S3 URL, generate a presigned URL
        if obj.avatar.startswith('http://') or obj.avatar.startswith('https://'):
            try:
                from .services.s3_service import S3Service
                s3_service = S3Service()
                key = s3_service.extract_key_from_url(obj.avatar)
                if key:
                    # Generate presigned URL with 1 hour expiration
                    return s3_service.generate_presigned_get_url(key, expiration=3600)
            except Exception:
                # Fallback to original URL if presigning fails
                pass
        
        # For local files, build absolute URL
        request = self.context.get('request')
        if request and not obj.avatar.startswith('http'):
            return request.build_absolute_uri(obj.avatar)
        
        # Return original URL as fallback
        return obj.avatar
    
    def update(self, instance, validated_data):
        # Handle avatar file upload
        if 'avatar_file' in validated_data:
            file_obj = validated_data.pop('avatar_file')
            # Get file extension
            file_extension = file_obj.name.split('.')[-1].lower()
            if file_extension not in ['jpg', 'jpeg', 'png', 'gif', 'webp']:
                raise serializers.ValidationError("Unsupported avatar format. Please use JPG, PNG, GIF, or WebP.")
            
            # Upload to S3
            from .services.s3_service import S3Service
            s3_service = S3Service()
            try:
                avatar_url = s3_service.upload_file(file_obj, folder='avatars', file_extension=file_extension)
                # Delete old avatar if exists
                if instance.avatar:
                    try:
                        old_key = s3_service.extract_key_from_url(instance.avatar)
                        if old_key:
                            s3_service.s3_client.delete_object(Bucket=s3_service.bucket_name, Key=old_key)
                    except Exception:
                        pass
                validated_data['avatar'] = avatar_url
            except Exception as e:
                # Fallback to local storage for development
                import os
                import uuid
                from django.conf import settings
                
                # Create media directory if it doesn't exist
                media_dir = os.path.join(settings.MEDIA_ROOT, 'avatars')
                os.makedirs(media_dir, exist_ok=True)
                
                # Generate unique filename
                filename = f"{uuid.uuid4()}.{file_extension}"
                file_path = os.path.join(media_dir, filename)
                
                # Save file locally
                try:
                    with open(file_path, 'wb') as f:
                        for chunk in file_obj.chunks():
                            f.write(chunk)
                except Exception as write_err:
                    raise serializers.ValidationError(
                        f'Failed to save avatar: {str(write_err)}'
                    )
                
                # Create URL for local file
                local_url = f"{settings.MEDIA_URL}avatars/{filename}"
                validated_data['avatar'] = local_url
        
        # Handle nested user data
        user_data = {}
        if 'user' in validated_data:
            user_data = validated_data.pop('user')
        
        # Update user fields if provided
        if user_data:
            user = instance.user
            for attr, value in user_data.items():
                setattr(user, attr, value)
            user.save()
        
        # Update profile fields
        return super().update(instance, validated_data)


class PhotoSubmissionSerializer(serializers.Serializer):
    """Serializer for photo submission with multipart form data"""
    photohunt_id = serializers.UUIDField()
    photo = serializers.ImageField()
    
    def validate_photohunt_id(self, value):
        try:
            PhotoHunt.objects.get(id=value, is_active=True)
        except PhotoHunt.DoesNotExist:
            raise serializers.ValidationError("PhotoHunt not found or inactive")
        return value


class ChangePasswordSerializer(serializers.Serializer):
    """Serializer for changing user password"""
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, min_length=8)
    new_password_confirm = serializers.CharField(required=True)
    
    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError("New passwords don't match")
        return attrs
    
    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Old password is incorrect")
        return value


class PublicUserProfileSerializer(serializers.ModelSerializer):
    """Serializer for public user profile with limited fields"""
    name = serializers.CharField(source='user.name', read_only=True)
    avatar = serializers.SerializerMethodField()  # Override to return signed URL
    
    class Meta:
        model = UserProfile
        fields = ['name', 'bio', 'avatar', 'total_completions', 'total_created']
        read_only_fields = ['name', 'bio', 'avatar', 'total_completions', 'total_created']
    
    def get_avatar(self, obj):
        """Return signed URL for S3 avatars or absolute URL for local files"""
        if not obj.avatar:
            return None
            
        # If it's an S3 URL, generate a presigned URL
        if obj.avatar.startswith('http://') or obj.avatar.startswith('https://'):
            try:
                from .services.s3_service import S3Service
                s3_service = S3Service()
                key = s3_service.extract_key_from_url(obj.avatar)
                if key:
                    # Generate presigned URL with 1 hour expiration
                    return s3_service.generate_presigned_get_url(key, expiration=3600)
            except Exception:
                # Fallback to original URL if presigning fails
                pass
        
        # For local files, build absolute URL
        request = self.context.get('request')
        if request and not obj.avatar.startswith('http'):
            return request.build_absolute_uri(obj.avatar)
        
        # Return original URL as fallback
        return obj.avatar
