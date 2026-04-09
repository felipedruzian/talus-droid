# Relatorio de Implementacao e Testes — Odom + Kinect + RTAB-Map Round 2

Data: 2026-04-08  
Operador: Codex via notebook `aiquitude` -> `ssh raspi`  
Branch principal testada: `feat/talus-base-serial-bringup`  
Commit final da branch principal: `f6e056e`

## Resumo

Esta rodada executou o plano de melhoria do pipeline de IMU, Kinect, odometria visual e RTAB-Map, com foco em:

- separar odometria visual de SLAM
- reduzir o custo do Kinect
- estabilizar a entrada do RTAB-Map
- documentar tudo para retomada posterior

O resultado final nao foi o plano inicial literalmente igual ao desenho original. O motivo foi descoberto no hardware:

- o modo `modular` do Kinect falhou no `raspi` com `LIBUSB_ERROR_BUSY`, porque RGB e depth tentaram abrir o mesmo dispositivo em paralelo

Por isso, a implementacao final mudou de estrategia:

- o bringup voltou a usar `kinect_ros2_node` como driver real
- a point cloud foi desligada por default
- os `frame_id` de RGB/depth foram alinhados aos frames opticos do bringup
- foi adicionado um helper versionado para aplicar a correcao no fork local `src/KinectV1-Ros2` do `raspi`

## Alteracoes implementadas

### Bringup e runtime

Foram implementadas estas mudancas no repositório principal:

- novo perfil `odom_test` em `talus_bringup`
- `kinect.launch.py` refeito para suportar:
  - `driver_mode=unified|modular`
  - `enable_point_cloud=true|false`
- `floor_test.launch.py` e `odom_test.launch.py` passaram a consumir:
  - `kinect_driver_mode`
  - `kinect_enable_point_cloud`
- `slam_rtabmap.launch.py` passou a expor:
  - `use_rgbd_sync`
  - `approx_sync`
  - `approx_sync_max_interval`

### Frames estaticos

Foi criado:

- `src/talus_bringup/config/frames.yaml`

Ele centraliza:

- `base_link -> imu_link`
- `base_link -> camera_link`
- `camera_link -> kinect_rgb_optical_frame`
- `camera_link -> kinect_depth_optical_frame`

Observacao:

- os offsets `base_link -> imu_link` e `base_link -> camera_link` continuam placeholders em `0,0,0`
- os frames opticos da camera agora existem explicitamente e ficam alinhados ao bringup

### Kinect

Foi criado:

- `scripts/apply-kinect-patches`

Esse helper modifica o fork local `src/KinectV1-Ros2` no `raspi` para:

- aceitar `--disable-pointcloud` no `kinect_ros2_node`
- mudar os `frame_id` publicados para:
  - `kinect_rgb_optical_frame`
  - `kinect_depth_optical_frame`
- remover a dependencia de TF interno legado do Kinect para o caso de bringup do Talus

Resultado pratico:

- o driver real do Kinect permanece unificado
- `/points` deixa de aparecer por default
- RGB/depth continuam saindo com `image_transport`

### Script operacional

O `scripts/talus-up` passou a aceitar:

- `odom_test`
- `TALUS_KINECT_DRIVER_MODE`
- `TALUS_KINECT_ENABLE_POINT_CLOUD`
- `TALUS_USE_RGBD_SYNC`
- `TALUS_APPROX_SYNC`
- `TALUS_APPROX_SYNC_MAX_INTERVAL`

### Documentacao

Foram atualizados:

- `README.md`
- `docs/INSTALL-GUIDE.md`
- `docs/HOSTS-CONTEXT.md`

## Commits gerados nesta rodada

- `3f181bd` `Add modular Kinect and odometry test bringup`
- `faf7464` `Patch Kinect driver for odometry bringup`
- `f6e056e` `Replace Kinect patch file with idempotent helper`

Leitura importante:

- o primeiro commit tentou tornar o modo `modular` o caminho principal
- os testes reais mostraram que isso nao era viavel neste hardware
- os dois commits seguintes corrigiram a estrategia e levaram ao desenho final validado

## Comandos executados

### Atualizacao e build no `raspi`

```bash
cd ~/talus-droid
git pull --ff-only origin feat/talus-base-serial-bringup
./scripts/apply-kinect-patches
source /opt/ros/jazzy/setup.bash
export ROS_DOMAIN_ID=42
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
colcon build --symlink-install --packages-select kinect_ros2 talus_base talus_bringup
```

Resultado:

- build concluido
- helper do Kinect aplicado com sucesso

### Teste 1: `floor_test` com Kinect unificado sem point cloud

