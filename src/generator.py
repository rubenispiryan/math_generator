import sympy as sp
from random import uniform, randint, choice

class ExpressionGenerator:
    DEFAULT_CONFIG = {
        'p_trig': (0.3, 0.5, 0.7, 0.9),
        'p_hyper_trig': (0.3, 0.5, 0.7),
        'p_exponent': 0.9,
        'p_log': 0.98,
        'p_root': 0.7,
        'p_compose': 0.3,
        'exp_range': (2, 5),
        'log_base_range': (2, 5),
        'root_degree_range': (3, 5),
        'coeff_range': (1, 5),
        'power_range': (0, 5),
        'function_choice': None
    }
    
    def __init__(self, symbol: sp.Symbol, config=None):
        self._symbol = symbol
        self.symbol = symbol

        self.default_functions = [
            self.make_poly,
            self.make_exponent,
            self.make_log,
            self.make_root,
            self.make_reciprocal,
            self.make_trig,
            self.make_hyper_trig,
        ]
        self.config = {**self.DEFAULT_CONFIG, **(config or {}),
                       'function_choice': self.default_functions}

    def update_config(self, new_config):
        self.config.update(new_config)

    def make_trig(self):
        prob = uniform(0, 1)
        if prob < self.config['p_trig'][0]:
            self._symbol = sp.sin(self._symbol)
        elif prob < self.config['p_trig'][1]:
            self._symbol = sp.cos(self._symbol)
        elif prob < self.config['p_trig'][2]:
            self._symbol = sp.tan(self._symbol)
        elif prob < self.config['p_trig'][3]:
            self._symbol = sp.sec(self._symbol)
        else:
            self._symbol = sp.cot(self._symbol)

    def make_hyper_trig(self):
        prob = uniform(0, 1)
        if prob < self.config['p_hyper_trig'][0]:
            self._symbol = sp.sinh(self._symbol)
        elif prob < self.config['p_hyper_trig'][1]:
            self._symbol = sp.cosh(self._symbol)
        elif prob < self.config['p_hyper_trig'][2]:
            self._symbol = sp.tanh(self._symbol)
        else:
            self._symbol = sp.sech(self._symbol)

    def make_poly(self):
        self._symbol = self._symbol

    def make_exponent(self):
        prob = uniform(0, 1)
        if prob < self.config['p_exponent']:
            self._symbol = sp.exp(self._symbol)
        else:
            a = randint(*self.config['exp_range'])
            self._symbol = a ** self._symbol

    def make_log(self):
        prob = uniform(0, 1)
        if prob < self.config['p_log']:
            self._symbol = sp.ln(self._symbol)
        else:
            a = randint(*self.config['log_base_range'])
            self._symbol = sp.log(self._symbol, a)

    def make_root(self):
        prob = uniform(0, 1)
        if prob < self.config['p_root']:
            self._symbol = sp.sqrt(self._symbol)
        else:
            a = randint(*self.config['root_degree_range'])
            self._symbol = self._symbol ** sp.Rational(1, a)

    def make_reciprocal(self):
        self._symbol = 1 / self._symbol

    def get_element(self):
        simple_functions = self.config['function_choice']
        choice(simple_functions)()
        a = randint(*self.config['coeff_range'])
        b = randint(*self.config['power_range'])
        return a * self._symbol ** b

    def get_composition(self):
        self.get_element()
        self.get_element()
        return self._symbol

    def get_expression(self, length_range: tuple[int, int]):
        a = randint(*length_range)
        problem = 0
        for _ in range(a):
            self._symbol = self.symbol
            prob = uniform(0, 1)
            if prob < self.config['p_compose']:
                problem += self.get_composition()
            else:
                problem += self.get_element()
            problem += self._symbol
        self._symbol = self.symbol
        return problem