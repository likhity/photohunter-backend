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
    hunted = serializers.SerializerMethodField()
    latitude = serializers.FloatField()
    longitude = serializers.FloatField()
    
    class Meta:
        model = PhotoHunt
        fields = [
            'id', 'name', 'description', 'latitude', 'longitude', 
            'reference_image', 'created_by', 'created_by_name',
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


class PhotoHuntCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating PhotoHunt with file upload support"""
    reference_image_file = serializers.ImageField(required=False, write_only=True)
    reference_image = serializers.URLField(required=False, write_only=True)
    # Support both field names for frontend compatibility
    lat = serializers.DecimalField(max_digits=20, decimal_places=15, write_only=True, required=True)
    long = serializers.DecimalField(max_digits=20, decimal_places=15, write_only=True, required=True)
    
    class Meta:
        model = PhotoHunt
        fields = ['name', 'description', 'lat', 'long', 'reference_image', 'reference_image_file']
    
    def validate(self, attrs):
        # Map lat/long to latitude/longitude if provided
        if 'lat' in attrs and attrs['lat'] is not None:
            attrs['latitude'] = attrs.pop('lat')
        if 'long' in attrs and attrs['long'] is not None:
            attrs['longitude'] = attrs.pop('long')
        
        # Handle reference image validation
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
        
        if not has_file and not has_url:
            raise serializers.ValidationError("Either reference_image_file or reference_image must be provided")
        
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
    
    class Meta:
        model = PhotoHuntCompletion
        fields = [
            'id', 'user', 'user_name', 'photohunt', 'photohunt_name',
            'submitted_image', 'validation_score', 'is_valid', 
            'validation_notes', 'created_at'
        ]
        read_only_fields = ['id', 'user', 'created_at']


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
    """Serializer for UserProfile model"""
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = UserProfile
        fields = [
            'user', 'bio', 'avatar', 'total_completions', 
            'total_created', 'created_at', 'updated_at'
        ]
        read_only_fields = ['total_completions', 'total_created', 'created_at', 'updated_at']


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
