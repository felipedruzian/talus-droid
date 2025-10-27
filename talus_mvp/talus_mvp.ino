// talus_mvp_move_buzzer.ino
// Move motores conforme "V L R\n" e sinaliza no buzzer/LED builtin a direção recebida.
// Buzzer no pino 11 (com 220Ω), LED builtin no pino 13, botão de buzina em D12 (para GND).

#include <Arduino.h>

const int STBY = 4;

// TB6612 - esquerda (A) / direita (B)
const int PWMA = 5;   // ESQ PWM
const int AIN1 = 7;
const int AIN2 = 8;
const int PWMB = 6;   // DIR PWM
const int BIN1 = 9;
const int BIN2 = 10;

const int BUZZ = 11;            // buzzer
const int LEDB = LED_BUILTIN;   // LED onboard
const int HORN_BTN = 12;        // botão para GND (INPUT_PULLUP)

int cmdL = 0, cmdR = 0;         // -255..255
unsigned long lastCmdMs = 0;

enum Dir { STOP=0, FWD, REV, LEFT, RIGHT };
Dir currentDir = STOP;

// --------- motor ---------
static inline void driveMotor(int pwmPin, int in1, int in2, int v) {
  bool fwd = (v >= 0);
  int d = v >= 0 ? v : -v;
  if (d > 255) d = 255;
  digitalWrite(in1, fwd ? HIGH : LOW);
  digitalWrite(in2, fwd ? LOW  : HIGH);
  analogWrite(pwmPin, d);
}

// --------- classificação da direção ---------
Dir classifyDir(int L, int R) {
  const int th = 20; // zona morta p/ direção
  if (abs(L) < th && abs(R) < th) return STOP;
  if (L > th && R > th) return FWD;
  if (L < -th && R < -th) return REV;
  // spins/curvas fortes
  if ((L >= 0 && R <= 0) || (L - R) > 60) return LEFT;
  if ((R >= 0 && L <= 0) || (R - L) > 60) return RIGHT;
  // caso contrário, usa o maior módulo
  return (L > R) ? LEFT : RIGHT;
}

// --------- buzzer/LED (não-bloqueante) ---------
// Padrões:
//  STOP: sem som, LED apagado
//  FWD : 1 beep curto a cada 500 ms (1000 Hz), LED aceso
//  REV : 2 beeps curtos (1000 Hz) com intervalo de 80 ms, ciclo ~700 ms, LED piscando
//  LEFT: 1 beep curto 1500 Hz a cada 400 ms, LED blink lento
//  RIGHT: 1 beep curto 700 Hz a cada 400 ms, LED blink lento
//  HORN (botão): 2000 Hz enquanto pressionado (override total)

struct BeepState {
  bool active = false;
  unsigned long tStart = 0;
  unsigned long tNext = 0;
  uint8_t step = 0;
} beep;

void stopTone() { noTone(BUZZ); beep.active = false; }

void updateSignal(Dir d) {
  // Horn override
  if (digitalRead(HORN_BTN) == LOW) {
    tone(BUZZ, 2000);
    digitalWrite(LEDB, (millis()/100)%2); // pisca rápido
    return;
  }

  const unsigned long now = millis();

  // LED baseline
  if (d == STOP) digitalWrite(LEDB, LOW);
  else if (d == FWD) digitalWrite(LEDB, HIGH);
  else digitalWrite(LEDB, (now/300)%2); // pisca lento para curvas/ré

  // padrão não-bloqueante
  if (!beep.active && now >= beep.tNext) {
    switch (d) {
      case STOP:
        stopTone();
        beep.tNext = now + 150; // checa logo de novo
        break;
      case FWD:
        tone(BUZZ, 1000); beep.active = true; beep.tStart = now; beep.tNext = now + 500;
        break;
      case LEFT:
        tone(BUZZ, 1500); beep.active = true; beep.tStart = now; beep.tNext = now + 400;
        break;
      case RIGHT:
        tone(BUZZ, 700);  beep.active = true; beep.tStart = now; beep.tNext = now + 400;
        break;
      case REV:
        // REV usa uma sequência de 2 beeps dentro do mesmo ciclo
        if (beep.step == 0) { tone(BUZZ, 1000); beep.active = true; beep.tStart = now; beep.step = 1; beep.tNext = now + 80; }
        else if (beep.step == 1) { stopTone(); beep.step = 2; beep.tNext = now + 80; }
        else if (beep.step == 2) { tone(BUZZ, 1000); beep.active = true; beep.tStart = now; beep.step = 3; beep.tNext = now + 80; }
        else { stopTone(); beep.step = 0; beep.tNext = now + 460; } // pausa até ~700 ms total
        break;
    }
  }

  // encerra beep curto (~40 ms) sem bloquear
  if (beep.active && (now - beep.tStart) >= 40) {
    stopTone();
  }
}

void setup() {
  pinMode(STBY, OUTPUT); digitalWrite(STBY, HIGH); // E-stop físico puxa STBY->GND

  pinMode(AIN1, OUTPUT); pinMode(AIN2, OUTPUT); pinMode(PWMA, OUTPUT);
  pinMode(BIN1, OUTPUT); pinMode(BIN2, OUTPUT); pinMode(PWMB, OUTPUT);

  pinMode(BUZZ, OUTPUT);
  pinMode(LEDB, OUTPUT);
  pinMode(HORN_BTN, INPUT_PULLUP); // botão para GND

  Serial.begin(115200);

  // sinal de boot
  tone(BUZZ, 1200); delay(80); noTone(BUZZ); delay(80); tone(BUZZ, 1600); delay(80); noTone(BUZZ);
  digitalWrite(LEDB, HIGH); delay(120); digitalWrite(LEDB, LOW);
}

void loop() {
  // lê linhas "V L R" (uma ou mais por loop)
  while (Serial.available()) {
    String s = Serial.readStringUntil('\n');
    if (s.length() && s[0] == 'V') {
      long l, r;
      if (sscanf(s.c_str(), "V %ld %ld", &l, &r) == 2) {
        if (l > 255)  l = 255; if (l < -255) l = -255;
        if (r > 255)  r = 255; if (r < -255) r = -255;
        cmdL = (int)l; cmdR = (int)r;
        lastCmdMs = millis();
      }
    }
  }

  // aplica motores
  driveMotor(PWMA, AIN1, AIN2, cmdL);
  driveMotor(PWMB, BIN1, BIN2, cmdR);

  // atualiza padrão de buzzer/LED conforme direção atual
  currentDir = classifyDir(cmdL, cmdR);
  updateSignal(currentDir);
}
