import sympy as sp

from generator import ExpressionGenerator


class Derivative:
    def __init__(self):
        symbol = sp.Symbol('x')
        self._exp_gen = ExpressionGenerator(symbol)

    def get_problem_pair(self, problem_length=(2, 4), answer_length=None, ans_zero=True):
        x = sp.symbols('x')
        while True:
            problem = self._exp_gen.get_expression(problem_length)
            answer = sp.diff(problem, x)
            if not ans_zero and answer == 0:
                continue
            if answer_length is None:
                break
            elif len(answer.args) <= answer_length:
                break
        return problem, sp.simplify(answer)

    def get_problem_pairs(self, n, problem_length=(2, 4), answer_length=None):
        problems, answers = [], []
        for _ in range(n):
            problem, answer = self.get_problem_pair(problem_length, answer_length)
            problems.append(problem)
            answers.append(answer)
        return problems, answers

if __name__ == '__main__':
    derivative = Derivative()
    p, ans = derivative.get_problem_pair()
    print(p)
    print(ans)