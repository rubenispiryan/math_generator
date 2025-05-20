import sympy as sp
import logging
from src.generator import ExpressionGenerator
from src.config import log_exceptions

logger = logging.getLogger(__name__)

class TaylorSeries:
    def __init__(self):
        self.x = sp.Symbol('x')
        self.generator = ExpressionGenerator(self.x)
        logger.debug("Initialized TaylorSeries instance")

    @log_exceptions(logger)
    def _round_coefficients(self, expr, decimals=2):
        logger.debug(f"Rounding coefficients to {decimals} decimal places")
        terms = expr.expand().as_ordered_terms()
        rounded_terms = []

        for term in terms:
            coeff, rest = term.as_coeff_Mul()
            if coeff.is_number and coeff.is_real and coeff.is_Number:
                coeff = sp.Float(round(float(coeff), decimals))
            rounded_terms.append(coeff * rest)

        return sp.Add(*rounded_terms)

    @log_exceptions(logger)
    def get_problem_pair(self, problem_length: tuple[int, int], a = 1, tries = 3):
        logger.debug(f"Generating Taylor series problem with length {problem_length}, around point {a}, {tries} tries remaining")
        try:
            expr = self.generator.get_expression(problem_length)
            logger.debug(f"Generated expression: {expr}")
            exprs = []
            for exp in expr.as_ordered_terms():
                exprs.append(exp.expand().series(self.x, a, 2))
            result = self._round_coefficients(sum(exprs).removeO())
            logger.debug(f"Computed Taylor series: {result}")
            return expr, result
        except Exception as e:
            logger.warning(f"Failed to generate problem: {str(e)}")
            if tries > 0:
                logger.debug(f"Retrying with {tries-1} attempts remaining")
                return self.get_problem_pair(problem_length, a=a, tries=tries - 1)
            raise e

    @log_exceptions(logger)
    def get_problem_pairs(self, n, problem_length=(1, 2), a = 1):
        logger.debug(f"Generating {n} Taylor series problems")
        problems, answers = [], []
        for i in range(n):
            logger.debug(f"Generating problem pair {i+1}/{n}")
            p, ans = self.get_problem_pair(problem_length, a)
            problems.append(p)
            answers.append(ans)
        return problems, answers


if __name__ == '__main__':
    taylor = TaylorSeries()
    print(taylor.get_problem_pair((1, 2)))