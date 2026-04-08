// Talus Arduino base controller
// Protocol:
//   PING
//   DRV <left_pwm> <right_pwm>
//   HORN <0|1>
//   BEEP <pattern_id>
// Replies:
//   PONG <fw_version> IMU_OK=<0|1>
//   IMU <ax> <ay> <az> <gx> <gy> <gz>
//   ENC <left_ticks> <right_ticks>
//   ERR <code> <detail>

#include <Wire.h>

const char FW_VERSION[] = "talus-base-serial-0.1.0";

const int STBY = 4;
const int PWMA = 5;
const int AIN1 = 7;
const int AIN2 = 8;
const int PWMB = 6;
const int BIN1 = 9;
const int BIN2 = 10;
const int BUZZER_PIN = 11;

const int HALL_L = 2;
const int HALL_R = 3;

const uint8_t MPU6050_ADDR = 0x68;
const uint8_t MPU6050_WHO_AM_I = 0x75;
const uint8_t MPU6050_PWR_MGMT_1 = 0x6B;
const uint8_t MPU6050_ACCEL_CONFIG = 0x1C;
const uint8_t MPU6050_GYRO_CONFIG = 0x1B;
const uint8_t MPU6050_ACCEL_XOUT_H = 0x3B;

const unsigned long CMD_TIMEOUT_MS = 250;
const unsigned long IMU_PERIOD_MS = 20;
const unsigned long ENCODER_PERIOD_MS = 50;
const size_t RX_BUFFER_SIZE = 96;
const bool BEEP_ON_DRIVE_TIMEOUT = false;

const unsigned int STATUS_BEEP_FREQ_HZ = 2400;
const unsigned int HORN_FREQ_HZ = 1800;
const unsigned long SHORT_BEEP_MS = 80;
const unsigned long LONG_BEEP_MS = 400;
const unsigned long BEEP_GAP_MS = 90;

volatile long ticksL = 0;
volatile long ticksR = 0;

int cmdL = 0;
int cmdR = 0;
bool hornEnabled = false;
bool imuAvailable = false;
bool driveTimedOut = true;

char rxBuffer[RX_BUFFER_SIZE];
size_t rxLen = 0;
unsigned long lastCmdMs = 0;
unsigned long lastImuMs = 0;
unsigned long lastEncoderMs = 0;
unsigned long lastImuErrorMs = 0;

bool beepActive = false;
bool beepToneOn = false;
bool hornToneActive = false;
uint8_t beepRemaining = 0;
unsigned long beepPhaseStartMs = 0;
unsigned long beepOnMs = 0;
unsigned long beepOffMs = 0;
unsigned int beepFrequencyHz = STATUS_BEEP_FREQ_HZ;

struct ImuSample {
  float ax;
  float ay;
  float az;
  float gx;
  float gy;
  float gz;
};

void isrL() { ticksL++; }
void isrR() { ticksR++; }

static inline void driveMotor(int pwmPin, int in1, int in2, int value) {
  if (value == 0) {
    digitalWrite(in1, LOW);
    digitalWrite(in2, LOW);
    analogWrite(pwmPin, 0);
    return;
  }

  bool forward = (value >= 0);
  int duty = abs(value);
  if (duty > 255) {
    duty = 255;
  }

  digitalWrite(in1, forward ? HIGH : LOW);
  digitalWrite(in2, forward ? LOW : HIGH);
  analogWrite(pwmPin, duty);
}

void stopBase() {
  cmdL = 0;
  cmdR = 0;
  hornEnabled = false;
}

void emitError(const char *code, const char *detail) {
  Serial.print("ERR ");
  Serial.print(code);
  if (detail != nullptr && detail[0] != '\0') {
    Serial.print(' ');
    Serial.print(detail);
  }
  Serial.println();
}

void emitPong() {
  Serial.print("PONG ");
  Serial.print(FW_VERSION);
  Serial.print(" IMU_OK=");
  Serial.println(imuAvailable ? 1 : 0);
}

