# Relatorio de Testes — Kinect + RTAB-Map Headless

Data: 2026-04-08  
Operador: Codex via notebook `aiquitude` -> `ssh raspi`  
Branch testada no `raspi`: `feat/talus-base-serial-bringup`  
Commit testado no `raspi`: `c3346c6`  
Branch deste relatorio: `report/2026-04-08-kinect-rtabmap-smoke`

## Resumo

Esta rodada validou o pipeline headless do Talus-Droid com:

- `talus_base_bridge`
- `imu_filter_madgwick`
- `kinect_ros2_node`
- transportes `compressed`, `compressedDepth` e `zstd`
- RTAB-Map sem GUI

O objetivo foi validar integracao e sinais minimos de funcionamento em bancada suspensa, sem alterar codigo e sem usar RViz ou `rtabmap_viz`.

Resultado geral:

- base + IMU + Kinect + transportes comprimidos: aprovados
- descoberta ROS pela rede: aprovada, com reinicio do `ros2 daemon` no notebook
- RTAB-Map headless: sobe e processa, mas a odometria visual ficou instavel na bancada suspensa
- pronto para um primeiro teste manual de chao com RTAB-Map
- ainda nao pronto para tratar RTAB-Map desta configuracao como validacao final de SLAM ou base para navegacao

## Ambiente

### `raspi`

- workspace: `/home/felip/talus-droid`
- ROS 2 Jazzy
- `ROS_DOMAIN_ID=42`
- `RMW_IMPLEMENTATION=rmw_cyclonedds_cpp`
- Kinect v1 conectado
- Arduino Nano em `/dev/ttyUSB0`

### notebook operador

- host: `aiquitude`
- ROS 2 Jazzy
- usado para observacao remota dos topicos ROS

## Restricoes desta rodada

- nenhuma alteracao de codigo na branch tecnica testada
- nenhuma GUI
- sem RViz
- sem `rtabmap_viz`
- foco em pipeline e integracao, nao em qualidade final de mapa

## Preparacao e comandos executados

### 1. Atualizacao e build no `raspi`

```bash
cd ~/talus-droid
git fetch origin feat/talus-base-serial-bringup
git pull --ff-only origin feat/talus-base-serial-bringup
source /opt/ros/jazzy/setup.bash
export ROS_DOMAIN_ID=42
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
colcon build --symlink-install --packages-select talus_base talus_bringup
```

Resultado esperado:

- branch do `raspi` atualizada para o commit testado
- overlay recompilado sem erro

Resultado observado:

- update e build concluidos com sucesso

### 2. Estado inicial do service

```bash
cd ~/talus-droid
systemctl status --no-pager talus-bringup.service | sed -n '1,12p'
```

Resultado esperado:

- service em estado conhecido antes da rodada

Resultado observado:

- `talus-bringup.service` estava `inactive (dead)` apos encerramento manual anterior
- o service permaneceu habilitado para boot, mas nao foi usado para esta rodada

### 3. Sessao persistente de teste no `raspi`

Foi criada uma sessao `tmux` dedicada:

```bash
tmux new-session -d -s codex-autotest
```

O profile de bancada foi executado nela:

```bash
cd ~/talus-droid
source /opt/ros/jazzy/setup.bash
source install/setup.bash
export ROS_DOMAIN_ID=42
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
./scripts/talus-up floor_test
```

Resultado esperado:

- base serial, IMU filtrada e Kinect ativos no mesmo dominio ROS

Resultado observado:

- `talus_base_bridge`, `imu_filter_madgwick_node`, `kinect_ros2_node` e `static_transform_publisher` subiram
- a bridge conectou na serial
- o filtro de IMU recebeu a primeira mensagem
- o Kinect subiu com RGB, depth e point cloud

Trechos relevantes de log:

```text
Talus profile: floor_test
Teleop enabled: false
Kinect enabled: true
ROS_DOMAIN_ID: 42
RMW_IMPLEMENTATION: rmw_cyclonedds_cpp
Serial connected: /dev/ttyUSB0 @ 115200 | talus-base-serial-0.1.0 IMU_OK=1
Arduino: PONG talus-base-serial-0.1.0 IMU_OK=1
TalusBaseBridge ready
First IMU message received.
```

### 4. Descoberta ROS pela rede

No notebook:

```bash
source /opt/ros/jazzy/setup.bash
export ROS_DOMAIN_ID=42
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
ros2 daemon stop || true
sleep 1
ros2 daemon start
sleep 2
ros2 topic list | sort
```

Resultado esperado:

- notebook enxerga os topicos publicados pelo `raspi`

Resultado observado:

- apos reiniciar o `ros2 daemon`, o notebook passou a ver os topicos remotos normalmente

