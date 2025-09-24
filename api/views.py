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
from django.shortcuts import redirect

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


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def download_reference_image(request, pk):
    """Return a redirect to a presigned URL (S3) or local media URL."""
    try:
        photohunt = PhotoHunt.objects.get(id=pk, is_active=True)
    except PhotoHunt.DoesNotExist:
        return Response({'error': 'PhotoHunt not found'}, status=status.HTTP_404_NOT_FOUND)

    if not photohunt.reference_image:
        return Response({'error': 'No reference image available'}, status=status.HTTP_404_NOT_FOUND)

    image_url = photohunt.reference_image

    # If we stored an S3 URL, generate a presigned URL
    if image_url.startswith('http://') or image_url.startswith('https://'):
        from .services.s3_service import S3Service
        s3 = S3Service()
        key = s3.extract_key_from_url(image_url)
        try:
            presigned = s3.generate_presigned_get_url(key, expiration=900)
            return redirect(presigned)
        except Exception:
            # As a fallback, still try redirecting to the stored URL
            return redirect(image_url)

    # Otherwise assume it's a local media URL like /media/...
    absolute_url = request.build_absolute_uri(image_url)
    return redirect(absolute_url)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def submit_photo(request):
    """Submit a photo for PhotoHunt validation using multipart form data"""
    serializer = PhotoSubmissionSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    photohunt_id = serializer.validated_data['photohunt_id']
    photo_file = serializer.validated_data['photo']
    
    try:
        photohunt = PhotoHunt.objects.get(id=photohunt_id, is_active=True)
    except PhotoHunt.DoesNotExist:
        return Response(
            {'error': 'PhotoHunt not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Allow retries even if previously completed; we'll replace on success
    
    # Validate file format
    file_extension = photo_file.name.split('.')[-1].lower()
    if file_extension not in ['jpg', 'jpeg', 'png', 'gif', 'webp']:
        return Response(
            {'error': 'Unsupported file format. Please use JPG, PNG, GIF, or WebP.'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Read file bytes for AI validation
    try:
        if hasattr(photo_file, 'seek'):
            photo_file.seek(0)
    except Exception:
        pass
    submitted_image_bytes = photo_file.read()
    
    # Upload to S3
    from .services.s3_service import S3Service
    s3_service = S3Service()
    try:
        # Reset file pointer for upload
        photo_file.seek(0)
        submitted_image_url = s3_service.upload_file(photo_file, folder='submissions', file_extension=file_extension)
        # Generate a presigned GET URL for the validator to fetch the image
        try:
            submitted_key = s3_service.extract_key_from_url(submitted_image_url)
            submitted_presigned_url = s3_service.generate_presigned_get_url(submitted_key, expiration=900)
        except Exception:
            # Fallback to using the public URL if presign fails
            submitted_presigned_url = submitted_image_url
    except Exception as e:
        # Fallback to local storage for development
        import os
        import uuid
        from django.conf import settings
        
        # Create media directory if it doesn't exist
        media_dir = os.path.join(settings.MEDIA_ROOT, 'submissions')
        os.makedirs(media_dir, exist_ok=True)
        
        # Generate unique filename
        filename = f"{uuid.uuid4()}.{file_extension}"
        file_path = os.path.join(media_dir, filename)
        
        # Save file locally
        try:
            with open(file_path, 'wb') as f:
                f.write(submitted_image_bytes)
        except Exception as write_err:
            return Response(
                {'error': f'Failed to save image: {str(write_err)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        # Create URL for local file
        submitted_image_url = f"{settings.MEDIA_URL}submissions/{filename}"
        # Build absolute URL for validator to fetch
        try:
            submitted_presigned_url = request.build_absolute_uri(submitted_image_url)
        except Exception:
            submitted_presigned_url = submitted_image_url
    
    # Prepare a presigned URL for the reference image as well
    reference_image_url = photohunt.reference_image
    try:
        if reference_image_url and (reference_image_url.startswith('http://') or reference_image_url.startswith('https://')):
            ref_key = s3_service.extract_key_from_url(reference_image_url)
            reference_presigned_url = s3_service.generate_presigned_get_url(ref_key, expiration=900)
        else:
            reference_presigned_url = request.build_absolute_uri(reference_image_url)
    except Exception:
        reference_presigned_url = reference_image_url

    # Validate photo using AI with presigned URLs for both images
    validation_service = PhotoValidationService()
    validation_result = validation_service.validate_photo(
        reference_image_url=reference_presigned_url,
        submitted_image_url=submitted_presigned_url,
        photohunt_description=photohunt.description
    )

    # If validation failed, delete uploaded image and allow retry
    if not validation_result.get('is_valid', False):
        try:
            if submitted_image_url.startswith('http://') or submitted_image_url.startswith('https://'):
                try:
                    key = s3_service.extract_key_from_url(submitted_image_url)
                    if key:
                        s3_service.s3_client.delete_object(Bucket=s3_service.bucket_name, Key=key)
                except Exception:
                    pass
            else:
                try:
                    # Remove local file if present
                    import os
                    from django.conf import settings
                    rel = submitted_image_url.replace(settings.MEDIA_URL, '')
                    local_path = os.path.join(settings.MEDIA_ROOT, rel)
                    if os.path.exists(local_path):
                        os.remove(local_path)
                except Exception:
                    pass
        except Exception:
            pass

        # Strip any signed URLs from response payload
        try:
            validation_result.pop('reference_image_url', None)
            validation_result.pop('submitted_image_url', None)
        except Exception:
            pass

        return Response({'validation': validation_result}, status=status.HTTP_200_OK)

    # Successful validation: update existing completion or create new
    existing_completion = PhotoHuntCompletion.objects.filter(user=request.user, photohunt=photohunt).first()
    previously_valid = bool(existing_completion and existing_completion.is_valid)
    old_image_url = existing_completion.submitted_image if existing_completion else None

    if existing_completion:
        existing_completion.submitted_image = submitted_image_url
        existing_completion.is_valid = True
        existing_completion.validation_score = validation_result['similarity_score']
        existing_completion.validation_notes = validation_result.get('notes', '')
        existing_completion.save()
        completion = existing_completion
    else:
        completion = PhotoHuntCompletion.objects.create(
            user=request.user,
            photohunt=photohunt,
            submitted_image=submitted_image_url,
            is_valid=True,
            validation_score=validation_result['similarity_score'],
            validation_notes=validation_result.get('notes', '')
        )

    # If replacing an older submission, delete the old object from storage
    try:
        if old_image_url and old_image_url != submitted_image_url:
            if old_image_url.startswith('http://') or old_image_url.startswith('https://'):
                try:
                    old_key = s3_service.extract_key_from_url(old_image_url)
                    if old_key:
                        s3_service.s3_client.delete_object(Bucket=s3_service.bucket_name, Key=old_key)
                except Exception:
                    pass
            else:
                try:
                    import os
                    from django.conf import settings
                    rel_old = old_image_url.replace(settings.MEDIA_URL, '')
                    local_old_path = os.path.join(settings.MEDIA_ROOT, rel_old)
                    if os.path.exists(local_old_path):
                        os.remove(local_old_path)
                except Exception:
                    pass
    except Exception:
        pass

    # Do not expose signed URLs in the API response
    try:
        validation_result.pop('reference_image_url', None)
        validation_result.pop('submitted_image_url', None)
    except Exception:
        pass

    # Create or update validation record (store non-signed, durable URLs)
    from django.db import transaction
    with transaction.atomic():
        validation_obj, _ = PhotoValidation.objects.select_for_update().get_or_create(
            completion=completion,
            defaults={
                'reference_image_url': photohunt.reference_image,
                'submitted_image_url': submitted_image_url,
                'similarity_score': validation_result['similarity_score'],
                'confidence_score': validation_result['confidence_score'],
                'validation_prompt': validation_result['prompt'],
                'ai_response': validation_result['ai_response'],
                'is_approved': True
            }
        )
        if validation_obj and validation_obj.pk:
            validation_obj.reference_image_url = photohunt.reference_image
            validation_obj.submitted_image_url = submitted_image_url
            validation_obj.similarity_score = validation_result['similarity_score']
            validation_obj.confidence_score = validation_result['confidence_score']
            validation_obj.validation_prompt = validation_result['prompt']
            validation_obj.ai_response = validation_result['ai_response']
            validation_obj.is_approved = True
            validation_obj.save()

    # Update user profile stats
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    if not previously_valid:
        profile.total_completions += 1
        profile.save()

    return Response({'completion': PhotoHuntCompletionSerializer(completion).data, 'validation': validation_result}, status=status.HTTP_201_CREATED)


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