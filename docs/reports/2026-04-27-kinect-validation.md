# Relatório — Validação Diagnóstica do Kinect

Data: 2026-04-27  
Host alvo: `raspi`  
Workspace: `/home/felip/talus-droid`  
Branch diagnóstica: `diag/2026-04-27-kinect-validation`  
Raiz de artefatos: `artifacts/testlogs/2026-04-27-kinect-validation/raspi/`

## Resumo executivo

O preflight real no `raspi` ainda bloqueia a bateria maior: o Kinect abre, o USB permanece presente e o tópico de profundidade entrega imagens, mas o fluxo RGB não entrega amostras quando o nó unificado sobe RGB + depth simultaneamente.

Resultado atual: falha atribuída à frente Kinect/driver/USB, **não** à odometria visual nem ao SLAM. A execução `raspi-v5` também confirmou que o cleanup diagnóstico foi corrigido (`cleanup_ok=true`), eliminando o falso `CLEANUP_FAIL` visto em rodadas anteriores.

Evidências adicionais apontam para limitação/falha no streaming simultâneo RGB+depth nesta configuração: `ros2 topic hz /depth/image_raw` mede depth, `ros2 topic hz /image_raw` não recebe frames no nó unificado; o nó modular RGB sozinho publica a ~30 Hz; e `freenect-camtest` nativo recebe depth mas registra perdas contínuas no stream de vídeo.

## Ambiente

- ROS 2 Jazzy
- `ROS_DOMAIN_ID=42`
- `RMW_IMPLEMENTATION=rmw_cyclonedds_cpp`
- Kinect v1 em modo `unified`
- Point cloud desligada por padrão
- Execução headless, sem RViz na bateria automática

## Resultado agregado

| Grupo | Rodadas | PASS | Falha dominante | Observação |
|---|---:|---:|---|---|
| `preflight` (`raspi-v5`) | 1 | 0 | `RGB_TIMEOUT` | USB presente antes/depois; depth OK; RGB sem amostra; cleanup OK |
| `isolated-default` | 0 | 0 | blocked | bloqueado até resolver RGB simultâneo |
| `settle-10s` | 0 | 0 | not-run-yet | aguardando execução |
| `settle-30s` | 0 | 0 | not-run-yet | aguardando execução |
| `settle-60s` | 0 | 0 | not-run-yet | aguardando execução |
| `usb-reset` | 0 | 0 | not-run-yet | opt-in; aguardando decisão |

## Preflight real no `raspi`

Artefatos principais:

- `artifacts/testlogs/2026-04-27-kinect-validation/raspi-v4/preflight/round-001/`
- `artifacts/testlogs/2026-04-27-kinect-validation/raspi-v5/preflight/round-001/`

### `raspi-v4`

- Status: `RGB_TIMEOUT`
- USB Kinect presente antes/depois: sim
- Tópicos `/image_raw` e `/depth/image_raw`: visíveis
- `depth_sample_ok`: `true`
- `rgb_sample_ok`: `false`
- `cleanup_ok`: `false`
- Causa do cleanup: processos `static_transform_publisher` órfãos do launch; corrigido depois com teardown por process group e `pkill` dos TF estáticos conhecidos.

### `raspi-v5`

- Status: `RGB_TIMEOUT`
- USB Kinect presente antes/depois: sim
- Tópicos `/image_raw` e `/depth/image_raw`: visíveis
- `depth_sample_ok`: `true`
- `rgb_sample_ok`: `false`
- `cleanup_ok`: `true`
- `launch_exit_code`: `-15` esperado pelo encerramento controlado do launch pelo runner.

Comandos/evidências manuais:

- Nó unificado, depth-first: `/depth/image_raw` publica ~30 Hz; `/image_raw` não entrega frames; sampler RGB expira.
- Nó unificado, video-first experimental: `/image_raw` publica ~30 Hz; `/depth/image_raw` não entrega frames; confirma que o primeiro stream iniciado monopoliza/vence e o segundo não fica utilizável nesta configuração.
- Nó modular RGB sozinho: `/kinect/rgb/image_raw` publica ~30 Hz.
- `freenect-camtest`: recebe frames de depth, mas reporta perdas contínuas no stream de vídeo (`[Stream 80] Lost ... packets`) e não mostra frames RGB úteis durante a janela testada.

## Verificação 6.1 (execução local)

| Passo | Status | Evidência / bloqueador |
|---|---|---|
| 1 | PASS | `pytest`: `19 passed in 0.04s` |
| 2 | BLOCKED | missing `/opt/ros/jazzy/setup.bash` |
| 3 | BLOCKED | `ros2: command not found` |
| 4 | BLOCKED | `install/setup.bash` absent |
| 5 | PENDENTE (raspi) | depende de artefatos no `raspi` |
| 6 | PENDENTE (raspi) | depende de artefatos no `raspi` |
| 7 | PENDENTE (raspi) | depende de artefatos no `raspi` |

## Decisões

- Melhor tempo de settle observado: aguardando execução da matriz.
- Reset USB ajuda: aguardando condição opt-in e execução controlada.
- Kinect confiável para `odom_test`: **não ainda**; preflight bloqueado por RGB simultâneo.
- Falhas anteriores atribuídas a: no estado atual, falha está na frente Kinect/driver/USB/coleta de imagem RGB simultânea, antes de odometria visual/SLAM.

## Continuação — 2026-04-29

Nova frente: validar aquisição RGB-D simultânea antes de retomar VO/SLAM.

Regra operacional mantida: o `preflight` do Kinect precisa passar antes de `odom_test` ou `slam`.

### `raspi-v6-preflight`

- Status: `RGB_TIMEOUT`
- USB Kinect presente antes/depois: sim
- `rgb_sample_ok`: `false`
- `depth_sample_ok`: `true`
- `cleanup_ok`: `true`
- `launch_exit_code`: `-15`, esperado pelo encerramento controlado do runner
- Artefatos: `artifacts/testlogs/2026-04-29-kinect-rgbd/raspi-v6-preflight/preflight/round-001/`

Interpretação: a falha foi reproduzida em uma rodada limpa; os tópicos aparecem e o depth entrega amostra, mas o RGB não entrega frame real no nó unificado. A classificação continua na camada Kinect/USB/driver/aquisição, antes de VO/SLAM.

### `raspi-v7-usb-direct`

Mudança física: Kinect movido da porta USB 3.0 de baixo para a porta USB 3.0 de cima no Raspberry Pi.

- Status: `PASS`
- USB Kinect presente antes/depois: sim
- `rgb_sample_ok`: `true`
- `depth_sample_ok`: `true`
- `cleanup_ok`: `true`
- `launch_exit_code`: `-15`, esperado pelo encerramento controlado do runner
- Topologia observada: Kinect atrás de hub NEC em `Bus 001`, câmera `045e:02ae` em `480M`
- Artefatos: `artifacts/testlogs/2026-04-29-kinect-rgbd/raspi-v7-usb-direct/preflight/round-001/`

Interpretação: a troca de porta USB alterou o comportamento de falha para sucesso no preflight. Isso aponta fortemente para sensibilidade a topologia/porta USB ou estado físico de conexão, não para falha fixa do pipeline ROS/RTAB-Map.

Próximo passo recomendado: rodar a bateria isolada de 10 rodadas na nova porta antes de liberar `odom_test` novamente.

### `raspi-v8-stability` — bateria A

