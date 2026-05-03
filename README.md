# Talus-Droid

Plataforma experimental de robô de serviço baseada em **Raspberry Pi + Arduino Nano + Kinect v1**, integrada ao ecossistema Talus.

> **Nota de nomenclatura:** hoje existem dois contextos chamados "Talus". O host `talus` e o PC/homeserver da sala, associado ao repositorio `talus-core` e aos servicos pessoais. O **Talus-Droid** e este projeto de robo/corpo fisico do assistente, executado no host embarcado `raspi`. Por enquanto o nome do repositorio fica como esta, mas futuras opcoes sao renomear o robo ou o repositorio para reduzir ambiguidade.

Este repositório representa o estado **mínimo restaurado e validado** do ambiente usado para retomar o ponto funcional do TCC1 e preparar os próximos testes do TCC2.

O stack antigo de serial e teleop ja foi validado em hardware. Nesta branch, a base tambem foi reorganizada em pacotes ROS 2 (`talus_base` e `talus_bringup`) com um contrato serial novo e unico entre Raspberry Pi e Arduino Nano, um bringup em camadas para testes de chao e um filtro de IMU no padrao ROS.

## Baseline restaurado e gate atual

No Raspberry Pi com **Ubuntu Server 24.04 LTS** e **ROS 2 Jazzy**, foi validado com sucesso:

- ROS 2 Jazzy instalado por pacotes `.deb`
- `rmw_cyclonedds_cpp` configurado
- gamepad USB publicando em `/joy`
- bridge serial com **Arduino Nano** funcionando em `/dev/ttyUSB0`
- `libfreenect` compilado e funcional
- Kinect v1 funcionando fora do ROS
- Kinect v1 funcionando no ROS 2 com:
  - RGB
  - depth
  - tilt
  - LED
- `kinect_ros2_node` também executando e publicando tópicos unificados

Nota de checkpoint: a frente atual reabriu a validação do Kinect RGB-D antes de continuar VO/SLAM. Em 2026-05-02, a matriz Kinect-only mostrou `depth` estável enquanto RGB/video falha ou não entrega frames reais em `libfreenect`/ROS Kinect-only; por isso `odom_test`, VO e RTAB-Map seguem bloqueados até a cadeia RGB-D ficar estável.

## Hardware usado

- Raspberry Pi 4
- Arduino Nano com CH341
- Kinect v1 (Xbox NUI)
- Gamepad Zikway USB

## Estrutura relevante

```text
~/talus-droid
├── src/
│   ├── talus_base/
│   ├── talus_bringup/
│   └── KinectV1-Ros2/
├── firmware/
│   └── arduino-nano/
│       └── arduino-nano.ino
└── docs/
```

## Workflow e Kanban (TCC2)

O gerenciamento de tarefas do TCC2 migrou oficialmente para o **Trello** como *Single Source of Truth*. O arquivo Kanban no Obsidian (`TCC2-Kanban.md`) atua apenas como cache de leitura passiva e registro histórico.

Para criar, mover ou atualizar tarefas, use o MCP `trello` no OpenCode com apoio da skill `trello-tcc`. Para sincronizar o cache do Trello para o Obsidian localmente, utilize `/trello-sync`; ele atualiza o Markdown no vault, mas não é o caminho de edição.

Contexto operacional versionado: `/home/felip/repos/TCC-KANBAN.md`.

## Documentacao de testes

Relatorios recentes desta frente:

- [2026-04-08-kinect-rtabmap-smoke.md](/home/felip/repos/talus-droid/docs/reports/2026-04-08-kinect-rtabmap-smoke.md)
- [2026-04-08-odom-kinect-rtabmap-round2.md](/home/felip/repos/talus-droid/docs/reports/2026-04-08-odom-kinect-rtabmap-round2.md)
- [2026-04-27-kinect-validation.md](/home/felip/repos/talus-droid/docs/reports/2026-04-27-kinect-validation.md)

Trilha viva da frente atual:

- [TEST-TRACK-KINECT-IMU-TF.md](/home/felip/repos/talus-droid/docs/TEST-TRACK-KINECT-IMU-TF.md)
- [Procedimento de validação diagnóstica do Kinect](/home/felip/repos/talus-droid/docs/diagnostics/kinect-validation.md) — suporte opcional de build/test no host `talus`; validacao real de hardware continua sendo no `raspi`
- [Fluxo de experimentos no `raspi`](/home/felip/repos/talus-droid/docs/diagnostics/raspi-experiment-flow.md) — padrao de run bundle com `experiment.yaml`, `notes.md` e artefatos em `artifacts/testlogs/...`

## Setup rápido

### 1. Ambiente ROS

Adicionar ao final do `~/.bashrc`:

```bash
source /opt/ros/jazzy/setup.bash
export ROS_DOMAIN_ID=42
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export PATH="$HOME/.local/bin:$PATH"
```

Aplicar:

```bash
source ~/.bashrc
```

### 2. Carregar o workspace

