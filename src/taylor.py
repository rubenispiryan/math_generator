import sympy as sp

from src.generator import ExpressionGenerator


class TaylorSeries:
    def __init__(self):
        self.x = sp.Symbol('x')
        self.generator = ExpressionGenerator(self.x)

    def _round_coefficients(self, expr, decimals=2):
        terms = expr.expand().as_ordered_terms()
        rounded_terms = []

        for term in terms:
            coeff, rest = term.as_coeff_Mul()
            if coeff.is_number and coeff.is_real and coeff.is_Number:
                coeff = sp.Float(round(float(coeff), decimals))
            rounded_terms.append(coeff * rest)

        return sp.Add(*rounded_terms)

    def get_problem_pair(self, problem_length: tuple[int, int], a = 1, tries = 3):
        try:
            expr = self.generator.get_expression(problem_length)
            exprs = []
            for exp in expr.as_ordered_terms():
                exprs.append(exp.expand().series(self.x, a, 2))
            return expr, self._round_coefficients(sum(exprs).removeO())
        except Exception as e:
            if tries > 0:
                return self.get_problem_pair(problem_length, a=a, tries=tries - 1)
            raise e

    def get_problem_pairs(self, n, problem_length=(1, 2), a = 1):
        problems, answers = [], []
        for _ in range(n):
            p, ans = self.get_problem_pair(problem_length, a)
            problems.append(p)
            answers.append(ans)
        return problems, answers


if __name__ == '__main__':
    taylor = TaylorSeries()
    print(taylor.get_problem_pair((1, 2)))