Objetivo: verificar se o `PASS` do `raspi-v7-usb-direct` se mantém em rodadas repetidas na nova porta USB antes de avançar para uptime longo ou `odom_test`.

- Modo: `isolated --rounds 10`
- Resultado agregado: `1 PASS`, `9 RGB_TIMEOUT`
- Rodadas `001` a `009`: `RGB_TIMEOUT`, com RGB `TIMEOUT` e depth `OK`
- Rodada `010`: `PASS`, com RGB `OK` e depth `OK`
- USB após a bateria: Kinect ainda presente; câmera `045e:02ae` em `480M`
- Processos remanescentes relevantes após a bateria: nenhum observado no snapshot salvo
- Artefatos: `artifacts/testlogs/2026-04-29-kinect-rgbd/raspi-v8-stability/round-battery-a/`

Interpretação: a nova porta USB permitiu um `PASS` pontual, mas ainda não é estável. O padrão dominante voltou a ser RGB não entregar frame real enquanto depth entrega amostra. Isso bloqueia as baterias B/C, o uptime de 30 minutos e qualquer retomada de `odom_test` até nova ação de diagnóstico.

Próximo passo recomendado: testar hub USB energizado ou executar o cross-check nativo com `freenect-camtest` para separar limitação de USB/hardware de problema no driver ROS.

## Diagnóstico profundo — 2026-04-29

Raiz de artefatos: `artifacts/testlogs/2026-04-29-kinect-rgbd/raspi-v9-deep-diagnostics/`

### Sistema e USB

- Kernel: `Linux raspi 6.8.0-1051-raspi #55-Ubuntu SMP PREEMPT_DYNAMIC Thu Mar 19 11:43:53 UTC 2026 aarch64`
- Uptime no início: 13 dias
- `vcgencmd get_throttled`: `throttled=0x0`, sem subtensão/throttling registrado no snapshot
- Kinect enumerado: sim, com Motor `045e:02b0`, Audio `045e:02ad` e Camera `045e:02ae`
- Topologia: câmera em `480M`, atrás de hub NEC no `Bus 001`
- Observação USB passiva por 60s: estável, sem desaparecimento das interfaces no `lsusb`
- `dmesg`: indisponível sem sudo (`Operation not permitted`)
- Estado final após testes: Kinect ainda enumerado e sem processos relevantes remanescentes no snapshot final

### `libfreenect` nativo

Ferramentas nativas presentes em `/usr/local/bin` e bibliotecas em `/usr/local/lib`.

Foram rodadas 3 execuções de `freenect-camtest` com `timeout 25`:

| Rodada | Exit code | Linhas `Stream 80 Lost` | Frames depth recebidos | Evidência de vídeo |
|---|---:|---:|---:|---|
| 1 | 124 | 154 | 612 | perdas contínuas; 0 frames úteis no stream de vídeo |
| 2 | 124 | 232 | 613 | perdas contínuas; 0 frames úteis no stream de vídeo |
| 3 | 124 | 154 | 429 | perdas contínuas; 0 frames úteis no stream de vídeo |

Interpretação: o problema não é exclusivo do ROS. O `libfreenect` nativo também recebe depth, mas o stream de vídeo apresenta perda contínua de pacotes e não produz frames úteis de forma estável.

### ROS unificado: tópico, QoS e amostras

Com `kinect_ros2_node` unificado e point cloud desligada:

- `/image_raw` e `/depth/image_raw` aparecem com publisher.
- QoS dos dois tópicos: `RELIABLE`, `KEEP_LAST (10)`, `VOLATILE`.
- `talus_kinect_sample_image /image_raw --timeout 15`: `TIMEOUT`
- `talus_kinect_sample_image /depth/image_raw --timeout 15`: `OK`, `640x480`, `16UC1`
- `ros2 topic echo --once /image_raw`: timeout
- `ros2 topic echo --once /depth/image_raw`: OK

Interpretação: não parece ser mismatch de QoS nem problema específico do sampler. O tópico RGB existe, mas não entrega mensagens reais; o depth entrega.

### ROS modular: streams isolados

Foram rodadas 5 tentativas de RGB modular e 5 de depth modular:

- RGB modular sozinho: 4/5 rodadas publicaram em aproximadamente 30 Hz; 1/5 falhou ao abrir o Kinect (`Could not open Kinect device`).
- Depth modular sozinho: 4/5 rodadas publicaram em aproximadamente 30 Hz; 1/5 falhou ao abrir o Kinect (`Could not open Kinect device`).
- Warnings de calibração ausente apareceram, mas não explicam a falha de stream.

Interpretação: cada stream isolado pode funcionar, mas reaberturas rápidas ainda podem falhar. A falha dominante do pipeline principal continua sendo a simultaneidade RGB-D, não a incapacidade absoluta de cada stream individual.

### ROS unificado repetido

Foram rodadas 10 execuções `isolated` do driver unificado:

- Resultado: `10 RGB_TIMEOUT`, `0 PASS`
- Padrão: depth entrega amostra; RGB não entrega frame real.

### Conclusão do diagnóstico profundo

Classificação provável: limitação/falha na camada Kinect/USB/libfreenect para streaming de vídeo sob esta topologia/alimentação, agravada no modo RGB-D simultâneo do driver ROS. A evidência nativa com `freenect-camtest` mostra que o problema existe abaixo do ROS; a evidência ROS mostra que QoS e tópico visível não bastam, pois o publisher RGB não entrega mensagens reais.

Decisão operacional: não liberar `odom_test` ainda. As próximas opções objetivas são testar hub USB energizado, testar outro cabo/fonte/Kinect, ou implementar um experimento de driver de baixa banda/ordem de streams com teste automatizado antes.

## Reorganização do fluxo de evidências — 2026-05-02

Durante a retomada da frente Kinect, foram usadas worktrees no `talus` para
separar diagnostico, experimento e documentacao. A sincronizacao com o `raspi`
mostrou que o problema principal nao era apenas rodar mais testes: era preciso
organizar melhor branch, workspace operacional, fork Kinect aninhado e artefatos
para que os proximos testes fossem reprodutiveis e interpretaveis por agentes e
por humanos.

O fluxo oficial para novos testes reais no `raspi` passa a ser o run bundle
documentado em `docs/diagnostics/raspi-experiment-flow.md`:

```text
artifacts/testlogs/<YYYY-MM-DD-frente>/<host>-vNN-<descricao>/
  experiment.yaml
  notes.md
  <grupos do runner>/round-XXX/
```

Para a frente atual, a convencao preferida e:

```text
artifacts/testlogs/YYYY-MM-DD-kinect-validation/raspi-vNN-<hipotese-ou-condicao>/
```

O termo `preflight` tambem foi formalizado: e o teste minimo de prontidao do
Kinect, no qual o driver unificado sobe, `/image_raw` e `/depth/image_raw`
entregam mensagens reais, USB permanece presente e cleanup termina limpo. Quando
o objetivo e VO/SLAM, falha no preflight bloqueia a etapa superior. Quando o
objetivo e investigar o Kinect, a falha do preflight e o resultado da rodada e
deve ser registrada no bundle.

## Experimento low-bandwidth descartado como hipótese ativa

A branch `exp/2026-04-29-kinect-low-bandwidth` adicionou uma matriz com variáveis
`TALUS_KINECT_VIDEO_RESOLUTION`, `TALUS_KINECT_STREAM_START_ORDER` e
`TALUS_KINECT_STREAM_START_DELAY_MS`. O resultado operacional foi util para
diagnostico, mas a hipotese `low` nao deve continuar ativa.

