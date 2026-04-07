"""
Configuration constants for Google Document AI extractor.
"""

# Critical Configuration Parameters
HEADER_CONFIDENCE_THRESHOLD = 0.3
CELL_CONFIDENCE_THRESHOLD = 0.2
PATTERN_MATCH_THRESHOLD = 0.6
HEADER_SIMILARITY_THRESHOLD = 0.8

# Processing parameters
MAX_RETRIES = 3

# Chunking parameters
REGULAR_MODE_MAX_PAGES = 15
IMAGELESS_MODE_MAX_PAGES = 30
CHUNK_SIZE = 15  # Pages per chunk for large documents

# Spatial clustering parameters
ROW_THRESHOLD = 20  # pixels for Y-axis proximity

# Table structure parameters
MIN_TABLE_WIDTH = 50  # pixels
MIN_TABLE_HEIGHT = 50  # pixels

# Credentials file locations (in order of preference)
CREDENTIALS_PATHS = [
    # Render secrets directory (production - root access)
    "/etc/secrets/pdf-tables-extractor-465009-d9172fd0045d.json",
    # Docker container path (production - fallback)
    "/app/pdf-tables-extractor-465009-d9172fd0045d.json",
]

# Default project configuration
DEFAULT_PROJECT_ID = "pdf-tables-extractor-465009"
DEFAULT_PROCESSOR_ID = "521303e404fb7809"
DEFAULT_LOCATION = "us"  # or "eu"