```bash
cd ~/talus-droid
source /opt/ros/jazzy/setup.bash
source install/setup.bash
export ROS_DOMAIN_ID=42
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export TALUS_ENABLE_TELEOP=false
export TALUS_ENABLE_KINECT=true
export TALUS_KINECT_DRIVER_MODE=unified
export TALUS_KINECT_ENABLE_POINT_CLOUD=false
./scripts/talus-up floor_test
```

### Teste 2: `odom_test` sem `rgbd_sync`

```bash
cd ~/talus-droid
source /opt/ros/jazzy/setup.bash
source install/setup.bash
export ROS_DOMAIN_ID=42
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export TALUS_KINECT_DRIVER_MODE=unified
export TALUS_KINECT_ENABLE_POINT_CLOUD=false
export TALUS_USE_RGBD_SYNC=false
./scripts/talus-up odom_test
```

### Teste 3: `odom_test` com `rgbd_sync`

```bash
cd ~/talus-droid
source /opt/ros/jazzy/setup.bash
source install/setup.bash
export ROS_DOMAIN_ID=42
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export TALUS_KINECT_DRIVER_MODE=unified
export TALUS_KINECT_ENABLE_POINT_CLOUD=false
export TALUS_USE_RGBD_SYNC=true
./scripts/talus-up odom_test
```

### Teste 4: `floor_test` + `slam`

Janela 1:

```bash
cd ~/talus-droid
source /opt/ros/jazzy/setup.bash
source install/setup.bash
export ROS_DOMAIN_ID=42
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export TALUS_ENABLE_TELEOP=false
export TALUS_ENABLE_KINECT=true
export TALUS_KINECT_DRIVER_MODE=unified
export TALUS_KINECT_ENABLE_POINT_CLOUD=false
./scripts/talus-up floor_test
```

Janela 2:

```bash
cd ~/talus-droid
source /opt/ros/jazzy/setup.bash
source install/setup.bash
export ROS_DOMAIN_ID=42
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export TALUS_RTABMAP_VIZ=false
export TALUS_RVIZ=false
export TALUS_USE_RGBD_SYNC=false
./scripts/talus-up slam
```

## Resultados observados

### 1. Descoberta principal desta rodada

O teste inicial com o modo `modular` falhou no hardware real:

```text
Failed to claim camera interface: LIBUSB_ERROR_BUSY
Could not open Kinect device
```

Interpretacao:

- RGB e depth nao podem abrir o Kinect em paralelo do jeito atual
- o caminho modular nao pode ser o default desta plataforma sem refatorar o fork

### 2. `floor_test` final validado

Com o driver unificado + `--disable-pointcloud`:

- `talus_base_bridge` conectou normalmente
- `imu_filter_madgwick` subiu normalmente
- `kinect_ros2_node` subiu normalmente
- `/points` nao apareceu no grafo
- os topicos comprimidos continuaram ativos

Trechos relevantes:

```text
Point cloud component disabled by CLI flag.
Skipping depth_image_proc component due to load failure.
Serial connected: /dev/ttyUSB0 @ 115200 | talus-base-serial-0.1.0 IMU_OK=1
TalusBaseBridge ready
First IMU message received.
```

Nos observados:

```text
/camera_depth_optical_static_tf
/camera_mount_static_tf
/camera_rgb_optical_static_tf
/imu_filter
/imu_static_tf
/kinect_ros2_node
/talus_base_bridge
```

Topicos principais:

```text
/camera_info
/depth/camera_info
/image_raw
/depth/image_raw
/image_raw/compressed
/depth/image_raw/compressedDepth
/imu/data
/imu/raw
```

Metricas de 5 s:

- `/image_raw`: `20.80 Hz` (`104 msgs/5s`)
- `/depth/image_raw`: `26.20 Hz` (`131 msgs/5s`)
- `/imu/data`: `49.80 Hz` (`249 msgs/5s`)
- `/image_raw/compressed`: `9.00 Hz` (`45 msgs/5s`)
- `/depth/image_raw/compressedDepth`: `8.60 Hz` (`43 msgs/5s`)

`/camera_info` observado:

- `frame_id: kinect_rgb_optical_frame`
- `640x480`
- matriz de calibracao presente

### 3. `odom_test` sem `rgbd_sync`

Nos observados:

```text
/camera_depth_optical_static_tf
/camera_mount_static_tf
/camera_rgb_optical_static_tf
/imu_filter
/imu_static_tf
/kinect_ros2_node
/rtabmap/rgbd_odometry
/talus_base_bridge
```

Topicos relevantes:

```text
/rtabmap/odom
/rtabmap/odom_info
/rtabmap/odom_info_lite
/rtabmap/odom_sensor_data/raw
```

Taxa observada:

- `/rtabmap/odom`: `1.60 Hz` (`8 msgs/5s`)

Mensagem amostrada de `/rtabmap/odom`:

- `frame_id: odom`
- `child_frame_id: base_link`
- pose em `0,0,0`
- covariancias `9999`

Warnings predominantes:

```text
Registration failed: Not enough inliers
Failed to find a transformation with the provided guess
Odom: quality=0
```

Interpretacao:

- o pipeline de odometria visual ficou de pe
- a falha dominante passou a ser VO em cena estatica, nao sincronizacao estrutural
- isso faz sentido porque o robo ficou parado/suspenso e sem movimento real da camera

### 4. `odom_test` com `rgbd_sync=true`

Nos observados:

```text
/rtabmap/rgbd_odometry
/rtabmap/rgbd_sync
```

Logs relevantes:

```text
RGBDOdometry: approx_sync = false
RGBDOdometry: subscribe_rgbd = true
odometry: waiting imu (/imu/data) to initialize orientation (wait_imu_to_init=true)
```

Interpretacao:

- o caminho com `rgbd_sync` voltou a complicar o startup
- nao trouxe um ganho claro nesta rodada
- o default `TALUS_USE_RGBD_SYNC=false` continua sendo a melhor escolha operacional

### 5. `slam` isolado

Quando `slam` foi executado sozinho, ele nao recebeu dados suficientes do mundo real.

Interpretacao:

- isso confirma que `slam` continua sendo um profile dependente
- ele deve ser usado por cima de `floor_test` ou de outro bringup que ja suba base + IMU + Kinect

### 6. `floor_test` + `slam`

Com os dois juntos:

- `kinect_ros2_node`, `talus_base_bridge`, `imu_filter`, `rgbd_odometry` e `rtabmap` ficaram ativos
- `/rtabmap/info` apareceu
- `/rtabmap/odom` apareceu
- `/points` continuou ausente

Nos observados:

```text
/imu_filter
/kinect_ros2_node
/rtabmap/rgbd_odometry
/rtabmap/rtabmap
/talus_base_bridge
```

Topicos observados:

```text
/image_raw
/depth/image_raw
/imu/data
/rtabmap/info
/rtabmap/odom
/rtabmap/odom_info
```

Taxa observada:

- `/rtabmap/odom`: `0.80 Hz` (`4 msgs/5s`)

Warnings observados:

```text
Registration failed: Not enough inliers
Odom: quality=0
Odom: quality=8
```

Interpretacao:

- o SLAM agora sobe corretamente em cima do bringup de sensores
- os warnings de sincronizacao deixaram de ser o comportamento dominante desta rodada
- a limitação restante continua sendo o fato de a camera estar parada na bancada

## Resultado esperado vs observado

### Esperado desta rodada

- reduzir carga do Kinect sem quebrar RGB/depth
- separar teste de VO do teste de SLAM
- manter topicos comprimidos para observacao remota
- tirar `rgbd_sync` do caminho default se ele continuasse piorando a pilha

### Observado

- objetivo atingido para o Kinect:
  - `/points` saiu do caminho default
  - RGB/depth e compressed continuaram vivos
- objetivo atingido para o bringup:
  - `odom_test` ficou separado de `slam`
- objetivo atingido para a pilha de odometria:
  - `rgbd_odometry` sobe sem depender do `rtabmap`
- objetivo atingido para o criterio A/B:
  - `use_rgbd_sync=false` ficou melhor como default operacional

Limite desta rodada:

- nao foi possivel validar odometria geometricamente boa porque nao houve movimento fisico real da camera nesta madrugada

## Conclusao

Status da rodada:

- implementacao: aprovada
- `floor_test`: aprovado
- `odom_test` headless: aprovado como pipeline
- `slam` headless: aprovado quando executado por cima de `floor_test`
- qualidade final de VO/SLAM: ainda inconclusiva em bancada estatica

## Proximos passos recomendados

1. Fazer um teste curto no chao com `floor_test` + `slam`, mantendo `TALUS_USE_RGBD_SYNC=false`.
2. Medir os offsets reais de `base_link -> camera_link` e `base_link -> imu_link` e atualizar `frames.yaml`.
3. Verificar a resposta do `/rtabmap/odom` durante movimento real da camera, nao apenas com o robô suspenso.
4. So depois disso decidir se entra `robot_localization` ou se ainda ha trabalho pendente no Kinect/VO.
