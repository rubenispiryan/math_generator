import random

class Game2x2:
    def __init__(self, player1, player2):
        self.p1 = player1
        self.p2 = player2
        self.matrix = [[(random.randint(0, 10), random.randint(0, 10))
                                 for _ in range(2)] for _ in range(2)]
        self.matrix = [[(10, 9), (0, 10)], [(2, 8), (10, 5)]]

    def _pure_nash_equilibria(self):
        p1_br = []
        p2_br = []
        for j in range(2):
            col = [self.matrix[i][j][0] for i in range(2)]
            max_val = max(col)
            for i in range(2):
                if self.matrix[i][j][0] == max_val:
                    p1_br.append((i, j))
        for i in range(2):
            row = [self.matrix[i][j][1] for j in range(2)]
            max_val = max(row)
            for j in range(2):
                if self.matrix[i][j][1] == max_val:
                    p2_br.append((i, j))
        return list(set(p1_br) & set(p2_br))

    def _indifference_probabilities(self):
        A = self.matrix

        denominator = (A[0][0][0] - A[0][1][0] - A[1][0][0] + A[1][1][0])
        if denominator != 0:
            p = (A[1][1][0] - A[0][1][0]) / denominator
            p = round(p, 2)
        else:
            p = None

        denominator = (A[0][0][1] - A[1][0][1] - A[0][1][1] + A[1][1][1])
        if denominator != 0:
            q = (A[1][1][1] - A[1][0][1]) / denominator
            q = round(q, 2)
        else:
            q = None

        return q, p

    def _mixed_strategy_nash(self):
        p, q = self._indifference_probabilities()
        if p is None or q is None or not (0 <= p <= 1 and 0 <= q <= 1):
            return None
        return (p, round(1 - p, 2)), (q, round(1 - q, 2))

    def get_pure_nash_equilibria(self):
        answers = self._pure_nash_equilibria()
        if answers is None or len(answers) == 0:
            return answers
        processed = []
        for ans in answers:
            processed.append(self.matrix[ans[0]][ans[1]])
        return processed

    def get_mixed_strategy_nash(self):
        answers = self._mixed_strategy_nash()
        if answers is None or len(answers) == 0:
            return answers
        return f'Probabilities for {self.p1}: {answers[0]}, {self.p2}: {answers[1]}'

    def show(self):
        for row in self.matrix:
            print(row)


if __name__ == "__main__":
    game = Game2x2('p1', 'p2')
    game.show()
    print("Pure Strategy Nash Equilibria:", game.get_pure_nash_equilibria())
    print("Mixed Strategy Nash Equilibrium:", game.get_mixed_strategy_nash())