"""Format detection for document processing."""

from pathlib import Path
from .document_types import DocumentFormat


class FormatDetector:
    """Detect document format based on file extension."""
    
    def __init__(self):
        """Initialize format detector."""
        # Format detection mappings
        self.format_mappings = {
            '.pdf': DocumentFormat.PDF,
            '.png': DocumentFormat.PNG,
            '.jpg': DocumentFormat.JPEG,
            '.jpeg': DocumentFormat.JPEG,
            '.tiff': DocumentFormat.TIFF,
            '.tif': DocumentFormat.TIFF,
            '.docx': DocumentFormat.DOCX
        }
    
    def detect_format(self, document_path: Path) -> DocumentFormat:
        """Detect document format based on file extension."""
        extension = document_path.suffix.lower()
        return self.format_mappings.get(extension, DocumentFormat.UNKNOWN)
