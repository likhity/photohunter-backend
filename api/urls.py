from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from . import views

# Create router for viewsets (if any)
router = DefaultRouter()

urlpatterns = [
    # Authentication endpoints
    path('auth/register/', views.register, name='register'),
    path('auth/login/', views.login_view, name='login'),
    path('auth/logout/', views.logout_view, name='logout'),
    
    # JWT Token endpoints
    path('auth/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # PhotoHunt endpoints
    path('photohunts/', views.PhotoHuntListCreateView.as_view(), name='photohunt-list-create'),
    path('photohunts/<uuid:pk>/', views.PhotoHuntDetailView.as_view(), name='photohunt-detail'),
    path('photohunts/<uuid:pk>/download/', views.download_reference_image, name='photohunt-download'),
    path('photohunts/my/', views.UserPhotoHuntsView.as_view(), name='user-photohunts'),
    path('photohunts/nearby/', views.nearby_photohunts, name='nearby-photohunts'),
    
    # Photo submission and validation
    path('photos/submit/', views.submit_photo, name='submit-photo'),
    
    # User completions
    path('completions/', views.PhotoHuntCompletionsView.as_view(), name='completions'),
    
    # User profile
    path('profile/', views.user_profile, name='user-profile'),
    path('profile/update/', views.update_profile, name='update-profile'),
    
    # Include router URLs
    path('', include(router.urls)),
]
