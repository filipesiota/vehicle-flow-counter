"""Cruzamento de segmento usando sinal consistente dos lados da reta."""

from __future__ import annotations

from dataclasses import dataclass, field

from vehicle_flow_counter.domain.models import CountingLine


def _oriented_cross_z(line: CountingLine, px: float, py: float) -> float:
    ax, ay = float(line.start.x), float(line.start.y)
    bx, by = float(line.end.x), float(line.end.y)
    # Produto vetorial 2D (AB x AP)_z para determinar o lado do ponto P em relação a AB.
    return (bx - ax) * (py - ay) - (by - ay) * (px - ax)


def _quantize_side(cross_z: float) -> int | None:
    eps = max(3.0, 1e-6)
    if cross_z > eps:
        return 1
    if cross_z < -eps:
        return -1
    return None


@dataclass
class LineCrossingState:
    """Mantém o último lado conhecido por ID e registra quando ocorreu um novo cruzamento."""

    counting_line: CountingLine
    _last_side_by_id: dict[int, int] = field(init=False, default_factory=dict)

    def reset(self) -> None:
        self._last_side_by_id.clear()

    def ingest(self, tracked_id: int, center_global_xy: tuple[int, int]) -> bool:
        """
        Atualiza o estado com um novo centro (coordenadas do frame inteiro).

        Retorna ``True`` se este frame correspondeu a um primeiro cruzamento detectado para o ID.
        """
        sx, sy = center_global_xy
        cross_z = _oriented_cross_z(self.counting_line, float(sx), float(sy))
        side_now = _quantize_side(cross_z)

        if side_now is None:
            return False

        prev = self._last_side_by_id.get(tracked_id)
        self._last_side_by_id[tracked_id] = side_now

        if prev is None:
            return False
        return prev != side_now
