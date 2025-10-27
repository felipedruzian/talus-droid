// TB6612 + 2 Halls (D2/D3) + serial @115200
// Comando: V L R\n  | Telemetria: T ticksL ticksR\n

// Pinos TB6612
const int STBY = 4;    // opcional (você ligou via 1k)
const int PWMA = 5;    // ESQ PWM
const int AIN1 = 7;
const int AIN2 = 8;
const int PWMB = 6;    // DIR PWM
const int BIN1 = 9;
const int BIN2 = 10;

// Halls
const int HALL_L = 2;  // INT0
const int HALL_R = 3;  // INT1

volatile long ticksL = 0, ticksR = 0;

int cmdL = 0, cmdR = 0;  // -255..255

void IRAM_ATTR isrL() { ticksL++; }
void IRAM_ATTR isrR() { ticksR++; }

void setup() {
  pinMode(STBY, OUTPUT);
  digitalWrite(STBY, HIGH); // habilita driver (botão E-stop puxa a GND e vence)

  pinMode(AIN1, OUTPUT); pinMode(AIN2, OUTPUT); pinMode(PWMA, OUTPUT);
  pinMode(BIN1, OUTPUT); pinMode(BIN2, OUTPUT); pinMode(PWMB, OUTPUT);

  pinMode(HALL_L, INPUT); pinMode(HALL_R, INPUT);
  attachInterrupt(digitalPinToInterrupt(HALL_L), isrL, RISING);
  attachInterrupt(digitalPinToInterrupt(HALL_R), isrR, RISING);

  Serial.begin(115200);
}

static inline void driveMotor(int pwmPin, int in1, int in2, int v) {
  bool fwd = (v >= 0);
  int d = abs(v); if (d > 255) d = 255;
  digitalWrite(in1, fwd ? HIGH : LOW);
  digitalWrite(in2, fwd ? LOW  : HIGH);
  analogWrite(pwmPin, d);
}

void loop() {
  // RX simples linha "V L R"
  if (Serial.available()) {
    String s = Serial.readStringUntil('\n');
    if (s.length() > 0 && s[0] == 'V') {
      long l, r;
      if (sscanf(s.c_str(), "V %ld %ld", &l, &r) == 2) {
        cmdL = constrain((int)l, -255, 255);
        cmdR = constrain((int)r, -255, 255);
      }
    }
  }

  driveMotor(PWMA, AIN1, AIN2, cmdL);
  driveMotor(PWMB, BIN1, BIN2, cmdR);

  static uint32_t t0 = 0;
  uint32_t now = millis();
  if (now - t0 >= 100) {
    noInterrupts();
    long tl = ticksL, tr = ticksR;
    interrupts();
    Serial.print("T "); Serial.print(tl); Serial.print(' '); Serial.println(tr);
    t0 = now;
  }
}
