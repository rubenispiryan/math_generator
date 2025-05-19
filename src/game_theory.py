from typing import List, Tuple, Optional
import random
import logging

logger = logging.getLogger(__name__)

class Game2x2:
    """A class representing a 2x2 game in normal form."""
    
    def __init__(self, player1: str, player2: str):
        """
        Initialize a 2x2 game with random payoffs.
        
        Args:
            player1: Name of the first player
            player2: Name of the second player
        """
        self.p1 = player1
        self.p2 = player2
        self.matrix = self._generate_random_matrix()

    def _generate_random_matrix(self) -> List[List[Tuple[int, int]]]:
        """Generate a random payoff matrix."""
        return [[(random.randint(0, 10), random.randint(0, 10))
                for _ in range(2)] for _ in range(2)]

    def _pure_nash_equilibria(self) -> List[Tuple[int, int]]:
        """
        Find pure strategy Nash equilibria.
        
        Returns:
            List of (row, col) tuples representing pure Nash equilibria
        """
        p1_br = self._find_best_responses(0)  # Player 1's best responses
        p2_br = self._find_best_responses(1)  # Player 2's best responses
        return list(set(p1_br) & set(p2_br))

    def _find_best_responses(self, player: int) -> List[Tuple[int, int]]:
        """
        Find best responses for a given player.
        
        Args:
            player: 0 for player 1, 1 for player 2
            
        Returns:
            List of (row, col) tuples representing best responses
        """
        best_responses = []
        
        if player == 0:
            # Find best responses for player 1 (column player)
            for j in range(2):
                col = [self.matrix[i][j][0] for i in range(2)]
                max_val = max(col)
                for i in range(2):
                    if self.matrix[i][j][0] == max_val:
                        best_responses.append((i, j))
        else:
            # Find best responses for player 2 (row player)
            for i in range(2):
                row = [self.matrix[i][j][1] for j in range(2)]
                max_val = max(row)
                for j in range(2):
                    if self.matrix[i][j][1] == max_val:
                        best_responses.append((i, j))
                        
        return best_responses

    def _indifference_probabilities(self) -> Tuple[Optional[float], Optional[float]]:
        """
        Calculate indifference probabilities for mixed strategy Nash equilibrium.
        
        Returns:
            Tuple of (q, p) where:
            - q is the probability of player 1 choosing strategy 1
            - p is the probability of player 2 choosing strategy 1
        """
        A = self.matrix

        # Calculate p (probability for player 2)
        denominator = (A[0][0][0] - A[0][1][0] - A[1][0][0] + A[1][1][0])
        p = (A[1][1][0] - A[0][1][0]) / denominator if denominator != 0 else None
        p = round(p, 2) if p is not None else None

        # Calculate q (probability for player 1)
        denominator = (A[0][0][1] - A[1][0][1] - A[0][1][1] + A[1][1][1])
        q = (A[1][1][1] - A[1][0][1]) / denominator if denominator != 0 else None
        q = round(q, 2) if q is not None else None

        return q, p

    def _mixed_strategy_nash(self) -> Optional[Tuple[Tuple[float, float], Tuple[float, float]]]:
        """
        Calculate mixed strategy Nash equilibrium.
        
        Returns:
            Tuple of ((p1_strat1_prob, p1_strat2_prob), (p2_strat1_prob, p2_strat2_prob))
            or None if no valid mixed strategy equilibrium exists
        """
        q, p = self._indifference_probabilities()
        
        if p is None or q is None or not (0 <= p <= 1 and 0 <= q <= 1):
            return None
            
        return (p, round(1 - p, 2)), (q, round(1 - q, 2))

    def get_pure_nash_equilibria(self) -> List[Tuple[int, int]]:
        """
        Get pure strategy Nash equilibria with their payoffs.
        
        Returns:
            List of payoff tuples at pure Nash equilibria
        """
        answers = self._pure_nash_equilibria()
        if not answers:
            return []
            
        return [self.matrix[ans[0]][ans[1]] for ans in answers]

    def get_mixed_strategy_nash(self) -> Optional[str]:
        """
        Get mixed strategy Nash equilibrium in a readable format.
        
        Returns:
            String describing the mixed strategy Nash equilibrium
            or None if no valid mixed strategy equilibrium exists
        """
        answers = self._mixed_strategy_nash()
        if answers is None:
            return None
            
        return f'Probabilities for {self.p1}: {answers[0]}, {self.p2}: {answers[1]}'

    def show(self) -> None:
        """Display the game matrix."""
        for row in self.matrix:
            print(row)


if __name__ == "__main__":
    # Example usage
    game = Game2x2('p1', 'p2')
    game.show()
    print("Pure Strategy Nash Equilibria:", game.get_pure_nash_equilibria())
    print("Mixed Strategy Nash Equilibrium:", game.get_mixed_strategy_nash())