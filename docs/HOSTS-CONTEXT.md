# Talus-Droid — Hosts Context

Contexto de hosts e runtime especifico deste projeto. Este arquivo complementa a memoria global em `/home/felip/.codex/memories/HOSTS-AND-WORKSPACES.md`.

Nao usar este arquivo para roadmap do projeto. Ele deve registrar apenas fatos operacionais relevantes para Talus-Droid.

## Hosts

## Nota de nomenclatura

O nome "Talus" tem dois usos historicos que podem causar confusao:

- `talus`: PC/homeserver da sala, associado ao ecossistema pessoal e ao repositorio `talus-core`.
- `talus-droid`: este repositorio/projeto do robo, originalmente pensado como o corpo fisico do assistente pessoal Talus.

Neste repositorio, quando a documentacao falar em validacao de hardware do robo, o host autoritativo e o `raspi`. O host `talus` pode ser usado como apoio de desenvolvimento, build e testes sem hardware, mas nao substitui o `raspi` para Kinect, Arduino, joystick, motores ou SLAM com sensor real.

Manter o nome atual por enquanto. Se a ambiguidade continuar atrapalhando, opcoes futuras sao renomear o robo, o repositorio, ou padronizar um nome operacional distinto para o corpo fisico.

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
- `~/.bashrc` ja carrega `source /opt/ros/jazzy/setup.bash`, `ROS_DOMAIN_ID=42`, `RMW_IMPLEMENTATION=rmw_cyclonedds_cpp` e `PATH="$HOME/.local/bin:$PATH"`

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
- a bridge serial empacotada, o firmware novo do Nano e o bringup com joystick foram validados em hardware
- `floor_test` foi validado em bancada e no chao com a base respondendo a `/cmd_vel`
- o novo workspace com `talus_base` e `talus_bringup` ja compilou com `colcon` no `raspi`
- o `arduino-cli` no `raspi` ja recebeu o core `arduino:avr`
- o pipeline headless `base + IMU + Kinect + RTAB-Map` ja subiu com sucesso no `raspi`
- o `odom_test` ja foi validado como smoke test de odometria visual headless

Nota de checkpoint em 2026-04-29: essas validacoes continuam registradas como baseline historico, mas a frente atual voltou para a camada Kinect porque RGB-D simultaneo ficou instavel. `odom_test`, VO e RTAB-Map nao devem ser tratados como liberados ate o preflight RGB-D voltar a passar de forma repetivel.

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
- a point cloud `/points` foi medida como muito pesada para uso remoto constante e nao deve ser tratada como entrada padrao do pipeline de SLAM neste momento

## Base serial atual

- a implementacao em desenvolvimento usa o pacote ROS `talus_base`
- o bring-up padrao de teleop usa `talus_bringup`
- o script operacional principal no `raspi` passa a ser `~/talus-droid/scripts/talus-up`
- o perfil principal para testes de chao e `floor_test`
- o perfil `odom_test` passa a ser o smoke test headless de odometria visual
- o startup opt-in fica modelado por `~/talus-droid/systemd/talus-bringup.service`
- o arquivo de toggles do service fica em `~/talus-droid/systemd/talus-bringup.env`
- o service atual no `raspi` injeta `ROS_DOMAIN_ID=42` e `RMW_IMPLEMENTATION=rmw_cyclonedds_cpp` via `talus-bringup.env`
- o service foi observado ativo em `floor_test`, com `enable_kinect=true` e `enable_teleop=false`
- o sketch oficial do Nano fica em `~/talus-droid/firmware/arduino-nano/arduino-nano.ino`
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
- a IMU crua sai em `/imu/raw` e `/imu/data_raw`
- a IMU filtrada alvo do bringup sai em `/imu/data`
- os frames estaticos agora ficam centralizados em `src/talus_bringup/config/frames.yaml`
- os offsets reais de `base_link -> imu_link` e `base_link -> camera_link` ainda precisam ser medidos
- a primeira estimativa levantada para o `frames.yaml` passou a ser:
  - `imu.xyz = [-0.07, -0.03, 0.01]`
  - `imu.rpy = [0.0, 0.0, 3.14159265359]`
  - `camera_mount.xyz = [0.13, 0.0, 0.08]`
- os frames opticos do Kinect ficam em `kinect_rgb_optical_frame` e `kinect_depth_optical_frame`
- o `yaw` da IMU filtrada nao deve ser tratado como heading absoluto, porque o sensor atual nao tem magnetometro
- o service `talus-bringup.service` ja sobe no boot, mas os testes operacionais mais recentes foram feitos manualmente com `scripts/talus-up`
- os testes reais no `raspi` devem usar run bundles conforme `docs/diagnostics/raspi-experiment-flow.md`, com `experiment.yaml`, `notes.md` e subpastas do runner em `artifacts/testlogs/...`
- o `talus` e headless; visualizacao com `rqt`, RViz2, Foxglove ou PlotJuggler deve ser feita no `aiquitude`/notebook com GUI quando necessaria

## RTAB-Map

- o fluxo oficial em teste continua sendo RTAB-Map no `raspi` e observacao remota no notebook
- a referencia atual para alimentar o RTAB-Map continua sendo:
  - `/image_raw`
  - `/depth/image_raw`
  - `/camera_info`
- o bringup atual privilegia `kinect_ros2_node` com point cloud desligada por patch/CLI; o modo modular ficou apenas experimental
- o modo `modular` falhou em hardware real com `LIBUSB_ERROR_BUSY`, entao o caminho operacional atual e o driver unificado
- o helper `scripts/apply-kinect-patches` e parte do fluxo de preparacao do fork no `raspi`
- a frente Kinect esta em modo `kinect-validation`: falha no preflight bloqueia VO/SLAM, mas e um resultado valido quando o objetivo da run e diagnosticar Kinect/USB/libfreenect/driver
- o perfil `slam` nao deve ser tratado como bringup completo sozinho; a referencia operacional atual e subir `floor_test` e depois `slam`
- o `odom_test` sem `rgbd_sync` ficou mais estavel que a variante com `rgbd_sync=true` nos testes preliminares
- houve teste preliminar com inscricoes em `/image_raw/compressed` e `/depth/image_raw/zstd`
- nesse experimento apareceram:
  - warnings de `Did not receive data since 5 seconds`
  - indicios de problemas de sincronizacao
  - spam de `VWDictionary.cpp::addWordRef()`
- os dois relatorios atuais da frente Kinect/RTAB-Map ficam em `docs/reports/2026-04-08-kinect-rtabmap-smoke.md` e `docs/reports/2026-04-08-odom-kinect-rtabmap-round2.md`

## Rede observada no `raspi`

- `eth0` estava `down`
- `wlan0` estava `up`
- o link Wi-Fi mostrou baixa qualidade e muitos retries
- a lentidao do SSH no `raspi` foi majoritariamente problema de rede sem fio
