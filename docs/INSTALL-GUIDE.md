# Talus-Droid — INSTALL-GUIDE

Guia enxuto de instalação e restauração do ambiente mínimo validado no **Raspberry Pi / Ubuntu Server 24.04 / ROS 2 Jazzy** para o Talus-Droid.

Este guia cobre o que foi necessário para voltar ao ponto funcional do TCC1 e preparar o ambiente para os próximos testes do TCC2:

- ROS 2 Jazzy funcionando no Raspberry Pi
- Cyclone DDS configurado
- gamepad funcionando no ROS (`/joy`)
- bridge serial com Arduino Nano funcionando
- `libfreenect` compilado e funcional
- Kinect v1 funcionando fora do ROS
- Kinect v1 funcionando no ROS 2 com RGB, depth, tilt e LED

---

## 1. Ambiente validado

### Hardware
- Raspberry Pi 4 (Ubuntu Server 24.04 LTS, arm64)
- Arduino Nano (conversor CH341, porta serial `/dev/ttyUSB0`)
- Kinect v1 (Xbox NUI)
- Gamepad Zikway USB

### Software
- Ubuntu Server 24.04 LTS
- ROS 2 Jazzy (instalação por pacotes `.deb`)
- RMW: `rmw_cyclonedds_cpp`
- Workspace ROS em `~/talus-droid`
- Repositórios locais em `~/repos`

### Estrutura local relevante
```bash
~/talus-droid
~/talus-droid/src/talus_base
~/talus-droid/src/talus_bringup
~/talus-droid/src/KinectV1-Ros2
~/repos/libfreenect
~/talus-droid/firmware/arduino-nano/talus-mvp.ino
```

---

## 2. Corrigir os repositórios do Ubuntu no Raspberry Pi

No Ubuntu 24.04 para Raspberry Pi, a ausência de `noble-updates` e `noble-backports` pode quebrar a instalação binária do ROS 2 por conflito de dependências.

Arquivo esperado: `/etc/apt/sources.list.d/ubuntu.sources`

```text
Types: deb
URIs: http://ports.ubuntu.com/ubuntu-ports/
Suites: noble noble-updates noble-backports
Components: main restricted universe multiverse
Signed-By: /usr/share/keyrings/ubuntu-archive-keyring.gpg

Types: deb
URIs: http://ports.ubuntu.com/ubuntu-ports/
Suites: noble-security
Components: main restricted universe multiverse
Signed-By: /usr/share/keyrings/ubuntu-archive-keyring.gpg
```

Depois:

```bash
sudo apt update
sudo apt full-upgrade -y
sudo apt --fix-broken install -y
sudo reboot
```

---

## 3. Dependências base do sistema

```bash
sudo apt update
sudo apt install -y \
  git curl build-essential cmake pkg-config \
  python3-pip python3-venv python3-dev \
  python3-serial python3-evdev \
  joystick evtest \
  software-properties-common
```

### Validar grupos e serial

```bash
groups
ls -l /dev/ttyACM* /dev/ttyUSB* 2>/dev/null
```

O usuário deve estar no grupo `dialout`.

---

## 4. Instalar ROS 2 Jazzy

### 4.1. Habilitar `universe`

```bash
sudo apt install -y software-properties-common
sudo add-apt-repository universe -y
```

### 4.2. Instalar `ros2-apt-source`

```bash
export ROS_APT_SOURCE_VERSION=$(curl -s https://api.github.com/repos/ros-infrastructure/ros-apt-source/releases/latest | grep -F "tag_name" | awk -F'"' '{print $4}')
curl -L -o /tmp/ros2-apt-source.deb "https://github.com/ros-infrastructure/ros-apt-source/releases/download/${ROS_APT_SOURCE_VERSION}/ros2-apt-source_${ROS_APT_SOURCE_VERSION}.$(. /etc/os-release && echo ${UBUNTU_CODENAME:-${VERSION_CODENAME}})_all.deb"
sudo dpkg -i /tmp/ros2-apt-source.deb
sudo apt update
```

### 4.3. Se houver conflito com repositório ROS antigo

Se aparecer conflito de `Signed-By`, remover a configuração manual antiga:

```bash
sudo rm -f /etc/apt/sources.list.d/ros2.list
sudo apt update
```

### 4.4. Instalar ROS base

```bash
sudo apt install -y ros-jazzy-ros-base
```

---

## 5. RMW Cyclone DDS e ambiente ROS

### 5.1. Instalar Cyclone DDS

```bash
sudo apt install -y ros-jazzy-rmw-cyclonedds-cpp
```

### 5.2. Adicionar ao `~/.bashrc`

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

### 5.3. Validar variáveis

```bash
printenv | grep -E 'ROS_DOMAIN_ID|RMW_IMPLEMENTATION'
```

Esperado:

```text
ROS_DOMAIN_ID=42
RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
```

---

## 6. Ferramentas de desenvolvimento ROS e Arduino

```bash
sudo apt install -y \
  python3-colcon-common-extensions \
  python3-rosdep \
  python3-vcstool \
  pipx

pipx ensurepath
source ~/.bashrc
```

