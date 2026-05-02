# Fluxo de experimentos no `raspi`

Este documento define o padrao operacional para testes reais do Talus-Droid no
`raspi`. O objetivo e manter evidencias rastreaveis para a validacao tecnica e
para o TCC sem transformar cada teste em um processo pesado demais.

O fluxo atual foi definido durante a frente de validacao do Kinect RGB-D. A regra
central e: **falhas do Kinect devem ser investigadas como falhas de
sensor/USB/libfreenect/driver antes de qualquer teste de VO, RTAB-Map ou SLAM**.

## Papel de cada host

| Host | Papel |
|---|---|
| `raspi` | Execucao real do robo, coleta de logs e artefatos, ROS nodes |
| `talus` | Repositorio, planejamento, documentacao, analise textual e automacoes locais |
| `aiquitude`/notebook com GUI | `rqt`, RViz2, Foxglove/PlotJuggler quando necessario |

O `talus` e headless; nao tratar RViz/rqt nele como fluxo normal de validacao.
Visualizacao remota e apoio de diagnostico, nao substitui os artefatos gerados no
`raspi`.

## Workspace operacional

- Workspace oficial no `raspi`: `/home/felip/talus-droid`.
- `~/ros2_ws` no `raspi` e legado.
- Evitar worktrees permanentes no `raspi` enquanto o fluxo de hardware nao estiver
  estavel. Worktrees continuam uteis no `talus` para desenvolvimento, docs e
  revisoes paralelas.

## Run bundle

Cada teste relevante no `raspi` deve gerar um **run bundle**:

```text
artifacts/testlogs/<YYYY-MM-DD-frente>/<host>-vNN-<descricao>/
  experiment.yaml
  notes.md
  <grupos do runner>/round-XXX/
```

Exemplos:

```text
artifacts/testlogs/2026-05-01-kinect-validation/raspi-v10-baseline-medium/
  experiment.yaml
  notes.md
  preflight/round-001/
  isolated-default/round-001/
```

```text
artifacts/testlogs/2026-05-02-kinect-validation/raspi-v11-powered-hub/
  experiment.yaml
  notes.md
  preflight/round-001/
  isolated-default/round-001/
```

### Convencao de nomes

```text
YYYY-MM-DD-<frente>/<host>-vNN-<descricao>
```

Para a frente atual, usar preferencialmente:

```text
YYYY-MM-DD-kinect-validation/raspi-vNN-<hipotese-ou-condicao>
```

Exemplos:

- `2026-05-01-kinect-validation/raspi-v10-baseline-medium`
- `2026-05-01-kinect-validation/raspi-v11-other-usb-port`
- `2026-05-02-kinect-validation/raspi-v12-powered-hub`
- `2026-05-02-kinect-validation/raspi-v13-other-cable`

## `experiment.yaml`

O `experiment.yaml` registra o contexto estruturado da rodada. Ele deve ser
preenchido antes do teste sempre que possivel e finalizado depois com o resultado.

Template minimo:

```yaml
run_id: 2026-05-01-kinect-validation/raspi-v10-baseline-medium
date: 2026-05-01
operator: felipe
host: raspi
workspace: /home/felip/talus-droid
branch: diag/2026-04-27-kinect-validation
git_commit: <sha>
git_dirty: <true|false>
ros_distro: jazzy
rmw_implementation: rmw_cyclonedds_cpp
ros_domain_id: 42

purpose: Validar e diagnosticar estabilidade RGB-D do Kinect v1 no raspi.
scenario: kinect_rgbd_preflight_investigation

hypothesis:
  summary: "RGB falha por topologia USB/alimentacao/libfreenect/driver, antes de VO/SLAM."
  variable_under_test: "baseline medium, porta USB atual, fonte atual"

hardware:
  kinect: Kinect v1 Xbox NUI
  raspberry_pi: Raspberry Pi 4
  usb_topology: <lsusb/topologia observada>
  power: <fonte/cabo/hub>
  powered_hub: <true|false>
  notes: <observacoes fisicas>

software:
  driver: kinect_ros2_node unified
  point_cloud: disabled
  video_resolution: medium
  invalidated_paths:
    - FREENECT_RESOLUTION_LOW + FREENECT_VIDEO_RGB

commands:
  - ros2 run talus_base talus_kinect_validate preflight --artifact-root <run-root>
  - ros2 run talus_base talus_kinect_validate isolated --rounds 10 --artifact-root <run-root>

acceptance:
  preflight_ready: "RGB e depth entregam amostra real, USB presente, cleanup OK"
  stability_ideal: "10/10 PASS"
  stability_minimum_to_consider_next_layer: ">= 8/10 PASS"
  block_next_layers_if: "RGB_TIMEOUT dominante, KINECT_OPEN_FAIL, USB_BUSY ou USB_MISSING"

result:
  pass: null
  rgb_timeout: null
  depth_timeout: null
  kinect_open_fail: null
  usb_busy: null
  usb_missing: null
  decision: pending
```