Motivo: `FREENECT_RESOLUTION_LOW + FREENECT_VIDEO_RGB` nao e uma combinacao
suportada pelo `libfreenect`. Nas rodadas `low-*`, o driver abortou em
`freenect_set_video_mode returned: -1`; portanto a leitura correta e falha de
modo de video invalido (`KINECT_OPEN_FAIL`), nao instabilidade fisica do Kinect.

Resumo da matriz low-bandwidth:

| Caso | Rodadas | Leitura correta | Observação |
|---|---:|---|---|
| `baseline` (`medium`, `depth-first`) | 10 | `1 PASS`, `9 RGB_TIMEOUT` | PASS pontual; nao prova estabilidade |
| `low-depth-first` | 10 | `KINECT_OPEN_FAIL` | `freenect_set_video_mode=-1` |
| `low-video-first` | 10 | `KINECT_OPEN_FAIL` | `freenect_set_video_mode=-1` |
| `low-video-first-delay-250` | 10 | `KINECT_OPEN_FAIL` | `freenect_set_video_mode=-1` |
| `low-video-first-delay-500` | 10 | `KINECT_OPEN_FAIL` | `freenect_set_video_mode=-1` |
| `low-depth-first-delay-500` | 10 | `KINECT_OPEN_FAIL` | `freenect_set_video_mode=-1` |

Decisao: nao usar `low` como caminho de investigacao. As proximas hipoteses
devem focar em `medium`, topologia USB, alimentacao/cabo/hub, comportamento
nativo do `libfreenect` e ajustes estaveis no driver/fork Kinect.

## Classificação inicial dos artefatos existentes

Os artefatos atuais no `raspi` foram classificados sem mover ou apagar arquivos.
A politica inicial e manter os caminhos existentes e adicionar metadados somente
nos runs que continuam relevantes para a narrativa tecnica.

| Frente | Estado | Decisão |
|---|---|---|
| `2026-04-27-kinect-validation` | preflights iniciais, cleanup corrigido, RGB ainda falhando | preservar como historico da criacao do gate |
| `2026-04-29-kinect-rgbd` | inclui `raspi-v7` PASS pontual, `raspi-v8` 1/10 PASS e diagnostico profundo | preservar como evidencia principal da instabilidade |
| `2026-04-29-kinect-low-bandwidth` | matriz `low` invalida para RGB; baseline medium 1/10 PASS | preservar como historico; nao usar como hipotese ativa |
| `rescue/2026-05-01-raspi-before-exp-low-bandwidth-sync` | snapshots antes da sincronizacao do `raspi` | preservar ate fechamento da limpeza do fork/branches |

Nenhuma reorganizacao fisica foi executada nesta etapa. Se os artefatos forem
movidos para `archive/` ou compactados posteriormente, os links deste relatorio
devem ser atualizados junto.

## Próximos testes recomendados

Continuar na frente `kinect-validation`, usando run bundles. Exemplos de rodadas
futuras:

```text
artifacts/testlogs/2026-05-01-kinect-validation/raspi-v10-baseline-medium/
artifacts/testlogs/2026-05-01-kinect-validation/raspi-v11-other-usb-port/
artifacts/testlogs/2026-05-02-kinect-validation/raspi-v12-powered-hub/
```

Cada rodada deve variar uma hipótese por vez e registrar explicitamente:

- topologia USB;
- fonte/cabo/hub;
- branch/commit e estado dirty;
- saída do preflight;
- decisão de bloquear ou repetir.

## Checklist de aceite

- [ ] Bateria isolada reproduzível no `raspi`.
- [ ] Logs por rodada suficientes para diagnosticar USB/processo/tópico.
- [ ] Classificação explícita de falhas registrada por rodada.
- [ ] Comparação entre settle padrão, 10s, 30s e 60s.
- [ ] Decisão documentada sobre reset USB.
- [x] Fluxo de run bundle definido para novos testes (`experiment.yaml` + `notes.md`).
- [x] Caminho `low` descartado como hipótese ativa para RGB.
- [x] Preflight Kinect executado antes dos testes maiores.
- [x] Conclusão separa Kinect/coleta/odometria/SLAM.

## Matriz Kinect-only — 2026-05-02

Raiz de artefatos: `artifacts/testlogs/2026-05-02-kinect-validation/raspi-v17-kinect-method-matrix/`

Objetivo: comparar metodos de subida focados somente no Kinect, sem usar `floor_test` como metodo de teste, para separar instabilidade do sensor/driver de efeitos de VO/RTAB-Map ou do bringup completo da base.

Condicao comum da matriz:

- `talus-bringup.service` parado antes dos testes Kinect-only.
- Espera de 120s entre metodos para reduzir interferencia de reabertura rapida do Kinect/libfreenect.
- Point cloud desligada.
- `ROS_DOMAIN_ID=42` e `RMW_IMPLEMENTATION=rmw_cyclonedds_cpp` nos testes ROS.
- O `floor_test` foi usado apenas no final para restaurar o estado operacional do robo, nao como metodo principal desta matriz.

### Resultado por metodo

| Metodo | Open/start | RGB | Depth | Leitura |
|---|---|---|---|---|
| `freenect-camtest` | nativo | video instavel | 619 frames depth | `Stream 80` com 189 linhas de perda; apenas 1 frame de video observado no log sumarizado |
| `ros2 run kinect_ros2 kinect_ros2_node --disable-pointcloud` | `freenect_start_video=0`, `freenect_start_depth=0` | `0/5 OK`, `5/5 TIMEOUT` | `5/5 OK` | driver abre e inicia streams, mas RGB nao entrega mensagens reais |
| `ros2 launch talus_bringup kinect.launch.py driver_mode:=unified enable_point_cloud:=false` | `freenect_start_video=0`, `freenect_start_depth=0` | `0/5 OK`, `5/5 TIMEOUT` | `5/5 OK` | mesmo padrao do no ROS direto; launch/TF nao explicam sozinhos |
| `./scripts/talus-up kinect` | `freenect_start_video=0`, `freenect_start_depth=0` | `0/5 OK`, `5/5 TIMEOUT` | `5/5 OK` | wrapper/ambiente/settle do `talus-up` nao resolve o modo Kinect-only |
| Restauracao final via `talus-bringup.service` | ativo | OK | OK | estado operacional restaurado; este caminho usa `floor_test` e nao entra como metodo Kinect-only da matriz |

### Interpretacao

A matriz reforca que a instabilidade observada antes do VO/RTAB-Map nao nasce no RTAB-Map. O padrao dominante e: depth entrega frames, enquanto RGB/video nao entrega frames reais no caminho Kinect-only, mesmo quando `freenect_start_video` retorna sucesso.

A evidencia nativa com `freenect-camtest` e especialmente relevante: ha frames de depth e perda persistente no stream de video (`Stream 80`), indicando que a cadeia RGB/video ja apresenta problema abaixo do ROS. A camada ROS reproduz o sintoma como topico `/image_raw` visivel sem mensagens reais, enquanto `/depth/image_raw` publica normalmente.

Conclusao operacional: manter a investigacao em Kinect/USB/libfreenect/fork ROS antes de qualquer nova conclusao sobre VO, RTAB-Map ou SLAM. As proximas perguntas tecnicas sao: RGB-only vs depth-only vs RGB+depth, ordem de inicio dos streams, callbacks RGB/depth no fork e perdas USB/isochronous do stream de video.


