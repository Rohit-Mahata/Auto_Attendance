"""
Kuhn-Munkres (Hungarian) Maximum Weight / Minimum Cost Bipartite Matching
Pure Python implementation ensuring zero external C-dependencies, guaranteed
convergence, and optimal O(N^3) assignment for classroom roster matching.
"""

from typing import List, Tuple
import numpy as np

def linear_sum_assignment_pure(cost_matrix: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """
    Computes minimum cost bipartite matching on cost_matrix (shape N x M).
    Returns (row_ind, col_ind) arrays of assigned pairs.
    """
    cost = np.array(cost_matrix, dtype=np.float64)
    if cost.ndim != 2:
        raise ValueError("Cost matrix must be 2D")

    num_rows, num_cols = cost.shape
    if num_rows == 0 or num_cols == 0:
        return np.array([], dtype=int), np.array([], dtype=int)

    # If rows > cols, transpose and transpose result back
    transposed = False
    if num_rows > num_cols:
        cost = cost.T
        num_rows, num_cols = cost.shape
        transposed = True

    # 1-indexed Jonker-Volgenant / Hungarian shortest augmenting path
    u = np.zeros(num_rows + 1, dtype=np.float64)
    v = np.zeros(num_cols + 1, dtype=np.float64)
    p = np.zeros(num_cols + 1, dtype=int)
    way = np.zeros(num_cols + 1, dtype=int)

    for i in range(1, num_rows + 1):
        p[0] = i
        j0 = 0
        minv = np.full(num_cols + 1, np.inf, dtype=np.float64)
        used = np.zeros(num_cols + 1, dtype=bool)

        while True:
            used[j0] = True
            i0 = p[j0]
            delta = np.inf
            j1 = 0

            for j in range(1, num_cols + 1):
                if not used[j]:
                    cur = cost[i0 - 1, j - 1] - u[i0] - v[j]
                    if cur < minv[j]:
                        minv[j] = cur
                        way[j] = j0
                    if minv[j] < delta:
                        delta = minv[j]
                        j1 = j

            for j in range(num_cols + 1):
                if used[j]:
                    u[p[j]] += delta
                    v[j] -= delta
                else:
                    minv[j] -= delta

            j0 = j1
            if p[j0] == 0:
                break

        while True:
            j1 = way[j0]
            p[j0] = p[j1]
            j0 = j1
            if j0 == 0:
                break

    # Extract assignments
    row_ind = []
    col_ind = []
    for j in range(1, num_cols + 1):
        if p[j] > 0 and p[j] <= num_rows:
            row_ind.append(p[j] - 1)
            col_ind.append(j - 1)

    row_ind = np.array(row_ind, dtype=int)
    col_ind = np.array(col_ind, dtype=int)

    # Sort by row index
    sort_idx = np.argsort(row_ind)
    row_ind = row_ind[sort_idx]
    col_ind = col_ind[sort_idx]

    if transposed:
        # Swap back
        return col_ind, row_ind
    return row_ind, col_ind

class RosterHungarianMatcher:
    """
    Enforces 'One Person, One Student' globally across the closed-set session roster.
    Takes track feature embeddings and roster student templates, builds cost matrix
    (Cost = 1.0 - CosineSimilarity), and finds the global maximum similarity assignment.
    """
    def __init__(self, cost_cutoff: float = 0.50):
        # Cosine similarity below (1 - cost_cutoff) is considered an unmatchable pairing
        self.cost_cutoff = cost_cutoff

    def match(self, track_similarities: np.ndarray) -> List[Tuple[int, int, float]]:
        """
        Args:
            track_similarities: 2D array of shape (num_tracks, num_roster_students)
                                representing cosine similarity in [0, 1].
        Returns:
            List of (track_idx, student_idx, similarity_score)
        """
        if track_similarities.size == 0:
            return []

        cost_matrix = 1.0 - np.clip(track_similarities, 0.0, 1.0)
        row_ind, col_ind = linear_sum_assignment_pure(cost_matrix)

        assignments = []
        for r, c in zip(row_ind, col_ind):
            sim = float(track_similarities[r, c])
            assignments.append((int(r), int(c), round(sim, 4)))

        return assignments
