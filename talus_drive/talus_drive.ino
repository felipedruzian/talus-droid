// talus_mvp_move_buzzer_ctrl.ino
// Move motores conforme "V L R" e aciona buzina (pino 11) conforme "H 0/1" vindo do controle.
// Mantém bipes de direção; "H 1" tem prioridade (buzina contínua).

#include <Arduino.h>

const int STBY = 4;

// TB6612
const int PWMA = 5;   // ESQ PWM
const int AIN1 = 7;
const int AIN2 = 8;
const int PWMB = 6;   // DIR PWM
const int BIN1 = 9;
const int BIN2 = 10;

// Sinalização
const int BUZZ = 11;            // buzzer em 11 (com 220R)
const int LEDB = LED_BUILTIN;

int cmdL = 0, cmdR = 0;         // -255..255
bool horn_active = false;

enum Dir { STOP=0, FWD, REV, LEFT, RIGHT };
Dir currentDir = STOP;

static inline void driveMotor(int pwmPin, int in1, int in2, int v) {
  bool fwd = (v >= 0);
  int d = v >= 0 ? v : -v;
  if (d > 255) d = 255;
  digitalWrite(in1, fwd ? HIGH : LOW);
  digitalWrite(in2, fwd ? LOW  : HIGH);
  analogWrite(pwmPin, d);
}

Dir classifyDir(int L, int R) {
  const int th = 20;
  if (abs(L) < th && abs(R) < th) return STOP;
  if (L > th && R > th) return FWD;
  if (L < -th && R < -th) return REV;
  if ((L >= 0 && R <= 0) || (L - R) > 60) return LEFT;
  if ((R >= 0 && L <= 0) || (R - L) > 60) return RIGHT;
  return (L > R) ? LEFT : RIGHT;
}

struct BeepState { bool on=false; unsigned long t0=0, tnext=0; uint8_t step=0; } beep;
void stopTone(){ noTone(BUZZ); beep.on=false; }

void updateSignal(Dir d){
  const unsigned long now = millis();

  // Prioridade: buzina do controle
  if (horn_active){
    tone(BUZZ, 2000);
    digitalWrite(LEDB, (now/100)%2);
    return;
  }

  // LED baseline
  if (d == STOP) digitalWrite(LEDB, LOW);
  else if (d == FWD) digitalWrite(LEDB, HIGH);
  else digitalWrite(LEDB, (now/300)%2);

  // Beeps de direção (não-bloqueante)
  if (!beep.on && now >= beep.tnext){
    switch(d){
      case STOP: stopTone(); beep.tnext = now + 150; break;
      case FWD:  tone(BUZZ,1000); beep.on=true; beep.t0=now; beep.tnext=now+500; break;
      case LEFT: tone(BUZZ,1500); beep.on=true; beep.t0=now; beep.tnext=now+400; break;
      case RIGHT:tone(BUZZ, 700); beep.on=true; beep.t0=now; beep.tnext=now+400; break;
      case REV:
        if (beep.step==0){ tone(BUZZ,1000); beep.on=true; beep.t0=now; beep.step=1; beep.tnext=now+80; }
        else if (beep.step==1){ stopTone(); beep.step=2; beep.tnext=now+80; }
        else if (beep.step==2){ tone(BUZZ,1000); beep.on=true; beep.t0=now; beep.step=3; beep.tnext=now+80; }
        else { stopTone(); beep.step=0; beep.tnext=now+460; }
        break;
    }
  }
  if (beep.on && (now - beep.t0) >= 40){ stopTone(); }
}

void setup() {
  pinMode(STBY, OUTPUT); digitalWrite(STBY, HIGH); // lembre de amarrar STBY a +5V (pull-up físico) também

  pinMode(AIN1, OUTPUT); pinMode(AIN2, OUTPUT); pinMode(PWMA, OUTPUT);
  pinMode(BIN1, OUTPUT); pinMode(BIN2, OUTPUT); pinMode(PWMB, OUTPUT);

  pinMode(BUZZ, OUTPUT);
  pinMode(LEDB, OUTPUT);

  Serial.begin(115200);

  // bip de boot
  tone(BUZZ, 1200); delay(80); noTone(BUZZ); delay(80); tone(BUZZ, 1600); delay(80); noTone(BUZZ);
  digitalWrite(LEDB, HIGH); delay(120); digitalWrite(LEDB, LOW);
}

void loop() {
  // lê linhas "V L R" e "H 0/1"
  while (Serial.available()){
    String s = Serial.readStringUntil('\n');
    if (!s.length()) continue;

    if (s[0]=='V'){
      long l, r;
      if (sscanf(s.c_str(), "V %ld %ld", &l, &r) == 2){
        if (l > 255)  l = 255; if (l < -255) l = -255;
        if (r > 255)  r = 255; if (r < -255) r = -255;
        cmdL = (int)l; cmdR = (int)r;
      }
    } else if (s[0]=='H'){
      int h=0;
      if (sscanf(s.c_str(), "H %d", &h) == 1){
        horn_active = (h != 0);
        if (!horn_active) stopTone(); // solta buzina retorna ao padrão
      }
    }
  }

  // motores
  driveMotor(PWMA, AIN1, AIN2, cmdL);
  driveMotor(PWMB, BIN1, BIN2, cmdR);

  // sinalização
  currentDir = classifyDir(cmdL, cmdR);
  updateSignal(currentDir);
}