void triggerBeepPattern(uint8_t patternId) {
  unsigned long onMs = 0;
  unsigned long offMs = BEEP_GAP_MS;
  uint8_t count = 0;

  switch (patternId) {
    case 1:
      count = 1;
      onMs = SHORT_BEEP_MS;
      break;
    case 2:
      count = 2;
      onMs = SHORT_BEEP_MS;
      break;
    case 3:
      count = 3;
      onMs = SHORT_BEEP_MS;
      break;
    case 4:
      count = 1;
      onMs = LONG_BEEP_MS;
      break;
    default:
      return;
  }

  beepActive = true;
  beepToneOn = true;
  hornToneActive = false;
  beepRemaining = count;
  beepOnMs = onMs;
  beepOffMs = offMs;
  beepFrequencyHz = STATUS_BEEP_FREQ_HZ;
  beepPhaseStartMs = millis();
  tone(BUZZER_PIN, beepFrequencyHz);
}

void updateBuzzer() {
  unsigned long now = millis();

  if (beepActive) {
    if (beepToneOn) {
      if (now - beepPhaseStartMs >= beepOnMs) {
        noTone(BUZZER_PIN);
        beepToneOn = false;
        beepPhaseStartMs = now;
      }
    } else if (now - beepPhaseStartMs >= beepOffMs) {
      if (beepRemaining > 0) {
        beepRemaining--;
      }

      if (beepRemaining == 0) {
        beepActive = false;
      } else {
        beepToneOn = true;
        beepPhaseStartMs = now;
        tone(BUZZER_PIN, beepFrequencyHz);
      }
    }
    return;
  }

  if (hornEnabled) {
    if (!hornToneActive) {
      tone(BUZZER_PIN, HORN_FREQ_HZ);
      hornToneActive = true;
    }
  } else if (hornToneActive) {
    noTone(BUZZER_PIN);
    hornToneActive = false;
  }
}

bool imuWriteByte(uint8_t reg, uint8_t value) {
  Wire.beginTransmission(MPU6050_ADDR);
  Wire.write(reg);
  Wire.write(value);
  return Wire.endTransmission(true) == 0;
}

bool imuReadBytes(uint8_t reg, uint8_t *buffer, size_t length) {
  Wire.beginTransmission(MPU6050_ADDR);
  Wire.write(reg);
  if (Wire.endTransmission(false) != 0) {
    return false;
  }

  size_t readLen = Wire.requestFrom(MPU6050_ADDR, (uint8_t)length, (uint8_t)true);
  if (readLen != length) {
    return false;
  }

  for (size_t i = 0; i < length; ++i) {
    buffer[i] = Wire.read();
  }
  return true;
}

bool initImu() {
  uint8_t whoAmI = 0;

  Wire.begin();
  Wire.setClock(400000);
  delay(50);

  if (!imuWriteByte(MPU6050_PWR_MGMT_1, 0x00)) {
    return false;
  }
  delay(100);

  if (!imuReadBytes(MPU6050_WHO_AM_I, &whoAmI, 1)) {
    return false;
  }
  if (whoAmI != MPU6050_ADDR) {
    return false;
  }

  if (!imuWriteByte(MPU6050_ACCEL_CONFIG, 0x00)) {
    return false;
  }
  if (!imuWriteByte(MPU6050_GYRO_CONFIG, 0x00)) {
    return false;
  }

  return true;
}

bool readImu(ImuSample &sample) {
  uint8_t buffer[14];
  if (!imuReadBytes(MPU6050_ACCEL_XOUT_H, buffer, sizeof(buffer))) {
    return false;
  }

  int16_t rawAx = (buffer[0] << 8) | buffer[1];
  int16_t rawAy = (buffer[2] << 8) | buffer[3];
  int16_t rawAz = (buffer[4] << 8) | buffer[5];
  int16_t rawGx = (buffer[8] << 8) | buffer[9];
  int16_t rawGy = (buffer[10] << 8) | buffer[11];
  int16_t rawGz = (buffer[12] << 8) | buffer[13];

  const float accelScale = 9.80665f / 16384.0f;
  const float gyroScale = 0.01745329252f / 131.0f;

  sample.ax = rawAx * accelScale;
  sample.ay = rawAy * accelScale;
  sample.az = rawAz * accelScale;
  sample.gx = rawGx * gyroScale;
  sample.gy = rawGy * gyroScale;
  sample.gz = rawGz * gyroScale;

  return true;
}

