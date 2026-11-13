"""Where DiscoveryAgent keeps its belief state.

IA Series 13 (documentation/ia-series/13-ontologies/blog.md) splits the
agent's facts by Kind:

- exogenous - sensed from the world: node(id), notifies(id, target),
  requires(id, target). Written by record_sensed().
- controllable - the agent's own belief: known(id), visited(id),
  cleared(id). Written by record_known(), record_visited(),
  record_cleared().

The agent reads and writes its beliefs only through this interface, so the
same walk can keep them in memory (InMemoryBeliefStore, the default) or in
a database (discovery/typedb/, TypeDBBeliefStore).
"""

from typing import Dict, Iterable, List, Protocol, Set, Tuple


class BeliefStore(Protocol):
    # exogenous: sensed facts
    def has_sensed(self, node_id: str) -> bool: ...

    def record_sensed(
        self, node_id: str, notifies: Tuple[str, ...], requires: Tuple[str, ...]
    ) -> None: ...

    def notifies_of(self, node_id: str) -> Tuple[str, ...]: ...

    def requires_of(self, node_id: str) -> Tuple[str, ...]: ...

    def sensed_edges(self) -> List[Tuple[str, str]]: ...

    # controllable: the agent's own beliefs
    def record_known(self, node_ids: Iterable[str]) -> None: ...

    def record_visited(self, node_id: str) -> None: ...

    def record_cleared(self, node_id: str) -> None: ...

    def known(self) -> Set[str]: ...

    def visited(self) -> Set[str]: ...

    def cleared(self) -> Set[str]: ...


class InMemoryBeliefStore:
    """The belief state as plain Python sets and dicts - what
    DiscoveryAgent held inside walk() before the store was split out."""

    def __init__(self) -> None:
        self._notifies: Dict[str, Tuple[str, ...]] = {}
        self._requires: Dict[str, Tuple[str, ...]] = {}
        self._edges: List[Tuple[str, str]] = []
        self._known: Set[str] = set()
        self._visited: Set[str] = set()
        self._cleared: Set[str] = set()

    def has_sensed(self, node_id: str) -> bool:
        return node_id in self._notifies

    def record_sensed(
        self, node_id: str, notifies: Tuple[str, ...], requires: Tuple[str, ...]
    ) -> None:
        self._notifies[node_id] = notifies
        self._requires[node_id] = requires
        for target in notifies:
            self._edges.append((node_id, target))

    def notifies_of(self, node_id: str) -> Tuple[str, ...]:
        return self._notifies[node_id]

    def requires_of(self, node_id: str) -> Tuple[str, ...]:
        return self._requires[node_id]

    def sensed_edges(self) -> List[Tuple[str, str]]:
        return list(self._edges)

    def record_known(self, node_ids: Iterable[str]) -> None:
        self._known.update(node_ids)

    def record_visited(self, node_id: str) -> None:
        self._visited.add(node_id)

    def record_cleared(self, node_id: str) -> None:
        self._cleared.add(node_id)

    def known(self) -> Set[str]:
        return set(self._known)

    def visited(self) -> Set[str]:
        return set(self._visited)

    def cleared(self) -> Set[str]:
        return set(self._cleared)
