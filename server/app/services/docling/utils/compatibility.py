"""Compatibility fixes for deprecated PIL features."""

import warnings
from PIL import Image

# Fix for PIL.Image.ANTIALIAS deprecation
# This is needed for EasyOCR and other libraries that haven't updated yet
if not hasattr(Image, 'ANTIALIAS'):
    # In newer Pillow versions, ANTIALIAS is replaced with Resampling.LANCZOS
    Image.ANTIALIAS = Image.Resampling.LANCZOS

# Suppress deprecation warnings for ANTIALIAS usage
warnings.filterwarnings("ignore", category=DeprecationWarning, module="PIL")

def apply_compatibility_fixes():
    """Apply all compatibility fixes."""
    # The ANTIALIAS fix is applied at module import time
    pass