import sympy as sp
import logging
from src.generator import ExpressionGenerator
from src.config import log_exceptions

logger = logging.getLogger(__name__)

class Derivative:
    def __init__(self):
        symbol = sp.Symbol('x')
        self._exp_gen = ExpressionGenerator(symbol)
        logger.debug("Initialized Derivative instance")

    @log_exceptions(logger)
    def get_problem_pair(self, problem_length=(2, 4), answer_length=None, ans_zero=True):
        logger.debug(f"Generating problem pair with length {problem_length}, answer_length={answer_length}, ans_zero={ans_zero}")
        x = sp.symbols('x')
        while True:
            problem = self._exp_gen.get_expression(problem_length)
            logger.debug(f"Generated problem: {problem}")
            answer = sp.diff(problem, x)
            logger.debug(f"Computed derivative: {answer}")
            if not ans_zero and answer == 0:
                logger.debug("Skipping zero derivative")
                continue
            if answer_length is None:
                break
            elif len(answer.args) <= answer_length:
                break
        return problem, sp.simplify(answer)

    @log_exceptions(logger)
    def get_problem_pairs(self, n, problem_length=(2, 4), answer_length=None):
        logger.debug(f"Generating {n} problem pairs")
        problems, answers = [], []
        for i in range(n):
            logger.debug(f"Generating problem pair {i+1}/{n}")
            problem, answer = self.get_problem_pair(problem_length, answer_length)
            problems.append(problem)
            answers.append(answer)
        return problems, answers

if __name__ == '__main__':
    derivative = Derivative()
    p, ans = derivative.get_problem_pair()
    print(p)
    print(ans)