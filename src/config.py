from dataclasses import dataclass
from typing import Tuple, List, Callable, Optional
import sympy as sp

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