Inicializar `rosdep`:

```bash
sudo rosdep init
rosdep update
```

### Arduino CLI

```bash
curl -fsSL https://raw.githubusercontent.com/arduino/arduino-cli/master/install.sh | BINDIR=$HOME/.local/bin sh
source ~/.bashrc
arduino-cli version
```

### Validar ferramentas

```bash
command -v colcon
command -v rosdep
command -v vcs
command -v arduino-cli
```

---

## 7. Pacotes ROS já necessários para o robô

```bash
sudo apt install -y \
  ros-jazzy-joy \
  ros-jazzy-teleop-twist-joy \
  ros-jazzy-twist-mux
```

### Testar joystick no Linux

```bash
jstest /dev/input/js0
```

ou

```bash
sudo evtest
```

### Testar joystick no ROS

Terminal 1:
```bash
ros2 run joy joy_node
```

Terminal 2:
```bash
ros2 topic echo /joy
```

### Teleop padrao da base

```bash
cd ~/talus-droid
source /opt/ros/jazzy/setup.bash
source ~/talus-droid/install/setup.bash
ros2 launch talus_bringup base_teleop.launch.py
```

---

## 8. Bridge serial do robô

### Porta validada
A placa apareceu como:

```text
/dev/ttyUSB0
```

### Sketch do Arduino Nano
```bash
~/talus-droid/firmware/arduino-nano/talus-mvp.ino
```

### Pacotes ROS da base
```bash
~/talus-droid/src/talus_base
~/talus-droid/src/talus_bringup
```

### Build dos pacotes da base

```bash
cd ~/talus-droid
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install --packages-select talus_base talus_bringup
source ~/talus-droid/install/setup.bash
```

### Executar bridge isolada

```bash
cd ~/talus-droid
source /opt/ros/jazzy/setup.bash
source ~/talus-droid/install/setup.bash
ros2 run talus_base talus_base_bridge
```

Fluxo validado:
- `joy_node` publicando `/joy`
- `teleop_twist_joy` convertendo `/joy` em `/cmd_vel`
- `talus_base_bridge` fazendo a ponte `/cmd_vel` ↔ serial
- Arduino Nano controlando o robô via `/dev/ttyUSB0`

---

## 9. Instalar e validar `libfreenect`

### 9.1. Confirmar Kinect conectado

Esperado no `lsusb`:
- `045e:02b0` — Xbox NUI Motor
- `045e:02ad` — Xbox NUI Audio
- `045e:02ae` — Xbox NUI Camera

### 9.2. Remover driver conflitante do kernel

```bash
sudo modprobe -r gspca_kinect gspca_main
```

### 9.3. Evitar que ele volte a carregar

```bash
echo 'blacklist gspca_kinect' | sudo tee /etc/modprobe.d/blacklist-gspca_kinect.conf
cat /etc/modprobe.d/blacklist-gspca_kinect.conf
```

### 9.4. Dependências de build do `libfreenect`

```bash
sudo apt install -y \
  git cmake build-essential pkg-config \
  libusb-1.0-0-dev libgl-dev \
  freeglut3-dev libxmu-dev libxi-dev libasound2-dev
```

### 9.5. Build do `libfreenect`

```bash
cd ~/repos/libfreenect
rm -rf build
mkdir build
cd build

cmake .. \
  -DBUILD_REDIST_PACKAGE=OFF \
  -DBUILD_AUDIO=ON \
  -DBUILD_EXAMPLES=ON \
  -DOpenGL_GL_PREFERENCE=GLVND \
  -DCMAKE_INSTALL_PREFIX=/usr/local

make -j$(nproc)
sudo make install
sudo ldconfig
```

### 9.6. Instalar regras `udev`

```bash
sudo cp ../platform/linux/udev/51-kinect.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules
sudo udevadm trigger
```

### 9.7. Validar biblioteca e binários

```bash
ldconfig -p | grep freenect
which freenect-glview freenect-micview freenect-tiltdemo
```

### 9.8. Teste fora do ROS

```bash
freenect-tiltdemo
```

Esse teste validou com sucesso:
- LED
- tilt
- acelerômetro

`freenect-glview` encontrou o dispositivo, mas pode falhar em ambiente headless com erro de display (`failed to open display ''`), o que não indica falha do Kinect.

---

## 10. Dependências ROS do Kinect

```bash
sudo apt install -y \
  ros-jazzy-cv-bridge \
  ros-jazzy-image-transport \
  ros-jazzy-image-view \
  ros-jazzy-camera-info-manager \
  ros-jazzy-camera-calibration-parsers \
  ros-jazzy-depth-image-proc
```

---

## 11. Workspace do Kinect no ROS 2

### Repositório usado
```bash
~/talus-droid/src/KinectV1-Ros2
```

### Observação importante
O upstream foi escrito para **ROS 2 Humble / Ubuntu 22.04**. Este guia documenta um **port/build validado localmente em Jazzy / Ubuntu 24.04**.

### Build limpo do workspace

