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
            
            # Upload file
            self.s3_client.upload_fileobj(
                file_obj,
                self.bucket_name,
                filename,
                ExtraArgs={
                    'ACL': settings.AWS_DEFAULT_ACL,
                    'ContentType': f'image/{file_extension}',
                    **settings.AWS_S3_OBJECT_PARAMETERS
                }
            )
            
            # Return public URL
            return f"https://{settings.AWS_S3_CUSTOM_DOMAIN}/{filename}"
            
        except ClientError as e:
            logger.error(f"Error uploading file to S3: {e}")
            raise Exception("Failed to upload file to S3")
    
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
