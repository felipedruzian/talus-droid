# Talus-Droid Agent Context

Contexto repo-local para agentes que atuarem neste repositorio.

## Leitura obrigatoria

Antes de mudancas relevantes, combinar:

- [README.md](/home/felip/repos/talus-droid/README.md)
- [docs/INSTALL-GUIDE.md](/home/felip/repos/talus-droid/docs/INSTALL-GUIDE.md)
- [docs/HOSTS-CONTEXT.md](/home/felip/repos/talus-droid/docs/HOSTS-CONTEXT.md)
- [docs/diagnostics/raspi-experiment-flow.md](/home/felip/repos/talus-droid/docs/diagnostics/raspi-experiment-flow.md)
- `/home/felip/.codex/memories/HOSTS-AND-WORKSPACES.md`

## Papel de cada arquivo

- `README.md`: apresentacao geral do projeto e do repositorio para leitura humana, inclusive no GitHub
- `docs/INSTALL-GUIDE.md`: setup, build e bring-up operacional
- `docs/HOSTS-CONTEXT.md`: fatos de hosts, runtime, remotos e caminhos canonicos do Talus-Droid
- `docs/diagnostics/raspi-experiment-flow.md`: padrao de run bundles e sincronizacao obrigatoria de artefatos `raspi -> talus`
- memoria global em `~/.codex/memories`: contexto mais amplo, compartilhado entre repositorios e sessoes

## Escopo do projeto

Talus-Droid e a base pratica do TCC para um robo de servico/domestico com:

- Raspberry Pi como computador principal
- Arduino Nano no controle de baixo nivel
- ROS 2 Jazzy como middleware
- Kinect v1 como sensor RGB-D
- joystick USB para teleop

## Estado atual confirmado

- repo canonico no `talus`: `/home/felip/repos/talus-droid`
- runtime oficial no `raspi`: `/home/felip/talus-droid`
- `~/ros2_ws` no `raspi` e legado; nao usar para novos testes
- `~/talus-droid/src/KinectV1-Ros2` no `raspi` e checkout real do fork, nao symlink
- ROS 2 Jazzy, `rmw_cyclonedds_cpp` e `ROS_DOMAIN_ID=42` estao em uso
- `talus_base` e pacote ROS 2 Python instalavel
- `talus_bringup` concentra bring-up de base, IMU, Kinect, teleop e SLAM/VO
- bridge e firmware foram realinhados para contrato serial unico com `PING/PONG`, `DRV`, `IMU`, `ENC` opcional e `BEEP`
- checkpoint 2026-05-10: `kinect-validation` foi encerrada como bloqueio principal apos corrigir GND incorreto entre Arduino/Raspberry Pi; hipoteses USB/libfreenect/VL805 foram rebaixadas sem nova evidencia
- RGB-D simultaneo, TF estatico da camera/IMU e VO curta no chao foram destravados; v73 validou `/rtabmap/odom` e `odom -> base_link` com `approx_sync_max_interval:=0.05`
- Hall/encoder esquerdo esta incompleto; `ENC`/wheel odom nao deve alimentar VO ate manutencao posterior
- motores podem ser usados como atuadores open-loop via `/cmd_vel`; IMU esta usavel
- `rqt`/`rqt_image_view` funcionam melhor que RViz para imagem remota; RViz/Foxglove/PlotJuggler devem rodar no notebook/`aiquitude` quando necessarios

## Cuidados atuais

### Bridge e firmware

- [serial_bridge.py](/home/felip/repos/talus-droid/src/talus_base/talus_base/serial_bridge.py) e [arduino-nano.ino](/home/felip/repos/talus-droid/firmware/arduino-nano/arduino-nano.ino) precisam permanecer alinhados ao mesmo protocolo serial
- manter `serial_bridge.py` e firmware alinhados antes de qualquer teste de motor
- `ENC` e wheel odom estao incompletos por causa do Hall/encoder esquerdo; nao usar como fonte de odometria em VO/RTAB-Map por enquanto

### Kinect, VO e rede