```bash
cd ~/talus-droid
rm -rf build install log
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install --event-handlers console_direct+
```

### Carregar o overlay

```bash
cd ~/talus-droid
source /opt/ros/jazzy/setup.bash
source install/setup.bash
```

### Pacotes ROS expostos no ambiente validado

```bash
ros2 pkg list | grep kinect
```

Saída validada:

```text
kinect_ros2
ros2_kinect_depth
ros2_kinect_led
ros2_kinect_mic_node
ros2_kinect_rgb
ros2_kinect_tilt
```

### Executáveis ROS expostos

```bash
ros2 pkg executables | grep kinect
```

Saída validada:

```text
kinect_ros2 kinect_ros2_node
ros2_kinect_depth depth_node
ros2_kinect_led ros2_kinect_led_node
ros2_kinect_mic_node ros2_kinect_mic_node_node
ros2_kinect_rgb rgb_node
ros2_kinect_tilt ros2_kinect_tilt_node
```

---

## 12. Subir os nós ROS do Kinect

Em todo terminal:

```bash
cd ~/talus-droid
source /opt/ros/jazzy/setup.bash
source install/setup.bash
```

### LED

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

### Tilt

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

### RGB

Terminal 1:
```bash
ros2 run ros2_kinect_rgb rgb_node
```

Terminal 2:
```bash
ros2 topic info /kinect/rgb/image_raw
ros2 topic hz /kinect/rgb/image_raw
ros2 topic echo --once /kinect/rgb/camera_info
```

### Depth

Terminal 1:
```bash
ros2 run ros2_kinect_depth depth_node
```

Terminal 2:
```bash
ros2 topic info /kinect/depth/image_raw
ros2 topic hz /kinect/depth/image_raw
ros2 topic echo --once /kinect/depth/camera_info
```

### Áudio

Terminal 1:
```bash
ros2 run ros2_kinect_mic_node ros2_kinect_mic_node_node
```

---

## 13. Nó unificado (`kinect_ros2_node`)

Além dos nós modulares, o ambiente validado também expôs um executável unificado:

```bash
ros2 run kinect_ros2 kinect_ros2_node
```

### Tópicos observados com o nó unificado

```text
/camera_info
/depth/camera_info
/depth/image_raw
/image_raw
/points
/tf_static
/tilt_angle
```

### Validação observada
- `/image_raw` ~30 Hz
- `/depth/image_raw` ~30 Hz

### Testar

```bash
ros2 run kinect_ros2 kinect_ros2_node
```

Em outro terminal:

```bash
ros2 topic list
ros2 topic hz /image_raw
ros2 topic hz /depth/image_raw
```

---

## 14. Captura de depth colorido (visualização)

A imagem depth bruta em `16UC1` fica escura em visualizadores comuns. Para inspeção visual, salvar também uma versão normalizada e colorida.

A abordagem validada foi:
- manter um PNG bruto de depth
- gerar um PNG colorido normalizado para visualização
- copiar o arquivo por `scp` para o Windows

Exemplo de cópia:

```powershell
scp felip@192.168.1.19:/home/felip/kinect_depth_color.png .
```

---

## 15. Checklist mínimo restaurado

Estado considerado restaurado quando estes itens passam:

- [x] `joy_node` funcionando
- [x] bridge serial do robô funcionando
- [x] Arduino Nano respondendo em `/dev/ttyUSB0`
- [x] `libfreenect` compilado e instalado
- [x] Kinect detectado via USB
- [x] `freenect-tiltdemo` funcionando
- [x] RGB no ROS a ~30 Hz
- [x] depth no ROS a ~30 Hz
- [x] LED no ROS funcionando
- [x] tilt no ROS funcionando
- [x] nó unificado `kinect_ros2_node` publicando RGB/depth

---

## 16. Troubleshooting rápido

### `RMW implementation not installed`
Se aparecer erro sobre `rmw_cyclonedds_cpp`, instalar:

```bash
sudo apt install -y ros-jazzy-rmw-cyclonedds-cpp
```

### Conflito `Signed-By` no repositório ROS
Remover o arquivo antigo criado manualmente:

```bash
sudo rm -f /etc/apt/sources.list.d/ros2.list
sudo apt update
```

### `gspca_kinect` voltou a carregar

```bash
lsmod | grep gspca_kinect
```

Se aparecer, descarregar:

```bash
sudo modprobe -r gspca_kinect gspca_main
```

### `freenect-glview: failed to open display ''`
Ambiente sem display gráfico/X. Não indica falha do Kinect.

### `Camera calibration file ... not found`
Warning não bloqueante. Os nós continuam publicando imagem e `camera_info`, mas sem YAML customizado de calibração.

---

## 17. Próximos testes recomendados

1. subir RGB + depth simultaneamente por vários minutos
2. gravar um `ros2 bag` curto com os tópicos do Kinect
3. testar assinatura dos tópicos a partir de outro computador na LAN
4. subir Kinect junto com `ros2 launch talus_bringup base_teleop.launch.py`
5. só depois avançar para SLAM/percepção