## Isolamento RGB/depth e teste Bayer — 2026-05-04

Raizes de artefatos no `raspi`:

- `artifacts/testlogs/2026-05-03-kinect-validation/raspi-v18-rgb-depth-isolation/`
- `artifacts/testlogs/2026-05-04-kinect-validation/raspi-v19-bayer-rgbd/`

Objetivo: separar o problema entre stream isolado, RGB-D simultaneo, ordem de inicio dos streams e formato de video (`RGB` vs `BAYER`), ainda sem VO, RTAB-Map ou SLAM.

### Patch diagnostico usado

No fork `KinectV1-Ros2` do `raspi`, foi criada a branch diagnostica `diag/2026-05-03-kinect-callbacks`, baseada em `talus-jazzy-bringup` (`59e5da2`). O patch local nao commitado adicionou apenas instrumentacao e chaves de teste:

- contadores de callbacks RGB/depth;
- contadores de publicacao RGB/depth;
- log periodico `kinect diag`;
- `TALUS_KINECT_STREAM_MODE=rgb-only|depth-only|rgbd`;
- `TALUS_KINECT_STREAM_START_ORDER=depth-first|video-first`;
- `TALUS_KINECT_VIDEO_FORMAT=rgb|bayer`;
- `TALUS_KINECT_FREENECT_LOG_LEVEL` para expor perdas de stream no `libfreenect`.

### v18 — RGB/depth isolados e simultaneos

| Caso | Resultado nativo/libfreenect | Resultado ROS | Leitura |
|---|---|---|---|
| `rgb-only` | passou nas retries: 539 frames de video/20s, sem perdas `Stream 80/70`; primeira tentativa falhou em `freenect_open_device=-1` | `/image_raw` OK; `cb_rgb=479`, `pub_rgb=479` | RGB isolado funciona; reabertura ainda e sensivel a timing |
| `depth-only` | 599 frames depth/20s | `/depth/image_raw` OK; `cb_depth=484`, `pub_depth=484` | depth isolado funciona |
| `rgbd-depth-first` | 483 depth frames, 1 video frame; `Stream80_loss_lines=166` | depth OK; `cb_depth=423`; RGB sem callback (`cb_rgb=0`); `Stream80_loss_lines=201` | depth vence; video/RGB perde no stream USB/libfreenect |
| `rgbd-video-first` | 427 video frames, 0 depth frames; `Stream70_loss_lines=670` | RGB OK; `cb_rgb=426`; depth sem callback (`cb_depth=0`); `Stream70_loss_lines=611` | video vence; depth perde no stream USB/libfreenect |

### v19 — `FREENECT_VIDEO_BAYER`

| Caso | Resultado nativo/libfreenect | Resultado ROS | Leitura |
|---|---|---|---|
| `bayer-only` | 599 frames de video/20s, sem perdas `Stream 80/70` | `/image_raw` OK com `encoding=bayer_grbg8`; `cb_rgb=479`, `pub_rgb=479` | Bayer isolado funciona |
| `bayer-rgbd-depth-first` | 412 depth frames, 1 video frame; `Stream80_loss_lines=62` | depth OK; `cb_depth=360`; RGB sem callback (`cb_rgb=0`); `Stream80_loss_lines=44` | Bayer nao resolve simultaneidade; depth vence |
| `bayer-rgbd-video-first` | 489 video frames, 0 depth frames; `Stream70_loss_lines=612` | Bayer video OK; `cb_rgb=427`; depth sem callback (`cb_depth=0`); `Stream70_loss_lines=641` | Bayer nao resolve simultaneidade; video vence |

### Interpretacao consolidada

Os testes mostram que a falha nao e um problema simples de publicacao ROS: quando o callback chega, o topico publica. RGB, Bayer e depth funcionam isoladamente. A falha aparece quando os dois streams isochronous da camera do Kinect sao ativados simultaneamente: o primeiro stream iniciado continua entregando callbacks e o segundo acumula perdas (`Stream 80` para video/RGB/Bayer, `Stream 70` para depth) e nao entrega frames reais.

A classificacao mais provavel passa a ser: limitacao/falha de simultaneidade na camada Kinect v1 + USB/libfreenect/topologia/kernel, possivelmente agravada por bandwidth/agenda isochronous/reabertura do dispositivo. `FREENECT_VIDEO_BAYER` nao e um contorno suficiente.

### Implicacoes para VO/RTAB-Map

Manter bloqueio de VO/RTAB-Map RGB-D com este caminho de camera ate haver uma fonte simultanea confiavel de RGB+depth ou uma estrategia alternativa de odometria. Testes com RGB-only ou depth-only podem ser usados como diagnosticos de subsistema, mas nao devem ser registrados como validacao do pipeline RGB-D completo.


## Teste `FREENECT_DEPTH_11BIT` — 2026-05-04

Raiz de artefatos no `raspi`:

- `artifacts/testlogs/2026-05-04-kinect-validation/raspi-v20-depth-11bit-rgbd/`

Objetivo: verificar se trocar o modo de profundidade de `FREENECT_DEPTH_MM` para `FREENECT_DEPTH_11BIT` altera a falha de simultaneidade RGB-D.

| Caso | Resultado nativo/libfreenect | Resultado ROS | Leitura |
|---|---|---|---|
| `depth-11bit-only` | 545 frames depth/20s; `Stream70_loss_lines=1` | `/depth/image_raw` OK; `cb_depth=485`, `pub_depth=485` | depth 11bit isolado funciona |
| `rgbd-11bit-depth-first` | 481 depth frames, 2 video frames; `Stream80_loss_lines=78`, `Stream70_loss_lines=13` | depth OK; `cb_depth=363`, `pub_depth=363`; RGB sem callback (`cb_rgb=0`) | 11bit nao resolve; depth vence quando iniciado primeiro |
| `rgbd-11bit-video-first` | 488 video frames, 0 depth frames; `Stream70_loss_lines=596` | RGB OK; `cb_rgb=426`, `pub_rgb=426`; depth sem callback (`cb_depth=0`) | 11bit nao resolve; video vence quando iniciado primeiro |

Interpretacao: `FREENECT_DEPTH_11BIT` tambem nao contorna a falha. O padrao continua sendo determinado pela ordem de inicio: o primeiro stream entrega frames e o segundo acumula perdas no stream USB/libfreenect correspondente. Isto reforca que a diferenca `MM` vs `11BIT` nao e o gargalo principal de banda/estabilidade observado nesta topologia.


## Matriz de portas USB do Raspberry Pi — 2026-05-05

Raizes de artefatos no `raspi`:

- `artifacts/testlogs/2026-05-05-kinect-validation/raspi-v21-usb2-upper/`
- `artifacts/testlogs/2026-05-05-kinect-validation/raspi-v22-usb2-lower/`
- `artifacts/testlogs/2026-05-05-kinect-validation/raspi-v23-usb3-lower/`
- `artifacts/testlogs/2026-05-05-kinect-validation/raspi-v24-usb3-upper/`

Objetivo: verificar se alguma das quatro portas fisicas do Raspberry Pi 4 muda a falha de simultaneidade RGB-D. A hipotese testada foi que uma porta especifica poderia alterar a topologia efetiva, o agendamento isochronous ou a estabilidade de reabertura do Kinect.

