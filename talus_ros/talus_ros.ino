// talus_nano_imu_enc.ino — Arduino Nano (ATmega328p)
// Comunicação: 115200 8N1
// Protocolo ROS2-ready com confirmações

#include <Arduino.h>
#include <Wire.h>

// ====== PINAGEM ======
const uint8_t PWMA = 5, AIN1 = 7, AIN2 = 8;   // Motor ESQ
const uint8_t PWMB = 6, BIN1 = 9, BIN2 = 10;  // Motor DIR
const uint8_t HALL_L = 2;  // INT0
const uint8_t HALL_R = 3;  // INT1
const uint8_t BUZZ = 11;

// ====== ENCODERS ======
volatile long ticksL = 0, ticksR = 0;
volatile unsigned long lastEdgeL = 0, lastEdgeR = 0;
const unsigned long DEBOUNCE_US = 500; // 0.5ms

void isrL() {
  unsigned long now = micros();
  if (now - lastEdgeL > DEBOUNCE_US) { 
    ticksL++; 
    lastEdgeL = now; 
  }
}

void isrR() {
  unsigned long now = micros();
  if (now - lastEdgeR > DEBOUNCE_US) { 
    ticksR++; 
    lastEdgeR = now; 
  }
}

// ====== IMU (MPU-6050) ======
#define MPU_ADDR 0x68

bool mpuWrite(uint8_t reg, uint8_t val) {
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(reg);
  Wire.write(val);
  return (Wire.endTransmission() == 0);
}

bool mpuReadN(uint8_t start, uint8_t *buf, uint8_t n) {
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(start);
  if (Wire.endTransmission(false) != 0) return false;

  uint8_t got = Wire.requestFrom((uint8_t)MPU_ADDR, (uint8_t)n, (uint8_t)true);
  if (got < n) return false;

  for (uint8_t i = 0; i < n && Wire.available(); i++) {
    buf[i] = Wire.read();
  }
  return true;
}

bool mpuInit() {
  Wire.begin();
  delay(50);

  if (!mpuWrite(0x6B, 0x00)) return false; // Acordar
  delay(10);

  uint8_t who = 0;
  if (!mpuReadN(0x75, &who, 1)) return false;
  if (who != 0x68 && who != 0x69) return false;

  mpuWrite(0x1C, 0x00); // Accel ±2g
  mpuWrite(0x1B, 0x00); // Gyro ±250°/s
  mpuWrite(0x1A, 0x03); // DLPF ~44Hz
  return true;
}

bool mpuRead(float &ax, float &ay, float &az, float &gx, float &gy, float &gz) {
  uint8_t b[14];
  if (!mpuReadN(0x3B, b, 14)) return false;

  int16_t rawAx = (int16_t)((b[0] << 8) | b[1]);
  int16_t rawAy = (int16_t)((b[2] << 8) | b[3]);
  int16_t rawAz = (int16_t)((b[4] << 8) | b[5]);
  int16_t rawGx = (int16_t)((b[8] << 8) | b[9]);
  int16_t rawGy = (int16_t)((b[10] << 8) | b[11]);
  int16_t rawGz = (int16_t)((b[12] << 8) | b[13]);

  ax = rawAx / 16384.0f;
  ay = rawAy / 16384.0f;
  az = rawAz / 16384.0f;
  
  const float DPS2RADS = 0.01745329252f;
  gx = (rawGx / 131.0f) * DPS2RADS;
  gy = (rawGy / 131.0f) * DPS2RADS;
  gz = (rawGz / 131.0f) * DPS2RADS;
  return true;
}

bool IMU_OK = false;

// ====== MOTORES ======
static inline void driveMotor(uint8_t pwmPin, uint8_t in1, uint8_t in2, int v) {
  bool fwd = (v >= 0);
  int d = abs(v);
  if (d > 255) d = 255;
  
  digitalWrite(in1, fwd ? HIGH : LOW);
  digitalWrite(in2, fwd ? LOW : HIGH);
  analogWrite(pwmPin, d);
}

int cmdL = 0, cmdR = 0;
bool horn = false;
unsigned long lastCmdTime = 0;
const unsigned long CMD_TIMEOUT = 500; // 500ms watchdog

// ====== PARSER SERIAL ======
char line[64];
uint8_t li = 0;