```bash
cd ~/talus-droid
source /opt/ros/jazzy/setup.bash
source install/setup.bash
```

## Bringup operacional

### Script unico

O ponto de entrada operacional agora e:

```bash
cd ~/talus-droid
./scripts/talus-up floor_test
```

Perfis disponiveis:

- `floor_test`: base + IMU filtrada + teleop opcional + Kinect opcional
- `base`: bridge serial + TF minimo + filtro de IMU
- `teleop`: joystick + `teleop_twist_joy`
- `kinect`: Kinect por bringup
- `odom_test`: base + IMU + Kinect + odometria visual headless
- `slam`: RTAB-Map em launch separado

O script detecta joystick e Kinect em modo `auto` e nao sobe esses subsistemas se os devices nao estiverem presentes.
No startup por `systemd`, o arquivo `talus-bringup.env` tambem pode definir `TALUS_DEVICE_SETTLE_SECS` para aguardar alguns segundos antes da deteccao de USB.
Para o Kinect, o bringup agora usa por default o executavel unificado com point cloud desligada, configuravel por `TALUS_KINECT_DRIVER_MODE` e `TALUS_KINECT_ENABLE_POINT_CLOUD`.

### Startup opt-in com systemd

Arquivos versionados:

- [talus-bringup.service](/home/felip/repos/talus-droid/systemd/talus-bringup.service)
- [talus-bringup.env](/home/felip/repos/talus-droid/systemd/talus-bringup.env)
- [install-systemd-service](/home/felip/repos/talus-droid/scripts/install-systemd-service)

Instalacao no `raspi`:

```bash
cd ~/talus-droid
./scripts/install-systemd-service
```

Ativar/desativar no boot:

```bash
sudo systemctl enable talus-bringup.service
sudo systemctl disable talus-bringup.service
```

## Controle do robô

### Fluxo oficial de comando da base

O caminho de movimento da base passa a ser:

```text
joy_node -> teleop_twist_joy -> /cmd_vel -> talus_base_bridge -> serial -> Arduino Nano
```

Esse e o mesmo caminho que depois deve ser reutilizado por Nav2, trocando apenas a origem de `/cmd_vel`.

### Teste do joystick

Terminal 1:

```bash
ros2 run joy joy_node
```

Terminal 2:

```bash
ros2 topic echo /joy
```

### Bridge serial isolada

```bash
cd ~/talus-droid
source /opt/ros/jazzy/setup.bash
source install/setup.bash
ros2 run talus_base talus_base_bridge
```

### Bringup de teste no chao

```bash
cd ~/talus-droid
source /opt/ros/jazzy/setup.bash
source install/setup.bash
ros2 launch talus_bringup floor_test.launch.py
```

### Teleop legado da base

O launch `base_teleop.launch.py` continua existindo como wrapper de compatibilidade para o `floor_test` sem Kinect.

### IMU no padrao ROS

O bridge publica:

- `/imu/raw`
- `/imu/data_raw`

O `talus_bringup` sobe `imu_filter_madgwick` para publicar a IMU filtrada em `/imu/data`.

Frames esperados:

- `base_link`
- `imu_link`
- `camera_link`
- `kinect_rgb_optical_frame`
- `kinect_depth_optical_frame`

Os frames estaticos agora ficam centralizados em [frames.yaml](/home/felip/repos/talus-droid/src/talus_bringup/config/frames.yaml). Os offsets default de `base_link -> imu_link` e `base_link -> camera_link` ainda sao placeholders e devem ser medidos no hardware.

### Firmware do Arduino Nano

Compilar e enviar para o Nano no `raspi`:

```bash
cd ~/talus-droid
arduino-cli compile --fqbn arduino:avr:nano firmware/arduino-nano
arduino-cli upload -p /dev/ttyUSB0 --fqbn arduino:avr:nano firmware/arduino-nano
```

Se o upload falhar por bootloader antigo, tentar:

```bash
arduino-cli compile --fqbn arduino:avr:nano:cpu=atmega328old firmware/arduino-nano
arduino-cli upload -p /dev/ttyUSB0 --fqbn arduino:avr:nano:cpu=atmega328old firmware/arduino-nano
```

### Beeps de status

O buzzer em `D11` usa uma tabela curta de status:

- `1 beep curto`: boot OK ou handshake serial OK
- `2 beeps curtos`: IMU indisponivel, mas base ainda controlavel
- `3 beeps curtos`: falha serial ou reconexao
- `1 beep longo`: timeout de drive ou parada de seguranca

### Wiring

As ligacoes atuais da base estao documentadas em [WIRING.md](/home/felip/repos/talus-droid/docs/WIRING.md).

## Kinect v1

### Observações importantes

- O `libfreenect` foi compilado manualmente em `/usr/local`
- O driver de kernel `gspca_kinect` foi blacklistado para evitar conflito
- As regras `udev` do Kinect foram instaladas
- O repositório `KinectV1-Ros2` foi originalmente pensado para **ROS 2 Humble / Ubuntu 22.04**, mas o ambiente abaixo foi validado em **ROS 2 Jazzy / Ubuntu 24.04**