| Porta/run | Isolados nativos | RGB-D nativo, depth-first | RGB-D nativo, video-first | RGB-D ROS | Restauracao final |
|---|---|---|---|---|---|
| v21 `usb2-upper` | RGB-only OK: 598 frames; depth-only abriu mas ficou com 0 frames nesta execucao | 2 video / 448 depth; perdas `Stream80=203`, `Stream70=131` | 301 video / 0 depth; perdas `Stream70=555` | depth-first: `cb_rgb=0`, `cb_depth=388`; video-first: `cb_rgb=485`, `cb_depth=0` | amostras finais nao consolidaram estado bom nesta bateria |
| v22 `usb2-lower` | RGB-only OK: 598 frames; depth-only OK: 598 frames | 2 video / 347 depth; perdas `Stream80=164`, `Stream70=59` | 324 video / 0 depth; perdas `Stream70=605` | depth-first: `cb_rgb=0`, `cb_depth=247`; video-first: `cb_rgb=426`, `cb_depth=0` | primeira tentativa sem RGB; segunda tentativa OK para RGB e depth |
| v23 `usb3-lower` | depth-only OK: 599 frames; RGB-only abriu mas ficou com 0 frames nesta execucao | 1 video / 468 depth; perdas `Stream80=173`, `Stream70=59` | 486 video / 0 depth; perdas `Stream70=692` | depth-first: `cb_rgb=0`, `cb_depth=345`; video-first: `cb_rgb=426`, `cb_depth=0` | restauracao falhou nas tentativas registradas |
| v24 `usb3-upper` | RGB-only OK: 598 frames; depth-only abriu mas ficou com 0 frames nesta execucao | 1 video / 471 depth; perdas `Stream80=156`, `Stream70=51` | 364 video / 0 depth; perdas `Stream70=487` | depth-first: `cb_rgb=0`, `cb_depth=412`; video-first: `cb_rgb=319`, `cb_depth=0` | OK para `/image_raw` e `/depth/image_raw` apos settle/restart |

### Interpretacao

A troca de porta fisica nao resolve a simultaneidade RGB-D. Todas as portas reproduzem o mesmo padrao estrutural: quando depth inicia primeiro, depth entrega frames e video/RGB acumula perda no `Stream 80`; quando video inicia primeiro, video/RGB entrega frames e depth acumula perda no `Stream 70`. As variacoes entre portas afetam estabilidade operacional e reabertura, mas nao mudam a causa principal observada.

O melhor estado operacional ao fim da matriz foi a porta `usb3-upper` (v24), porque o servico foi restaurado com `/image_raw` e `/depth/image_raw` respondendo. Isto nao significa RGB-D simultaneo validado: a restauracao final apenas confirma que o bring-up voltou a publicar amostras apos settle, enquanto a bateria RGB-D controlada continuou falhando.


## Cross-check em outro host com o mesmo Kinect/libfreenect — 2026-05-08

Raiz de artefatos no `aiquitude`:

- `artifacts/testlogs/2026-05-08-kinect-validation/aiquitude-v01-native-libfreenect-rgbd-crosscheck/`

Objetivo: separar defeito do sensor/fonte USB do Kinect de uma limitacao especifica do `raspi`. O teste usou o mesmo Kinect v1 e build local do `libfreenect` upstream no commit `09a1f09`, igual ao checkout observado no `raspi` em `/home/felip/repos/libfreenect`.

| Caso | Resultado nativo no `aiquitude` | Leitura |
|---|---|---|
| `rgbd-depth-first` | 601 video / 603 depth; `Stream80=0`, `Stream70=5` | RGB-D simultaneo funcional, com perdas baixas |
| `rgbd-depth-first` repetido | 601 video / 603 depth; `Stream70=3` | repetibilidade boa |
| `rgbd-video-first` | 615 video / 598 depth; `Stream70=0` | ordem de inicio nao mata o segundo stream |
| `rgbd-video-first` repetido | 618 video / 598 depth; `Stream70=0` | repetibilidade boa |

Os testes isolados no `aiquitude` ficaram anomalos nessa execucao, com 0 frames, mas o dado relevante para esta frente e que RGB-D simultaneo funcionou de forma repetida no mesmo Kinect. Portanto, a hipotese de Kinect fisicamente incapaz de RGB-D simultaneo ou de bug universal do `libfreenect` upstream fica enfraquecida. A falha passa a apontar mais fortemente para o conjunto `raspi` + controlador/topologia USB + kernel/firmware/configuracao.


## Diagnostico do host USB do `raspi` — 2026-05-08

Raiz de artefatos no `raspi`:

- `artifacts/testlogs/2026-05-08-kinect-validation/raspi-v25-usb-host-diagnostics/`

Objetivo: caracterizar o host onde a falha ocorre, sem ainda aplicar mudancas. Este passo segue a regra de investigar causa antes de propor correcoes: a evidencia acumulada ja isola o sintoma na camada abaixo do ROS, mas ainda falta identificar qual diferenca do `raspi` explica o comportamento.

Fatos coletados:

- host: Raspberry Pi 4 Model B Rev 1.4, Ubuntu 24.04.4 LTS, kernel `6.8.0-1053-raspi`;
- bootloader EEPROM reportado como atualizado para o canal instalado: `2026/01/09 16:12:13`; `vcgencmd get_throttled` retornou `0x0`, sem sinal atual de undervoltage/throttling;
- controlador USB principal: VIA/VL805/806 xHCI (`1106:3483`) em PCIe, driver `xhci_hcd`, link PCIe `5.0 GT/s x1`;
- topologia observada: Kinect em `Bus 001` HighSpeed 480M, atras do hub USB2 interno do Pi (`2109:3431`) e do hub interno do Kinect (`0409:005a`); camera `045e:02ae` em 480M, audio `045e:02ad` em 480M, motor `045e:02b0` em 12M;
- Arduino/CH340 `1a86:7523` tambem aparece no mesmo hub USB2 interno do Pi, em 12M;
- ha tambem um root hub `dwc2` (`usb3`) habilitado por overlay/cmdline, mas o Kinect em teste esta no xHCI/VL805, nao nesse controlador;
- `dmesg` nao ficou disponivel sem permissao privilegiada nesta coleta (`Operation not permitted`), entao ainda nao ha evidencia nova de mensagens de kernel para correlacionar perdas USB.

O codigo do `libfreenect` local confirma que os streams relevantes sao dois endpoints isochronous na camera: depth usa endpoint `0x82` e e logado como `Stream 70`; video usa endpoint `0x81` e e logado como `Stream 80`. A falha do `raspi` portanto nao e apenas conversao Bayer/RGB nem publicacao ROS: ela aparece exatamente nos dois streams isochronous que o host precisa agendar simultaneamente.

### Interpretacao consolidada apos v25

A explicacao mais consistente ate aqui e uma limitacao ou bug especifico do caminho USB do `raspi`: Pi 4/VL805/xHCI/kernel/configuracao/topologia, possivelmente com sensibilidade a agendamento isochronous e reabertura do dispositivo. A matriz de portas mostra que escolher outra porta fisica nao contorna; o cross-check no `aiquitude` mostra que o mesmo Kinect e o mesmo `libfreenect` conseguem RGB-D simultaneo fora do `raspi`.

Ainda nao ha base suficiente para mudar firmware, kernel, boot config ou aplicar quirk. O proximo dado de maior valor seria uma coleta privilegiada curta no `raspi` durante uma tentativa RGB-D, incluindo `dmesg -T`, descritores completos `lsusb -v -d 045e:02ae` e, se aceitavel, usbmon com filtro pequeno. Sem isso, qualquer alteracao em cmdline/driver seria tentativa por palpite.


