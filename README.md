# Contador de fluxo veicular (vehicle-flow-counter)

Aplicativo desktop em **Python 3.12** para contar veículos que atravessam uma **linha de contagem** desenhada em um vídeo de rodovia. Utiliza **CustomTkinter** para a interface principal e **OpenCV** para seleção de ROI e linha, detecção baseada em subtração de fundo (**MOG2**) e playback do tracking — **sem modelos de aprendizado de máquina**.

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

Isso instala `opencv-python`, `customtkinter`, `pillow` e `numpy` conforme o `pyproject.toml`.

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
4. **Tracking em tempo real** — Janela do vídeo com máscara, centróides e rótulos; painel lateral com estatísticas (início da sessão, total de veículos, média veículos/minuto). Ao **sair do fluxo** (botão ou tecla informada na janela), a sessão encerra.

**Contagem**: considera-se a passagem quando o **centro do bounding box** do blob cruza a linha dentro da ROI — não na simples entrada da ROI.

## Armazenamento de dados (`data/`)

A pasta **`data/`** fica na raiz do projeto (está no `.gitignore` e não é versionada):

```text
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
├── tracking/             # detector MOG2, tracker por centróides, linha cruzamento, visualização
├── ui/                   # app, telas home/upload, wizard ROI/linha, painel stats, galeria
└── utils/               # sanitização de nomes, FPS e leitura de frames
```

## Limitações conhecidas

- Iluminação variável forte, reflexos e má sombra podem piorar a subtração de fundo (**MOG2**).
- Oclusões (veículos sobrepostos) e blobs que se mesclam podem trocar **IDs** entre frames — aceitável na v1 ao custo de contagens menos estáveis quando os veículos passam muito próximos.
- **ROI e linha** não são gravadas entre sessões: precisam ser redefinidas a cada nova verificação.
- Funciona bem como experimento pedagogico/engineering; cenários complexos ao vivo exigiriam sensores dedicados ou modelos especializados.

## Licença e contribuições

Este repositório é um projeto pessoal; adapte livremente para o seu cenário local.
