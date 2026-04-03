from collections import deque

from DataFlow.data_column import ParsedDerived


def topo_sort_derived(
    derived: list[ParsedDerived],
) -> list[ParsedDerived]:
    derived_by_id = {d.id: d for d in derived}
    in_degree = {
        d.id: sum(1 for inp in d.inputs if inp in derived_by_id)
        for d in derived
    }
    queue = deque(d_id for d_id, deg in in_degree.items() if deg == 0)
    result: list[ParsedDerived] = []
    while queue:
        current = queue.popleft()
        result.append(derived_by_id[current])
        for d in derived:
            if current in d.inputs:
                in_degree[d.id] -= 1
                if in_degree[d.id] == 0:
                    queue.append(d.id)
    if len(result) != len(derived):
        sorted_ids = {d.id for d in result}
        cycle_ids = [d.id for d in derived if d.id not in sorted_ids]
        raise ValueError(f"Circular dependency among: {cycle_ids}")
    return result