## Coleta privilegiada com usbmon — 2026-05-08

Raizes de artefatos no `raspi`:

- `artifacts/testlogs/2026-05-08-kinect-validation/raspi-v26-privileged-usb-rgbd/`
- `artifacts/testlogs/2026-05-08-kinect-validation/raspi-v27-corrected-rgbd-usbmon/`
- `artifacts/testlogs/2026-05-08-kinect-validation/raspi-v28-settle120-rgbd-usbmon/`

Objetivo: coletar descritores, `dmesg` e `usbmon` com permissao privilegiada durante uma tentativa RGB-D nativa, para diferenciar erro de abertura/reabertura do Kinect de falha real dos endpoints isochronous.

### v26 e v27 — tentativas de coleta

A v26 coletou corretamente dados privilegiados de host, firmware, descritores e PCI, mas o probe RGB-D foi chamado com a sintaxe antiga. Portanto, ela nao reproduziu a falha RGB-D durante a janela usbmon. Ainda assim confirmou:

- `VL805_FW` atualizado em `000138c0`;
- `vcgencmd get_throttled = 0x0`;
- camera Kinect `045e:02ae` com dois endpoints isochronous IN:
  - `0x81` (`EP 1 IN`), `wMaxPacketSize 0x0bc0` (`2x 960 bytes`), usado pelo video/`Stream 80`;
  - `0x82` (`EP 2 IN`), `wMaxPacketSize 0x0bc0` (`2x 960 bytes`), usado pelo depth/`Stream 70`.

A v27 corrigiu a sintaxe do probe, mas usou settle curto apos parar o servico. Os dois casos falharam antes da transmissao RGB-D, ainda em `freenect_open_device=-1`, com mensagens como `send_cmd: Bad cmd 03 != 16` e `send_cmd: Bad len 0004 != 000c`. Isto confirma uma segunda caracteristica do problema: reabrir o Kinect pouco tempo apos o bring-up aumenta falhas de inicializacao. Esse erro nao deve ser confundido com a falha RGB-D simultanea; ele e um problema de settle/reabertura.

### v28 — settle de 120s e usbmon durante RGB-D

A v28 esperou 120s apos parar o servico e conseguiu executar os dois casos RGB-D nativos com `freenect_open_device=0`, `freenect_start_video=0` e `freenect_start_depth=0`.

| Caso | Resultado nativo | Logs `libfreenect` | `dmesg` durante o caso | Evidencia usbmon |
|---|---|---|---|---|
| `depth-first` | `FINAL video_frames=1 depth_frames=480` | `Stream 80` chegou a `Lost 2005 total packets in 0 frames`; `Stream 70` teve perdas menores e resyncs, mas formou frames | vazio | endpoint `1`/video teve `6662` pacotes ISO com status `-18`; endpoint `2`/depth teve `75` |
| `video-first` | `FINAL video_frames=365 depth_frames=0` | `Stream 70` chegou a `Lost 2760 total packets in 0 frames`; video formou frames | vazio | endpoint `2`/depth teve `4207` pacotes ISO com status `-18`; endpoint `1`/video teve `75` |

Interpretacao do usbmon: endpoint `1` corresponde ao endpoint USB `0x81` do video (`Stream 80`) e endpoint `2` corresponde ao `0x82` do depth (`Stream 70`). O status `-18` nos descritores de pacotes isochronous e `-EXDEV`; em transfers ISO ele indica pacote parcialmente completado/missed service. Assim, a v28 mostra que a perda nao e aleatoria entre os dois endpoints: ela se concentra no endpoint do segundo stream iniciado.

Nao houve mensagem nova em `dmesg` durante os casos e nao apareceu erro explicito de reserva de banda como `Not enough bandwidth`/`-ENOSPC`. O padrao observado e de falha em tempo de execucao no atendimento de pacotes ISO, nao de rejeicao limpa da configuracao pelo kernel.

### Diagnostico mais preciso apos v28

A melhor classificacao atual e: o `raspi`/VL805/xHCI aceita iniciar os dois endpoints isochronous do Kinect, mas perde service intervals do endpoint que entra como segundo stream. Isto explica por que `freenect_start_*` retorna sucesso, por que o ROS nao recebe callback do segundo stream e por que o mesmo Kinect funciona em outro host.

Ainda nao e correto afirmar qual camada exata contem o bug final — firmware VL805, driver xHCI, agendamento periodico do kernel, topologia do Pi 4 ou alguma interacao especifica do Kinect v1 com esse host. Mas a evidencia agora aponta para `missed service`/runtime isochronous no controlador/caminho USB do `raspi`, e enfraquece as hipoteses de QoS ROS, RTAB-Map, conversao RGB/Bayer, defeito fisico do Kinect ou saturacao de CPU/userspace.


## Replug USB, base serial e cross-check de TF/RTAB-Map — 2026-05-09

Raizes de artefatos sincronizadas no repo:

- `artifacts/testlogs/2026-05-09-pre-floor-validation/raspi-v50-suspended-base-tf-rtabmap/`
- `artifacts/testlogs/2026-05-09-pre-floor-validation/raspi-v51-no-motor-camera-tf-rtabmap-default/`
- `artifacts/testlogs/2026-05-09-kinect-validation/raspi-v48-ground-fixed-arduino-usb-kinect-serial/`
- `artifacts/testlogs/2026-05-09-kinect-validation/raspi-v49-ground-fixed-kinect-restart-native-ros/`
- `artifacts/testlogs/2026-05-09-kinect-validation/raspi-v52-after-usb-replug-baseline/`
- `artifacts/testlogs/2026-05-09-kinect-validation/raspi-v56-managed-kinect-base-rtabmap/`
- `artifacts/testlogs/2026-05-09-kinect-validation/raspi-v57-video-first-crosscheck/`
- `artifacts/testlogs/2026-05-09-kinect-validation/raspi-v58-arduino-base-after-replug/`

Tambem existem artefatos `raspi-v42-*` a `raspi-v47-*`, preservando monitoramentos e smokes intermediarios da mesma frente, e artefatos parciais `raspi-v53-*`, `raspi-v54-*` e `raspi-v55-*`; estes ultimos registram tentativas de harness descartadas e nao sao usados como evidencia principal. A v55 foi util para mostrar que `ros2 topic echo --once /image_raw` nao e uma boa condicao de espera para mensagens `sensor_msgs/Image` grandes: o driver podia publicar, mas o comando usado como wait expirava sem saida. As rodadas v56/v57 substituem esse gate por `ros2 topic hz` e leitura de `header`.

### v48/v49 — serial corrigida e contraste ROS vs nativo

A v48 foi executada apos a correcao fisica do GND do Arduino/Raspberry Pi. O GND havia sido ligado no pino fisico `10` (`GPIO15/RXD0`) em vez de um pino GND real; apos mover para GND correto, a serial `/dev/ttyUSB0` e a bridge voltaram a responder. O Kinect que ja estava vivo publicou `/image_raw` a ~30.0 Hz e `/depth/image_raw` a ~28.6 Hz no baseline; com a bridge ativa, `/imu/raw` ficou em ~50 Hz.

