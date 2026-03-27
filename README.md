# Talus-Droid

Plataforma experimental de robô de serviço baseada em **Raspberry Pi + Arduino Nano + Kinect v1**, integrada ao ecossistema Talus.

Este repositório representa o estado **mínimo restaurado e validado** do ambiente usado para retomar o ponto funcional do TCC1 e preparar os próximos testes do TCC2.

## Estado atual validado

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

## Hardware usado

- Raspberry Pi 4
- Arduino Nano com CH341
- Kinect v1 (Xbox NUI)
- Gamepad Zikway USB

## Estrutura relevante

```text
~/ros2_ws
├── src/
│   ├── talus_base/
│   │   └── talus_base_bridge.py
│   └── KinectV1-Ros2/

~/repos
├── libfreenect/
└── talus-droid/
    └── talus-mvp.ino
```

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
cd ~/ros2_ws
source /opt/ros/jazzy/setup.bash
source install/setup.bash
```

## Controle do robô

### Teste do joystick

Terminal 1:

```bash
ros2 run joy joy_node
```

Terminal 2:

```bash
ros2 topic echo /joy
```

### Bridge serial com Arduino

```bash
cd ~/ros2_ws
source /opt/ros/jazzy/setup.bash
python3 src/talus_base/talus_base_bridge.py
```

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
cd ~/ros2_ws
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

- bridge serial do robô: `~/ros2_ws/src/talus_base/talus_base_bridge.py`
- sketch do Arduino: `~/repos/talus-droid/talus-mvp.ino`
- workspace ROS: `~/ros2_ws`
- repositório do Kinect ROS 2: `~/ros2_ws/src/KinectV1-Ros2`
- `libfreenect`: `~/repos/libfreenect`

## Próximos passos

- validar coexistência de `joy_node + talus_base_bridge.py + rgb_node + depth_node`
- testar gravação curta com `ros2 bag`
- testar consumo remoto dos tópicos a partir de outra máquina na rede
- decidir se o fluxo principal ficará nos nós modulares ou no `kinect_ros2_node`
- depois disso, seguir para integração com SLAM / RTAB-Map / navegação

## Referências

- ROS 2 Jazzy — instalação via pacotes Debian
- OpenKinect `libfreenect`
- `KinectV1-Ros2`