Observacao:

- nesta rodada, o reinicio do daemon local foi necessario para a descoberta remota ficar consistente

## Topicos e nos observados

### Lista principal de nos

```text
/imu_filter
/imu_static_tf
/kinect_ros2_node
/kinect_ros2_node
/kinect_static_tf
/rtabmap/rgbd_odometry
/rtabmap/rgbd_sync
/rtabmap/rtabmap
/talus_base_bridge
```

Observacao:

- houve warning de nome duplicado para `kinect_ros2_node`

### Topicos principais observados

```text
/camera_info
/depth/camera_info
/image_raw
/depth/image_raw
/image_raw/compressed
/depth/image_raw/compressedDepth
/image_raw/zstd
/depth/image_raw/zstd
/points
/imu/raw
/imu/data_raw
/imu/data
/rtabmap/odom
/rtabmap/info
/tf
/tf_static
```

## Medicoes de frequencia

| Topico | Esperado nesta rodada | Observado |
| --- | --- | --- |
| `/image_raw` | RGB estavel | ~10.17 Hz |
| `/depth/image_raw` | depth estavel | ~15.10 Hz |
| `/image_raw/compressed` | transporte ativo | ~11.26 Hz |
| `/depth/image_raw/compressedDepth` | transporte ativo | ~15.39 Hz |
| `/image_raw/zstd` | transporte ativo | ~9.75 a 10.02 Hz |
| `/depth/image_raw/zstd` | transporte ativo | ~14.84 a 14.98 Hz |
| `/imu/raw` | IMU crua estavel | ~50.0 Hz |
| `/imu/data` | IMU filtrada estavel | ~50.0 Hz |
| `/points` | point cloud ativa | ~8.6 a 8.8 Hz |
| `/rtabmap/odom` | odometria visual minima | ~1.5 a 1.7 Hz |

## Medicoes de banda

| Topico | Observado |
| --- | --- |
| `/image_raw` | ~25 a 27 MB/s |
| `/depth/image_raw` | ~15.6 a 16.2 MB/s |
| `/image_raw/compressed` | ~1.60 a 1.66 MB/s |
| `/depth/image_raw/compressedDepth` | ~2.45 a 2.49 MB/s |
| `/image_raw/zstd` | ~2.71 a 4.54 MB/s |
| `/depth/image_raw/zstd` | ~2.21 a 2.24 MB/s |
| `/points` | ~64.5 a 67.6 MB/s |

Leitura pratica:

- os transportes comprimidos reduziram bastante a banda de RGB e depth
- a point cloud continua pesada para uso remoto constante

## Validacao da IMU

Comandos:

```bash
ros2 topic hz /imu/raw
ros2 topic hz /imu/data
ros2 topic echo --once /imu/data
ros2 run tf2_ros tf2_echo base_link imu_link
```

Resultado esperado:

- IMU crua e filtrada publicando
- `imu_filter_madgwick` entregando orientacao
- `base_link -> imu_link` existente

Resultado observado:

- `/imu/raw` e `/imu/data` em ~50 Hz
- `frame_id` em `/imu/data`: `imu_link`
- quaternion presente
- `linear_acceleration.z` perto de `9.95`
- `base_link -> imu_link` existente

Interpretacao:

- a IMU esta coerente para testes iniciais de integracao
- ainda faltam os offsets reais de montagem, hoje publicados como transformacoes identicas

## Validacao do Kinect

Comandos:

```bash
ros2 topic hz /image_raw
ros2 topic hz /depth/image_raw
ros2 topic bw /image_raw
ros2 topic bw /depth/image_raw
ros2 topic echo --once /camera_info
ros2 topic echo --once /depth/camera_info
```

Resultado esperado:

- RGB, depth e `camera_info` presentes e estaveis

Resultado observado:

- RGB e depth publicando com frequencias estaveis para esta rodada
- `camera_info` e `depth/camera_info` presentes
- `camera_info.frame_id = kinect_rgb`
- `depth/camera_info.frame_id = kinect_depth`
- resolucao observada: `640x480`

## Validacao dos transportes comprimidos

Comandos:

```bash
ros2 topic hz /image_raw/compressed
ros2 topic hz /depth/image_raw/compressedDepth
ros2 topic hz /image_raw/zstd
ros2 topic hz /depth/image_raw/zstd
ros2 topic bw /image_raw/compressed
ros2 topic bw /depth/image_raw/compressedDepth
ros2 topic bw /image_raw/zstd
ros2 topic bw /depth/image_raw/zstd
```

Resultado esperado:

- transportes presentes e publicando

Resultado observado:

- `compressed`, `compressedDepth` e `zstd` ativos
- frequencia e banda coerentes
- nenhum colapso estrutural do pipeline ao observar esses topicos

