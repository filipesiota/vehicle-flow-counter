"""Ponto de entrada para `python -m vehicle_flow_counter`."""

from __future__ import annotations

from vehicle_flow_counter.ui.app import VehicleFlowCounterApp


def main() -> None:
    """Inicia a aplicação CustomTkinter."""
    app = VehicleFlowCounterApp()
    app.mainloop()


if __name__ == "__main__":
    main()
