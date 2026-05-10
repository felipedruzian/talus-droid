# VO/TF no chao — 2026-05-10

## Escopo

Baterias no chao apos destravar RGB-D simultaneo do Kinect no ROS. O objetivo foi validar RGB-D + IMU + TF + `rgbd_odometry` usando motores apenas como atuadores open-loop. A odometria de rodas/Arduino nao foi usada, pois o Hall/encoder esquerdo esta incompleto.

Artefatos:

- `artifacts/testlogs/2026-05-10-vo-floor-validation/raspi-v69-floor-rgbd-imu-tf-gate/`
- `artifacts/testlogs/2026-05-10-vo-floor-validation/raspi-v70-floor-vo-baseline-stationary/`
- `artifacts/testlogs/2026-05-10-vo-floor-validation/raspi-v71-floor-open-loop-short-forward/`
- `artifacts/testlogs/2026-05-10-vo-floor-validation/raspi-v72-floor-open-loop-arc-rclpy/`
- `artifacts/testlogs/2026-05-10-vo-floor-validation/raspi-v73-floor-sync005-conditional-forward/`
- `artifacts/testlogs/2026-05-10-vo-floor-validation/raspi-v74-floor-slam-tf-recheck/`

## Resultado consolidado

A validacao principal passou em janela curta/controlada: com `approx_sync_max_interval:=0.05`, o `rgbd_odometry` publicou odometria valida no chao e o TF `odom -> base_link` foi confirmado. A cadeia RGB-D/IMU/TF esta desbloqueada para proximas baterias maiores.

O movimento por motor nao foi validado visualmente como deslocamento perceptivel nesta rodada. Os comandos no chao foram conservadores (`linear.x` baixo e duracao curta), e podem ter ficado perto do deadband/friccao estatica. Portanto, estes testes validam melhor VO/TF do que locomocao.

## v69 — gate RGB-D + IMU + TF

Entradas principais passaram:

| Topico/TF | Evidencia |
|---|---|
| `/image_raw` | aproximadamente 29.2–30.2 Hz |
| `/depth/image_raw` | aproximadamente 28.7–30.0 Hz |
| `/imu/data` | aproximadamente 50 Hz |
| `/camera_info` | `frame_id: kinect_rgb_optical_frame` |
| `base_link -> kinect_rgb_optical_frame` | transform presente |
| `base_link -> kinect_depth_optical_frame` | transform presente |
| `base_link -> imu_link` | transform presente |

Os primeiros avisos de `tf2_echo` sobre frame inexistente ocorreram antes de a arvore TF chegar ao processo de echo; em seguida as transforms foram impressas e consideradas presentes.

## v70 — VO baseline parado

Com a configuracao padrao do launch (`approx_sync_max_interval=0.01`), o `rgbd_odometry` chegou a publicar odometria valida, com qualidades como `70`, `68`, `80` e `89`. Depois voltou a alternar para `quality=0`, `Registration failed: Not enough inliers` e avisos de dados/sincronizacao.

Leitura: RGB-D/IMU/TF eram suficientes para iniciar VO, mas a configuracao padrao estava apertada para os atrasos/jitter reais do pipeline.

## v71 — pulso curto via CLI

Rodada inconclusiva. O arquivo de pulso ficou vazio e nao ha evidencia confiavel de que o comando de movimento tenha sido publicado como planejado. Nao usar v71 como validacao de motor nem de VO.

## v72 — arco open-loop com monitor rclpy

O comando rclpy foi iniciado, mas o monitor Python falhou ao ler a covariancia (`ValueError` por tratar array como booleano). O log do RTAB-Map ficou majoritariamente em `Registration failed` e `Odom: quality=0`. Esta rodada nao valida VO estavel.

## v73 — VO valida com sync relaxado

Mudanca aplicada:

```text
approx_sync_max_interval:=0.05
```

O monitor rclpy registrou odometria valida antes e depois do pulso open-loop:

```text
before_count=14 before_valid=14
odom_count=42 valid_count=42
```

A posicao estimada mudou durante a janela:

```text
inicio: x=0.0090, y=0.0021
fim:    x=0.0168, y=0.0170
```

A covariancia permaneceu baixa, nao `9999`, por exemplo:

```text
cov0 final ~= 1.4e-05
```

O recheck posterior confirmou TF dinamico `odom -> base_link`:

```text
Translation: [0.018, 0.024, -0.002]
Rotation valida
```

Leitura: esta e a primeira evidencia forte de VO RGB-D no chao com IMU e motores apenas como atuador open-loop. A correcao de sync foi determinante.

## v74 — checagem SLAM/TF global

`map -> odom` apareceu e ficou estavel perto de identidade:

```text
Translation: [0.000, 0.000, -0.000]
Rotation proxima de identidade
```

`map -> base_link` direto nao foi capturado de forma robusta na janela do `tf2_echo`. Como `odom -> base_link` foi confirmado separadamente em v73 e `map -> odom` em v74, a arvore completa provavelmente esta proxima de funcionar, mas ainda precisa de uma bateria dedicada com monitor continuo de TF.

## Conclusao e proximos passos

A frente VO esta desbloqueada para testes maiores. O proximo passo nao e investigar wheel odom; e consolidar VO/TF com:

1. repetir v73 com `approx_sync_max_interval:=0.05` por janela maior;
2. monitorar continuamente `/rtabmap/odom`, `odom -> base_link`, `map -> odom` e `map -> base_link`;
3. usar comando de motor um pouco mais forte/mais longo se o objetivo incluir deslocamento perceptivel, sempre com parada explicita;
4. manter `ENC` fora do pipeline de VO ate resolver o Hall esquerdo.
