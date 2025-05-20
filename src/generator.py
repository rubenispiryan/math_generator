from typing import List, Callable, Optional, Union, Tuple
import sympy as sp
import numpy as np
import logging
from random import uniform, randint, choice
from .config import GeneratorConfig, log_exceptions

logger = logging.getLogger(__name__)

class ExpressionGenerator:
    def __init__(self, symbol: sp.Symbol, config: Optional[GeneratorConfig] = None):
        self._symbol = symbol
        self.symbol = symbol
        self.config = config or GeneratorConfig()
        logger.debug("Initialized ExpressionGenerator")

        # Initialize default functions if not provided
        if not self.config.function_choice:
            self.config.function_choice = [
            self.make_poly,
            self.make_exponent,
            self.make_log,
            self.make_root,
            self.make_reciprocal,
            self.make_trig,
            self.make_hyper_trig,
        ]

    @log_exceptions(logger)
    def update_config(self, new_config: dict) -> None:
        """Update the generator configuration with new values."""
        logger.debug(f"Updating config with: {new_config}")
        for key, value in new_config.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
            else:
                logger.warning(f"Unknown config parameter: {key}")

    def make_trig(self) -> None:
        """Apply a trigonometric function to the current symbol."""
        prob = uniform(0, 1)
        if prob < self.config.p_trig[0]:
            self._symbol = sp.sin(self._symbol)
        elif prob < self.config.p_trig[1]:
            self._symbol = sp.cos(self._symbol)
        elif prob < self.config.p_trig[2]:
            self._symbol = sp.tan(self._symbol)
        elif prob < self.config.p_trig[3]:
            self._symbol = sp.sec(self._symbol)
        else:
            self._symbol = sp.cot(self._symbol)

    def make_hyper_trig(self) -> None:
        """Apply a hyperbolic trigonometric function to the current symbol."""
        prob = uniform(0, 1)
        if prob < self.config.p_hyper_trig[0]:
            self._symbol = sp.sinh(self._symbol)
        elif prob < self.config.p_hyper_trig[1]:
            self._symbol = sp.cosh(self._symbol)
        elif prob < self.config.p_hyper_trig[2]:
            self._symbol = sp.tanh(self._symbol)
        else:
            self._symbol = sp.sech(self._symbol)

    def make_poly(self) -> None:
        """Keep the current symbol as a polynomial term."""
        self._symbol = self._symbol

    def make_exponent(self) -> None:
        """Apply an exponential function to the current symbol."""
        prob = uniform(0, 1)
        if prob < self.config.p_exponent:
            self._symbol = sp.exp(self._symbol)
        else:
            a = randint(*self.config.exp_range)
            self._symbol = a ** self._symbol

    def make_log(self) -> None:
        """Apply a logarithmic function to the current symbol."""
        prob = uniform(0, 1)
        if prob < self.config.p_log:
            self._symbol = sp.ln(self._symbol)
        else:
            a = randint(*self.config.log_base_range)
            self._symbol = sp.log(self._symbol, a)

    def make_root(self) -> None:
        """Apply a root function to the current symbol."""
        prob = uniform(0, 1)
        if prob < self.config.p_root:
            self._symbol = sp.sqrt(self._symbol)
        else:
            a = randint(*self.config.root_degree_range)
            self._symbol = self._symbol ** sp.Rational(1, a)

    def make_reciprocal(self) -> None:
        """Apply a reciprocal function to the current symbol."""
        self._symbol = 1 / self._symbol

    def get_element(self) -> sp.Expr:
        """Generate a single element of the expression."""
        choice(self.config.function_choice)()
        a = randint(*self.config.coeff_range)
        b = randint(*self.config.power_range)
        return a * self._symbol ** b

    def get_composition(self) -> sp.Expr:
        """Generate a composition of functions."""
        self.get_element()
        self.get_element()
        return self._symbol

    @log_exceptions(logger)
    def get_expression(self, length_range: tuple[int, int]) -> sp.Expr:
        """Generate a complete expression with the specified length range."""
        logger.debug(f"Generating expression with length range: {length_range}")
        length = randint(*length_range)
        problem = sp.Integer(0)
        
        for _ in range(length):
            self._symbol = self.symbol
            prob = uniform(0, 1)
            if prob < self.config.p_compose:
                problem += self.get_composition()
            else:
                problem += self.get_element()
            problem += self._symbol
            
        self._symbol = self.symbol
        return problem