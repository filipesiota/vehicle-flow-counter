"""Caminhos de dados, textos da UI e constantes globais."""

from __future__ import annotations

from pathlib import Path

# Raiz do projeto (onde está `pyproject.toml`; dois níveis acima deste pacote em `src/`).
_PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Armazenamento local (pastas ignoradas no git).
DATA_DIR = _PROJECT_ROOT / "data"
VIDEOS_DIR = DATA_DIR / "videos"
MODELS_DIR = DATA_DIR / "models"

# UI — títulos e mensagens em PT-BR.
APP_TITLE = "Contador de fluxo veicular"

# Home
BTN_UPLOAD_NEW_VIDEO = "Enviar novo vídeo"
HOME_VIDEOS_HEADER = "Vídeos armazenados"
HOME_NO_VIDEOS = "Nenhum vídeo encontrado. Envie um MP4 para começar."
HOME_DETAILS_HEADER = "Detalhes do vídeo"
HOME_DETAILS_NO_SELECTION = (
    "Selecione um vídeo na lista à esquerda para ver caminho da pasta e miniaturas das capturas."
)
HOME_SELECTED_LABEL = "Pasta:"
HOME_SELECTED_PATH = "Caminho do arquivo:"
HOME_GALLERY_HEADER = "Capturas"
HOME_GALLERY_EMPTY = (
    "Nenhuma captura neste vídeo. Execute uma verificação de fluxo e feche quando terminar;"
    " as imagens são salvas quando um veículo cruza a linha de contagem."
)
HOME_GALLERY_COLS_DEFAULT = 3
HOME_GALLERY_THUMB_MAX_PX = 118
HOME_CAPTURE_CAPTION_VEHICLE = "Veículo "

# Envio / upload
UPLOAD_TITLE = "Enviar vídeo"
BTN_SELECT_FILE = "Escolher arquivo MP4"
BTN_CONFIRM_SEND = "Confirmar envio"
BTN_CHANGE_FILE = "Trocar arquivo"
BTN_BACK = "Voltar"
UPLOAD_SELECTED_NONE = "Nenhum arquivo selecionado."
BTN_START_VERIFICATION = "Iniciar verificação de fluxo"
UPLOAD_COPYING_LABEL = "Armazenando o vídeo…"
UPLOAD_SUCCESS = "Vídeo armazenado com sucesso."
UPLOAD_DIALOG_TITLE = "Selecionar vídeo MP4"
UPLOAD_DIALOG_FILETYPES = [("MP4", "*.mp4"), ("Todos os arquivos", "*.*")]
UPLOAD_MP4_REQUIRED = "Selecione um arquivo com extensão .mp4."
UPLOAD_SAVE_ERROR = "Não foi possível salvar o vídeo."

# Wizard de ROI / linha (OpenCV — títulos e textos guiados PT-BR)
FLOW_ROI_WINDOW_TITLE = (
    "Passo 4/6 — Área de interesse (ROI): arraste um retângulo e pressione ENTER."
)
FLOW_LINE_WINDOW_TITLE = (
    "Passo 5/6 — Linha de contagem: clique dois pontos dentro da ROI; ENTER confirma."
)
FLOW_SELECTOR_MAX_DISPLAY_SIDE_PX = 1200  # lado maior máximo apenas para pré-visualização
ROI_SELECTOR_MIN_SIDE_PX = 32  # lado mínimo da ROI antes de aceitar ENTER
FLOW_CONFIGURED_TITLE = "Configuração da verificação"
FLOW_CONFIGURED_MESSAGE = (
    "ROI e linha de contagem definidas com sucesso. "
    "O passo seguinte será o tracking em tempo real (próxima fase)."
)
FLOW_CONFIGURE_ERROR_TITLE = "Não foi possível ler o vídeo"

TRACKING_CV_WINDOW_TITLE = (
    "Passo 6/6 — Tracking em tempo real (pressione ESC, Q ou use o botão para encerrar)."
)
TRACKING_CV_WINDOW_HINT = (
    "Acompanhe a máscara e os rótulos; estatísticas na janela lateral | ESC ou Q encerra"
)

STATS_PANEL_TITLE = "Estatísticas da sessão"
STATS_PANEL_STARTED_LABEL = "Início:"
STATS_PANEL_TOTAL_LABEL = "Veículos contados:"
STATS_PANEL_RATE_LABEL = "Média (veículos/min):"
BTN_EXIT_TRACKING_FLOW = "Sair do fluxo"
TRACKING_OPEN_FAILED_TITLE = "Falha ao abrir vídeo"
TRACKING_OPEN_FAILED_MESSAGE = "Não foi possível abrir este arquivo MP4 para leitura contínua."

# Detector YOLO26 / tracking — valores razoáveis para v1.
YOLO_MODEL = str(MODELS_DIR / "yolo26n.pt")
YOLO_CONFIDENCE = 0.35
YOLO_IMGSZ = 480
YOLO_DEVICE = ""  # vazio = auto (CUDA se disponível, senão CPU)
# COCO: car=2, motorcycle=3, bus=5, truck=7
YOLO_VEHICLE_CLASS_IDS = frozenset({2, 3, 5, 7})
YOLO_COCO_VEHICLE_LABELS_PT: dict[int, str] = {
    2: "Carro",
    3: "Moto",
    5: "Ônibus",
    7: "Caminhão",
}
YOLO_COCO_VEHICLE_SLUGS: dict[int, str] = {
    2: "carro",
    3: "moto",
    5: "onibus",
    7: "caminhao",
}
VEHICLE_SLUG_LABELS_PT: dict[str, str] = {
    **{slug: label for slug, label in zip(YOLO_COCO_VEHICLE_SLUGS.values(), YOLO_COCO_VEHICLE_LABELS_PT.values(), strict=True)},
    "veiculo": "Veículo",
}


def vehicle_class_label_pt(class_id: int) -> str:
    """Rótulo PT-BR para exibição (ex.: Carro, Moto)."""
    return YOLO_COCO_VEHICLE_LABELS_PT.get(class_id, "Veículo")


def vehicle_class_slug(class_id: int) -> str:
    """Slug curto para nomes de arquivo (ex.: carro, moto)."""
    return YOLO_COCO_VEHICLE_SLUGS.get(class_id, "veiculo")

MAX_ASSOCIATION_DISTANCE_PIXELS = 120
MAX_TRACK_MISSES = 18
MIN_TRACK_FRAMES_BEFORE_COUNT = 3
TRACK_MATCH_IOU_THRESHOLD = 0.12
TRACKING_WARMUP_FRAMES = 0
# Mantém o vídeo no ritmo natural (1 s de vídeo ≈ 1 s real); descarta frames se a inferência atrasar.
TRACKING_REALTIME_SYNC = True
