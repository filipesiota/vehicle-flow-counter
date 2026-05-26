# Vehicle Flow Counter

## Task 1 — Implementar tracking manual com OpenCV

* **Responsável:** Pessoa 1
* **Arquivo:** `tracking/manual_tracker.py`

Criar:

```python
def run_manual_tracking(
    video_path: str,
    detection_area: list[tuple[int, int]],
) -> None:
    ...
```

### Escopo

Implementar object tracking do zero usando OpenCV, sem modelo de IA.

A função deve:

* abrir o vídeo;
* processar frame a frame;
* detectar objetos em movimento com OpenCV;
* rastrear objetos com estratégia própria, como centroid tracking;
* verificar se o centroide do veículo entrou no polígono `detection_area`;
* evitar contagem duplicada do mesmo veículo;
* exibir o vídeo em tempo real com `cv2.imshow()`;
* desenhar no frame:

  * polígono da área de detecção;
  * bounding boxes;
  * IDs dos objetos;
  * total de veículos detectados;
  * média de veículos por minuto.

### Critérios de aceite

* A função recebe apenas `video_path` e `detection_area`.
* `detection_area` é uma lista de pontos do polígono.
* A função não retorna valor.
* O vídeo é exibido com `cv2.imshow()`.
* A tecla `q` encerra o processamento.
* O polígono é desenhado no frame.
* A contagem acontece quando o veículo entra no polígono.
* O mesmo veículo não é contado múltiplas vezes.
* O total e a média por minuto aparecem no frame.

---

## Task 2 — Implementar tracking com YOLO

* **Responsável:** Pessoa 2
* **Arquivo:** `tracking/yolo_tracker.py`

Criar:

```python
def run_yolo_tracking(
    video_path: str,
    detection_area: list[tuple[int, int]],
) -> None:
    ...
```

### Escopo

Implementar object tracking usando YOLO.

A função deve:

* abrir o vídeo;
* carregar o modelo YOLO;
* processar frame a frame;
* detectar veículos:

  * carro;
  * moto;
  * caminhão;
  * ônibus;
* rastrear veículos com IDs;
* verificar se o centroide do veículo entrou no polígono `detection_area`;
* evitar contagem duplicada pelo `track_id`;
* exibir o vídeo em tempo real com `cv2.imshow()`;
* desenhar no frame:

  * polígono da área de detecção;
  * bounding boxes;
  * ID;
  * classe;
  * total geral;
  * total por categoria;
  * média de veículos por minuto.

### Critérios de aceite

* A função recebe apenas `video_path` e `detection_area`.
* `detection_area` é uma lista de pontos do polígono.
* A função não retorna valor.
* O vídeo é exibido com `cv2.imshow()`.
* A tecla `q` encerra o processamento.
* O polígono é desenhado no frame.
* A contagem acontece quando o veículo entra no polígono.
* O mesmo veículo não é contado múltiplas vezes.
* O total geral, total por categoria e média por minuto aparecem no frame.

---

## Task 3 — Criar UI para upload, escolha do tracking e seleção de polígono

* **Responsável:** Pessoa 3
* **Arquivo:** `app.py`

### Escopo

Criar uma UI básica para configurar e iniciar o processamento.

A aplicação deve:

* permitir upload de vídeo;
* salvar o vídeo em `uploads/`;
* capturar o primeiro frame do vídeo;
* exibir o primeiro frame para o usuário;
* permitir que o usuário selecione múltiplos pontos sobre a imagem;
* formar um polígono com os pontos selecionados;
* permitir limpar/refazer a seleção;
* permitir escolher o tipo de tracking:

  * manual com OpenCV;
  * YOLO;
* converter os pontos selecionados para:

```python
detection_area = [
    (x1, y1),
    (x2, y2),
    (x3, y3),
    ...
]
```

* chamar a função correta:

```python
if tracking_type == "manual":
    run_manual_tracking(video_path, detection_area)
else:
    run_yolo_tracking(video_path, detection_area)
```

### Critérios de aceite

* A aplicação permite upload de vídeo.
* O vídeo enviado é salvo em `uploads/`.
* O primeiro frame do vídeo é exibido.
* O usuário consegue selecionar pontos sobre o primeiro frame.
* A área de detecção é formada como um polígono.
* O polígono exige no mínimo 3 pontos.
* O usuário consegue limpar/refazer a seleção.
* O usuário consegue escolher entre tracking manual e YOLO.
* Ao iniciar, a aplicação chama a função correta.
* A UI passa apenas `video_path` e `detection_area` para os trackers.
* A estrutura inicial do projeto fica assim:

```text
app.py
tracking/
  manual_tracker.py
  yolo_tracker.py
uploads/
requirements.txt
README.md
```
