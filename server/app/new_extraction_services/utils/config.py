"""Configuration management for table extraction pipeline."""

from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from pathlib import Path
import yaml
import os
from loguru import logger


@dataclass
class ModelConfig:
    """Model configuration parameters."""
    tableformer_path: str = "microsoft/table-transformer-structure-recognition"
    layout_model_path: str = "microsoft/layoutlmv3-base"
    ocr_engine: str = "easyocr"
    device: str = "cpu"
    batch_size: int = 1
    confidence_threshold: float = 0.8
    cache_dir: str = "./models_cache"
    enable_advanced_tableformer: bool = True
    enable_ensemble_ocr: bool = True
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        if self.device not in ["cpu", "cuda", "mps"]:
            logger.warning(f"Unknown device '{self.device}', defaulting to 'cpu'")
            self.device = "cpu"


@dataclass
class ProcessingConfig:
    """Processing configuration parameters."""
    max_image_size: Tuple[int, int] = (2048, 2048)
    confidence_threshold: float = 0.8
    enable_multipage: bool = True
    output_format: str = "json"
    enable_ocr: bool = True
    ocr_languages: list = field(default_factory=lambda: ["en"])
    table_detection_threshold: float = 0.7
    cell_detection_threshold: float = 0.6
    merge_threshold: float = 0.1
    enable_financial_processing: bool = True
    enable_advanced_metrics: bool = True
    multipage_similarity_threshold: float = 0.85
    # Adaptive learning settings
    enable_adaptive_learning: bool = True
    pattern_matching_threshold: float = 0.6
    content_similarity_threshold: float = 0.7
    # Rotation detection settings
    enable_automatic_rotation: bool = True
    rotation_detection_threshold: float = 5.0
    enable_exif_orientation: bool = True
    enable_text_orientation: bool = True
    enable_structure_orientation: bool = True
    
    def __post_init__(self):
        """Validate processing configuration."""
        if self.output_format not in ["json", "csv", "xlsx", "pandas"]:
            logger.warning(f"Unknown output format '{self.output_format}', defaulting to 'json'")
            self.output_format = "json"


