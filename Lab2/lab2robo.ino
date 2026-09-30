#include <IRrecv.h>
#include <IRremoteESP8266.h>
#include <IRutils.h>

const uint16_t RECV_PIN = 36;
const uint8_t LED_PIN = 12;

IRrecv irrecv(RECV_PIN);
decode_results results;

unsigned long lastCommandTime = 0;
const unsigned long COMMAND_TIMEOUT = 180;
uint32_t lastCode = 0;
bool motorsRunning = false;

int currentSpeed = 50;          // Default speed
const int MIN_SPEED = 0;        // Speed range: 0-100
const int MAX_SPEED = 100;

String digitBuffer = "";        // Holds digits typed with buttons 1-9


#define SPEED_DOWN_CODE 0xFF6897   // '*' -> decrease speed by 5
#define SPEED_UP_CODE   0xFFB04F   // '#' -> increase speed by 5

#define DIGIT_0 0xFF9867   
#define DIGIT_1 0xFFA25D
#define DIGIT_2 0xFF629D
#define DIGIT_3 0xFFE21D
#define DIGIT_4 0xFF22DD
#define DIGIT_5 0xFF02FD
#define DIGIT_6 0xFFC23D
#define DIGIT_7 0xFFE01F
#define DIGIT_8 0xFFA857
#define DIGIT_9 0xFF906F

void setup() {
  Serial.begin(115200);

  pinMode(25, OUTPUT);
  pinMode(26, OUTPUT);
  ledcSetup(4, 20000, 8);
  ledcAttachPin(33, 4);

  pinMode(27, OUTPUT);
  pinMode(32, OUTPUT);
  ledcSetup(5, 20000, 8);
  ledcAttachPin(14, 5);

  pinMode(18, OUTPUT);
  pinMode(21, OUTPUT);
  ledcSetup(6, 20000, 8);
  ledcAttachPin(5, 6);

  pinMode(22, OUTPUT);
  pinMode(23, OUTPUT);
  ledcSetup(7, 20000, 8);
  ledcAttachPin(19, 7);

  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW);

  irrecv.enableIRIn();
}

void loop() {
  if (irrecv.decode(&results)) {

    uint64_t irCode = results.value;
    Serial.println(irCode, HEX);

    if (irCode == 0xFFFFFFFF) {
      irCode = lastCode;
    } else {
      lastCode = irCode;
    }

    if (irCode == 0xFF18E7) {
      Serial.println("Forward");
      moveForward();
    }
    else if (irCode == 0xFF4AB5) {
      Serial.println("Backward");
      moveBackward();
    }
    else if (irCode == 0xFF10EF) {
      Serial.println("TurnLeft");
      turnLeft();
    }
    else if (irCode == 0xFF5AA5) {
      Serial.println("TurnRight");
      turnRight();
    }
    else if (irCode == 0xFF38C7) {
      Serial.println("STOP");
      stopMotors();
    }
    else if (irCode == SPEED_DOWN_CODE) {
      currentSpeed -= 5;
      if (currentSpeed < MIN_SPEED) currentSpeed = MIN_SPEED;
      Serial.print("Speed is decreasing by 5, the current speed is ");
      Serial.println(currentSpeed);
      applyCurrentSpeed();
    }
    else if (irCode == SPEED_UP_CODE) {
      currentSpeed += 5;
      if (currentSpeed > MAX_SPEED) currentSpeed = MAX_SPEED;
      Serial.print("Speed is increasing by 5, the current speed is ");
      Serial.println(currentSpeed);
      applyCurrentSpeed();
    }
    else if (irCode == DIGIT_0) {
      if (digitBuffer.length() > 0) {
        int typedSpeed = digitBuffer.toInt();
        if (typedSpeed > MAX_SPEED) typedSpeed = MAX_SPEED;
        if (typedSpeed < MIN_SPEED) typedSpeed = MIN_SPEED;
        currentSpeed = typedSpeed;
        Serial.print("Speed set -> ");
        Serial.println(currentSpeed);
        applyCurrentSpeed();
      }
      digitBuffer = "";
    }


    if (irCode == DIGIT_1) digitBuffer += "1";
    else if (irCode == DIGIT_2) digitBuffer += "2";
    else if (irCode == DIGIT_3) digitBuffer += "3";
    else if (irCode == DIGIT_4) digitBuffer += "4";
    else if (irCode == DIGIT_5) digitBuffer += "5";
    else if (irCode == DIGIT_6) digitBuffer += "6";
    else if (irCode == DIGIT_7) digitBuffer += "7";
    else if (irCode == DIGIT_8) digitBuffer += "8";
    else if (irCode == DIGIT_9) digitBuffer += "9";

    lastCommandTime = millis();
    irrecv.resume();
  }
  else if (motorsRunning && (millis() - lastCommandTime > COMMAND_TIMEOUT)) {
    stopMotors();
  }
  delay(100);
}
void moveForward(){
  ledcWrite(4, currentSpeed);
  digitalWrite(25, HIGH);
  digitalWrite(26, LOW);
  ledcWrite(5, currentSpeed);
  digitalWrite(27, HIGH);
  digitalWrite(32, LOW);
  ledcWrite(6, currentSpeed);
  digitalWrite(18, LOW);
  digitalWrite(21, HIGH);
  ledcWrite(7, currentSpeed);
  digitalWrite(22, LOW);
  digitalWrite(23, HIGH);
}


void applyCurrentSpeed(){
  ledcWrite(4, currentSpeed);
  ledcWrite(5, currentSpeed);
  ledcWrite(6, currentSpeed);
  ledcWrite(7, currentSpeed);
}

void moveBackward(){

  ledcWrite(4, currentSpeed);
  digitalWrite(25, LOW);
  digitalWrite(26, HIGH);
  ledcWrite(5, currentSpeed);
  digitalWrite(27, LOW);
  digitalWrite(32, HIGH);
  ledcWrite(6, currentSpeed);
  digitalWrite(18, HIGH);
  digitalWrite(21, LOW);
  ledcWrite(7, currentSpeed);
  digitalWrite(22, HIGH);
  digitalWrite(23, LOW);

}
void turnLeft(){
  ledcWrite(4, currentSpeed);
  digitalWrite(25, LOW);
  digitalWrite(26, HIGH);
  ledcWrite(5, currentSpeed);
  digitalWrite(27, LOW);
  digitalWrite(32, LOW);
  ledcWrite(6, currentSpeed);
  digitalWrite(18, LOW);
  digitalWrite(21, HIGH);
  ledcWrite(7, currentSpeed);
  digitalWrite(22, LOW);
  digitalWrite(23, HIGH);
}

void turnRight(){

  ledcWrite(4, currentSpeed);
  digitalWrite(25, HIGH);
  digitalWrite(26, LOW);
  ledcWrite(5, currentSpeed);
  digitalWrite(27, HIGH);
  digitalWrite(32, HIGH);
  ledcWrite(6, currentSpeed);
  digitalWrite(18, HIGH);
  digitalWrite(21, LOW);
  ledcWrite(7, currentSpeed);
  digitalWrite(22, HIGH);
  digitalWrite(23, LOW);
}
void stopMotors(){
  ledcWrite(4, 0);
  digitalWrite(25, LOW);
  digitalWrite(26, LOW);
  ledcWrite(5, 0);
  digitalWrite(27, LOW);
  digitalWrite(32, LOW);
  ledcWrite(6, 0);
  digitalWrite(18, LOW);
  digitalWrite(21, LOW);
  ledcWrite(7, 0);
  digitalWrite(22, LOW);
  digitalWrite(23, LOW);
}