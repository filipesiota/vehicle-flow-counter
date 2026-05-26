# Contador de fluxo veicular (vehicle-flow-counter)

Aplicativo desktop em **Python 3.12** para contar veículos que atravessam uma **linha de contagem** desenhada em um vídeo de rodovia. Utiliza **CustomTkinter** para a interface principal, **OpenCV** para seleção de ROI e linha, e **[Ultralytics YOLO26](https://github.com/ultralytics/ultralytics)** para detecção de veículos (carro, moto, ônibus, caminhão).

## Requisitos

- **Python** 3.12 (vide `requires-python` no `pyproject.toml`)
- **[uv](https://docs.astral.sh/uv/)** para ambiente virtual e dependências
- **Tkinter** (necessário para CustomTkinter):
  - Debian / Ubuntu / WSL: `sudo apt install python3-tk`
  - outros sistemas: use o pacote Tk da sua distro ou o instalador Python oficial com Tcl/Tk

## Instalação

Na raiz do repositório:

```bash
uv venv
uv sync
```

Isso instala `opencv-python`, `customtkinter`, `pillow`, `numpy`, `ultralytics` (PyTorch incluído) e demais dependências conforme o `pyproject.toml`.

Na primeira execução do tracking, o modelo **`yolo26n.pt`** é baixado automaticamente para `data/models/`.

## Executar

```bash
uv run python -m vehicle_flow_counter
```

Alternativa equivalente depois do `uv sync`:

```bash
uv run vehicle-flow-counter
```

## Fluxo de uso (passo a passo)

1. **Home** — Veja os vídeos já armazenados em disco ou envie um novo MP4.
2. **Enviar novo vídeo** — Escolha um arquivo `.mp4`, confirme o envio e aguarde a cópia para a pasta de dados local.
3. **Iniciar verificação de fluxo** — Abre um assistente com janelas **OpenCV**:
   - desenhar a **região de interesse (ROI)** com um retângulo;
   - marcar dois pontos para a **linha de contagem** dentro da ROI (idealmente perpendicular ao fluxo esperado).
4. **Tracking em tempo real** — Janela do vídeo com máscara das detecções, bounding boxes e rótulos; painel lateral com estatísticas (início da sessão, total de veículos, média veículos/minuto). Ao **sair do fluxo** (botão ou tecla informada na janela), a sessão encerra.

**Contagem**: considera-se a passagem quando o **centro do bounding box** do veículo cruza a linha dentro da ROI — não na simples entrada da ROI.

## Armazenamento de dados (`data/`)

A pasta **`data/`** fica na raiz do projeto (está no `.gitignore` e não é versionada):

```text
data/models/yolo26n.pt
data/videos/<nome-da-pasta-do-video>/video.mp4
data/videos/<nome-da-pasta-do-video>/capturas/*.jpg
```

- A pasta `<nome-da-pasta-do-video>` é derivada do nome original do arquivo, sanitizado para o sistema de ficheiros; em caso de colisão, é acrescentado sufixo numérico (`_2`, etc.).
- Cada foto de captura segue o padrão:

  **`{unix_timestamp}_vehicle_{id}.jpg`**

  Ordenação na galeria da home pelo **timestamp** no nome — ordem cronológica das contagens registadas em disco.

## Estrutura do código (visão rápida)

```text
src/vehicle_flow_counter/
├── __main__.py          # entrada `python -m vehicle_flow_counter`
├── config.py            # caminhos, strings da UI em PT-BR, constantes de visão
├── domain/models.py      # VideoEntry, Roi, CountingLine, TrackingStats…
├── services/             # vídeo, capturas, sessão de tracking
├── tracking/             # detector YOLO26, tracker por centróides, linha cruzamento, visualização
├── ui/                   # app, telas home/upload, wizard ROI/linha, painel stats, galeria
└── utils/               # sanitização de nomes, FPS e leitura de frames
```

## Configuração do detector (YOLO26)

Constantes em `config.py`:

| Constante | Padrão | Descrição |
|-----------|--------|-----------|
| `YOLO_MODEL` | `yolo26n.pt` | Modelo Ultralytics (nano — rápido; use `yolo26s.pt` etc. para mais precisão) |
| `YOLO_CONFIDENCE` | `0.35` | Limiar mínimo de confiança |
| `YOLO_IMGSZ` | `640` | Tamanho de inferência |
| `YOLO_DEVICE` | `""` (auto) | `cpu`, `0` (GPU), etc. |

Classes COCO filtradas: carro, motocicleta, ônibus, caminhão.

## Limitações conhecidas

- Veículos muito pequenos ou parcialmente oclusos podem não ser detectados pelo modelo nano.
- Oclusões entre veículos próximos podem trocar **IDs** entre frames — aceitável na v1.
- **ROI e linha** não são gravadas entre sessões: precisam ser redefinidas a cada nova verificação.
- Inferência em CPU é mais lenta; GPU NVIDIA acelera significativamente.

## Licença e contribuições

Este repositório é um projeto pessoal; adapte livremente para o seu cenário local.

O pacote **ultralytics** é licenciado sob [AGPL-3.0](https://github.com/ultralytics/ultralytics/blob/main/LICENSE); verifique os termos se usar em produção comercial.