void emitImu() {
  if (!imuAvailable) {
    return;
  }

  ImuSample sample;
  if (!readImu(sample)) {
    unsigned long now = millis();
    if (now - lastImuErrorMs >= 1000) {
      emitError("IMU_READ", "failed");
      lastImuErrorMs = now;
    }
    return;
  }

  Serial.print("IMU ");
  Serial.print(sample.ax, 5);
  Serial.print(' ');
  Serial.print(sample.ay, 5);
  Serial.print(' ');
  Serial.print(sample.az, 5);
  Serial.print(' ');
  Serial.print(sample.gx, 5);
  Serial.print(' ');
  Serial.print(sample.gy, 5);
  Serial.print(' ');
  Serial.println(sample.gz, 5);
}

void emitEncoder() {
  long leftTicks = 0;
  long rightTicks = 0;

  noInterrupts();
  leftTicks = ticksL;
  rightTicks = ticksR;
  interrupts();

  Serial.print("ENC ");
  Serial.print(leftTicks);
  Serial.print(' ');
  Serial.println(rightTicks);
}

void applyLine(const char *line) {
  long left = 0;
  long right = 0;
  long value = 0;

  if (strcmp(line, "PING") == 0) {
    emitPong();
    return;
  }

  if (sscanf(line, "DRV %ld %ld", &left, &right) == 2) {
    cmdL = constrain((int)left, -255, 255);
    cmdR = constrain((int)right, -255, 255);
    lastCmdMs = millis();
    driveTimedOut = false;
    return;
  }

  if (sscanf(line, "HORN %ld", &value) == 1) {
    hornEnabled = (value != 0);
    return;
  }

  if (sscanf(line, "BEEP %ld", &value) == 1) {
    triggerBeepPattern((uint8_t)value);
    return;
  }

  emitError("BAD_CMD", line);
}

void readSerial() {
  while (Serial.available() > 0) {
    char c = (char)Serial.read();

    if (c == '\r') {
      continue;
    }

    if (c == '\n') {
      rxBuffer[rxLen] = '\0';
      if (rxLen > 0) {
        applyLine(rxBuffer);
      }
      rxLen = 0;
      continue;
    }

    if (rxLen < RX_BUFFER_SIZE - 1) {
      rxBuffer[rxLen++] = c;
    } else {
      rxLen = 0;
      emitError("RX_OVERFLOW", "");
    }
  }
}

void setup() {
  pinMode(STBY, OUTPUT);
  digitalWrite(STBY, HIGH);

  pinMode(AIN1, OUTPUT);
  pinMode(AIN2, OUTPUT);
  pinMode(PWMA, OUTPUT);
  pinMode(BIN1, OUTPUT);
  pinMode(BIN2, OUTPUT);
  pinMode(PWMB, OUTPUT);

  pinMode(BUZZER_PIN, OUTPUT);
  noTone(BUZZER_PIN);

  pinMode(HALL_L, INPUT);
  pinMode(HALL_R, INPUT);
  attachInterrupt(digitalPinToInterrupt(HALL_L), isrL, RISING);
  attachInterrupt(digitalPinToInterrupt(HALL_R), isrR, RISING);

  Serial.begin(115200);
  lastCmdMs = millis();
  lastImuMs = millis();
  lastEncoderMs = millis();

  imuAvailable = initImu();
  if (!imuAvailable) {
    triggerBeepPattern(2);
    emitError("IMU_INIT", "failed");
  }

  emitPong();
}

void loop() {
  unsigned long now = millis();

  readSerial();

  if (!driveTimedOut && (now - lastCmdMs > CMD_TIMEOUT_MS)) {
    stopBase();
    driveTimedOut = true;
    if (BEEP_ON_DRIVE_TIMEOUT) {
      triggerBeepPattern(4);
    }
  }

  driveMotor(PWMA, AIN1, AIN2, cmdL);
  driveMotor(PWMB, BIN1, BIN2, cmdR);

  if (imuAvailable && (now - lastImuMs >= IMU_PERIOD_MS)) {
    emitImu();
    lastImuMs = now;
  }

  if (now - lastEncoderMs >= ENCODER_PERIOD_MS) {
    emitEncoder();
    lastEncoderMs = now;
  }

  updateBuzzer();
}
