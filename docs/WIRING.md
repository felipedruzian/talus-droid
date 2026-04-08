# Talus-Droid — WIRING

Fonte unica de verdade das ligacoes atuais da base.

## Arduino Nano

| Pino Nano | Sinal | Destino |
| --- | --- | --- |
| `D4` | `STBY` | driver de motores |
| `D5` | `PWMA` | driver de motores |
| `D6` | `PWMB` | driver de motores |
| `D7` | `AIN1` | driver de motores |
| `D8` | `AIN2` | driver de motores |
| `D9` | `BIN1` | driver de motores |
| `D10` | `BIN2` | driver de motores |
| `D11` | `BUZZER_PIN` | buzzer (+) |
| `D2` | `HALL_L` | encoder esquerdo |
| `D3` | `HALL_R` | encoder direito |
| `A4` | `SDA` | `MPU6050` |
| `A5` | `SCL` | `MPU6050` |
| `5V` | alimentacao | `MPU6050` / perifericos 5V compatíveis |
| `GND` | referencia | driver, buzzer, IMU, encoders |

## Observacoes

- O buzzer atual esta ligado direto em `D11` e `GND`.
- O firmware atual aplica inversao logica no motor direito para alinhar o sentido global do movimento.
- O encoder direito respondeu nos testes iniciais; o esquerdo ainda precisa de revisao fisica.
- O frame da IMU no ROS e `imu_link`.
- O frame base esperado no ROS e `base_link`.

## Kinect e Raspberry Pi

As ligacoes do Kinect ficam no lado USB/alimentacao do Raspberry Pi, nao no Nano.

- Kinect v1 conectado ao Raspberry Pi por USB + alimentacao externa/adaptador proprio.
- O bringup ROS assume `camera_link` como frame base da camera.
- A transformacao `base_link -> camera_link` fica configurada no `talus_bringup` e deve ser ajustada quando a posicao fisica final da camera estiver definida.
