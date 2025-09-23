from rest_framework import status, generics, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from django.contrib.auth import login
from django.db.models import Q
from django.utils import timezone
# CSRF is disabled via middleware for API endpoints
import uuid

from .models import User, PhotoHunt, PhotoHuntCompletion, PhotoValidation, UserProfile
from .serializers import (
    UserSerializer, UserRegistrationSerializer, UserLoginSerializer,
    PhotoHuntSerializer, PhotoHuntCreateSerializer, PhotoHuntCompletionSerializer,
    PhotoValidationSerializer, UserProfileSerializer, PhotoSubmissionSerializer
)
from .services.photo_validation_service import PhotoValidationService
from .services.s3_service import S3Service


@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    """User registration endpoint"""
    serializer = UserRegistrationSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        refresh = RefreshToken.for_user(user)
        return Response({
            'user': UserSerializer(user).data,
            'access': str(refresh.access_token),
            'refresh': str(refresh)
        }, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    """User login endpoint"""
    serializer = UserLoginSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.validated_data['user']
        login(request, user)
        refresh = RefreshToken.for_user(user)
        return Response({
            'user': UserSerializer(user).data,
            'access': str(refresh.access_token),
            'refresh': str(refresh)
        }, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    """User logout endpoint - blacklist refresh token"""
    try:
        refresh_token = request.data.get('refresh')
        if refresh_token:
            token = RefreshToken(refresh_token)
            token.blacklist()
        return Response({'message': 'Successfully logged out'}, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({'error': 'Invalid token'}, status=status.HTTP_400_BAD_REQUEST)


# JWT Token Views are now handled directly in urls.py


class PhotoHuntListCreateView(generics.ListCreateAPIView):
    """List and create PhotoHunts"""
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return PhotoHuntCreateSerializer
        return PhotoHuntSerializer
    
    def get_queryset(self):
        queryset = PhotoHunt.objects.filter(is_active=True)
        
        # Filter by user-generated or system-generated
        user_generated = self.request.query_params.get('user_generated')
        if user_generated is not None:
            queryset = queryset.filter(is_user_generated=user_generated.lower() == 'true')
        
        # Filter by creator
        created_by = self.request.query_params.get('created_by')
        if created_by:
            queryset = queryset.filter(created_by_id=created_by)
        
        # Search by name or description
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | Q(description__icontains=search)
            )
        
        return queryset.order_by('-created_at')
    


class PhotoHuntDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or delete a PhotoHunt"""
    queryset = PhotoHunt.objects.filter(is_active=True)
    serializer_class = PhotoHuntSerializer
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return PhotoHuntCreateSerializer
        return PhotoHuntSerializer


class UserPhotoHuntsView(generics.ListAPIView):
    """Get PhotoHunts created by the current user"""
    serializer_class = PhotoHuntSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return PhotoHunt.objects.filter(
            created_by=self.request.user,
            is_active=True
        ).order_by('-created_at')


class PhotoHuntCompletionsView(generics.ListAPIView):
    """Get PhotoHunt completions by the current user"""
    serializer_class = PhotoHuntCompletionSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return PhotoHuntCompletion.objects.filter(
            user=self.request.user
        ).order_by('-created_at')


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def submit_photo(request):
    """Submit a photo for PhotoHunt validation"""
    serializer = PhotoSubmissionSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    photohunt_id = serializer.validated_data['photohunt_id']
    image_url = serializer.validated_data['image_url']
    
    try:
        photohunt = PhotoHunt.objects.get(id=photohunt_id, is_active=True)
    except PhotoHunt.DoesNotExist:
        return Response(
            {'error': 'PhotoHunt not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Check if user already completed this hunt
    if PhotoHuntCompletion.objects.filter(user=request.user, photohunt=photohunt).exists():
        return Response(
            {'error': 'You have already completed this PhotoHunt'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Create completion record
    completion = PhotoHuntCompletion.objects.create(
        user=request.user,
        photohunt=photohunt,
        submitted_image=image_url
    )
    
    # Validate photo using AI
    validation_service = PhotoValidationService()
    validation_result = validation_service.validate_photo(
        reference_image_url=photohunt.reference_image,
        submitted_image_url=image_url,
        photohunt_description=photohunt.description
    )
    
    # Update completion with validation results
    completion.validation_score = validation_result['similarity_score']
    completion.is_valid = validation_result['is_valid']
    completion.validation_notes = validation_result['notes']
    completion.save()
    
    # Create validation record
    PhotoValidation.objects.create(
        completion=completion,
        reference_image_url=photohunt.reference_image,
        submitted_image_url=image_url,
        similarity_score=validation_result['similarity_score'],
        confidence_score=validation_result['confidence_score'],
        validation_prompt=validation_result['prompt'],
        ai_response=validation_result['ai_response'],
        is_approved=validation_result['is_valid']
    )
    
    # Update user profile stats
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    if completion.is_valid:
        profile.total_completions += 1
        profile.save()
    
    return Response({
        'completion': PhotoHuntCompletionSerializer(completion).data,
        'validation': validation_result
    }, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_profile(request):
    """Get current user's profile"""
    try:
        profile = request.user.profile
        serializer = UserProfileSerializer(profile)
        return Response(serializer.data)
    except UserProfile.DoesNotExist:
        # Create profile if it doesn't exist
        profile = UserProfile.objects.create(user=request.user)
        serializer = UserProfileSerializer(profile)
        return Response(serializer.data)


@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def update_profile(request):
    """Update current user's profile"""
    try:
        profile = request.user.profile
    except UserProfile.DoesNotExist:
        profile = UserProfile.objects.create(user=request.user)
    
    serializer = UserProfileSerializer(profile, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def nearby_photohunts(request):
    """Get PhotoHunts near a given location"""
    lat = request.query_params.get('lat')
    lng = request.query_params.get('lng')
    radius = float(request.query_params.get('radius', 10))  # Default 10km radius
    
    if not lat or not lng:
        return Response(
            {'error': 'lat and lng parameters are required'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        lat = float(lat)
        lng = float(lng)
    except ValueError:
        return Response(
            {'error': 'Invalid lat or lng values'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Simple bounding box search (for production, use PostGIS or similar)
    # This is a rough approximation - for accurate distance calculation,
    # you'd want to use proper geospatial queries
    lat_range = radius / 111.0  # Rough conversion: 1 degree ≈ 111km
    lng_range = radius / (111.0 * abs(lat))  # Adjust for latitude
    
    photohunts = PhotoHunt.objects.filter(
        is_active=True,
        latitude__range=(lat - lat_range, lat + lat_range),
        longitude__range=(lng - lng_range, lng + lng_range)
    ).order_by('-created_at')
    
    serializer = PhotoHuntSerializer(photohunts, many=True, context={'request': request})
    return Response(serializer.data)