void resetLine() { 
  li = 0; 
  line[0] = '\0'; 
}

void handleLine() {
  while (li > 0 && (line[li-1] == '\r' || line[li-1] == '\n')) {
    line[--li] = 0;
  }
  if (li == 0) return;

  // "V <L> <R>"
  if (line[0] == 'V') {
    long L = 0, R = 0;
    if (sscanf(line, "V %ld %ld", &L, &R) == 2) {
      cmdL = constrain((int)L, -255, 255);
      cmdR = constrain((int)R, -255, 255);
      lastCmdTime = millis();
      // Serial.print(F("OK V ")); Serial.print(cmdL); Serial.print(' '); Serial.println(cmdR);
    }
  }
  // "H <0|1>"
  else if (line[0] == 'H') {
    int h = 0;
    if (sscanf(line, "H %d", &h) == 1) {
      horn = (h != 0);
    }
  }
  // "RST"
  else if (line[0] == 'R' && line[1] == 'S' && line[2] == 'T') {
    noInterrupts();
    ticksL = 0;
    ticksR = 0;
    interrupts();
    Serial.println(F("OK RST"));
  }

  resetLine();
}

// ====== SETUP/LOOP ======
unsigned long tIMU = 0, tENC = 0;

void setup() {
  pinMode(AIN1, OUTPUT); pinMode(AIN2, OUTPUT); pinMode(PWMA, OUTPUT);
  pinMode(BIN1, OUTPUT); pinMode(BIN2, OUTPUT); pinMode(PWMB, OUTPUT);
  pinMode(BUZZ, OUTPUT);

  pinMode(HALL_L, INPUT_PULLUP);
  pinMode(HALL_R, INPUT_PULLUP);
  attachInterrupt(digitalPinToInterrupt(HALL_L), isrL, RISING);
  attachInterrupt(digitalPinToInterrupt(HALL_R), isrR, RISING);

  Serial.begin(115200);
  while (!Serial && millis() < 3000); // Aguarda até 3s
  
  Wire.begin();
  IMU_OK = mpuInit();

  // Bip de boot
  tone(BUZZ, 1200); delay(90); noTone(BUZZ); 
  delay(90); 
  tone(BUZZ, 1700); delay(90); noTone(BUZZ);

  Serial.print(F("VER talus_nano_imu_enc 1.1 IMU_OK="));
  Serial.println(IMU_OK ? F("1") : F("0"));
  
  lastCmdTime = millis();
}

void loop() {
  unsigned long now = millis();

  // ===== RX Serial =====
  while (Serial.available()) {
    char c = Serial.read();
    if (c == '\n') {
      line[li] = 0;
      handleLine();
    } else if (li < sizeof(line) - 1) {
      line[li++] = c;
    }
  }

  // ===== Watchdog - para motores se não receber comando =====
  if (now - lastCmdTime > CMD_TIMEOUT) {
    cmdL = 0;
    cmdR = 0;
  }

  // ===== Controle Motores =====
  driveMotor(PWMA, AIN1, AIN2, cmdL);
  driveMotor(PWMB, BIN1, BIN2, cmdR);
  
  // ===== Buzina =====
  if (horn) {
    tone(BUZZ, 2000);
  } else {
    noTone(BUZZ);
  }

  // ===== Publicação IMU (~50 Hz) =====
  if (now - tIMU >= 20) {
    float ax = 0, ay = 0, az = 0, gx = 0, gy = 0, gz = 0;
    if (IMU_OK) {
      mpuRead(ax, ay, az, gx, gy, gz);
    }
    
    Serial.print(F("IMU "));
    Serial.print(ax, 3); Serial.print(' ');
    Serial.print(ay, 3); Serial.print(' ');
    Serial.print(az, 3); Serial.print(' ');
    Serial.print(gx, 3); Serial.print(' ');
    Serial.print(gy, 3); Serial.print(' ');
    Serial.println(gz, 3);
    tIMU = now;
  }

  // ===== Publicação ENC (~20 Hz) =====
  if (now - tENC >= 50) {
    noInterrupts();
    long l = ticksL, r = ticksR;
    interrupts();
    
    Serial.print(F("ENC "));
    Serial.print(l); Serial.print(' ');
    Serial.println(r);
    tENC = now;
  }
}
