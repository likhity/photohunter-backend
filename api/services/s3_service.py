import boto3
import uuid
from django.conf import settings
from botocore.exceptions import ClientError
import logging

logger = logging.getLogger(__name__)


class S3Service:
    """Service for handling AWS S3 operations"""
    
    def __init__(self):
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_S3_REGION_NAME
        )
        self.bucket_name = settings.AWS_STORAGE_BUCKET_NAME
        # Prefer explicit custom domain; otherwise use region-specific S3 endpoint
        region = settings.AWS_S3_REGION_NAME
        default_domain = f"{self.bucket_name}.s3.{region}.amazonaws.com" if region else f"{self.bucket_name}.s3.amazonaws.com"
        self.public_base_domain = getattr(settings, 'AWS_S3_CUSTOM_DOMAIN', '') or default_domain
    
    def upload_file(self, file_obj, folder='images', file_extension='jpg'):
        """
        Upload a file to S3 and return the URL
        
        Args:
            file_obj: File object to upload
            folder: S3 folder to upload to
            file_extension: File extension (jpg, png, etc.)
        
        Returns:
            str: URL of the uploaded file
        """
        try:
            # Generate unique filename
            filename = f"{folder}/{uuid.uuid4()}.{file_extension}"
            
            # Ensure we have reusable bytes for multiple attempts
            import io
            try:
                # Try to read all bytes from provided file-like
                if hasattr(file_obj, 'seek'):
                    try:
                        file_obj.seek(0)
                    except Exception:
                        pass
                file_bytes = file_obj.read()
                if file_bytes is None:
                    file_bytes = b''
            except Exception:
                # As a last resort, treat it as empty stream
                file_bytes = b''

            # Prepare ExtraArgs
            base_extra_args = {
                'ContentType': f'image/{file_extension}',
                **getattr(settings, 'AWS_S3_OBJECT_PARAMETERS', {})
            }

            # Try with ACL if configured
            acl_value = getattr(settings, 'AWS_DEFAULT_ACL', None)
            tried_without_acl = False
            # Best-effort determine file size for logging
            file_size = None
            try:
                file_size = len(file_bytes)
            except Exception:
                pass
            try:
                extra_args = dict(base_extra_args)
                if acl_value:
                    extra_args['ACL'] = acl_value
                first_buffer = io.BytesIO(file_bytes)
                self.s3_client.upload_fileobj(
                    first_buffer,
                    self.bucket_name,
                    filename,
                    ExtraArgs=extra_args
                )
            except ClientError as e:
                # If bucket blocks public ACLs or ACL isn't permitted, retry without ACL
                error_code = e.response.get('Error', {}).get('Code', '')
                if acl_value and error_code in {
                    'AccessDenied',
                    'InvalidRequest',
                    'AccessControlListNotSupported',
                    'InvalidBucketAclWithObjectOwnership',
                }:
                    tried_without_acl = True
                    # Recreate a fresh buffer for retry
                    retry_buffer = io.BytesIO(file_bytes)
                    try:
                        self.s3_client.upload_fileobj(
                            retry_buffer,
                            self.bucket_name,
                            filename,
                            ExtraArgs=base_extra_args
                        )
                    except ClientError as e2:
                        raise
                else:
                    raise
            
            # Return public URL
            return f"https://{self.public_base_domain}/{filename}"
        except ClientError as e:
            logger.error(f"Error uploading file to S3: {e}")
            raise Exception("Failed to upload file to S3")
        except Exception as e:
            logger.error(f"Unexpected error during S3 upload: {e}")
            raise Exception("Failed to upload file to S3")

    def generate_presigned_get_url(self, key: str, expiration: int = 900) -> str:
        """Generate a presigned GET URL for an S3 object key."""
        try:
            return self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': key},
                ExpiresIn=expiration,
            )
        except ClientError as e:
            logger.error(f"Error generating presigned URL: {e}")
            raise Exception("Failed to generate presigned URL")

    def extract_key_from_url(self, url: str) -> str:
        """Extract S3 key from a URL that uses the configured public domain."""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            path = parsed.path or ''
            if path.startswith('/'):
                path = path[1:]
            return path
        except Exception:
            return url
        
    
    def upload_base64_image(self, base64_data, folder='images', file_extension='jpg'):
        """
        Upload a base64 encoded image to S3
        
        Args:
            base64_data: Base64 encoded image data
            folder: S3 folder to upload to
            file_extension: File extension (jpg, png, etc.)
        
        Returns:
            str: URL of the uploaded file
        """
        import base64
        import io
        
        try:
            # Decode base64 data
            image_data = base64.b64decode(base64_data)
            file_obj = io.BytesIO(image_data)
            
            return self.upload_file(file_obj, folder, file_extension)
            
        except Exception as e:
            logger.error(f"Error uploading base64 image to S3: {e}")
            raise Exception("Failed to upload base64 image to S3")
    
    def delete_file(self, file_url):
        """
        Delete a file from S3
        
        Args:
            file_url: URL of the file to delete
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Extract key from URL
            key = file_url.split(f"{settings.AWS_S3_CUSTOM_DOMAIN}/")[-1]
            
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=key
            )
            
            return True
            
        except ClientError as e:
            logger.error(f"Error deleting file from S3: {e}")
            return False
    
    def get_presigned_url(self, key, expiration=3600):
        """
        Generate a presigned URL for S3 object
        
        Args:
            key: S3 object key
            expiration: URL expiration time in seconds
        
        Returns:
            str: Presigned URL
        """
        try:
            response = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': key},
                ExpiresIn=expiration
            )
            return response
            
        except ClientError as e:
            logger.error(f"Error generating presigned URL: {e}")
            raise Exception("Failed to generate presigned URL")
    
    def list_files(self, prefix='', max_keys=1000):
        """
        List files in S3 bucket
        
        Args:
            prefix: Prefix to filter files
            max_keys: Maximum number of keys to return
        
        Returns:
            list: List of file objects
        """
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix,
                MaxKeys=max_keys
            )
            
            return response.get('Contents', [])
            
        except ClientError as e:
            logger.error(f"Error listing files from S3: {e}")
            return []