### Testes nativos do libfreenect

Tilt / LED / acelerômetro:

```bash
freenect-tiltdemo
```

Visualizadores e utilitários instalados:

```bash
ls -1 /usr/local/bin/freenect-*
```

### Nós ROS modulares

Carregar o ambiente antes:

```bash
cd ~/talus-droid
source /opt/ros/jazzy/setup.bash
source install/setup.bash
```

#### LED

Terminal 1:

```bash
ros2 run ros2_kinect_led ros2_kinect_led_node
```

Terminal 2:

```bash
ros2 topic pub --once /kinect/led_cmd std_msgs/msg/String "{data: 'green'}"
ros2 topic pub --once /kinect/led_cmd std_msgs/msg/String "{data: 'blink_green'}"
ros2 topic pub --once /kinect/led_cmd std_msgs/msg/String "{data: 'off'}"
```

#### Tilt

Terminal 1:

```bash
ros2 run ros2_kinect_tilt ros2_kinect_tilt_node
```

Terminal 2:

```bash
ros2 topic pub --once /kinect/tilt_cmd std_msgs/msg/String "{data: 'center'}"
ros2 topic pub --once /kinect/tilt_cmd std_msgs/msg/String "{data: 'up'}"
ros2 topic pub --once /kinect/tilt_cmd std_msgs/msg/String "{data: 'down'}"
ros2 topic pub --once /kinect/tilt_cmd std_msgs/msg/String "{data: 'set 10'}"
```

#### RGB

```bash
ros2 run ros2_kinect_rgb rgb_node
```

Em outro terminal:

```bash
ros2 topic hz /kinect/rgb/image_raw
ros2 topic info /kinect/rgb/image_raw
```

#### Depth

```bash
ros2 run ros2_kinect_depth depth_node
```

Em outro terminal:

```bash
ros2 topic hz /kinect/depth/image_raw
ros2 topic info /kinect/depth/image_raw
```

### Nó unificado

Também foi validado:

```bash
ros2 run kinect_ros2 kinect_ros2_node
```

Tópicos observados com o nó unificado:

```text
/camera_info
/depth/camera_info
/depth/image_raw
/image_raw
/points
/tf_static
/tilt_angle
```

O bringup atual do robo usa por default o executavel `kinect_ros2_node` com a point cloud desligada para reduzir CPU e banda. O modo `modular` continua disponivel para experimentos, mas nao e o padrao.

No `raspi`, o fork local do Kinect recebe essa correcao pelo helper [apply-kinect-patches](/home/felip/repos/talus-droid/scripts/apply-kinect-patches).

## Testes recomendados após subir os nós

### Ver pacotes e executáveis do Kinect

```bash
ros2 pkg list | grep kinect
ros2 pkg executables | grep kinect
```

### Medir taxa de publicação

```bash
ros2 topic hz /image_raw
ros2 topic hz /depth/image_raw
```

ou, nos nós modulares:

```bash
ros2 topic hz /kinect/rgb/image_raw
ros2 topic hz /kinect/depth/image_raw
```

### Gravar bag curto

```bash
mkdir -p ~/bags
ros2 bag record -o ~/bags/kinect_smoke \
  /kinect/rgb/image_raw \
  /kinect/rgb/camera_info \
  /kinect/depth/image_raw \
  /kinect/depth/camera_info
```

### Validar pela rede

Em outra máquina na mesma LAN, com o mesmo `ROS_DOMAIN_ID` e o mesmo `RMW_IMPLEMENTATION`:

```bash
ros2 topic list | grep kinect
ros2 topic hz /kinect/rgb/image_raw
ros2 topic hz /kinect/depth/image_raw
```

## Ferramentas instaladas no ambiente

- `colcon`
- `rosdep`
- `vcs`
- `arduino-cli`

Validação rápida:

```bash
command -v colcon
command -v rosdep
command -v vcs
command -v arduino-cli
```

## Arquivos importantes

- pacote base do robô: `~/talus-droid/src/talus_base`
- pacote de bringup: `~/talus-droid/src/talus_bringup`
- sketch do Arduino: `~/talus-droid/firmware/arduino-nano/arduino-nano.ino`
- workspace ROS: `~/talus-droid`
- repositório do Kinect ROS 2: `~/talus-droid/src/KinectV1-Ros2`
- `libfreenect`: `~/repos/libfreenect`

## Próximos passos

- validar coexistência de `ros2 launch talus_bringup base_teleop.launch.py + rgb_node + depth_node`
- testar gravação curta com `ros2 bag`
- testar consumo remoto dos tópicos a partir de outra máquina na rede
- decidir se o fluxo principal ficará nos nós modulares ou no `kinect_ros2_node`
- depois disso, seguir para integração com SLAM / RTAB-Map / navegação

## Referências

- ROS 2 Jazzy — instalação via pacotes Debian
- OpenKinect `libfreenect`
- `KinectV1-Ros2`
