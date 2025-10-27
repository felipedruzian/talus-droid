// motor_test_cycle.ino
// Teste simples dos 2 motores com TB6612: frente, ré, giro à esquerda, giro à direita.
// Pinos conforme você montou.

const int STBY = 4;

const int PWMA = 5;   // Motor ESQ (canal A) - PWM
const int AIN1 = 7;
const int AIN2 = 8;

const int PWMB = 6;   // Motor DIR (canal B) - PWM
const int BIN1 = 9;
const int BIN2 = 10;

// Intensidade básica (0..255)
const int POWER = 160;

// Durações (ms)
const unsigned long T_STEP = 2000;  // tempo rodando em cada passo
const unsigned long T_PAUSE = 500;  // pausa entre passos

static inline void driveMotor(int pwmPin, int in1, int in2, int val) {
  // val: -255..255 (sinal = direção; módulo = velocidade)
  bool fwd = (val >= 0);
  int d = val >= 0 ? val : -val;
  if (d > 255) d = 255;
  digitalWrite(in1, fwd ? HIGH : LOW);
  digitalWrite(in2, fwd ? LOW  : HIGH);
  analogWrite(pwmPin, d);
}

void motorsStop() {
  analogWrite(PWMA, 0);
  analogWrite(PWMB, 0);
  // opcional: frenagem (curto) — aqui deixamos flutuar (coast)
}

void setup() {
  pinMode(STBY, OUTPUT);
  digitalWrite(STBY, HIGH); // habilita o driver (E-stop físico derruba este pino para GND)

  pinMode(AIN1, OUTPUT);
  pinMode(AIN2, OUTPUT);
  pinMode(PWMA, OUTPUT);

  pinMode(BIN1, OUTPUT);
  pinMode(BIN2, OUTPUT);
  pinMode(PWMB, OUTPUT);

  motorsStop();
  delay(500);
}

void loop() {
  // 1) Ambos pra FRENTE
  driveMotor(PWMA, AIN1, AIN2,  POWER);
  driveMotor(PWMB, BIN1, BIN2,  POWER);
  delay(T_STEP);
  motorsStop();
  delay(T_PAUSE);

  // 2) Ambos pra RÉ
  driveMotor(PWMA, AIN1, AIN2, -POWER);
  driveMotor(PWMB, BIN1, BIN2, -POWER);
  delay(T_STEP);
  motorsStop();
  delay(T_PAUSE);

  // 3) Giro à ESQUERDA (esq. ré, dir. frente)
  driveMotor(PWMA, AIN1, AIN2, -POWER);
  driveMotor(PWMB, BIN1, BIN2,  POWER);
  delay(T_STEP);
  motorsStop();
  delay(T_PAUSE);

  // 4) Giro à DIREITA (esq. frente, dir. ré)
  driveMotor(PWMA, AIN1, AIN2,  POWER);
  driveMotor(PWMB, BIN1, BIN2, -POWER);
  delay(T_STEP);
  motorsStop();
  delay(T_PAUSE);
}
