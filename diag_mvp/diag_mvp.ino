#include <Wire.h>

// === TB6612 (só usamos STBY como "blink" de RX) ===
const int STBY = 4;

// === Halls ===
const int HALL_L = 2;  // INT0
const int HALL_R = 3;  // INT1
volatile long ticksL = 0, ticksR = 0;

// === MPU6050 ===
const uint8_t MPU_ADDR = 0x68; // 0x68 (AD0=0) ou 0x69 (AD0=1)
bool mpu_ok = false;

void isrL(){ ticksL++; }
void isrR(){ ticksR++; }

bool mpu_write(uint8_t reg, uint8_t val){
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(reg); Wire.write(val);
  return Wire.endTransmission()==0;
}
bool mpu_readN(uint8_t start, uint8_t *buf, uint8_t n){
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(start);
  if(Wire.endTransmission(false)!=0) return false;
  Wire.requestFrom((int)MPU_ADDR, (int)n, (int)true);
  for(uint8_t i=0;i<n;i++){
    if(!Wire.available()) return false;
    buf[i]=Wire.read();
  }
  return true;
}

String last_rx = "";


void setup(){
  pinMode(STBY, OUTPUT); digitalWrite(STBY, HIGH); // E-stop no botão p/ GND

  pinMode(HALL_L, INPUT);
  pinMode(HALL_R, INPUT);
  attachInterrupt(digitalPinToInterrupt(HALL_L), isrL, RISING);
  attachInterrupt(digitalPinToInterrupt(HALL_R), isrR, RISING);

  Serial.begin(115200);
  delay(200);
  Serial.println(F("== DIAG MVP START =="));

  Wire.begin();     // I2C em A4/A5
  delay(50);
  // Acorda MPU: PWR_MGMT_1(0x6B)=0
  if(mpu_write(0x6B, 0x00)){
    uint8_t who=0;
    if(mpu_readN(0x75, &who, 1)){ // WHO_AM_I
      Serial.print(F("MPU WHO_AM_I=0x")); Serial.println(who, HEX);
      mpu_ok = (who==0x68 || who==0x69);
    }
  }
  if(!mpu_ok) Serial.println(F("MPU NOT OK (checar VCC=3.3V e pull-ups I2C)!"));
}

void loop(){
  // Ecoa qualquer linha recebida (do Raspi)
  if(Serial.available()){
    String s = Serial.readStringUntil('\n');
    if(s.length()>0){
      last_rx = s;
      // pulso visual no STBY pra indicar RX
      digitalWrite(STBY, LOW); delay(15); digitalWrite(STBY, HIGH);
    }
  }
  
  // Status a cada 200 ms
  static uint32_t t0=0;
  uint32_t now = millis();
  if(now - t0 >= 200){
    noInterrupts(); long tl=ticksL, tr=ticksR; interrupts();

    int16_t ax=0,ay=0,az=0,gx=0,gy=0,gz=0;
    if(mpu_ok){
      uint8_t b[14];
      if(mpu_readN(0x3B, b, 14)){ // ax,ay,az,temp,gx,gy,gz
        ax=(b[0]<<8)|b[1]; ay=(b[2]<<8)|b[3]; az=(b[4]<<8)|b[5];
        gx=(b[8]<<8)|b[9]; gy=(b[10]<<8)|b[11]; gz=(b[12]<<8)|b[13];
      }
    }

    // imprime TUDO em UMA LINHA
    Serial.print("T "); Serial.print(tl); Serial.print(' ');
    Serial.print(tr); Serial.print(" | MPU ");
    Serial.print(ax); Serial.print(' ');
    Serial.print(ay); Serial.print(' ');
    Serial.print(az); Serial.print(' ');
    Serial.print(gx); Serial.print(' ');
    Serial.print(gy); Serial.print(' ');
    Serial.print(gz);

    if(last_rx.length()){
      Serial.print(" | RX "); Serial.print(last_rx);
      last_rx = ""; // limpa após mostrar
    }
  
    Serial.println();

    t0 = now;
  }
}
