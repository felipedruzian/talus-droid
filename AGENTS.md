# Talus-Droid Agent Context

Contexto repo-local para agentes que atuarem neste repositorio.

## Leitura obrigatoria

Antes de mudancas relevantes, combinar:

- [README.md](/home/felip/repos/talus-droid/README.md)
- [docs/INSTALL-GUIDE.md](/home/felip/repos/talus-droid/docs/INSTALL-GUIDE.md)
- [docs/HOSTS-CONTEXT.md](/home/felip/repos/talus-droid/docs/HOSTS-CONTEXT.md)
- `/home/felip/.codex/memories/HOSTS-AND-WORKSPACES.md`

## Papel de cada arquivo

- `README.md`: apresentacao geral do projeto e do repositorio para leitura humana, inclusive no GitHub
- `docs/INSTALL-GUIDE.md`: setup, build e bring-up operacional
- `docs/HOSTS-CONTEXT.md`: fatos de hosts e runtime especificos do Talus-Droid
- memoria global em `~/.codex/memories`: contexto mais amplo, compartilhado entre repositorios e sessoes

## Escopo do projeto

Talus-Droid e a base pratica do TCC para um robo de servico/domestico com:

- Raspberry Pi como computador principal
- Arduino Nano no controle de baixo nivel
- ROS 2 Jazzy como middleware
- Kinect v1 como sensor RGB-D
- joystick USB para teleop

## Estado atual confirmado

- o stack funcional equivalente ao TCC1 ja foi restaurado
- `~/talus-droid` e o workspace oficial no `raspi`
- `~/ros2_ws` deve ser tratado como legado
- `~/talus-droid/src/KinectV1-Ros2` e checkout real do fork, nao symlink
- ROS 2 Jazzy, `rmw_cyclonedds_cpp` e `ROS_DOMAIN_ID=42` estao em uso
- joystick, bridge serial e Kinect ja foram validados no stack restaurado
- `talus_base` agora e pacote ROS 2 Python instalavel
- `talus_bringup` agora concentra o bring-up de joystick + teleop + bridge
- bridge e firmware foram realinhados para um contrato serial unico com `PING/PONG`, `DRV`, `IMU`, `ENC` opcional e `BEEP`
- os topicos comprimidos do Kinect ja foram validados pela rede
- `rqt`/`rqt_image_view` funcionaram melhor que o RViz para imagem remota
- RTAB-Map esta instalado no `raspi`, mas ainda nao teve a visualizacao consolidada no RViz2

## Cuidados atuais

### Bridge e firmware

- [serial_bridge.py](/home/felip/repos/talus-droid/src/talus_base/talus_base/serial_bridge.py) e [talus-mvp.ino](/home/felip/repos/talus-droid/firmware/arduino-nano/talus-mvp.ino) precisam permanecer alinhados ao mesmo protocolo serial
- a nova bridge empacotada e o novo firmware ainda precisam de validacao sistematica em hardware no `raspi`
- o encoder esquerdo apresentou assimetria nos testes anteriores e nao deve bloquear a validacao inicial de motores + IMU

### Kinect e rede

- o fork `KinectV1-Ros2` ja usa `image_transport`
- os transportes comprimidos foram recuperados via plugins ROS, nao via codigo customizado no fork
- o RViz nao e o cliente preferido para imagem comprimida remota; usar `rqt` para imagem e RViz para 3D, `TF` e mapa

### RTAB-Map

- o pipeline em teste deve usar topicos raw locais no `raspi`
- nao tratar `/image_raw/compressed` e `/depth/image_raw/zstd` como entrada oficial do RTAB-Map nesta fase
- houve experimento preliminar com esses transportes que gerou warnings de sincronizacao e spam de `VWDictionary.cpp::addWordRef()`

## Prioridades do momento

1. validar a nova bridge serial empacotada, o firmware do Nano e o bring-up com joystick no `raspi`
2. continuar os testes com RTAB-Map e RViz2 para chegar a testes de SLAM o quanto antes
3. revisar o fork `KinectV1-Ros2` para decidir entre no unificado e nos essenciais para SLAM
4. documentar os experimentos e as decisoes sem duplicar contexto desnecessario entre arquivos

## Fora do escopo imediato

- grandes refactors alem do necessario para estabilizar serial + Kinect + SLAM minimo
- integrar a monografia `.tex` ao repositorio antes de fechar melhor a frente tecnica atual