A v49 contrastou o estado operacional ROS com o comportamento nativo controlado. O ROS, com o node ja vivo/recuperado, publicou RGB em ~30.0 Hz e depth em ~29.4 Hz antes do restart. O teste nativo continuou reproduzindo a falha estrutural: `depth-first` terminou com `FINAL video_frames=1 depth_frames=419`; `video-first` terminou com `FINAL video_frames=489 depth_frames=0`. Isso e importante para interpretar os periodos em que o ROS aparenta ficar bom: eles nao anulam a falha nativa de simultaneidade no `raspi`; apenas mostram que alguns estados long-lived/restart podem manter os dois topicos publicando por uma janela operacional.

### v50/v51 — causa do erro de RTAB-Map nao era IMU

A v50 subiu `base.launch.py` com o Kinect iniciado diretamente por `ros2 run kinect_ros2 kinect_ros2_node --disable-pointcloud`. A base serial conectou em `/dev/ttyUSB0` e a IMU ficou estavel em aproximadamente 50 Hz, mas a arvore TF da camera nao estava completa: `base_link -> imu_link` funcionou e `base_link -> camera_link` falhou. O RTAB-Map subiu, mas `/rtabmap/odom` nao produziu taxa util e o log acumulou milhares de `Dropping imu data!`.

A v51 repetiu o smoke sem motor publicando manualmente os TFs de camera de `frames.yaml`. Com `base_link -> kinect_rgb_optical_frame` e `base_link -> kinect_depth_optical_frame` presentes, o spam `Dropping imu data!` sumiu. Isso isola o problema da v50: o erro primario daquele teste era o bring-up incompleto de TF da camera, nao uma falha nova da IMU. O caminho operacional correto para VO/SLAM e subir a camera por `talus_bringup kinect.launch.py` ou por um perfil que inclua esse launch; iniciar o binario `kinect_ros2_node` solto e depois chamar `slam_rtabmap.launch.py` deixa faltando a cadeia `base_link -> camera_link -> kinect_*_optical_frame`.

Mesmo com os TFs corrigidos, a v51 nao validou VO: `/rtabmap/odom` apareceu apenas como mensagem invalida/covariancia alta e o log registrou `Registration failed: Not enough inliers`. Esse resultado nao libera teste de chao; ele apenas remove a hipotese de TF/IMU como causa principal do spam anterior.

### v52/v56/v57 — replug USB reproduz o padrao "primeiro stream vence"

Depois de desconectar e reconectar USB do Kinect e do Arduino, a v52 mostrou que o processo antigo do Kinect continuava vivo, com topicos ainda visiveis no grafo ROS, mas sem amostras reais em `/image_raw`, `/depth/image_raw` ou `/camera_info`. A correcao operacional imediata foi parar os processos ROS antigos e reiniciar o bring-up da camera.

Na v56, com `kinect.launch.py` fresco e ordem padrao `depth-first`, a arvore TF de camera ficou correta e `/depth/image_raw` publicou entre 28 e 29 Hz. O log do driver mostrou, porem, `cb_rgb=0` e `pub_rgb=0` durante toda a janela, enquanto `cb_depth` e `pub_depth` subiam continuamente. Ou seja: depth funcionou, RGB nao recebeu callbacks.

Na v57, com `TALUS_KINECT_STREAM_START_ORDER=video-first`, o comportamento inverteu: `/image_raw` publicou aproximadamente 30 Hz e o log mostrou `cb_rgb`/`pub_rgb` subindo, enquanto `cb_depth=0` e `/depth/image_raw` nao entregou amostras. Isso confirma novamente, apos o replug, o mesmo padrao ja medido com usbmon: no `raspi`, o primeiro endpoint isochronous iniciado pelo Kinect entrega frames e o segundo fica sem callbacks uteis.

Conclusao da rodada: a causa raiz que bloqueia RTAB-Map RGB-D no `raspi` continua sendo a falha de simultaneidade RGB+depth na camada Kinect/USB/libfreenect/VL805/xHCI do Raspberry Pi, nao QoS ROS, RTAB-Map, TF, IMU, Arduino ou conversao Bayer/RGB. A correcao simples aplicavel no teste e reiniciar os processos apos replug e usar o launch oficial para garantir TF; a falha RGB-D simultanea em si nao teve correcao simples confirmada nesta bateria.

### v58 — Arduino/base apos replug

A v58 validou o Arduino/CH340 apos o replug, sem mover motores. O symlink persistente continuou correto (`usb-1a86_USB_Serial-if00-port0 -> ../../ttyUSB0`) e a bridge conectou com:

```text
Serial connected: /dev/ttyUSB0 @ 115200 | talus-base-serial-0.1.0 IMU_OK=1
TalusBaseBridge ready
Arduino: PONG talus-base-serial-0.1.0 IMU_OK=1
```

Evidencia observada:

- `/imu/raw`: aproximadamente 50 Hz;
- `/imu/data`: mensagens publicadas, mas a medicao chegou a ~100 Hz porque havia um `imu_filter_madgwick_node` legado ainda vivo de uma tentativa anterior; esse processo foi encerrado ao fim da sessao;
- `base_link -> imu_link`: TF estatico correto;
- `/wheel/left_ticks` e `/wheel/right_ticks`: ambos `0` sem comando de motor, como esperado.

Nao houve teste novo de motor nesta bateria. O teste suspenso anterior v50 tambem terminou com ticks `0/0`, entao movimento de motores/encoders ainda precisa de uma rodada dedicada, com autorizacao explicita para acionar motor e com cleanup que mate os processos filhos do launch, nao apenas o processo pai.


## Cold power-cycle, RGB-D vivo e RTAB-Map headless — 2026-05-09

Raizes de artefatos sincronizadas no repo:

- `artifacts/testlogs/2026-05-09-kinect-validation/raspi-v59-pre-powercycle-safety-stop/`
- `artifacts/testlogs/2026-05-09-kinect-validation/raspi-v60-post-powercycle-enumeration/`
- `artifacts/testlogs/2026-05-09-kinect-validation/raspi-v61-native-rgbd-after-cold-powercycle/`
- `artifacts/testlogs/2026-05-09-kinect-validation/raspi-v62-ros-kinect-depth-first-after-powercycle/`
- `artifacts/testlogs/2026-05-09-kinect-validation/raspi-v63-ros-kinect-video-first-after-powercycle/`
- `artifacts/testlogs/2026-05-09-kinect-validation/raspi-v64-base-imu-tf-with-live-rgbd/`
- `artifacts/testlogs/2026-05-09-kinect-validation/raspi-v65-rtabmap-headless-live-rgbd-no-motor/`

Objetivo: limpar o estado anterior do `raspi`, fazer um cold power-cycle fisico do Kinect, medir novamente o comportamento nativo/ROS e, caso o RGB-D ficasse vivo, testar RTAB-Map headless sem comando de motor.

### v59/v60 — limpeza e enumeracao apos power-cycle

A v59 foi uma parada segura antes do power-cycle: processos de Kinect, base, RTAB-Map, TF e filtro de IMU foram encerrados e a verificacao final registrou `matches=0`. Depois disso, o Kinect foi desconectado/reconectado fisicamente em USB e energia.

A v60 confirmou enumeracao limpa apos o cold power-cycle:

- Kinect motor `045e:02b0`, audio `045e:02ad` e camera `045e:02ae` presentes;
- Arduino/CH340 `1a86:7523` presente;
- symlink serial persistente `usb-1a86_USB_Serial-if00-port0 -> ../../ttyUSB0`;
- grafo ROS limpo, com apenas `/parameter_events` e `/rosout` antes dos novos testes;
- processos Kinect/base/RTAB-Map remanescentes: `matches=0`.

