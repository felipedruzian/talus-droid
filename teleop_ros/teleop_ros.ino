#include <Wire.h>

// TB6612FNG
const uint8_t PWMA = 5;   // ESQ PWM
const uint8_t AIN1 = 7;   // ESQ dir
const uint8_t AIN2 = 8;   // ESQ dir
const uint8_t PWMB = 6;   // DIR PWM
const uint8_t BIN1 = 9;   // DIR dir
const uint8_t BIN2 = 10;  // DIR dir

// Halls (INT0=D2, INT1=D3)
const uint8_t HALL_LEFT_PIN  = 2;
const uint8_t HALL_RIGHT_PIN = 3;

volatile uint32_t left_count  = 0;
volatile uint32_t right_count = 0;

const uint8_t  MPU_ADDR = 0x68;
const float    ACCEL_SCALE = 16384.0f;   // LSB/g (±2g)
const float    G_TO_MS2    = 9.80665f;
const float    GYRO_SCALE  = 131.0f;     // LSB/(deg/s) (±250 dps)

// Tx a ~50 Hz
const uint16_t SEND_INTERVAL_MS = 20;
uint32_t lastSendMs = 0;

// Parser de linha (comando "M <L> <R>")
char cmdBuf[32];
uint8_t cmdIdx = 0;

void isr_left()  { left_count++; }
void isr_right() { right_count++; }

static inline void setMotorLeft(int16_t v) {
  if (v > 0) { digitalWrite(AIN1, HIGH); digitalWrite(AIN2, LOW);  analogWrite(PWMA,  v); }
  else if (v < 0) { digitalWrite(AIN1, LOW);  digitalWrite(AIN2, HIGH); analogWrite(PWMA, -v); }
  else { digitalWrite(AIN1, LOW); digitalWrite(AIN2, LOW); analogWrite(PWMA, 0); } // brake
}

static inline void setMotorRight(int16_t v) {
  if (v > 0) { digitalWrite(BIN1, HIGH); digitalWrite(BIN2, LOW);  analogWrite(PWMB,  v); }
  else if (v < 0) { digitalWrite(BIN1, LOW);  digitalWrite(BIN2, HIGH); analogWrite(PWMB, -v); }
  else { digitalWrite(BIN1, LOW); digitalWrite(BIN2, LOW); analogWrite(PWMB, 0); } // brake
}

static inline bool readMPU(float &ax, float &ay, float &az, float &gx, float &gy, float &gz) {
  // Pede 14 bytes a partir de 0x3B
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(0x3B);
  if (Wire.endTransmission(false) != 0) return false;

  if (Wire.requestFrom(MPU_ADDR, (uint8_t)14, (uint8_t)1) != 14) return false;

  int16_t axr = (Wire.read() << 8) | Wire.read();
  int16_t ayr = (Wire.read() << 8) | Wire.read();
  int16_t azr = (Wire.read() << 8) | Wire.read();
  (void)(Wire.read() << 8 | Wire.read()); // temp (ignorado)
  int16_t gxr = (Wire.read() << 8) | Wire.read();
  int16_t gyr = (Wire.read() << 8) | Wire.read();
  int16_t gzr = (Wire.read() << 8) | Wire.read();

  ax = (float)axr / ACCEL_SCALE * G_TO_MS2;
  ay = (float)ayr / ACCEL_SCALE * G_TO_MS2;
  az = (float)azr / ACCEL_SCALE * G_TO_MS2;

  // usa macro DEG_TO_RAD definida pelo core Arduino
  gx = ((float)gxr / GYRO_SCALE) * DEG_TO_RAD;
  gy = ((float)gyr / GYRO_SCALE) * DEG_TO_RAD;
  gz = ((float)gzr / GYRO_SCALE) * DEG_TO_RAD;

  return true;
}

static inline void processLine(char *line) {
  // Espera: "M <int> <int>"
  if (line[0] != 'M') return;
  int velL = 0, velR = 0;
  if (sscanf(line, "M %d %d", &velL, &velR) == 2) {
    if (velL > 255) velL = 255; if (velL < -255) velL = -255;
    if (velR > 255) velR = 255; if (velR < -255) velR = -255;
    setMotorLeft((int16_t)velL);
    setMotorRight((int16_t)velR);
  }
}

void setup() {
  Serial.begin(115200);

  pinMode(PWMA, OUTPUT); pinMode(AIN1, OUTPUT); pinMode(AIN2, OUTPUT);
  pinMode(PWMB, OUTPUT); pinMode(BIN1, OUTPUT); pinMode(BIN2, OUTPUT);

  pinMode(HALL_LEFT_PIN, INPUT_PULLUP);
  pinMode(HALL_RIGHT_PIN, INPUT_PULLUP);
  attachInterrupt(digitalPinToInterrupt(HALL_LEFT_PIN),  isr_left,  FALLING);
  attachInterrupt(digitalPinToInterrupt(HALL_RIGHT_PIN), isr_right, FALLING);

  Wire.begin();
  // Wake MPU6050
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(0x6B); Wire.write(0x00);
  Wire.endTransmission(true);
  delay(50);
}

void loop() {
  // --- RX comandos ---
  while (Serial.available() > 0) {
    char c = (char)Serial.read();
    if (c == '\n' || c == '\r') {
      if (cmdIdx > 0) {
        cmdBuf[cmdIdx] = '\0';
        processLine(cmdBuf);
        cmdIdx = 0;
      }
    } else {
      if (cmdIdx < sizeof(cmdBuf) - 1) cmdBuf[cmdIdx++] = c;
      else cmdIdx = 0; // overflow -> reseta
    }
  }

  // --- TX sensores a ~50 Hz ---
  uint32_t now = millis();
  if ((now - lastSendMs) >= SEND_INTERVAL_MS) {
    lastSendMs = now;

    // snapshot dos ticks
    noInterrupts();
    uint32_t l = left_count;
    uint32_t r = right_count;
    interrupts();

    float ax, ay, az, gx, gy, gz;
    if (readMPU(ax, ay, az, gx, gy, gz)) {
      // linha: "<ticksL> <ticksR> <ax> <ay> <az> <gx> <gy> <gz>\n"
      Serial.print(l); Serial.print(' ');
      Serial.print(r); Serial.print(' ');
      Serial.print(ax, 3); Serial.print(' ');
      Serial.print(ay, 3); Serial.print(' ');
      Serial.print(az, 3); Serial.print(' ');
      Serial.print(gx, 3); Serial.print(' ');
      Serial.print(gy, 3); Serial.print(' ');
      Serial.print(gz, 3); Serial.println();
    }
  }
}
