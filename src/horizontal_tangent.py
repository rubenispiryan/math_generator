from typing import Tuple, List, Optional, Dict
import sympy as sp
import numpy as np
import logging
from .generator import ExpressionGenerator
from .config import log_exceptions

logger = logging.getLogger(__name__)

class HorizontalTangent:
    def __init__(self):
        self.x = sp.Symbol('x')
        self.exp_gen = ExpressionGenerator(self.x)
        logger.debug("Initialized HorizontalTangent instance")

    @log_exceptions(logger)
    def get_problem_pairs(self, n: int) -> Tuple[List[str], List[str]]:
        logger.debug(f"Generating {n} problem pairs")
        problems = []
        answers = []
        for i in range(n):
            logger.debug(f"Generating problem pair {i+1}/{n}")
            problem, answer = self.get_problem_pair()
            problems.append(problem)
            answers.append(f"x = {', '.join(map(lambda x: f'{x:.1f}', answer))}")
        return problems, answers
        
    @log_exceptions(logger)
    def get_problem_pair(self) -> Tuple[str, List[float]]:
        """Generate a horizontal tangent problem and its solution."""
        for attempt in range(10):  # Max attempts to get a valid problem
            try:
                logger.debug(f"Attempt {attempt+1} to generate problem")
                # Generate a function with appropriate complexity
                f = self._generate_function()
                logger.debug(f"Generated function: {f}")
                
                # Compute derivative
                f_prime = sp.diff(f, self.x)
                logger.debug(f"Derivative: {f_prime}")
                
                # Solve f'(x) = 0
                solutions = sp.solve(f_prime, self.x)
                logger.debug(f"Raw solutions: {solutions}")
                
                # Filter real solutions and convert to floats
                real_solutions = [float(sol.evalf()) 
                                for sol in solutions 
                                if sol.is_real]
                
                if real_solutions:  # Only return if we found real solutions
                    logger.info(f"Found {len(real_solutions)} real solutions")
                    return f, sorted(real_solutions)
                else:
                    logger.debug("No real solutions found")
                    
            except Exception as e:
                logger.debug(f"Failed to generate problem: {str(e)}")
                continue
                
        raise RuntimeError("Failed to generate valid problem after multiple attempts")
    
    @log_exceptions(logger)
    def _generate_function(self) -> sp.Expr:
        """Generate a differentiable function with likely horizontal tangents."""
        logger.debug("Configuring function generator")
        # Configure generator for appropriate function types
        config = {
            'power_range': (2, 4),  # For polynomials of degree 2-4
            'p_trig': (0.3, 0.7, 0, 1),  # Moderate probability of trig functions
            'p_compose': 0.2,  # Low probability of composition
            'function_choice': [
                self.exp_gen.make_poly,
                self.exp_gen.make_trig,
                self.exp_gen.make_root,
            ]
        }
        
        self.exp_gen.update_config(config)
        expr = self.exp_gen.get_expression((1, 1))
        logger.debug(f"Generated expression: {expr}")
        return expr