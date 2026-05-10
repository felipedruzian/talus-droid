# Motor validation suspenso — 2026-05-10

## Escopo

Bateria curta para validar a base como atuador e separar o estado dos motores/encoders da frente de VO. O robo estava suspenso, com autorizacao explicita para acionar motores. A odometria propria do Arduino nao foi usada como insumo de VO, porque o sensor Hall/encoder esquerdo esta incompleto e sera investigado separadamente.

Artefatos:

- `artifacts/testlogs/2026-05-10-motor-validation/raspi-v66-suspended-forward-pulse/`
- `artifacts/testlogs/2026-05-10-motor-validation/raspi-v67-suspended-stronger-forward-debug/`
- `artifacts/testlogs/2026-05-10-motor-validation/raspi-v68-suspended-direct-serial-wheel-isolation/`

## Contexto operacional

A bridge serial conectou em `/dev/ttyUSB0 @ 115200` com firmware `talus-base-serial-0.1.0` e `IMU_OK=1`. A IMU permaneceu em torno de 50 Hz nas rodadas em que foi medida. O firmware publica `ENC <left_ticks> <right_ticks>`, mas os ticks nao devem ser tratados como odometria confiavel enquanto o Hall esquerdo estiver pendente.

O mapeamento da bridge para PWM usa `v_max=0.50` e `pwm_max=255`. Portanto comandos baixos geram PWM baixo:

- `linear.x=0.06` -> aproximadamente PWM 30;
- `linear.x=0.08` -> aproximadamente PWM 40;
- `linear.x=0.10` -> aproximadamente PWM 51;
- `linear.x=0.12` -> aproximadamente PWM 61;
- `linear.x=0.25` -> aproximadamente PWM 127.

Isso explica por que pulsos baixos, especialmente no chao, podem nao gerar movimento perceptivel mesmo com o caminho de comando funcionando.

## Resultados

| Run | Comando | Evidencia | Leitura |
|---|---|---|---|
| v66 | `/cmd_vel linear.x=0.06` suspenso | ticks antes `L=0 R=0`; depois `L=0 R=0` | comando provavelmente abaixo do deadband mecanico/driver; nao valida movimento |
| v67 | `/cmd_vel linear.x=0.25` suspenso | ticks antes `L=0 R=0`; depois `L=0 R=13` | caminho `/cmd_vel -> bridge -> Arduino -> lado direito` respondeu |
| v68 | serial direto `DRV` por canal | `left_only_pos`: delta `L=0 R=0`; `right_only_pos`: delta `L=0 R=3`; `both_pos`: delta `L=0 R=8`; `both_neg`: delta `L=0 R=4` | lado direito conta; lado esquerdo nao conta; problema do Hall/encoder esquerdo fica abaixo do ROS |

## Conclusao

A frente de motores nao bloqueia a VO RGB-D. Os motores podem ser usados como atuadores open-loop via `/cmd_vel`, mas a odometria da base nao deve ser usada nos testes atuais. A leitura correta e:

- IMU da base: usavel;
- `/cmd_vel`: caminho exercitado e confirmado pelo lado direito em v67/v68;
- encoder/Hall esquerdo: pendente, fora da prioridade imediata;
- wheel odom: incompleta, nao usada para VO.

Para validar movimento perceptivel no chao, usar pulsos mais fortes/longos do que os da primeira bateria de VO, sempre com parada explicita. Para VO, continuar ignorando `ENC` ate a manutencao do Hall esquerdo.
