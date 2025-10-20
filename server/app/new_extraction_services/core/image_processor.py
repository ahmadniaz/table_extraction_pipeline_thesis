"""Image document processor."""

from pathlib import Path
from typing import List
import numpy as np
from PIL import Image

from ..utils.config import Config
from .document_types import DocumentFormat, ProcessedDocument
from .format_detector import FormatDetector


class ImageProcessor:
    """Process image documents."""
    
    def __init__(self, config: Config, logger):
        """Initialize image processor."""
        self.config = config
        self.processing_config = config.processing
        self.logger = logger
        self.format_detector = FormatDetector()
    
    async def process(self, image_path: Path) -> ProcessedDocument:
        """Process image document."""
        self.logger.logger.info(f"Processing image document: {image_path.suffix}")
        
        try:
            # Load and validate image
            with Image.open(image_path) as img:
                # Convert to RGB if needed
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Resize if too large
                max_size = self.processing_config.max_image_size
                if img.size[0] > max_size[0] or img.size[1] > max_size[1]:
                    img.thumbnail(max_size, Image.Resampling.LANCZOS)
                    self.logger.logger.info(f"Resized image to {img.size}")
                
                # Convert to numpy array
                img_array = np.array(img)
                
                # Create page data
                page_data = {
                    'page_number': 0,
                    'width': img.size[0],
                    'height': img.size[1],
                    'elements': [],
                    'text': '',
                    'tables': []
                }
                
                # Metadata
                metadata = {
                    'original_size': img.size,
                    'mode': img.mode,
                    'format': img.format,
                    'num_pages': 1,
                    'source': 'pillow'
                }
                
                return ProcessedDocument(
                    document_path=str(image_path),
                    format=self.format_detector.detect_format(image_path),
                    pages=[page_data],
                    metadata=metadata,
                    raw_images=[img_array]
                )
                
        except Exception as e:
            self.logger.logger.error(f"Image processing failed: {e}")
            raise
    
    async def extract_images(self, processed_doc: ProcessedDocument) -> List[np.ndarray]:
        """Extract images from processed document pages."""
        if processed_doc.raw_images:
            return processed_doc.raw_images
        
        # Handle single image files
        try:
            pil_image = Image.open(processed_doc.document_path)
            image_array = np.array(pil_image.convert('RGB'))
            self.logger.logger.info(f"Loaded image file: {image_array.shape}")
            return [image_array]
        except Exception as e:
            self.logger.logger.error(f"Failed to load image file: {e}")
            blank_image = np.zeros((800, 600, 3), dtype=np.uint8)
            return [blank_image]
