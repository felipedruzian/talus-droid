# Test Track — Kinect + IMU + TF

Documento vivo para a frente atual de validacao de sensores e geometria do Talus-Droid antes de retomar testes mais fortes de RTAB-Map e, depois, navegacao.

## Objetivo atual

Concluir uma linha de base confiavel para:

- IMU no padrao ROS
- Kinect v1 como entrada RGB-D local
- `TF` do robo com offsets reais de camera e IMU
- `odom_test` como smoke test de odometria visual
- `slam` rodando sobre `floor_test`

## Baseline ja validado

Esta trilha parte do seguinte estado ja confirmado:

- bridge serial empacotada e firmware novo do Nano funcionando
- joystick e `cmd_vel` validados em hardware
- bringup `floor_test` funcional
- `imu_filter_madgwick` publicando `/imu/data`
- `kinect_ros2_node` unificado operacional no `raspi`
- topicos comprimidos do Kinect observados pela rede
- RTAB-Map headless subindo no `raspi`

Referencias historicas desta frente:

- [2026-04-08-kinect-rtabmap-smoke.md](/home/felip/repos/talus-droid/docs/reports/2026-04-08-kinect-rtabmap-smoke.md)
- [2026-04-08-odom-kinect-rtabmap-round2.md](/home/felip/repos/talus-droid/docs/reports/2026-04-08-odom-kinect-rtabmap-round2.md)

## Decisoes atuais

- usar `kinect_ros2_node` unificado como baseline operacional
- manter `/points` desligada por default
- usar RTAB-Map com topicos raw locais:
  - `/image_raw`
  - `/depth/image_raw`
  - `/camera_info`
- tratar o `yaw` da IMU como relativo, nao absoluto
- tratar `slam` como dependente de `floor_test`, nao como bringup completo standalone

## Sequencia oficial de testes

### 1. IMU

Validar:

- `/imu/raw`
- `/imu/data_raw`
- `/imu/data`
- coerencia de gravidade e orientacao

Aceite:

- frequencia estavel
- `frame_id` correto
- `roll/pitch` coerentes
- sem tratar `yaw` como heading absoluto

### 2. TF

Levantar e validar:

- `base_link -> imu_link`
- `base_link -> camera_link`
- `camera_link -> kinect_rgb_optical_frame`
- `camera_link -> kinect_depth_optical_frame`

Aceite:

- transforms existentes
- offsets fisicos medidos
- `frames.yaml` pronto para receber valores reais

### 3. Kinect

Validar:

- `image_raw`
- `depth/image_raw`
- `camera_info`
- transportes comprimidos apenas para observacao

Aceite:

- RGB e depth estaveis
- `camera_info` coerente
- `/points` fora do caminho critico

### 4. VO

Rodar:

- `odom_test`

Default desta trilha:

- `use_rgbd_sync=false`
- `approx_sync=true`
- `kinect_enable_point_cloud=false`

Aceite:

- `/rtabmap/odom` responde a movimento real
- warnings de sync e inliers ficam documentados
- resultado classificado como utilizavel ou bloqueado

### 5. SLAM

Rodar:

- `floor_test`
- depois `slam`

Aceite:

- `rtabmap` permanece ativo
- `/rtabmap/info` e `/rtabmap/odom` aparecem
- conclusao objetiva sobre prontidao para novo teste de chao

## Pendencias abertas

- medir offsets reais de camera e IMU
- revisar warning de nome duplicado de `kinect_ros2_node`
- revisar se o modo `modular` do Kinect merece investigacao agora ou fica como limitacao conhecida
- repetir VO com movimento real no chao

## Fora do escopo imediato

- Nav2
- fusao mais completa com `robot_localization`
- reabilitar `/points` como default
- tratar o encoder como bloqueador desta fase
