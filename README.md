# Fantasy Cave

Jogo 2D em **Python + Pygame** para a atividade de Computação Gráfica e Realidade Virtual/Aumentada (tema *Fantasy Cave*).
Você controla um explorador numa caverna fantástica: **quebre rochas** para abrir caminho, **colete todos os cristais** e
**encontre a saída**. Dá para jogar com **teclado**, **mouse** e, opcionalmente, **gestos de mão** pela câmera (OpenCV + MediaPipe).

## Estrutura

```
fantasy_cave/
├── main.py                 # ponto de entrada
├── requirements.txt        # pygame + (opcional) mediapipe/opencv
├── requirements-core.txt   # só o pygame (teclado e mouse)
├── README.md
├── .gitignore
├── src/
│   ├── config.py           # resolução, velocidade, dificuldades
│   ├── level.py            # mapas, rochas, cristais, saída, caminhos (sem Pygame)
│   ├── player.py           # explorador e colisões
│   ├── input_manager.py    # teclado + mouse + gestos em uma só entrada
│   ├── hand_controller.py  # câmera/MediaPipe em thread separada (opcional)
│   ├── renderer.py         # desenho da caverna, iluminação, efeitos
│   ├── ui.py               # menus, botões, partículas
│   ├── audio.py            # sons sintetizados (opcional)
│   └── game.py             # loop principal e estados
└── tests/test_game_logic.py
```

Tudo é desenhado com formas do Pygame e os sons são gerados por código: não há imagens nem áudios externos.
(Se quiser, coloque `hit.wav`, `break.wav`, `crystal.wav`, `exit.wav`, `click.wav` ou `win.wav` em `assets/sounds/` para substituí-los.)

## Requisitos

- **Python 3.12 recomendado** (3.9 a 3.12 funcionam com MediaPipe 0.10.21). Em Python 3.13+ o MediaPipe desta versão não instala:
  use `requirements-core.txt` e jogue com teclado e mouse.
- Windows, Linux ou macOS. Webcam apenas para os gestos.

## Como executar no VS Code