- `kinect-validation` esta fechada como bloqueio principal; nova falha RGB-D deve ser tratada como regressao/nova hipotese com run bundle proprio
- o fork `KinectV1-Ros2` ja usa `image_transport`
- os transportes comprimidos foram recuperados via plugins ROS, nao via codigo customizado no fork
- o RViz nao e o cliente preferido para imagem comprimida remota; usar `rqt` para imagem e RViz para 3D, `TF` e mapa
- para VO/RTAB-Map no chao, usar topicos raw locais no `raspi` e considerar `approx_sync_max_interval:=0.05` como baseline inicial a confirmar

### RTAB-Map

- o pipeline em teste deve usar topicos raw locais no `raspi`: `/image_raw`, `/depth/image_raw`, `/camera_info`, `/imu/data`
- nao tratar `/image_raw/compressed` e `/depth/image_raw/zstd` como entrada oficial do RTAB-Map nesta fase
- houve experimento preliminar com esses transportes que gerou warnings de sincronizacao e spam de `VWDictionary.cpp::addWordRef()`
- proxima frente deve consolidar continuidade de `/rtabmap/odom`, `odom -> base_link`, `map -> odom` e `map -> base_link`

## Prioridades do momento

1. consolidar VO/RTAB-Map no chao com `approx_sync_max_interval:=0.05` e monitor continuo de TF/odom
2. validar movimento perceptivel por `/cmd_vel` open-loop com pulsos mais fortes/longos e parada explicita
3. manter wheel odom fora do pipeline ate corrigir Hall/encoder esquerdo
4. sincronizar artefatos `raspi -> talus` com `rsync` ao fim de toda rodada e verificar com `rsync -ani --delete`
5. documentar apenas conclusoes duraveis, evitando duplicar logs brutos nos relatorios


## Artefatos, remotos e worktrees

- `artifacts/` e ignorado pelo Git; artefatos brutos nascem no `raspi` e precisam ser sincronizados para o `talus` antes de qualquer analise/relatorio/commit.
- Padrao de sync: `rsync -a raspi:/home/felip/talus-droid/artifacts/testlogs/<frente>/ /home/felip/repos/talus-droid/artifacts/testlogs/<frente>/`.
- Verificacao obrigatoria: `rsync -ani --delete raspi:/home/felip/talus-droid/artifacts/testlogs/<frente>/ /home/felip/repos/talus-droid/artifacts/testlogs/<frente>/` deve sair vazia.
- `origin` canonico: `git@github.com:felipedruzian/talus-droid.git`.
- O `raspi` deve ser mantido em fast-forward a partir do remoto; evitar commits locais nele salvo emergencia operacional.
- Worktrees isoladas devem ficar no `talus` em `/home/felip/repos/_worktrees/talus-droid/<slug>`; nao criar worktrees permanentes no runtime do `raspi`.
- `.opencode/`, caches e artefatos locais de agentes/harnesses nao devem ser commitados.

## TCC / Trello

- Fonte da verdade para tarefas do TCC2: Trello board `TCC2`.
- Contexto operacional versionado: `/home/felip/repos/TCC-KANBAN.md`.
- Edicoes vivas de cards devem usar o MCP `trello` no OpenCode com apoio da skill `trello-tcc`.
- `/trello-sync` apenas exporta cache read-only para `/home/felip/syncthing/vault/Facul/TCC/TCC2-Kanban.md`; nao edite esse cache como fonte primaria.
- Novas pendencias de teste/monografia encontradas neste repo devem virar cards Trello quando forem relevantes para planejamento.

## Skills e agentes

- Para contexto TCC/Talus-Droid, usar a skill/subagente `tcc-context` antes de planejar frentes grandes.
- Para Trello, usar a skill `trello-tcc`; nao editar o cache Obsidian como fonte primaria.
- Para debugging de falhas de VO/Kinect/base, seguir investigacao por evidencia e manter run bundles sincronizados.
- Ao terminar testes ou trocar branch/worktree, registrar estado Git e sincronizar artefatos antes de concluir.

## Fora do escopo imediato

- grandes refactors alem do necessario para estabilizar serial + Kinect + SLAM minimo
- integrar a monografia `.tex` ao repositorio antes de fechar melhor a frente tecnica atual
