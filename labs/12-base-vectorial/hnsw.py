"""A small HNSW (Hierarchical Navigable Small World) index, written to understand Qdrant.

The idea: a graph where every vector is linked to its M nearest neighbours. Search starts at
an entry point and greedily walks to whichever neighbour is closer to the query. To avoid
walking across the whole graph, there are layers: the top ones are sparse (few nodes, long
jumps) and the bottom one has every node (short, precise jumps). A node reaches layer l with
probability exp(-l / mL), like a skip list.

Vectors are L2-normalised, so distance = 1 - dot product.
"""

import heapq
import math
import random

import numpy as np


class HNSW:
    def __init__(self, dim: int, capacity: int, m: int = 16, ef_construction: int = 100,
                 seed: int = 0, heuristic: bool = True):
        self.m = m
        self.m0 = 2 * m  # the bottom layer keeps more links: it is where precision is made
        self.ef_construction = ef_construction
        self.ml = 1 / math.log(m)
        self.vectors = np.zeros((capacity, dim), dtype=np.float32)
        self.count = 0
        self.layers: list[dict[int, list[int]]] = []  # layer -> node -> neighbours
        self.entry: int | None = None
        self.rng = random.Random(seed)
        self.distance_evals = 0
        self.heuristic = heuristic

    def _dist(self, q: np.ndarray, ids: list[int]) -> np.ndarray:
        self.distance_evals += len(ids)
        return 1 - self.vectors[ids] @ q

    def _search_layer(self, q: np.ndarray, entries: list[int], ef: int, layer: int):
        """Best-first search on one layer. Returns up to ef (distance, id), closest first."""
        visited = set(entries)
        d = self._dist(q, entries)
        candidates = [(float(x), i) for x, i in zip(d, entries)]  # min-heap: to expand
        heapq.heapify(candidates)
        best = [(-float(x), i) for x, i in zip(d, entries)]  # max-heap: current results
        heapq.heapify(best)
        graph = self.layers[layer]
        while candidates:
            dist, node = heapq.heappop(candidates)
            if dist > -best[0][0] and len(best) >= ef:
                break  # the closest unexpanded candidate is worse than our worst result
            new = [n for n in graph.get(node, []) if n not in visited]
            if not new:
                continue
            visited.update(new)
            for nd, n in zip(self._dist(q, new), new):
                nd = float(nd)
                if len(best) < ef or nd < -best[0][0]:
                    heapq.heappush(candidates, (nd, n))
                    heapq.heappush(best, (-nd, n))
                    if len(best) > ef:
                        heapq.heappop(best)
        return sorted((-d, i) for d, i in best)

    def add(self, vec: np.ndarray) -> int:
        node = self.count
        self.vectors[node] = vec
        self.count += 1
        level = int(-math.log(1 - self.rng.random()) * self.ml)
        while len(self.layers) <= level:
            self.layers.append({})
        if self.entry is None:
            for layer in range(level + 1):
                self.layers[layer][node] = []
            self.entry = node
            return node

        entries = [self.entry]
        top = len(self.layers) - 1
        # Above the new node's level: greedy descent with ef=1, just to find a good door
        for layer in range(top, level, -1):
            entries = [self._search_layer(vec, entries, 1, layer)[0][1]]
        # From its level down: connect to the M closest found with ef_construction
        for layer in range(min(level, top), -1, -1):
            found = self._search_layer(vec, entries, self.ef_construction, layer)
            limit = self.m0 if layer == 0 else self.m
            neighbours = self._select(found, limit)
            self.layers[layer][node] = neighbours
            for n in neighbours:
                links = self.layers[layer].setdefault(n, [])
                links.append(node)
                if len(links) > limit:  # prune with the same selection rule
                    d = self._dist(self.vectors[n], links)
                    ranked = sorted(zip(d.tolist(), links))
                    self.layers[layer][n] = self._select(ranked, limit)
            entries = [i for _, i in found]
        if level > self._level(self.entry):
            self.entry = node
        return node

    def _select(self, candidates: list[tuple[float, int]], limit: int) -> list[int]:
        """Pick neighbours from (distance, id) pairs sorted by distance.

        Simple rule: the closest ones. Heuristic (HNSW paper, algorithm 4): keep a candidate
        only if it is closer to the node than to every neighbour already kept, so links point
        in different directions instead of all into the same cluster of near-duplicates.
        Discarded candidates fill the remaining slots, so the degree stays the same.
        """
        if not self.heuristic:
            return [i for _, i in candidates[:limit]]
        kept: list[int] = []
        discarded: list[int] = []
        for dist, c in candidates:
            if len(kept) >= limit:
                break
            if not kept or (1 - self.vectors[kept] @ self.vectors[c] > dist).all():
                kept.append(c)
            else:
                discarded.append(c)
        return kept + discarded[:limit - len(kept)]

    def _level(self, node: int) -> int:
        return max(layer for layer, g in enumerate(self.layers) if node in g)

    def search(self, q: np.ndarray, k: int = 10, ef: int = 50) -> list[int]:
        entries = [self.entry]
        for layer in range(len(self.layers) - 1, 0, -1):
            entries = [self._search_layer(q, entries, 1, layer)[0][1]]
        found = self._search_layer(q, entries, max(ef, k), 0)
        return [i for _, i in found[:k]]
