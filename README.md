# PhotoHunter Backend

A Django REST API backend for PhotoHunter: a scavenger hunt app similar to Geocaching where users take photos of specific locations and objects, validated using multi-modal LLMs.

## Features

- **User Authentication**: JWT-based authentication with user registration and login
- **PhotoHunt Management**: Create, read, update, and delete photo hunts
- **AI Photo Validation**: Uses LangChain with OpenAI GPT-4 Vision to validate user-submitted photos against the reference images for the photohunts (also created by users)
- **AWS S3 Integration**: Store and manage photos in AWS S3
- **PostgreSQL Database**: Robust data storage with proper relationships
- **RESTful API**: Clean API endpoints for mobile app integration

## Tech Stack

- **Backend**: Django 5.2, Django REST Framework
- **Database**: PostgreSQL 15
- **AI/ML**: LangChain, OpenAI GPT-4 Vision
- **Storage**: AWS S3
- **Package Management**: uv (Python package manager)

## Setup

### Prerequisites

- Python 3.11+
- PostgreSQL 15
- uv (Python package manager)
- AWS S3 account (for photo storage)
- OpenAI API key (for photo validation)

### Installation

1. **Clone and navigate to the backend directory**:
   ```bash
   cd photohunter-backend
   ```

2. **Install dependencies**:
   ```bash
   uv sync
   ```

3. **Set up environment variables**:
   ```bash
   cp .env.example .env
   # Edit .env with your actual values
   ```

4. **Set up PostgreSQL**:
   ```bash
   # Create database and user
   createdb photohunter_db
   psql -d photohunter_db -c "CREATE USER photohunter_user WITH PASSWORD 'your_password' CREATEDB;"
   psql -d photohunter_db -c "GRANT ALL PRIVILEGES ON DATABASE photohunter_db TO photohunter_user;"
   ```

5. **Run migrations**:
   ```bash
   uv run python manage.py migrate
   ```

6. **Create superuser**:
   ```bash
   uv run python manage.py createsuperuser
   ```

7. **Start the development server**:
   ```bash
   uv run python manage.py runserver
   ```

## Environment Variables

Create a `.env` file with the following variables:

```env
# Django Settings
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database Settings
DB_NAME=photohunter_db
DB_USER=photohunter_user
DB_PASSWORD=your-db-password
DB_HOST=localhost
DB_PORT=5432

# AWS S3 Settings
AWS_ACCESS_KEY_ID=your-aws-access-key
AWS_SECRET_ACCESS_KEY=your-aws-secret-key
AWS_STORAGE_BUCKET_NAME=photohunter-images
AWS_S3_REGION_NAME=us-east-1

# LangChain Settings
OPENAI_API_KEY=your-openai-api-key
LANGCHAIN_API_KEY=your-langchain-api-key
LANGCHAIN_TRACING_V2=false
```

## API Endpoints

### Authentication
- `POST /api/auth/register/` - User registration
- `POST /api/auth/login/` - User login
- `POST /api/auth/logout/` - User logout

### PhotoHunts
- `GET /api/photohunts/` - List all PhotoHunts
- `POST /api/photohunts/` - Create a new PhotoHunt
- `GET /api/photohunts/{id}/` - Get PhotoHunt details
- `PUT /api/photohunts/{id}/` - Update PhotoHunt
- `DELETE /api/photohunts/{id}/` - Delete PhotoHunt
- `GET /api/photohunts/my/` - Get user's PhotoHunts
- `GET /api/photohunts/nearby/` - Get nearby PhotoHunts

### Photo Submission
- `POST /api/photos/submit/` - Submit photo for validation

### User Profile
- `GET /api/profile/` - Get user profile
- `PUT /api/profile/update/` - Update user profile

### Completions
- `GET /api/completions/` - Get user's PhotoHunt completions

## Database Models

### User
- Custom user model with email as username
- Fields: id, email, name, created_at

### PhotoHunt
- Represents a scavenger hunt location
- Fields: id, name, description, latitude, longitude, reference_image, created_by, is_user_generated, is_active, created_at, updated_at

### PhotoHuntCompletion
- Tracks when a user completes a PhotoHunt
- Fields: id, user, photohunt, submitted_image, validation_score, is_valid, validation_notes, created_at

### PhotoValidation
- Stores AI validation results
- Fields: id, completion, reference_image_url, submitted_image_url, similarity_score, confidence_score, validation_prompt, ai_response, is_approved, created_at

### UserProfile
- Extended user profile information
- Fields: user, bio, avatar, total_completions, total_created, created_at, updated_at

## AI Photo Validation

The app uses LangChain with OpenAI's GPT-4 Vision model to validate user-submitted photos against reference images. The validation process:

1. Compares the submitted photo with the reference image
2. Analyzes architectural features, landmarks, and key elements
3. Provides a similarity score (0.0 to 1.0)
4. Returns confidence level and detailed notes
5. Approves or rejects the submission based on the analysis

## Development

### Running Tests
```bash
uv run python manage.py test
```

### Database Management
```bash
# Create migrations
uv run python manage.py makemigrations

# Apply migrations
uv run python manage.py migrate

# Access Django admin
# Visit http://localhost:8000/admin/
```

### Adding New Features
1. Create models in `api/models.py`
2. Create serializers in `api/serializers.py`
3. Create views in `api/views.py`
4. Add URL patterns in `api/urls.py`
5. Run migrations

## Deployment

For production deployment:

1. Set `DEBUG=False` in environment variables
2. Configure proper `ALLOWED_HOSTS`
3. Use a production database
4. Set up proper AWS S3 permissions
5. Configure static file serving
6. Use a production WSGI server (e.g., Gunicorn)
