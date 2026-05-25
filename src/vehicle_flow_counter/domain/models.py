"""Modelos de dados para vídeos, ROI, linha de contagem e estatísticas de tracking."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


@dataclass(frozen=True, slots=True)
class Point2D:
    """Ponto inteiro em coordenadas de imagem (pixels)."""

    x: int
    y: int


@dataclass(frozen=True, slots=True)
class Roi:
    """Região retangular de interesse (origem canto superior esquerdo)."""

    x: int
    y: int
    width: int
    height: int

    def contains(self, p: Point2D) -> bool:
        """True se o ponto estiver dentro ou na borda do retângulo."""
        return self.x <= p.x < self.x + self.width and self.y <= p.y < self.y + self.height


@dataclass(frozen=True, slots=True)
class CountingLine:
    """Segmento definido por dois pontos; contagem quando o centro cruza."""

    start: Point2D
    end: Point2D


@dataclass(frozen=True, slots=True)
class VideoEntry:
    """Vídeo armazenado sob `data/videos/<slug>/`."""

    slug: str
    video_path: Path
    captures_dir: Path


@dataclass(slots=True)
class TrackingStats:
    """Estado acumulado durante uma sessão de tracking."""

    started_at: datetime
    vehicles_counted: int = 0
    last_known_ids: set[int] = field(default_factory=set)

    def vehicles_per_minute(self, now: datetime | None = None) -> float:
        """Média de veículos por minuto desde o início (0 se ainda não passou tempo)."""
        clock = now or datetime.now()
        elapsed_seconds = max(0.0, (clock - self.started_at).total_seconds())
        if elapsed_seconds < 1e-6:
            return 0.0
        return self.vehicles_counted / (elapsed_seconds / 60.0)