## `notes.md`

O `notes.md` guarda a leitura humana da rodada. Ele deve explicar a hipotese, o
que mudou, o resultado e a proxima decisao.

Template minimo:

```markdown
# raspi-v10-baseline-medium

## Objetivo

Validar/investigar o funcionamento RGB-D simultaneo do Kinect no `raspi` usando baseline medium.

## Hipotese

A falha dominante de RGB ocorre antes de VO/SLAM, possivelmente em USB, alimentacao, topologia, `libfreenect` ou driver.

## Condicao testada

- Porta USB:
- Fonte/cabo/hub:
- Branch/commit:
- Driver:

## Resultado

- PASS: X/N
- RGB_TIMEOUT: Y/N
- DEPTH_TIMEOUT: Z/N
- KINECT_OPEN_FAIL: W/N
- USB_BUSY/USB_MISSING:

## Evidencia principal

- Artifact root: `artifacts/testlogs/...`
- Logs relevantes:
- Topologia USB:

## Decisao

- [ ] Kinect suficientemente estavel para proxima etapa
- [ ] Manter bloqueio em Kinect/USB/libfreenect
- [ ] Repetir com nova condicao fisica
- [ ] Alterar driver/fork e repetir

## Proxima hipotese

...
```

## Fluxo para a frente Kinect

### Definicao de preflight

Neste projeto, **preflight** e o teste minimo de prontidao do Kinect antes de
qualquer etapa superior.

Ele verifica que o driver unificado sobe no `raspi`, os topicos esperados
aparecem, RGB e depth entregam pelo menos uma mensagem real, o USB continua
presente e o cleanup nao deixa processos relevantes vivos.

O preflight e usado de duas formas:

- se a meta e testar VO/SLAM, falha no preflight bloqueia a etapa superior;
- se a meta e investigar o Kinect, falha no preflight e resultado valido e deve
  ser registrada no run bundle.

### Sequencia recomendada

1. Criar o run bundle com `experiment.yaml` e `notes.md`.
2. Registrar estado inicial: branch, commit, dirty state, topologia USB,
   fonte/cabo/hub e observacoes fisicas.
3. Rodar `preflight` com `--artifact-root` apontando para o run bundle.
4. Se falhar, registrar a classificacao e manter a investigacao em
   Kinect/USB/libfreenect/driver.
5. Se passar, rodar `isolated --rounds 10` no mesmo artifact root.
6. Considerar camadas superiores apenas com estabilidade repetivel, idealmente
   `10/10 PASS` e no minimo `>= 8/10 PASS` para investigacao controlada.

## Tratamento de artefatos antigos

O padrao acima vale para os testes futuros. Para artefatos antigos, a politica
inicial e **manter os caminhos existentes** e adicionar metadados apenas aos runs
que continuam relevantes para a narrativa tecnica.

Antes de mover, compactar ou apagar qualquer artefato:

1. inventariar origem e destino;
2. verificar links existentes em `docs/reports/`;
3. preservar as evidencias usadas para decisoes tecnicas;
4. pedir confirmacao explicita.

## Uso de Obsidian e Trello

- Obsidian pode funcionar como caderno auxiliar e indice para monografia,
  apontando para run-id, commit, relatorio versionado e artifact root.
- Trello deve controlar tarefas e decisoes pendentes.
- Nenhum dos dois deve ser fonte primaria dos dados brutos.

## Regra de bloqueio

Enquanto o Kinect RGB-D nao estiver estavel, manter bloqueados:

- `odom_test` como validacao de VO;
- RTAB-Map;
- SLAM;
- conclusoes de estabilidade de navegacao.

Falhas como `RGB_TIMEOUT`, `KINECT_OPEN_FAIL`, `USB_BUSY` ou `USB_MISSING` devem
ser classificadas como frente Kinect/USB/libfreenect/driver ate que haja
evidencia repetivel em contrario.