### v61/v62 — nativo e ROS ainda mostram o padrao estrutural

Mesmo apos cold power-cycle, o teste nativo RGB-D continuou reproduzindo o padrao "primeiro stream vence":

| Caso v61 | Resultado |
|---|---|
| `depth-first` | `FINAL video_frames=0 depth_frames=602`; video sem frames |
| `video-first` | `FINAL video_frames=427 depth_frames=0`; depth sem frames, com perdas `Stream 70` em milhares de pacotes |

A v62 repetiu o bring-up ROS com `TALUS_KINECT_STREAM_START_ORDER=depth-first`: `/depth/image_raw` publicou, `/image_raw` nao entregou amostras reais, e os TFs da camera foram publicados corretamente pelo `talus_bringup kinect.launch.py`. Ao fim da v62, os processos foram limpos (`matches=0`).

Conclusao desta etapa: o cold power-cycle nao corrige a falha nativa de simultaneidade. Ele apenas garante um ponto de partida limpo para observar o comportamento.

### v63 — estado ROS excepcionalmente bom com RGB-D simultaneo

A v63 iniciou a camera via `talus_bringup kinect.launch.py` com `TALUS_KINECT_STREAM_START_ORDER=video-first` e, nesta janela operacional, o ROS entregou RGB e depth simultaneamente:

| Topico | Evidencia |
|---|---|
| `/image_raw` | aproximadamente 30.02 a 30.30 Hz |
| `/depth/image_raw` | aproximadamente 29.96 a 30.02 Hz |
| header RGB | `frame_id: kinect_rgb_optical_frame` |
| header depth | `frame_id: kinect_depth_optical_frame` |
| TF camera | `base_link -> kinect_rgb_optical_frame` e `base_link -> kinect_depth_optical_frame` presentes |

Este resultado deve ser interpretado com cuidado. Ele mostra que existe um estado operacional do driver ROS long-lived em que os dois topicos publicam juntos por varios segundos/minutos, mas nao contradiz a falha nativa controlada da v61 nem a evidencia usbmon anterior. Por isso, a decisao operacional foi preservar o processo da camera vivo e encadear v64/v65 sem reiniciar o Kinect.

### v64 — base/IMU com RGB-D vivo

Com a camera v63 ainda viva, a v64 subiu a base sem mover motores. A bridge conectou normalmente:

```text
Serial connected: /dev/ttyUSB0 @ 115200 | talus-base-serial-0.1.0 IMU_OK=1
TalusBaseBridge ready
Arduino: PONG talus-base-serial-0.1.0 IMU_OK=1
```

Evidencia observada:

- `/imu/raw`: aproximadamente 49.9 a 50.0 Hz;
- `/imu/data`: aproximadamente 49.9 a 50.0 Hz;
- `base_link -> imu_link`: TF estatico correto;
- `/wheel/left_ticks` e `/wheel/right_ticks`: ambos `0` sem comando de motor;
- RGB e depth continuaram vivos depois da base: `/image_raw` ~30.0 Hz e `/depth/image_raw` ~30.0 Hz.

Isso valida que, quando a camera esta no estado ROS bom, a base serial e a IMU nao derrubam imediatamente o RGB-D. Ainda assim, nao houve acionamento de motor nesta etapa.

### v65 — RTAB-Map headless sem motor

A v65 subiu `slam_rtabmap.launch.py` headless, sem RViz e sem comando de motor, reutilizando RGB-D e IMU vivos. As entradas principais estavam presentes durante a janela:

| Entrada | Evidencia v65 |
|---|---|
| `/image_raw` | `average rate: 26.589` durante RTAB-Map |
| `/depth/image_raw` | `average rate: 28.540` e `29.271` durante RTAB-Map |
| `/imu/data` | `average rate: 49.985` e `50.016` |
| `/rtabmap/odom` | mensagem unica/invalida, pose zero e covariancia `9999` |
| TF `odom -> base_link` | nao publicado; `tf2_echo` reportou frame `odom` inexistente |

O log do `rgbd_odometry` mostra que o VO recebeu dados suficientes para tentar registro, mas falhou repetidamente por falta de inliers:

```text
Registration failed: "Not enough inliers 0/20 ..."
Failed to find a transformation with the provided guess ... trying again without a guess.
Trial with no guess still fail.
Odom: quality=0 ...
```

Como consequencia, o `rtabmap` tambem reportou:

```text
RGB-D SLAM mode is enabled, memory is incremental but no odometry is provided. Image 0 is ignored!
```

Leitura: a v65 e diferente das falhas anteriores em que RGB ou depth simplesmente nao publicavam. Aqui, RGB, depth e IMU estavam vivos durante o teste, mas o `rgbd_odometry` nao conseguiu estimar transformacao visual valida. O motivo imediato registrado e visual/algoritmico (`Not enough inliers`, `quality=0`), provavelmente influenciado por cena estatica/pouco texturizada, ausencia de movimento translacional util, qualidade/alinhamento RGB-depth do Kinect ou parametros de VO. A v65 nao valida odometria nem SLAM e nao libera teste no chao.

Ao fim desta rodada, foi enviado `/cmd_vel` zero e os processos de Kinect/base/RTAB-Map/IMU/TF foram encerrados; verificacao posterior nao listou processos correspondentes. A proxima validacao de motor/encoder deve ser uma bateria suspensa dedicada, com autorizacao explicita para acionar motor, medindo ticks antes/depois e mantendo parada segura.



## Fechamento da frente `kinect-validation` — 2026-05-10

Esta frente fica encerrada como investigacao principal do Kinect. A conclusao operacional foi revista apos a correcao fisica do jumper de GND entre Arduino/Raspberry Pi: o fio estava no pino fisico `10` do Raspberry Pi (`GPIO15/RXD0`), que nao e GND, e foi movido para um pino GND real. Depois dessa correcao, o pipeline ROS voltou a entregar RGB-D simultaneo em janelas estaveis, permitindo prosseguir para TF, IMU, `cmd_vel` e VO no chao.

Com isso, as hipoteses anteriores de problema primario em USB/libfreenect/VL805/xHCI ficam rebaixadas. Elas explicavam sintomas reais observados nos logs — perdas isochronous, padrao "primeiro stream vence" e falhas nativas —, mas nao devem mais ser tratadas como causa raiz operacional dominante sem nova evidencia. A melhor leitura consolidada e:

- havia uma falha eletrica/wiring clara e corrigida: GND comum ligado no pino errado do Raspberry Pi;
- essa falha tornava a base/serial e o ambiente eletrico do `raspi` instaveis o suficiente para confundir a investigacao do Kinect;
- apos corrigir o GND, o caminho ROS `kinect.launch.py` conseguiu manter `/image_raw` e `/depth/image_raw` simultaneos perto de 30 Hz;
- a cadeia estatica de TF da camera e IMU ficou valida;
- o bloqueio seguinte deixou de ser RGB-D simultaneo e passou a ser ajuste/robustez da VO e sincronizacao do RTAB-Map.

A evidencia historica desta pagina deve ser lida como registro de diagnostico incremental, nao como conclusao final imutavel. Em particular, as secoes que apontam para USB/libfreenect/VL805 representam a melhor hipotese antes da descoberta do GND incorreto. A partir de 2026-05-10, a frente Kinect e considerada suficientemente destravada para os testes de validacao no chao documentados em `2026-05-10-vo-floor-validation.md`.