1. Extraia o `.zip` e abra a pasta: **Arquivo → Abrir Pasta…** → `fantasy_cave`.
2. Abra o terminal integrado (**Ctrl+`**).
3. Crie e ative o ambiente virtual.

   **Windows (PowerShell):**
   ```powershell
   python -m venv .venv
   .venv\Scripts\Activate.ps1
   ```
   Se o PowerShell bloquear o script: `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` e tente de novo. No CMD use `.venv\Scripts\activate.bat`.

   **Linux / macOS:**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```
4. Instale as dependências:
   ```
   pip install -r requirements.txt
   ```
5. Execute:
   ```
   python main.py
   ```
6. No VS Code, se pedir o interpretador: **Ctrl+Shift+P → Python: Select Interpreter → `.venv`**.

### Jogar sem MediaPipe (só teclado e mouse)

```
pip install -r requirements-core.txt
python main.py
```
O jogo nunca exige MediaPipe/OpenCV. Sem eles (ou sem câmera), a tecla **M** apenas mostra "Câmera indisponível" na tela.

## Controles

| Ação | Teclado | Mouse | Gesto (câmera) |
|---|---|---|---|
| Mover | WASD ou setas | clicar no chão: o explorador anda até lá | mão à esquerda/direita/acima/abaixo do centro da imagem |
| Quebrar rocha | **Espaço** (rocha à frente) | clicar na rocha (anda até ela se estiver longe) | **apontar** com 1 ou 2 dedos para a rocha, ou **martelada** (mão rápida de cima para baixo **ou para os lados**) |
| Coletar cristal | contato, ou **E** perto dele | clicar no cristal | fechar a mão (aberta → punho) |
| Entrar na saída | caminhar até ela | clicar na saída liberada | mover até ela |
| Câmera ligar/desligar | **M** | — | — |
| Reiniciar nível | **R** | botão "Reiniciar" na pausa | — |
| Pausa / voltar / sair | **ESC** | botões | — |
| Menus | setas/WASD + **Enter** | clique nos botões | — |

Na vitória: **R** jogar novamente, **N** próxima dificuldade, **D** trocar dificuldade, **Q** sair (ou use os botões).
O objeto sob o mouse é realçado; perto de rochas, cristais e da saída aparece uma dica na parte de baixo da tela.

## Dificuldades

Selecione no menu "Jogar" com o mouse (clique no cartão) ou com setas + Enter. Cada uma tem seu próprio mapa.

| Dificuldade | Cristais | Golpes por rocha | Rochas no mapa | Velocidade |
|---|---:|---:|---:|---:|
| Fácil | 5 | 2 | 4 | 5,6 blocos/s |
| Médio | 8 | 3 | 11 | 5,2 blocos/s |
| Difícil | 12 | 4 | 24 | 5,0 blocos/s |

A saída fica trancada (grade e cadeado) até todos os cristais serem coletados. Pontuação =
(cristais × 100 + rochas quebradas × 20 + bônus de tempo) × multiplicador (1/2/3). O melhor valor da sessão é mostrado na vitória.
Para ajustar resolução (`TILE`), velocidade, golpes por rocha e tempo de referência, edite `src/config.py`;
os mapas ficam em `src/level.py` (legenda no topo do arquivo).

## Câmera e gestos

1. Pressione **M**. O topo da tela mostra: *iniciando*, *ativa · sem mão*, *ativa · mão detectada* ou *indisponível* (com o motivo).
2. A miniatura da câmera fica no **canto direito da barra superior** (não cobre o mapa). Nela aparece uma **cruz de mira**:
   verde = posição da palma da mão; laranja = ponta do dedo indicador quando você está apontando. O pequeno "+" cinza marca o centro (zona neutra).
3. **Mover**: a posição da mão em relação ao centro da imagem funciona como joystick (com zona morta no meio). Mantenha a mão perto do centro para parar.
4. **Apontar (novo)**: estenda o indicador (ou indicador + médio) com anelar e mínimo fechados e aponte para a rocha ao lado do explorador.
   O explorador vira para a direção do dedo e golpeia a rocha mais alinhada que esteja ao alcance; enquanto você mantiver o dedo apontado, ele golpeia de novo a cada 0,7 s. Enquanto aponta, o explorador não anda.
5. **Martelada**: movimento rápido da mão de cima para baixo **ou de um lado para o outro**. Intervalo mínimo de 0,6 s entre golpes; o movimento fica pausado por 0,4 s depois do golpe.
   A martelada atinge a rocha que está à frente do explorador (a que ele está olhando).
6. **Interagir**: feche a mão (de aberta para punho) para coletar um cristal próximo.
7. Teclado e mouse continuam funcionando com a câmera ligada. A câmera é liberada ao desligar com M ou ao fechar o jogo.

Ajuste fino (se os gestos ficarem sensíveis demais ou de menos): parâmetros de `GestureDetector` em `src/hand_controller.py`
(`hammer_speed`, `swing_min`, `swing_speed`, `point_hold`, `point_interval`).

## Erros comuns

- **`ModuleNotFoundError: pygame`** → o ambiente virtual não está ativo ou faltou `pip install -r requirements.txt`.
- **Falha ao instalar mediapipe** (Python 3.13+, ARM, etc.) → use `pip install -r requirements-core.txt`; ou instale o Python 3.12.
- **"Câmera não encontrada ou em uso"** → feche Zoom/Teams/navegador que usem a webcam; se houver mais de uma, mude `CAMERA_INDEX` em `src/config.py`. No macOS/Windows, autorize o acesso à câmera ao terminal/VS Code.
- **"versão do MediaPipe incompatível"** → `pip install mediapipe==0.10.21`.
- **Conflito com numpy ao instalar** → o MediaPipe 0.10.21 exige `numpy<2`; use o `requirements.txt` do projeto num ambiente virtual novo (não instale `opencv-python` novo junto).
- **Sem som** → o áudio é opcional; se o dispositivo de som falhar, o jogo continua mudo.
- **Gestos instáveis** → boa iluminação, mão inteira visível, fundo simples; a martelada precisa de um movimento rápido; para apontar, mantenha a palma virada para a câmera e o indicador bem estendido.

## Testes

```
python -m unittest discover -s tests -v
```
Cobrem mapas (cristais, resolubilidade), rochas (quantidade exata de golpes), cristais (coleta única), saída trancada,
colisões, detecção de martelada (vertical e lateral), apontar e punho e um fluxo completo do jogo com janela "dummy" (menu → dificuldade → golpe por Espaço e clique → vitória → pausa → reinício).

## Limitações

- Os gestos **não foram testados com uma câmera real** pelo autor (o ambiente de desenvolvimento não tinha webcam): a lógica de detecção (martelada vertical e lateral, apontar, punho) foi testada com dados simulados e o comportamento sem câmera foi verificado. A detecção de "apontar" depende da qualidade da imagem; se falhar, ajuste a posição da mão ou use a martelada. Os limiares (martelada, zona morta) podem precisar de ajuste no seu computador (parâmetros em `GestureDetector`, `src/hand_controller.py`).
- Clique para mover usa caminho por blocos (BFS); se rochas bloquearem o caminho, o jogo avisa para quebrá-las primeiro.
- Não há salvamento de recordes entre sessões nem limite de tempo (o tempo só influencia a pontuação).
