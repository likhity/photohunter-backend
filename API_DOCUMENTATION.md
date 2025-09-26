# PhotoHunter Backend API Documentation

## Overview

This document covers all API endpoints for the PhotoHunter backend, including recent updates for user account management, profile management with avatar uploads, and PhotoHunt management with difficulty/hint features.

**Base URL:** `http://localhost:8000/api/` (development) or your production URL

**Authentication:** Most endpoints require JWT authentication. Include the access token in the Authorization header:
```
Authorization: Bearer <access_token>
```

---

## Authentication Endpoints

### 1. User Registration
**POST** `/auth/register/`

**Content-Type:** `application/json`

**Request Body:**
```json
{
    "email": "user@example.com",
    "name": "John Doe",
    "password": "password123",
    "password_confirm": "password123"
}
```

**Response (201 Created):**
```json
{
    "user": {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "email": "user@example.com",
        "name": "John Doe",
        "created_at": "2023-09-25T10:30:00Z"
    },
    "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

### 2. User Login
**POST** `/auth/login/`

**Content-Type:** `application/json`

**Request Body:**
```json
{
    "email": "user@example.com",
    "password": "password123"
}
```

**Response (200 OK):**
```json
{
    "user": {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "email": "user@example.com",
        "name": "John Doe",
        "created_at": "2023-09-25T10:30:00Z"
    },
    "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

### 3. User Logout
**POST** `/auth/logout/`

**Authentication:** Required

**Content-Type:** `application/json`

**Request Body:**
```json
{
    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

**Response (200 OK):**
```json
{
    "message": "Successfully logged out"
}
```

### 4. Token Refresh
**POST** `/auth/token/refresh/`

**Content-Type:** `application/json`

**Request Body:**
```json
{
    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

**Response (200 OK):**
```json
{
    "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

---

## User Profile Management

### 5. Get User Profile
**GET** `/profile/`

**Authentication:** Required

**Response (200 OK):**
```json
{
    "user": {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "email": "user@example.com",
        "name": "John Doe",
        "created_at": "2023-09-25T10:30:00Z"
    },
    "name": "John Doe",
    "bio": "I love photography and exploring new places!",
    "avatar": "https://my-bucket.s3.amazonaws.com/avatars/uuid.jpg?AWSAccessKeyId=...&Signature=...&Expires=1695659999",
    "total_completions": 15,
    "total_created": 8,
    "created_at": "2023-09-25T10:30:00Z",
    "updated_at": "2023-09-25T15:45:00Z"
}
```

**Note:** The `avatar` field returns a signed URL that expires in 1 hour. For local development, it returns an absolute URL to the local file.

### 6. Update User Profile (Text Fields Only)
**PUT/PATCH** `/profile/update/`

**Authentication:** Required

**Content-Type:** `application/json`

**Request Body:**
```json
{
    "name": "John Doe Updated",
    "bio": "Updated bio text here"
}
```

**Response (200 OK):**
```json
{
    "user": {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "email": "user@example.com",
        "name": "John Doe Updated",
        "created_at": "2023-09-25T10:30:00Z"
    },
    "name": "John Doe Updated",
    "bio": "Updated bio text here",
    "avatar": "https://my-bucket.s3.amazonaws.com/avatars/uuid.jpg?AWSAccessKeyId=...&Signature=...&Expires=1695659999",
    "total_completions": 15,
    "total_created": 8,
    "created_at": "2023-09-25T10:30:00Z",
    "updated_at": "2023-09-25T16:00:00Z"
}
```

### 7. Update User Profile (With Avatar Upload)
**PUT/PATCH** `/profile/update/`

**Authentication:** Required

**Content-Type:** `multipart/form-data`

**Form Data:**
```
name: "John Doe Updated"
bio: "Updated bio with new avatar"
avatar_file: [binary image file - JPG, PNG, GIF, or WebP]
```

**Response (200 OK):**
```json
{
    "user": {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "email": "user@example.com",
        "name": "John Doe Updated",
        "created_at": "2023-09-25T10:30:00Z"
    },
    "name": "John Doe Updated",
    "bio": "Updated bio with new avatar",
    "avatar": "https://my-bucket.s3.amazonaws.com/avatars/new-uuid.jpg?AWSAccessKeyId=...&Signature=...&Expires=1695659999",
    "total_completions": 15,
    "total_created": 8,
    "created_at": "2023-09-25T10:30:00Z",
    "updated_at": "2023-09-25T16:15:00Z"
}
```

**Notes:**
- The old avatar is automatically deleted when a new one is uploaded
- Supported formats: JPG, JPEG, PNG, GIF, WebP
- Avatar is stored in S3 under the `avatars/` folder

### 8. Change Password
**POST** `/profile/change-password/`

**Authentication:** Required

**Content-Type:** `application/json`

**Request Body:**
```json
{
    "old_password": "oldpassword123",
    "new_password": "newpassword123",
    "new_password_confirm": "newpassword123"
}
```

**Response (200 OK):**
```json
{
    "message": "Password changed successfully"
}
```

**Error Response (400 Bad Request):**
```json
{
    "old_password": ["Old password is incorrect"],
    "new_password": ["New passwords don't match"]
}
```

### 9. Delete Account
**DELETE** `/profile/delete-account/`

**Authentication:** Required

**Response (200 OK):**
```json
{
    "message": "Account deleted successfully"
}
```

**What gets deleted:**
- User account and profile
- All PhotoHunts created by the user
- All PhotoHunt completions by the user
- All PhotoHunt completions by other users on this user's PhotoHunts
- All associated PhotoValidations
- All S3 objects (avatar, PhotoHunt reference images, submitted images)

### 10. Get Public User Profile
**GET** `/users/<uuid:user_id>/profile/`

**Authentication:** Required

**Description:** Get limited public profile information for any user. Returns only public fields (no email, private settings, etc.).

**Response (200 OK):**
```json
{
    "name": "Jane Smith",
    "bio": "Photography enthusiast and world traveler. Love capturing hidden gems in urban landscapes!",
    "avatar": "https://my-bucket.s3.amazonaws.com/avatars/uuid.jpg?AWSAccessKeyId=...&Signature=...&Expires=1695659999",
    "total_completions": 42,
    "total_created": 15
}
```

**Response (404 Not Found):**
```json
{
    "error": "User not found"
}
```

**Notes:**
- Returns limited public information only (no email, private data)
- `avatar` returns a signed URL that expires in 1 hour (null if no avatar)
- `total_created` and `total_completions` are updated in real-time
- Useful for displaying user info when viewing their PhotoHunts or in leaderboards

---

## PhotoHunt Management

### 11. List PhotoHunts
**GET** `/photohunts/`

**Authentication:** Required

**Query Parameters:**
- `user_generated` (optional): `true` or `false` to filter by user-generated vs system-generated
- `created_by` (optional): User ID to filter by creator
- `search` (optional): Search in name or description

**Example:** `GET /photohunts/?search=park&user_generated=true`

**Response (200 OK):**
```json
[
    {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "name": "Beautiful Park Fountain",
        "description": "Find and photograph the historic fountain in Central Park",
        "latitude": 40.7829,
        "longitude": -73.9654,
        "reference_image": "https://my-bucket.s3.amazonaws.com/photohunts/uuid.jpg?AWSAccessKeyId=...&Signature=...&Expires=1695659999",
        "difficulty": 3.5,
        "hint": "Look near the main entrance, it has bronze sculptures",
        "created_by": "550e8400-e29b-41d4-a716-446655440001",
        "created_by_name": "Jane Smith",
        "created_by_avatar": "https://my-bucket.s3.amazonaws.com/avatars/creator-uuid.jpg?AWSAccessKeyId=...&Signature=...&Expires=1695659999",
        "is_user_generated": true,
        "is_active": true,
        "created_at": "2023-09-25T10:30:00Z",
        "updated_at": "2023-09-25T10:30:00Z",
        "hunted": false
    }
]
```

**Notes:**
- `reference_image` returns a signed URL that expires in 1 hour
- `created_by_avatar` returns a signed URL for the creator's avatar (null if no avatar)
- `hunted` indicates if the current user has completed this PhotoHunt
- `difficulty` is a float from 0-5 (optional)
- `hint` is optional text to help users

### 12. Create PhotoHunt (With Image URL)
**POST** `/photohunts/`

**Authentication:** Required

**Content-Type:** `application/json`

**Request Body:**
```json
{
    "name": "Beautiful Park Fountain",
    "description": "Find and photograph the historic fountain in Central Park",
    "lat": 40.7829,
    "long": -73.9654,
    "difficulty": 3.5,
    "hint": "Look near the main entrance, it has bronze sculptures",
    "reference_image": "https://example.com/image.jpg"
}
```

### 13. Create PhotoHunt (With File Upload)
**POST** `/photohunts/`

**Authentication:** Required

**Content-Type:** `multipart/form-data`

**Form Data:**
```
name: "Beautiful Park Fountain"
description: "Find and photograph the historic fountain in Central Park"
lat: 40.7829
long: -73.9654
difficulty: 3.5
hint: "Look near the main entrance, it has bronze sculptures"
reference_image_file: [binary image file - JPG, PNG, GIF, or WebP]
```

**Response (201 Created):**
```json
{
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Beautiful Park Fountain",
    "description": "Find and photograph the historic fountain in Central Park",
    "latitude": 40.7829,
    "longitude": -73.9654,
    "reference_image": "https://my-bucket.s3.amazonaws.com/photohunts/uuid.jpg?AWSAccessKeyId=...&Signature=...&Expires=1695659999",
    "difficulty": 3.5,
    "hint": "Look near the main entrance, it has bronze sculptures",
    "created_by": "550e8400-e29b-41d4-a716-446655440001",
    "created_by_name": "John Doe",
    "created_by_avatar": "https://my-bucket.s3.amazonaws.com/avatars/creator-uuid.jpg?AWSAccessKeyId=...&Signature=...&Expires=1695659999",
    "is_user_generated": true,
    "is_active": true,
    "created_at": "2023-09-25T10:30:00Z",
    "updated_at": "2023-09-25T10:30:00Z",
    "hunted": false
}
```

### 14. Get PhotoHunt Details
**GET** `/photohunts/<uuid:pk>/`

**Authentication:** Required

**Response (200 OK):**
```json
{
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Beautiful Park Fountain",
    "description": "Find and photograph the historic fountain in Central Park",
    "latitude": 40.7829,
    "longitude": -73.9654,
    "reference_image": "https://my-bucket.s3.amazonaws.com/photohunts/uuid.jpg?AWSAccessKeyId=...&Signature=...&Expires=1695659999",
    "difficulty": 3.5,
    "hint": "Look near the main entrance, it has bronze sculptures",
    "created_by": "550e8400-e29b-41d4-a716-446655440001",
    "created_by_name": "Jane Smith",
    "created_by_avatar": "https://my-bucket.s3.amazonaws.com/avatars/creator-uuid.jpg?AWSAccessKeyId=...&Signature=...&Expires=1695659999",
    "is_user_generated": true,
    "is_active": true,
    "created_at": "2023-09-25T10:30:00Z",
    "updated_at": "2023-09-25T10:30:00Z",
    "hunted": false
}
```

### 15. Update PhotoHunt (Text Fields Only)
**PATCH** `/photohunts/<uuid:pk>/`

**Authentication:** Required (must be creator)

**Content-Type:** `application/json`

**Request Body:**
```json
{
    "name": "Updated Fountain Name",
    "description": "Updated description",
    "difficulty": 4.0,
    "hint": "Updated hint text"
}
```

### 16. Update PhotoHunt (With Image Replacement)
**PATCH** `/photohunts/<uuid:pk>/`

**Authentication:** Required (must be creator)

**Content-Type:** `multipart/form-data`

**Form Data:**
```
name: "Updated Fountain Name"
description: "Updated description"
difficulty: 4.0
hint: "Updated hint text"
reference_image_file: [binary image file - JPG, PNG, GIF, or WebP]
```

**Response (200 OK):**
```json
{
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Updated Fountain Name",
    "description": "Updated description",
    "latitude": 40.7829,
    "longitude": -73.9654,
    "reference_image": "https://my-bucket.s3.amazonaws.com/photohunts/new-uuid.jpg?AWSAccessKeyId=...&Signature=...&Expires=1695659999",
    "difficulty": 4.0,
    "hint": "Updated hint text",
    "created_by": "550e8400-e29b-41d4-a716-446655440001",
    "created_by_name": "John Doe",
    "created_by_avatar": "https://my-bucket.s3.amazonaws.com/avatars/creator-uuid.jpg?AWSAccessKeyId=...&Signature=...&Expires=1695659999",
    "is_user_generated": true,
    "is_active": true,
    "created_at": "2023-09-25T10:30:00Z",
    "updated_at": "2023-09-25T16:45:00Z",
    "hunted": false
}
```

**Notes:**
- Only the creator can update their PhotoHunts
- When replacing the reference image, the old image is automatically deleted from S3
- All fields are optional in PATCH requests (including coordinates and reference image)
- You can update text fields without providing a new image
- Coordinates (lat/long) are only required when creating new PhotoHunts

### 17. Delete PhotoHunt
**DELETE** `/photohunts/<uuid:pk>/`

**Authentication:** Required (must be creator)

**Response (204 No Content)**

**What gets deleted:**
- The PhotoHunt record
- All PhotoHunt completions for this PhotoHunt
- All associated PhotoValidations
- Reference image and all submitted images from S3

### 18. Get User's PhotoHunts
**GET** `/photohunts/my/`

**Authentication:** Required

**Response (200 OK):**
```json
[
    {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "name": "My PhotoHunt",
        "description": "A PhotoHunt I created",
        "latitude": 40.7829,
        "longitude": -73.9654,
        "reference_image": "https://my-bucket.s3.amazonaws.com/photohunts/uuid.jpg?AWSAccessKeyId=...&Signature=...&Expires=1695659999",
        "difficulty": 3.0,
        "hint": "Helpful hint",
        "created_by": "550e8400-e29b-41d4-a716-446655440001",
        "created_by_name": "John Doe",
        "created_by_avatar": "https://my-bucket.s3.amazonaws.com/avatars/creator-uuid.jpg?AWSAccessKeyId=...&Signature=...&Expires=1695659999",
        "is_user_generated": true,
        "is_active": true,
        "created_at": "2023-09-25T10:30:00Z",
        "updated_at": "2023-09-25T10:30:00Z",
        "hunted": false
    }
]
```

### 19. Get Nearby PhotoHunts
**GET** `/photohunts/nearby/`

**Authentication:** Required

**Query Parameters:**
- `lat` (required): Latitude
- `lng` (required): Longitude
- `radius` (optional): Search radius in kilometers (default: 10)

**Example:** `GET /photohunts/nearby/?lat=40.7829&lng=-73.9654&radius=5`

**Response (200 OK):**
```json
[
    {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "name": "Nearby PhotoHunt",
        "description": "A PhotoHunt near your location",
        "latitude": 40.7830,
        "longitude": -73.9655,
        "reference_image": "https://my-bucket.s3.amazonaws.com/photohunts/uuid.jpg?AWSAccessKeyId=...&Signature=...&Expires=1695659999",
        "difficulty": 2.5,
        "hint": "Look for the red door",
        "created_by": "550e8400-e29b-41d4-a716-446655440002",
        "created_by_name": "Jane Smith",
        "created_by_avatar": "https://my-bucket.s3.amazonaws.com/avatars/creator-uuid.jpg?AWSAccessKeyId=...&Signature=...&Expires=1695659999",
        "is_user_generated": true,
        "is_active": true,
        "created_at": "2023-09-25T10:30:00Z",
        "updated_at": "2023-09-25T10:30:00Z",
        "hunted": true
    }
]
```

---

## Photo Submission and Validation

### 20. Submit Photo for Validation
**POST** `/photos/submit/`

**Authentication:** Required

**Content-Type:** `multipart/form-data`

**Form Data:**
```
photohunt_id: "550e8400-e29b-41d4-a716-446655440000"
photo: [binary image file - JPG, PNG, GIF, or WebP]
```

**Response (201 Created) - Valid Submission:**
```json
{
    "completion": {
        "id": "550e8400-e29b-41d4-a716-446655440003",
        "user": "550e8400-e29b-41d4-a716-446655440001",
        "user_name": "John Doe",
        "photohunt": "550e8400-e29b-41d4-a716-446655440000",
        "photohunt_name": "Beautiful Park Fountain",
        "submitted_image": "https://my-bucket.s3.amazonaws.com/submissions/uuid.jpg?AWSAccessKeyId=...&Signature=...&Expires=1695659999",
        "validation_score": 0.85,
        "is_valid": true,
        "validation_notes": "Great match! The fountain is clearly visible.",
        "created_at": "2023-09-25T16:30:00Z"
    },
    "validation": {
        "is_valid": true,
        "similarity_score": 0.85,
        "confidence_score": 0.92,
        "notes": "Great match! The fountain is clearly visible.",
        "prompt": "Compare these two images...",
        "ai_response": "The submitted image shows the same fountain..."
    }
}
```

**Response (200 OK) - Invalid Submission:**
```json
{
    "validation": {
        "is_valid": false,
        "similarity_score": 0.23,
        "confidence_score": 0.78,
        "notes": "The submitted image doesn't match the target. Try looking for the fountain with bronze sculptures.",
        "prompt": "Compare these two images...",
        "ai_response": "The images show different subjects..."
    }
}
```

**Notes:**
- If validation fails, the uploaded image is automatically deleted
- If validation succeeds, it creates or updates a PhotoHuntCompletion record
- Users can retry submissions even after completing a PhotoHunt (replaces previous submission)
- `submitted_image` returns a signed URL that expires in 1 hour

---

## User Completions

### 21. Get User's Completions
**GET** `/completions/`

**Authentication:** Required

**Response (200 OK):**
```json
[
    {
        "id": "550e8400-e29b-41d4-a716-446655440003",
        "user": "550e8400-e29b-41d4-a716-446655440001",
        "user_name": "John Doe",
        "photohunt": "550e8400-e29b-41d4-a716-446655440000",
        "photohunt_name": "Beautiful Park Fountain",
        "submitted_image": "https://my-bucket.s3.amazonaws.com/submissions/uuid.jpg?AWSAccessKeyId=...&Signature=...&Expires=1695659999",
        "validation_score": 0.85,
        "is_valid": true,
        "validation_notes": "Great match! The fountain is clearly visible.",
        "created_at": "2023-09-25T16:30:00Z"
    }
]
```

---

## Legacy Endpoint (Still Available)

### 22. Download PhotoHunt Reference Image
**GET** `/photohunts/<uuid:pk>/download/`

**Authentication:** Required

**Response:** Redirect to presigned URL or local file URL

**Note:** This endpoint is still available but not necessary since the main PhotoHunt endpoints now return signed URLs directly in the `reference_image` field.

---

## Error Responses

### Common Error Formats

**400 Bad Request:**
```json
{
    "field_name": ["Error message for this field"],
    "non_field_errors": ["General error message"]
}
```

**401 Unauthorized:**
```json
{
    "detail": "Authentication credentials were not provided."
}
```

**403 Forbidden:**
```json
{
    "detail": "You can only modify your own PhotoHunts"
}
```

**404 Not Found:**
```json
{
    "error": "PhotoHunt not found"
}
```

**500 Internal Server Error:**
```json
{
    "error": "Failed to save image: [error details]"
}
```

---

## Important Notes for Frontend Development

### 1. **Signed URLs**
- All image URLs (avatars, reference images, submitted images) are now signed URLs that expire in 1 hour
- These URLs can be used directly in `<img>` tags or for downloads
- URLs are regenerated on each API call, so don't cache them long-term

### 2. **File Uploads**
- Use `multipart/form-data` content type for file uploads
- Supported formats: JPG, JPEG, PNG, GIF, WebP
- Files are automatically uploaded to S3 with local fallback for development

### 3. **Authentication**
- Use JWT tokens in the Authorization header: `Bearer <access_token>`
- Refresh tokens before they expire using the `/auth/token/refresh/` endpoint
- Handle 401 responses by redirecting to login

### 4. **Coordinates**
- Use `lat`/`long` in create/update requests
- Responses return `latitude`/`longitude`
- Coordinates are stored with high precision (20 digits, 15 decimal places)

### 5. **Optional Fields**
- `difficulty` (0-5 float) and `hint` (text) are optional for PhotoHunts
- `bio` and `avatar` are optional for user profiles
- Use PATCH for partial updates

### 6. **Permissions**
- Users can only edit/delete their own PhotoHunts
- Account deletion cascades to all related data and S3 objects
- Profile updates require authentication

### 7. **Validation**
- Password minimum length: 8 characters
- Email format validation on registration/login
- Image format validation for uploads
- Coordinate validation for PhotoHunt creation

This documentation should provide your frontend developer with all the information needed to integrate with the updated API!