@dataclass
class APIConfig:
    """API configuration parameters."""
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 1
    max_file_size: int = 50 * 1024 * 1024  # 50MB
    allowed_extensions: list = field(default_factory=lambda: [".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".docx"])
    cors_origins: list = field(default_factory=lambda: ["*"])
    

@dataclass
class LoggingConfig:
    """Logging configuration parameters."""
    level: str = "INFO"
    format: str = "{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} | {message}"
    rotation: str = "100 MB"
    retention: str = "30 days"
    log_file: Optional[str] = "logs/table_extraction.log"


@dataclass
class Config:
    """Main configuration class."""
    models: ModelConfig = field(default_factory=ModelConfig)
    processing: ProcessingConfig = field(default_factory=ProcessingConfig)
    api: APIConfig = field(default_factory=APIConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    
    # Environment settings
    environment: str = "development"
    debug: bool = False
    
    @classmethod
    def from_yaml(cls, config_path: str) -> 'Config':
        """Load configuration from YAML file."""
        config_path = Path(config_path)
        
        if not config_path.exists():
            logger.warning(f"Configuration file {config_path} not found, using defaults")
            return cls()
        
        try:
            with open(config_path, 'r') as f:
                config_data = yaml.safe_load(f)
            
            # Create nested configs
            models_config = ModelConfig(**config_data.get('models', {}))
            processing_config = ProcessingConfig(**config_data.get('processing', {}))
            api_config = APIConfig(**config_data.get('api', {}))
            logging_config = LoggingConfig(**config_data.get('logging', {}))
            
            return cls(
                models=models_config,
                processing=processing_config,
                api=api_config,
                logging=logging_config,
                environment=config_data.get('environment', 'development'),
                debug=config_data.get('debug', False)
            )
            
        except Exception as e:
            logger.error(f"Failed to load configuration from {config_path}: {e}")
            logger.info("Using default configuration")
            return cls()
    
    @classmethod
    def from_env(cls) -> 'Config':
        """Load configuration from environment variables."""
        config = cls()
        
        # Override with environment variables if present
        config.environment = os.getenv('ENVIRONMENT', config.environment)
        config.debug = os.getenv('DEBUG', str(config.debug)).lower() == 'true'
        
        # Model config from env
        config.models.device = os.getenv('DEVICE', config.models.device)
        config.models.ocr_engine = os.getenv('OCR_ENGINE', config.models.ocr_engine)
        
        # API config from env
        config.api.host = os.getenv('HOST', config.api.host)
        config.api.port = int(os.getenv('PORT', config.api.port))
        config.api.workers = int(os.getenv('WORKERS', config.api.workers))
        
        # Logging config from env
        config.logging.level = os.getenv('LOG_LEVEL', config.logging.level)
        
        return config
    
    def save_yaml(self, config_path: str) -> None:
        """Save configuration to YAML file."""
        config_dict = {
            'models': {
                'tableformer_path': self.models.tableformer_path,
                'layout_model_path': self.models.layout_model_path,
                'ocr_engine': self.models.ocr_engine,
                'device': self.models.device,
                'batch_size': self.models.batch_size,
                'confidence_threshold': self.models.confidence_threshold,
                'cache_dir': self.models.cache_dir,
                'enable_advanced_tableformer': self.models.enable_advanced_tableformer,
                'enable_ensemble_ocr': self.models.enable_ensemble_ocr,
            },
            'processing': {
                'max_image_size': list(self.processing.max_image_size),
                'confidence_threshold': self.processing.confidence_threshold,
                'enable_multipage': self.processing.enable_multipage,
                'output_format': self.processing.output_format,
                'enable_ocr': self.processing.enable_ocr,
                'ocr_languages': self.processing.ocr_languages,
                'table_detection_threshold': self.processing.table_detection_threshold,
                'cell_detection_threshold': self.processing.cell_detection_threshold,
                'merge_threshold': self.processing.merge_threshold,
                'enable_financial_processing': self.processing.enable_financial_processing,
                'enable_advanced_metrics': self.processing.enable_advanced_metrics,
                'multipage_similarity_threshold': self.processing.multipage_similarity_threshold,
                'enable_adaptive_learning': self.processing.enable_adaptive_learning,
                'pattern_matching_threshold': self.processing.pattern_matching_threshold,
                'content_similarity_threshold': self.processing.content_similarity_threshold,
                'enable_automatic_rotation': self.processing.enable_automatic_rotation,
                'rotation_detection_threshold': self.processing.rotation_detection_threshold,
                'enable_exif_orientation': self.processing.enable_exif_orientation,
                'enable_text_orientation': self.processing.enable_text_orientation,
                'enable_structure_orientation': self.processing.enable_structure_orientation,
            },
            'api': {
                'host': self.api.host,
                'port': self.api.port,
                'workers': self.api.workers,
                'max_file_size': self.api.max_file_size,
                'allowed_extensions': self.api.allowed_extensions,
                'cors_origins': self.api.cors_origins,
            },
            'logging': {
                'level': self.logging.level,
                'format': self.logging.format,
                'rotation': self.logging.rotation,
                'retention': self.logging.retention,
                'log_file': self.logging.log_file,
            },
            'environment': self.environment,
            'debug': self.debug,
        }
        
        config_path = Path(config_path)
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(config_path, 'w') as f:
            yaml.safe_dump(config_dict, f, default_flow_style=False, indent=2)
        
        logger.info(f"Configuration saved to {config_path}")


def get_config(config_path: Optional[str] = None) -> Config:
    """Get configuration from file or environment."""
    if config_path:
        return Config.from_yaml(config_path)
    
    # Try to find config file in standard locations
    standard_paths = [
        "configs/new_extraction_config.yaml",
        "configs/default.yaml",
        "configs/config.yaml",
        "config.yaml",
        "../configs/new_extraction_config.yaml",
        "../configs/default.yaml"
    ]
    
    for path in standard_paths:
        if Path(path).exists():
            return Config.from_yaml(path)
    
    # Fallback to environment variables
    return Config.from_env()
