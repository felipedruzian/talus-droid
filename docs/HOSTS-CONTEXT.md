# Talus-Droid — Hosts Context

Contexto de hosts e runtime especifico deste projeto. Este arquivo complementa a memoria global em `/home/felip/.codex/memories/HOSTS-AND-WORKSPACES.md`.

Nao usar este arquivo para roadmap do projeto. Ele deve registrar apenas fatos operacionais relevantes para Talus-Droid.

## Hosts

### Notebook operador

- host observado: `aiquitude`
- sistema: Linux Mint 22.3
- repositorio local observado: `/home/felip/repos/talus-droid`
- papel: SSH, revisao, consumo remoto de topicos ROS e visualizacao
- ROS 2 Jazzy instalado
- `rviz2` e `rqt` disponiveis

### `talus`

- papel: host principal de desenvolvimento na LAN
- IP observado: `192.168.1.69`
- caminho esperado do repo: `/home/felip/repos/talus-droid`
- deve ser preferido para sessoes de desenvolvimento sem dependencia direta de hardware

### `raspi`

- papel: host embarcado do robo
- sistema: Ubuntu Server 24.04
- IP observado: `192.168.1.19`
- workspace oficial confirmado: `/home/felip/talus-droid`
- executa joystick, bridge serial, Kinect e RTAB-Map
- `arduino-cli` disponivel em `/home/felip/.local/bin/arduino-cli`
- `colcon` disponivel no ambiente ROS

## ROS e workspace

- os hosts usam:
  - `ROS_DOMAIN_ID=42`
  - `RMW_IMPLEMENTATION=rmw_cyclonedds_cpp`
- esses exports ja foram adicionados aos `.bashrc` dos hosts
- `~/ros2_ws` deve ser tratado apenas como legado
- `~/talus-droid/install/setup.bash` no `raspi` expoe os pacotes validados do Kinect e da base
- `~/talus-droid/src/KinectV1-Ros2` no `raspi` ja e copia real do repositorio, nao symlink

Pacotes confirmados no overlay do `raspi`:

- `kinect_ros2`
- `ros2_kinect_depth`
- `ros2_kinect_led`
- `ros2_kinect_mic_node`
- `ros2_kinect_rgb`
- `ros2_kinect_tilt`
- `talus_base`
- `talus_bringup`

## Validacoes ja feitas

- notebook recebeu `/joy` publicado pelo `raspi`
- notebook observou os topicos raw do Kinect
- via Wi-Fi, os topicos raw ficaram por volta de `4-5 Hz`
- os topicos comprimidos do Kinect foram observados pela rede
- `rqt` no notebook visualizou os topicos comprimidos com fluidez melhor que o RViz
- a bridge serial antiga e o firmware antigo responderam a testes de `cmd_vel`, timeout e reconexao
- o novo workspace com `talus_base` e `talus_bringup` ja compilou com `colcon` no `raspi`
- o `arduino-cli` no `raspi` ja recebeu o core `arduino:avr`

## Transporte de imagem

- o fork `KinectV1-Ros2` ja usa `image_transport`
- os plugins de `image_transport` ja foram instalados no `raspi`
- o `raspi` passou a expor topicos como:
  - `/image_raw/compressed`
  - `/depth/image_raw/compressedDepth`
  - `/image_raw/zstd`
  - `/depth/image_raw/zstd`
- para visualizacao remota, usar preferencialmente:
  - `rqt` para imagem
  - RViz para `TF`, `PointCloud2` e mapa

## Base serial atual

- a implementacao em desenvolvimento usa o pacote ROS `talus_base`
- o bring-up padrao de teleop usa `talus_bringup`
- o contrato serial alvo atual entre Pi e Nano e:
  - `PING`
  - `PONG <fw_version> IMU_OK=<0|1>`
  - `DRV <left_pwm> <right_pwm>`
  - `IMU <ax> <ay> <az> <gx> <gy> <gz>`
  - `ENC <left_ticks> <right_ticks>` opcional
  - `HORN <0|1>` opcional
  - `BEEP <pattern_id>`
  - `ERR <code> <detail>`
- buzzer do Nano ligado em `D11`
- encoder esquerdo apresentou comportamento suspeito nos testes anteriores e nao deve ser tratado como bloqueador desta fase

## RTAB-Map

- o fluxo oficial em teste continua sendo RTAB-Map no `raspi` e observacao remota no notebook
- a referencia atual para alimentar o RTAB-Map continua sendo:
  - `/image_raw`
  - `/depth/image_raw`
  - `/camera_info`
- houve teste preliminar com inscricoes em `/image_raw/compressed` e `/depth/image_raw/zstd`
- nesse experimento apareceram:
  - warnings de `Did not receive data since 5 seconds`
  - indicios de problemas de sincronizacao
  - spam de `VWDictionary.cpp::addWordRef()`

## Rede observada no `raspi`

- `eth0` estava `down`
- `wlan0` estava `up`
- o link Wi-Fi mostrou baixa qualidade e muitos retries
- a lentidao do SSH no `raspi` foi majoritariamente problema de rede sem fio