## Validacao de TF

Comandos:

```bash
ros2 run tf2_ros tf2_echo base_link imu_link
ros2 run tf2_ros tf2_echo base_link camera_link
```

Resultado esperado:

- `base_link -> imu_link` e `base_link -> camera_link` existentes

Resultado observado:

- ambas as transformacoes existem
- ambas apareceram como identidade

Interpretacao:

- a arvore de TF esta presente
- os offsets reais de camera e IMU ainda nao foram modelados
- isso nao bloqueou a rodada de integracao, mas precisa ser corrigido para validacao espacial mais seria

## Smoke test do RTAB-Map sem GUI

Comando:

```bash
cd ~/talus-droid
source /opt/ros/jazzy/setup.bash
source install/setup.bash
export ROS_DOMAIN_ID=42
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export TALUS_RTABMAP_VIZ=false
export TALUS_RVIZ=false
./scripts/talus-up slam
```

Resultado esperado:

- `rgbd_sync`, `rgbd_odometry` e `rtabmap` sobem
- o pipeline nao cai imediatamente
- `/rtabmap/odom` e `/rtabmap/info` aparecem

Resultado observado:

- nos do RTAB-Map subiram e permaneceram ativos
- `/rtabmap/info` e `/rtabmap/odom` apareceram
- `/rtabmap/odom` publicou em ~1.5 a 1.7 Hz
- o `rtabmap` permaneceu processando e publicando informacoes internas

Principais warnings e erros observados:

```text
The time difference between rgb and depth frames is high
Registration failed: Not enough inliers
Failed to find a transformation with the provided guess
RGB-D SLAM mode is enabled, memory is incremental but no odometry is provided. Image 0 is ignored!
```

Interpretacao:

- o stack sobe e processa
- a sincronizacao RGB/depth esta ruidosa
- a odometria visual ficou instavel na bancada suspensa
- houve frames com qualidade positiva, mas muitos quadros foram rejeitados por falta de inliers

## Recursos do sistema

Snapshot durante Kinect + RTAB-Map:

```text
Memoria: 7.6 GiB total, ~6.5 GiB disponivel
Load average: 7.86, 3.54, 1.77
```

Processos mais pesados observados:

| Processo | CPU aproximada |
| --- | --- |
| `rgbd_odometry` | ~81.7% |
| `kinect_ros2_node` | ~68.2% |
| `rgbd_sync` | ~59.7% |
| `talus_base_bridge` | ~22.9% |
| `imu_filter_madgwick_node` | ~3.4% |

Leitura pratica:

- o `raspi` consegue rodar o stack headless
- o custo computacional ja e alto com Kinect + RTAB-Map

## Achados principais

1. O pipeline headless completo da rodada subiu e permaneceu ativo.
2. A descoberta ROS remota funcionou no notebook apos reiniciar o `ros2 daemon`.
3. Os transportes comprimidos do Kinect estao operando corretamente.
4. A IMU filtrada esta saindo em `/imu/data` com sinais coerentes em repouso.
5. A arvore de TF existe, mas `imu_link` e `camera_link` ainda estao com offsets identicos.
6. O RTAB-Map sobe, mas a odometria visual ficou instavel nesta bancada suspensa.
7. Houve warning de nome duplicado para `kinect_ros2_node`.
8. A point cloud em `/points` continua muito pesada para consumo remoto constante.

## Conclusao

Status desta rodada:

- aprovado para primeiro teste manual de chao com RTAB-Map
- nao aprovado ainda como validacao final de SLAM
- nao aprovado ainda como base para navegacao autonoma

Justificativa:

- a integracao entre base, IMU, Kinect e RTAB-Map foi validada
- o stack headless permaneceu de pe
- o comportamento de odometria visual em bancada suspensa foi insuficiente para concluir robustez
- ainda faltam pelo menos:
  - medir offsets reais de `base_link -> imu_link`
  - medir offsets reais de `base_link -> camera_link`
  - repetir a rodada no chao com movimento real da camera
  - revisar a sincronizacao RGB/depth antes de conclusoes mais fortes

## Proximos passos recomendados

1. Rodar um teste de chao curto com RTAB-Map ainda em modo manual por joystick.
2. Medir e publicar os offsets reais de camera e IMU no `talus_bringup`.
3. Revisar os parametros de sincronizacao do RTAB-Map e do Kinect antes de tentar navegacao.
4. Decidir se `/points` deve continuar ativo por padrao no profile de teste ou ficar opcional.

## Observacao operacional

Este relatorio foi o unico artefato versionado desta rodada. Nao houve mudancas de codigo na branch tecnica testada.
