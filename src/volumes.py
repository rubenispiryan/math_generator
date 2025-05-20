from multiprocessing import Queue, Process
from typing import Tuple, List, Optional, Union, Dict
import logging
import os
import numpy as np

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import sympy as sp

from .generator import ExpressionGenerator
from .config import VolumeConfig, log_exceptions

logger = logging.getLogger(__name__)

class Volumes:
    def __init__(self, filename: str, config: Optional[VolumeConfig] = None):
        self.filename = filename
        self.x = sp.Symbol('x')
        self.config = config or VolumeConfig()
        self.exp_gen = ExpressionGenerator(self.x)
        self.image_index = 0
        self.a: Optional[float] = None
        self.b: Optional[float] = None
        
        logger.debug(f"Initializing Volumes with filename: {filename}")
        
        # Pre-create figure with standard settings
        self.fig, self.ax = plt.subplots(figsize=self.config.figure_size)
        self._setup_plot_style()
        
        # Create output directory once
        os.makedirs('output', exist_ok=True)
        
        # Cache for x values to avoid regeneration
        self._x_cache: Dict[Tuple[int, int], np.ndarray] = {}
        logger.info("Volumes instance initialized successfully")

    def _setup_plot_style(self) -> None:
        """Setup standard plot styling to avoid repeated calls."""
        self.ax.grid(True, which='both', linestyle="--", linewidth=0.5)
        self.ax.set_xlabel("$x$", fontsize=14)
        self.ax.set_ylabel("$f(x)$", fontsize=14)
        self.ax.set_title("Graph of the Function", fontsize=16)
        self.ax.axhline(0, color='black', linewidth=1)
        self.ax.axvline(0, color='black', linewidth=1)

    @log_exceptions(logger)
    def get_problem_pairs(self, n: int, difficulty: str, x_range: Tuple[int, int]) -> Tuple[List[sp.Expr], List[sp.Expr]]:
        """Generate n pairs of problems and their answers."""
        logger.info(f"Generating {n} problem pairs with difficulty: {difficulty}")
        problems = []
        answers = []
        for i in range(n):
            logger.debug(f"Generating problem pair {i+1}/{n}")
            try:
                p, ans = self.get_problem_pair(difficulty, x_range)
                problems.append(p)
                answers.append(ans)
            except Exception as e:
                logger.error(f"Failed to generate problem pair {i+1}: {str(e)}")
                raise
        return problems, answers

    def _try_integrate(self, expr: sp.Expr, var: sp.Symbol, queue: Queue) -> None:
        """Attempt to integrate the expression in a separate process."""
        try:
            result = sp.integrate(expr, var)
            queue.put(result)
        except Exception as e:
            queue.put(e)

    def _integrate_with_timeout(self, expr: sp.Expr, var: sp.Symbol, timeout: int = 3) -> Union[sp.Expr, int]:
        """Integrate with timeout protection."""
        queue = Queue()
        p = Process(target=self._try_integrate, args=(expr, var, queue))
        p.start()
        p.join(timeout)
        
        if p.is_alive():
            p.terminate()
            p.join()
            return -1
        
        result = queue.get()
        return result if not isinstance(result, Exception) else -1

    @log_exceptions(logger)
    def get_problem_pair(self, difficulty: str, x_range: Tuple[int, int]) -> Tuple[sp.Expr, sp.Expr]:
        """Generate a single problem-answer pair."""
        logger.debug(f"Generating problem pair with difficulty {difficulty}")
        for attempt in range(self.config.max_attempts):
            logger.debug(f"Attempt {attempt + 1}/{self.config.max_attempts}")
            p = sp.simplify(self._get_problem(x_range, difficulty))
            integral_result = self._integrate_with_timeout(p, (self.x, self.a, self.b))

            if integral_result == -1 or isinstance(integral_result, Exception):
                logger.debug("Integration failed or timed out")
                self.image_index -= 1
                continue

            ans = sp.pi * integral_result
            self.a, self.b = None, None
            simpl = sp.expand(sp.simplify(ans))

            if ans == sp.nan or len(simpl.as_ordered_terms()) > 2:
                logger.debug("Invalid answer or too complex")
                self.image_index -= 1
                continue

            logger.debug("Successfully generated problem pair")
            return p, sp.simplify(ans)

        error_msg = "Failed to generate valid problem after multiple attempts"
        logger.error(error_msg)
        raise RuntimeError(error_msg)

    @log_exceptions(logger)
    def _get_x_values(self, x_range: Tuple[int, int]) -> np.ndarray:
        """Get or create cached x values for the given range."""
        if x_range not in self._x_cache:
            logger.debug(f"Creating new x values cache for range {x_range}")
            self._x_cache[x_range] = np.linspace(x_range[0], x_range[1], self.config.plot_points)
        return self._x_cache[x_range]

    def _get_problem(self, x_range: Tuple[int, int], difficulty: str = 'simple', debug: bool = False) -> Optional[sp.Expr]:
        """Generate a problem based on difficulty level."""
        config = self._get_difficulty_config(difficulty)
        if config is None:
            logger.error(f'Unknown difficulty: {difficulty}')
            return None

        self.exp_gen.update_config(config)
        p = self.exp_gen.get_expression((1, 1) if difficulty == 'simple' else (2, 2))
        p = sp.diff(p, self.x)

        try:
            self._create_graph(p, x_range)
        except Exception as e:
            if debug:
                logger.error(f'Failed to render equation: {str(e)}')
            return self._get_problem(x_range, difficulty)

        return p

    def _get_difficulty_config(self, difficulty: str) -> Optional[dict]:
        """Get configuration based on difficulty level."""
        if difficulty == 'simple':
            return {
                'power_range': (1, 3),
                'p_trig': (0.5, 0.9, 0, 1),
                'p_compose': 0,
                'function_choice': [
                    self.exp_gen.make_poly,
                    self.exp_gen.make_exponent,
                    self.exp_gen.make_log,
                    self.exp_gen.make_root,
                ]
            }
        elif difficulty == 'hard':
            return {
                'power_range': (1, 3),
                'p_trig': (0.5, 0.9, 0, 1),
                'p_compose': 0,
                'function_choice': [
                    self.exp_gen.make_poly,
                    self.exp_gen.make_exponent,
                    self.exp_gen.make_log,
                    self.exp_gen.make_root,
                    self.exp_gen.make_reciprocal,
                    self.exp_gen.make_trig,
                ]
            }
        elif difficulty == 'extreme':
            return {
                'p_trig': (0.5, 0.9, 0, 1),
                'function_choice': self.exp_gen.config.function_choice
            }
        return None

    def _create_graph(self, f: sp.Expr, x_range: Tuple[int, int], debug: bool = False) -> None:
        """Create and save a graph of the function."""
        # Get cached x values
        x_vals = self._get_x_values(x_range)
        
        # Convert the symbolic function to a numerical function
        f_lambdified = sp.lambdify(self.x, f, 'numpy')

        # Calculate y values with error handling
        with np.errstate(divide='ignore', invalid='ignore'):
            y_vals = f_lambdified(x_vals)

        # Efficient filtering using boolean indexing
        mask = np.isfinite(y_vals) & (np.abs(y_vals) <= self.config.threshold)
        x_filtered = x_vals[mask]
        y_filtered = y_vals[mask]

        if len(x_filtered) == 0:
            if debug:
                logger.error(f'Invalid x values: {x_vals}')
            raise ValueError("No valid points to plot")

        # Calculate boundaries
        self._calculate_boundaries((np.min(x_filtered), np.max(x_filtered)))

        # Update plot
        self._update_plot(f, x_filtered, y_filtered)

    def _calculate_boundaries(self, x_range: Tuple[float, float]) -> None:
        """Calculate the integration boundaries."""
        x_min, x_max = x_range
        mid_point = (x_max + x_min) / 2
        
        # More efficient boundary calculation
        self.a = np.clip(np.ceil(x_min), x_min, mid_point)
        self.b = np.clip(self.a + 1, self.a + 1, np.ceil(x_max))

    def _update_plot(self, f: sp.Expr, x_vals: np.ndarray, y_vals: np.ndarray) -> None:
        """Update the plot with new data."""
        # Clear previous plot content while keeping the style
        self.ax.clear()
        self._setup_plot_style()
        
        # Plot new data
        self.ax.plot(x_vals, y_vals, label=f"${sp.latex(f)}$", linewidth=2, color="b")
        self.ax.axvline(self.a, color='r', linestyle='--', linewidth=2, label=f"$x = {self.a}$")
        self.ax.axvline(self.b, color='g', linestyle='--', linewidth=2, label=f"$x = {self.b}$")
        self.ax.legend(fontsize=14)
        
        # Save plot
        self.fig.savefig(f'./output/{self.filename}_{self.image_index}.jpg',
                        format='jpg', bbox_inches='tight')
        self.image_index += 1

    def __del__(self):
        """Cleanup matplotlib resources."""
        plt.close(self.fig)

if __name__ == "__main__":
    vols = Volumes('templates/volumes.xml')
    vols.get_problem_pair('extreme', (1, 15))
    vols.get_problem_pair('hard', (1, 15))
    vols.get_problem_pair('simple', (1, 15))