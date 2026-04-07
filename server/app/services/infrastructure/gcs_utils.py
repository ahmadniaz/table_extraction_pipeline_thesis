import os
import tempfile
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from google.cloud import storage
from google.auth import default
from google.cloud.exceptions import NotFound, GoogleCloudError
from dotenv import load_dotenv

load_dotenv()

# GCS Configuration
GCS_BUCKET_NAME = "pdf_extraction_files_saver"
GOOGLE_CLOUD_PROJECT_ID = os.environ.get('GOOGLE_CLOUD_PROJECT_ID', 'pdf-tables-extractor-465009')

# Initialize logger
logger = logging.getLogger(__name__)

class GCSService:
    """Google Cloud Storage service for file operations."""
    
    def __init__(self):
        self.bucket_name = GCS_BUCKET_NAME
        self.project_id = GOOGLE_CLOUD_PROJECT_ID
        self.client = None
        self.bucket = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize Google Cloud Storage client."""
        try:
            # Set up environment variables if not already set (same as DocAI setup)
            if not os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
                # Look for the credentials file in multiple possible locations
                possible_paths = [
                    # Render secrets directory (production - root access)
                    "/etc/secrets/pdf-tables-extractor-465009-d9172fd0045d.json",
                    # Docker container path (production - fallback)
                    "/app/pdf-tables-extractor-465009-d9172fd0045d.json",
                    # Local development path (your server directory)
                    os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "pdf-tables-extractor-465009-d9172fd0045d.json"),
                    # Current working directory
                    os.path.join(os.getcwd(), "pdf-tables-extractor-465009-d9172fd0045d.json"),
                ]
                
                creds_file = None
                for path in possible_paths:
                    if os.path.exists(path):
                        creds_file = path
                        break
                
                if creds_file:
                    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = creds_file
                    logger.info(f"✅ Set GOOGLE_APPLICATION_CREDENTIALS to: {creds_file}")
                else:
                    logger.error(f"❌ Credentials file not found. Tried paths: {possible_paths}")
                    self.client = None
                    self.bucket = None
                    return
            
            # Set project ID if not already set
            if not os.getenv("GOOGLE_CLOUD_PROJECT_ID"):
                os.environ["GOOGLE_CLOUD_PROJECT_ID"] = "pdf-tables-extractor-465009"
                logger.info("✅ Set GOOGLE_CLOUD_PROJECT_ID to: pdf-tables-extractor-465009")
            
            # Get credentials from environment
            credentials, project_id = default()
            
            if not project_id:
                project_id = self.project_id
            
            if not project_id:
                logger.error("❌ Google Cloud Project ID not found. Set GOOGLE_CLOUD_PROJECT_ID environment variable")
                self.client = None
                self.bucket = None
                return
            
            # Initialize GCS client
            self.client = storage.Client(credentials=credentials, project=project_id)
            self.bucket = self.client.bucket(self.bucket_name)
            
            logger.info(f"✅ GCS initialized - Project: {project_id}, Bucket: {self.bucket_name}")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize GCS: {e}")
            self.client = None
            self.bucket = None
    
    def is_available(self) -> bool:
        """Check if GCS is available and properly configured."""
        return self.client is not None and self.bucket is not None
    
    def upload_file(self, file_path: str, gcs_key: str, content_type: str = None) -> bool:
        """
        Upload a file to Google Cloud Storage.
        
        Args:
            file_path: Local path to the file to upload
            gcs_key: GCS object key (path in bucket)
            content_type: MIME type of the file
            
        Returns:
            bool: True if upload successful, False otherwise
        """
        if not self.is_available():
            logger.error("GCS not available or not properly configured")
            return False
        
        try:
            # Determine content type if not provided
            if not content_type:
                content_type = self._get_content_type(file_path)
            
            # Create blob
            blob = self.bucket.blob(gcs_key)
            
            # Upload file
            blob.upload_from_filename(file_path, content_type=content_type)
            
            logger.info(f"✅ File uploaded to GCS: {gcs_key}")
            return True
            
        except GoogleCloudError as e:
            logger.error(f"GCS upload error: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error uploading to GCS: {e}")
            return False
    
    def upload_file_from_bytes(self, file_content: bytes, gcs_key: str, content_type: str = None) -> bool:
        """
        Upload file content from bytes to Google Cloud Storage.
        
        Args:
            file_content: File content as bytes
            gcs_key: GCS object key (path in bucket)
            content_type: MIME type of the file
            
        Returns:
            bool: True if upload successful, False otherwise
        """
        if not self.is_available():
            logger.error("GCS not available or not properly configured")
            return False
        
        try:
            # Create blob
            blob = self.bucket.blob(gcs_key)
            
            # Upload from bytes
            blob.upload_from_string(file_content, content_type=content_type)
            
            logger.info(f"✅ File uploaded to GCS from bytes: {gcs_key}")
            return True
            
        except GoogleCloudError as e:
            logger.error(f"GCS upload error: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error uploading to GCS: {e}")
            return False
    
    def download_file(self, gcs_key: str, local_path: str = None) -> Optional[str]:
        """
        Download a file from Google Cloud Storage.
        
        Args:
            gcs_key: GCS object key (path in bucket)
            local_path: Optional local path to save the file. If None, creates a temporary file.
        
        Returns:
            str: Path to the downloaded file, or None if download failed
        """
        if not self.is_available():
            logger.error("GCS not available or not properly configured")
            return None
        
        try:
            if local_path is None:
                # Create a temporary file
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
                local_path = temp_file.name
                temp_file.close()
            
            # Get blob
            blob = self.bucket.blob(gcs_key)
            
            # Check if blob exists
            if not blob.exists():
                logger.error(f"File not found in GCS: {gcs_key}")
                return None
            
            # Download file
            blob.download_to_filename(local_path)
            
            logger.info(f"✅ File downloaded from GCS: {gcs_key} to {local_path}")
            return local_path
            
        except NotFound:
            logger.error(f"File not found in GCS: {gcs_key}")
            return None
        except GoogleCloudError as e:
            logger.error(f"GCS download error: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error downloading from GCS: {e}")
            return None
    
    def get_file_url(self, gcs_key: str) -> str:
        """
        Get the public URL for a file in GCS.
        
        Args:
            gcs_key: GCS object key (path in bucket)
            
        Returns:
            str: Public URL of the file
        """
        return f"https://storage.googleapis.com/{self.bucket_name}/{gcs_key}"
    
    def generate_signed_url(self, gcs_key: str, expiration_hours: int = 1) -> Optional[str]:
        """
        Generate a signed URL for a file in GCS with proper headers for PDF inline viewing.
        
        Args:
            gcs_key: GCS object key (path in bucket)
            expiration_hours: Hours until the URL expires
            
        Returns:
            str: Signed URL with proper response headers, or None if generation failed
        """
        if not self.is_available():
            logger.error("GCS not available or not properly configured")
            return None
        
        try:
            # Get blob
            blob = self.bucket.blob(gcs_key)
            
            # Check if blob exists
            if not blob.exists():
                logger.error(f"File not found in GCS: {gcs_key}")
                return None
            
            # Determine content type based on file extension
            content_type = 'application/pdf' if gcs_key.lower().endswith('.pdf') else 'application/octet-stream'
            
            # Generate signed URL with proper response headers for PDF inline viewing
            expiration = datetime.utcnow() + timedelta(hours=expiration_hours)
            url = blob.generate_signed_url(
                version="v4",
                expiration=expiration,
                method="GET",
                response_type=content_type,
                response_disposition='inline'  # Critical for inline viewing instead of download
            )
            
            logger.info(f"✅ Generated signed URL for GCS file with inline headers: {gcs_key}")
            return url
            
        except NotFound:
            logger.error(f"File not found in GCS: {gcs_key}")
            return None
        except GoogleCloudError as e:
            logger.error(f"GCS signed URL error: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error generating signed URL: {e}")
            return None
    
    def copy_file(self, source_key: str, dest_key: str) -> bool:
        """
        Copy a file within Google Cloud Storage.
        
        Args:
            source_key: Source GCS object key (path in bucket)
            dest_key: Destination GCS object key (path in bucket)
            
        Returns:
            bool: True if copy successful, False otherwise
        """
        if not self.is_available():
            logger.error("GCS not available or not properly configured")
            return False
        
        try:
            # Get source blob
            source_blob = self.bucket.blob(source_key)
            
            # Check if source exists
            if not source_blob.exists():
                logger.error(f"Source file not found in GCS: {source_key}")
                return False
            
            # Copy to destination
            destination_blob = self.bucket.copy_blob(
                source_blob, self.bucket, dest_key
            )
            
            logger.info(f"✅ File copied in GCS: {source_key} -> {dest_key}")
            return True
            
        except NotFound:
            logger.error(f"Source file not found in GCS: {source_key}")
            return False
        except GoogleCloudError as e:
            logger.error(f"GCS copy error: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error copying in GCS: {e}")
            return False
    
    def delete_file(self, gcs_key: str) -> bool:
        """
        Delete a file from Google Cloud Storage.
        
        Args:
            gcs_key: GCS object key (path in bucket)
            
        Returns:
            bool: True if deletion successful, False otherwise
        """
        if not self.is_available():
            logger.error("GCS not available or not properly configured")
            return False
        
        try:
            # Get blob
            blob = self.bucket.blob(gcs_key)
            
            # Delete blob
            blob.delete()
            
            logger.info(f"✅ File deleted from GCS: {gcs_key}")
            return True
            
        except NotFound:
            logger.warning(f"File not found in GCS for deletion: {gcs_key}")
            return True  # Consider it successful if file doesn't exist
        except GoogleCloudError as e:
            logger.error(f"GCS deletion error: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error deleting from GCS: {e}")
            return False
    
    def file_exists(self, gcs_key: str) -> bool:
        """
        Check if a file exists in Google Cloud Storage.
        
        Args:
            gcs_key: GCS object key (path in bucket)
            
        Returns:
            bool: True if file exists, False otherwise
        """
        if not self.is_available():
            return False
        
        try:
            blob = self.bucket.blob(gcs_key)
            return blob.exists()
        except Exception as e:
            logger.error(f"Error checking file existence in GCS: {e}")
            return False
    
    def get_file_metadata(self, gcs_key: str) -> Optional[Dict[str, Any]]:
        """
        Get metadata for a file in Google Cloud Storage.
        
        Args:
            gcs_key: GCS object key (path in bucket)
            
        Returns:
            dict: File metadata, or None if not found
        """
        if not self.is_available():
            return None
        
        try:
            blob = self.bucket.blob(gcs_key)
            
            if not blob.exists():
                return None
            
            # Reload to get metadata
            blob.reload()
            
            return {
                'name': blob.name,
                'size': blob.size,
                'content_type': blob.content_type,
                'created': blob.time_created,
                'updated': blob.updated,
                'etag': blob.etag,
                'md5_hash': blob.md5_hash
            }
            
        except Exception as e:
            logger.error(f"Error getting file metadata from GCS: {e}")
            return None
    
    def _get_content_type(self, file_path: str) -> str:
        """
        Determine content type based on file extension.
        
        Args:
            file_path: Path to the file
            
        Returns:
            str: MIME type
        """
        import mimetypes
        
        content_type, _ = mimetypes.guess_type(file_path)
        if content_type:
            return content_type
        
        # Fallback for common file types
        if file_path.lower().endswith('.pdf'):
            return 'application/pdf'
        elif file_path.lower().endswith(('.xlsx', '.xls')):
            return 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        elif file_path.lower().endswith('.docx'):
            return 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        else:
            return 'application/octet-stream'

# Global GCS service instance
gcs_service = GCSService()

# Convenience functions for backward compatibility with S3 utils
def upload_file_to_gcs(file_path: str, gcs_key: str) -> bool:
    """Upload file to GCS (replaces upload_file_to_s3)."""
    return gcs_service.upload_file(file_path, gcs_key)

def get_gcs_file_url(gcs_key: str) -> str:
    """Get GCS file URL (replaces get_s3_file_url)."""
    return gcs_service.get_file_url(gcs_key)

def download_file_from_gcs(gcs_key: str, local_path: str = None) -> Optional[str]:
    """Download file from GCS (replaces download_file_from_s3)."""
    return gcs_service.download_file(gcs_key, local_path)

def generate_gcs_signed_url(gcs_key: str, expiration_hours: int = 1) -> Optional[str]:
    """Generate signed URL for GCS file (replaces generate_presigned_url)."""
    return gcs_service.generate_signed_url(gcs_key, expiration_hours)

def copy_gcs_file(source_key: str, dest_key: str) -> bool:
    """Copy file within GCS."""
    return gcs_service.copy_file(source_key, dest_key)

def delete_gcs_file(gcs_key: str) -> bool:
    """Delete file from GCS."""
    return gcs_service.delete_file(gcs_key)
