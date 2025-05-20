from dataclasses import dataclass
from typing import Tuple, List, Callable, Optional
import sympy as sp
import os
import logging
import traceback
import sys
from functools import wraps
from typing import Any, Callable, TypeVar

F = TypeVar('F', bound=Callable[..., Any])

def log_exceptions(logger: logging.Logger) -> Callable[[F], F]:
    """Decorator to log exceptions with full traceback."""
    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # Get the full traceback
                exc_info = sys.exc_info()
                tb_lines = traceback.format_exception(*exc_info)
                
                # Log the error with full traceback
                logger.error(
                    f"Exception in {func.__name__} ({func.__module__}:{func.__code__.co_firstlineno})\n"
                    f"{''.join(tb_lines)}"
                )
                raise
        return wrapper
    return decorator

@dataclass
class GeneratorConfig:
    p_trig: Tuple[float, float, float, float] = (0.3, 0.5, 0.7, 0.9)
    p_hyper_trig: Tuple[float, float, float] = (0.3, 0.5, 0.7)
    p_exponent: float = 0.9
    p_log: float = 0.98
    p_root: float = 0.7
    p_compose: float = 0.3
    exp_range: Tuple[int, int] = (2, 5)
    log_base_range: Tuple[int, int] = (2, 5)
    root_degree_range: Tuple[int, int] = (3, 5)
    coeff_range: Tuple[int, int] = (1, 5)
    power_range: Tuple[int, int] = (0, 5)
    function_choice: Optional[List[Callable]] = None

    def __post_init__(self):
        if self.function_choice is None:
            self.function_choice = []

@dataclass
class VolumeConfig:
    difficulty: str = 'simple'
    x_range: Tuple[int, int] = (-10, 20)
    ab_range: Tuple[int, int] = (1, 15)
    threshold: float = 1e2
    max_attempts: int = 20
    timeout: int = 3
    plot_points: int = 2000
    figure_size: Tuple[int, int] = (8, 6)

@dataclass
class PDFConfig:
    output_dir: str = 'output'
    image_format: str = 'jpg'
    dpi: int = 200
    fontsize: int = 16

@dataclass
class LogConfig:
    """Logging configuration."""
    level: int = logging.DEBUG
    format: str = (
        '%(asctime)s - %(name)s - [%(filename)s:%(lineno)d:%(funcName)s] - '
        '%(levelname)s - %(message)s'
    )
    log_file: str = 'edugnosis_python.log'
    console_level: int = logging.INFO
    file_level: int = logging.DEBUG
    max_file_size: int = 1 * 1024 * 1024  # 1MB
    backup_count: int = 5

def setup_logging(config: LogConfig = LogConfig()) -> None:
    """Setup logging configuration with rotation and detailed error tracking."""
    # Create logs directory if it doesn't exist
    os.makedirs('logs', exist_ok=True)
    log_file = os.path.join('logs', config.log_file)
    
    # Create formatters
    formatter = logging.Formatter(config.format)
    
    # Setup rotating file handler
    from logging.handlers import RotatingFileHandler
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=config.max_file_size,
        backupCount=config.backup_count
    )
    file_handler.setLevel(config.file_level)
    file_handler.setFormatter(formatter)
    
    # Setup console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(config.console_level)
    console_handler.setFormatter(formatter)
    
    # Set third-party loggers to INFO or higher to reduce noise
    noisy_loggers = [
        'matplotlib',
        'PIL',
        'fontTools',
        'matplotlib.font_manager',
        'matplotlib.axes',
        'matplotlib.backends',
        'matplotlib.pyplot',
    ]
    
    for logger_name in noisy_loggers:
        third_party_logger = logging.getLogger(logger_name)
        third_party_logger.setLevel(logging.INFO)
    
    # Setup root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(config.level)
    
    # Remove any existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Add our handlers
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    # Log initial message with debug test
    root_logger.info(
        f"Logging initialized. Log file: {log_file}\n"
        f"Log level: File={logging.getLevelName(config.file_level)}, "
        f"Console={logging.getLevelName(config.console_level)}"
    )
    
    # Disable Matplotlib's debug logging completely
    mpl_logger = logging.getLogger('matplotlib')
    mpl_logger.setLevel(logging.WARNING)
    
    # Disable PIL's debug logging
    pil_logger = logging.getLogger('PIL')
    pil_logger.setLevel(logging.WARNING)
    
    # Log that we've configured third-party loggers
    logger = logging.getLogger(__name__)
    logger.debug("Third-party loggers configured to reduce noise") 