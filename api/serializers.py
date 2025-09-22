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
    """Serializer for creating PhotoHunt"""
    class Meta:
        model = PhotoHunt
        fields = ['name', 'description', 'latitude', 'longitude', 'reference_image']
    
    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)


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
    """Serializer for photo submission and validation"""
    photohunt_id = serializers.UUIDField()
    image_url = serializers.URLField()
    
    def validate_photohunt_id(self, value):
        try:
            PhotoHunt.objects.get(id=value, is_active=True)
        except PhotoHunt.DoesNotExist:
            raise serializers.ValidationError("PhotoHunt not found or inactive")
        return value
