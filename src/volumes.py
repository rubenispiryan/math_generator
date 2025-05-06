from multiprocessing import Queue, Process

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import sympy as sp
import numpy as np

from src.generator import ExpressionGenerator

class Volumes:
    def __init__(self, filename):
        self.filename = filename
        self.x = sp.Symbol('x')
        self.exp_gen = ExpressionGenerator(self.x)
        self.image_index = 0
        self.a, self.b = None, None

    def get_problem_pairs(self, n, difficulty, x_range):
        problems = []
        answers = []
        for _ in range(n):
            p, ans = self.get_problem_pair(difficulty, x_range)
            problems.append(p)
            answers.append(ans)
        return problems, answers

    def _try_integrate(self, expr, var, queue):
        try:
            result = sp.integrate(expr, var)
            queue.put(result)
        except Exception as e:
            queue.put(e)

    def _integrate_with_timeout(self, expr, var, timeout=3):
        queue = Queue()
        p = Process(target=self._try_integrate, args=(expr, var, queue))
        p.start()
        p.join(timeout)
        if p.is_alive():
            p.terminate()
            return -1
        else:
            return queue.get()

    def get_problem_pair(self, difficulty, x_range):
        p = sp.simplify(self._get_problem(x_range, difficulty))
        ans = sp.pi * self._integrate_with_timeout(p, (self.x, self.a, self.b))
        self.a, self.b = None, None
        simpl = sp.expand(sp.simplify(ans))
        if ans == sp.nan or ans == -1 or len(simpl.as_ordered_terms()) > 2:
            self.image_index -= 1
            return self.get_problem_pair(difficulty, x_range)
        return p, sp.simplify(ans)

    def _get_problem(self, x_range, difficulty='simple', debug=False):
        if difficulty == 'simple':
            config = {
                'power_range': (1, 3),
                'p_trig': (0.5, 0.9, 0, 1),
                'p_compose': 0,
                'function_choice': [
                    self.exp_gen.make_poly,
                    self.exp_gen.make_exponent,
                    self.exp_gen.make_log,
                    self.exp_gen.make_root,
                    self.exp_gen.make_trig,
            ]}
            self.exp_gen.update_config(config)
            p = self.exp_gen.get_expression((1, 1))
        elif difficulty == 'hard':
            config = {
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
                ]}
            self.exp_gen.update_config(config)
            p = self.exp_gen.get_expression((2, 2))
        elif difficulty == 'extreme':
            config = self.exp_gen.DEFAULT_CONFIG
            config['p_trig'] = (0.5, 0.9, 0, 1)
            config['function_choice'] = self.exp_gen.default_functions
            self.exp_gen.update_config(config)
            p = self.exp_gen.get_expression((2, 3))
        else:
            print('Unknown difficulty')
            return None
        p = sp.diff(p, self.x)
        try:
            self._create_graph(p, x_range)
        except Exception as e:
            if debug:
                print(f'Failed to render equation: {str(e)}')
            plt.close('all')
            return self._get_problem(x_range, difficulty)
        return p


    def _create_graph(self, f, x_range, debug=False):
        ab_range = (1, 15)
        # Convert the symbolic function to a numerical function
        f_lambdified = sp.lambdify(self.x, f, 'numpy')

        # Generate x values
        x_vals = np.linspace(x_range[0], x_range[1], 2000)
        with np.errstate(divide='ignore', invalid='ignore'):  # Suppress warnings
            y_vals = f_lambdified(x_vals)

        mask = np.isfinite(y_vals)  # Keep only finite values
        x_vals = x_vals[mask]
        y_vals = y_vals[mask]

        threshold = 10 ** 2  # Adjust based on function scale
        mask = np.abs(y_vals) > threshold  # Mask large values
        x_vals = x_vals[~mask]  # Remove corresponding x values
        y_vals = y_vals[~mask]  # Remove corresponding y values

        try:
            x_range = max(ab_range[0], np.min(x_vals)), min(ab_range[1], np.max(x_vals))
        except ValueError:
            if debug:
                print(f'{x_vals=}')
            raise


        # Create Boundaries
        if np.ceil(x_range[0]) >= x_range[1] / 2 + 1:
            a = np.ceil(x_range[0])
        else:
            a = np.random.randint(np.ceil(x_range[0]), x_range[1] / 2 + 1)
        if np.ceil(x_range[1]) <= a + 1:
            b = np.ceil(x_range[1])
        else:
            b = np.random.randint(a+1, np.ceil(x_range[1]))

        self.a, self.b = a, b

        # Create a figure
        plt.figure(figsize=(8, 6))

        # Plot the function
        plt.plot(x_vals, y_vals, label=f"${sp.latex(f)}$", linewidth=2, color="b")

        # Enhance plot appearance
        plt.xlabel("$x$", fontsize=14)
        plt.ylabel("$f(x)$", fontsize=14)
        plt.title("Graph of the Function", fontsize=16)
        plt.axhline(0, color='black', linewidth=1)  # x-axis
        plt.axvline(0, color='black', linewidth=1)  # y-axis
        plt.axvline(a, color='r', linestyle='--', linewidth=2, label=f"$x = {a}$")
        plt.axvline(b, color='g', linestyle='--', linewidth=2, label=f"$x = {b}$")
        plt.grid(True, which='both', linestyle="--", linewidth=0.5)
        plt.legend(fontsize=14)

        # Save the plot as an image file (e.g., 'function_graph.png')
        plt.savefig(f'../output/{self.filename}_{self.image_index}.jpg',
                    format='jpg', bbox_inches='tight')
        self.image_index += 1

        # Close the plot
        plt.close()

if __name__ == "__main__":
    vols = Volumes('templates/volumes.xml')
    vols.get_problem_pair('extreme', (1, 15))
    vols.get_problem_pair('hard', (1, 15))
    vols.get_problem_pair('simple', (1, 15))