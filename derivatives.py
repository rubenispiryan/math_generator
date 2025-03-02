import sympy as sp
from random import uniform, randint, choice


def get_trig(symbol):
    prob = uniform(0, 1)
    if prob < 0.3:
        return sp.sin(symbol)
    elif prob < 0.5:
        return sp.cos(symbol)
    elif prob < 0.7:
        return sp.tan(symbol)
    elif prob < 0.9:
        return sp.sec(symbol)
    else:
        return sp.cot(symbol)

def get_hyper_trig(symbol):
    prob = uniform(0, 1)
    if prob < 0.3:
        return sp.sinh(symbol)
    elif prob < 0.5:
        return sp.cosh(symbol)
    elif prob < 0.7:
        return sp.tanh(symbol)
    else:
        return sp.sech(symbol)

def get_poly(symbol):
    return symbol

def get_exponent(symbol):
    prob = uniform(0, 1)
    if prob < 0.9:
        return sp.exp(symbol)
    else:
        a = randint(2, 5)
        return a ** symbol

def get_log(symbol):
    prob = uniform(0, 1)
    if prob < 0.98:
        return sp.ln(symbol)
    else:
        a = randint(2, 5)
        return sp.log(symbol, a)

def get_root(symbol):
    prob = uniform(0, 1)
    if prob < 0.7:
        return sp.sqrt(symbol)
    else:
        a = randint(3, 5)
        return symbol ** sp.Rational(1, a)

def get_reciprocal(symbol):
    return 1 / symbol

def get_element(symbol):
    simple_functions = (
        get_poly,
        get_trig,
        get_exponent,
        get_log,
        get_root,
        get_reciprocal,
        get_hyper_trig,
    )
    element = choice(simple_functions)(symbol)
    a = randint(1, 5)
    b = randint(0, 5)
    return a * element ** b

def get_composition(symbol):
    return get_element(get_element(symbol))

def make_problem(symbol, a, b):
    a = randint(a, b)
    problem = 0
    for _ in range(a):
        prob = uniform(0, 1)
        if prob < 0.3:
            problem += get_composition(symbol)
        else:
            problem += get_element(symbol)
    return problem

def get_problem_pair(problem_length=(2, 4), answer_length=None):
    a, b = problem_length
    x = sp.symbols('x')
    while True:
        problem = make_problem(x, a, b)
        answer = sp.diff(problem, x)
        if answer_length is None:
            break
        elif len(answer.args) <= answer_length:
            break
    return problem, sp.simplify(answer)

def get_problem_pairs(n, problem_length=(2, 4), answer_length=None):
    problems, answers = [], []
    for _ in range(n):
        problem, answer = get_problem_pair(problem_length, answer_length)
        problems.append(problem)
        answers.append(answer)
    return problems, answers

if __name__ == '__main__':
    p, ans = get_problem_pair()
    print(p)
    print(ans)