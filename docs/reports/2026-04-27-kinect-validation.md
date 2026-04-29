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

## Checklist de aceite

- [ ] Bateria isolada reproduzível no `raspi`.
- [ ] Logs por rodada suficientes para diagnosticar USB/processo/tópico.
- [ ] Classificação explícita de falhas registrada por rodada.
- [ ] Comparação entre settle padrão, 10s, 30s e 60s.
- [ ] Decisão documentada sobre reset USB.
- [x] Preflight Kinect executado antes dos testes maiores.
- [x] Conclusão separa Kinect/coleta/odometria/SLAM.
