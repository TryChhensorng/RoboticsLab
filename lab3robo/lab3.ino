#define CUSTOM_SETTINGS
#define INCLUDE_GAMEPAD_MODULE
#include <DabbleESP32.h>
#include <ESP32Servo.h>

#define TRIG_PIN 13
#define ECHO_PIN 39

const int   MOTOR_SPEED   = 50;     
const int   TURN_SPEED    = 90;     
const float FRONT_STOP_CM = 25.0;   
const float SIDE_WARN_CM  = 40.0;   
const float SIDE_MIN_CM   = 12.0;   
const float CLEAR_CM      = 35.0;   
const int   TURN_90_MS    = 600;    
const int   BACKUP_MS     = 250;    
const int   SERVO_MIN     = 30;     
const int   SERVO_MAX     = 140;
const int   SERVO_STEP    = 10;
const char* BT_NAME       = "Robotic";

const int SCAN_ANGLES[] = {30, 52, 74, 96, 118, 140};
const int NUM_ANGLES    = 6;
float scanDist[NUM_ANGLES];
int   scanIdx = 0;
int   scanDir = 1;
bool  needScan = true;

Servo myServo;
int servoAngle = 90;

bool autoMode = false;               
unsigned long lastModeToggle = 0;

bool prevSquare = false;
bool prevCircle = false;

void setup() {
  Serial.begin(115200);

  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);

  myServo.attach(17);
  setServo(90);

  Dabble.begin(BT_NAME);

  pinMode(25, OUTPUT); pinMode(26, OUTPUT);
  ledcSetup(4, 20000, 8); ledcAttachPin(33, 4);
  pinMode(27, OUTPUT); pinMode(32, OUTPUT);
  ledcSetup(5, 20000, 8); ledcAttachPin(14, 5);
  pinMode(18, OUTPUT); pinMode(21, OUTPUT);
  ledcSetup(6, 20000, 8); ledcAttachPin(5, 6);
  pinMode(22, OUTPUT); pinMode(23, OUTPUT);
  ledcSetup(7, 20000, 8); ledcAttachPin(19, 7);

  for (int i = 0; i < NUM_ANGLES; i++) scanDist[i] = 400.0;

  stopMotors();
  delay(1000);
  Serial.println("Robot initialized");
  Serial.println("SELECT = MANUAL mode, START = AUTO mode");
}

void loop() {
  Dabble.processInput();
  checkModeButtons();

  if (autoMode) {
    autoMode_Navigate();
  } else {
    manualMode_Control();
  }
}

// ===== MODE SWITCHING =====
void checkModeButtons() {
  if (millis() - lastModeToggle < 500) return;

  // SELECT -> MANUAL
  if (GamePad.isSelectPressed() && autoMode) {
    autoMode = false;
    lastModeToggle = millis();
    stopMotors();
    setServo(90);
    Serial.println("MODE: MANUAL");
  }
  // START -> AUTO
  else if (GamePad.isStartPressed() && !autoMode) {
    autoMode = true;
    lastModeToggle = millis();
    stopMotors();
    needScan = true;                  // scan surroundings before moving
    Serial.println("MODE: AUTO");
  }
}

bool waitMs(unsigned long ms) {
  unsigned long t = millis();
  while (millis() - t < ms) {
    Dabble.processInput();
    checkModeButtons();
    if (!autoMode) return false;
    delay(5);
  }
  return true;
}

void setServo(int angle) {
  servoAngle = constrain(angle, SERVO_MIN, SERVO_MAX);
  myServo.write(servoAngle);
}

void manualMode_Control() {
  if (GamePad.isUpPressed())         moveForward();
  else if (GamePad.isDownPressed())  moveBackward();
  else if (GamePad.isLeftPressed())  turnLeft();
  else if (GamePad.isRightPressed()) turnRight();
  else                               stopMotors();

  bool sq = GamePad.isSquarePressed();
  if (sq && !prevSquare) {
    setServo(servoAngle + SERVO_STEP);
    Serial.print("Servo: "); Serial.println(servoAngle);
  }
  prevSquare = sq;

  bool ci = GamePad.isCirclePressed();
  if (ci && !prevCircle) {
    setServo(servoAngle - SERVO_STEP);
    Serial.print("Servo: "); Serial.println(servoAngle);
  }
  prevCircle = ci;

  if (GamePad.isCrossPressed()) {
    setServo(30);
    Serial.println("Servo: 30");
  }
  if (GamePad.isTrianglePressed()) {
    setServo(140);
    Serial.println("Servo: 140");
  }

  delay(20);
}

float minRange(int a, int b) {
  float m = 999.0;
  for (int i = a; i <= b; i++) {
    if (scanDist[i] < m) m = scanDist[i];
  }
  return m;
}

bool fullScan() {
  for (int i = 0; i < NUM_ANGLES; i++) {
    setServo(SCAN_ANGLES[i]);
    if (!waitMs(i == 0 ? 250 : 100)) return false;
    scanDist[i] = measureDistance();
  }
  scanIdx = NUM_ANGLES - 2;           
  scanDir = -1;
  return true;
}

void autoMode_Navigate() {
  if (needScan) {
    stopMotors();
    if (!fullScan()) return;
    needScan = false;
  }

  setServo(SCAN_ANGLES[scanIdx]);
  if (!waitMs(70)) return;
  scanDist[scanIdx] = measureDistance();

  if (scanIdx + scanDir < 0 || scanIdx + scanDir >= NUM_ANGLES) scanDir = -scanDir;
  scanIdx += scanDir;

  float right  = minRange(0, 1);
  float center = minRange(2, 3);
  float left   = minRange(4, 5);

  Serial.print("R:"); Serial.print(right);
  Serial.print(" C:"); Serial.print(center);
  Serial.print(" L:"); Serial.println(left);

  if (center < FRONT_STOP_CM) {
    avoidFront();
    return;
  }

  bool rightClose = right < SIDE_WARN_CM;
  bool leftClose  = left  < SIDE_WARN_CM;

  if (rightClose && (!leftClose || right <= left)) {
    steerAway(true, right);           
  } else if (leftClose) {
    steerAway(false, left);           
  } else {
    moveForward();                    
  }
}

void avoidFront() {
  stopMotors();
  if (!waitMs(100)) return;

  moveBackward();
  if (!waitMs(BACKUP_MS)) return;
  stopMotors();
  if (!waitMs(100)) return;

  while (autoMode) {
    turnLeft();
    if (!waitMs(TURN_90_MS)) return;
    stopMotors();
    if (!waitMs(200)) return;         

    if (!fullScan()) return;          
    float front = minRange(2, 3);
    Serial.print("After turn, front: "); Serial.println(front);
    if (front >= CLEAR_CM) break;     
  }
  needScan = false;
}

void steerAway(bool goLeft, float dist) {
  float d = dist;
  if (d < SIDE_MIN_CM)  d = SIDE_MIN_CM;
  if (d > SIDE_WARN_CM) d = SIDE_WARN_CM;

  float closeness = (SIDE_WARN_CM - d) / (SIDE_WARN_CM - SIDE_MIN_CM);
  int minMs = TURN_90_MS / 8;         // small nudge
  int maxMs = (TURN_90_MS * 2) / 3;   // about 60 degrees
  int ms = minMs + (int)(closeness * (maxMs - minMs));

  Serial.print(goLeft ? "Steer LEFT " : "Steer RIGHT ");
  Serial.print(ms); Serial.println(" ms");

  stopMotors();
  if (!waitMs(60)) return;

  if (goLeft) turnLeft(); else turnRight();
  if (!waitMs(ms)) return;
  stopMotors();
  if (!waitMs(150)) return;

  fullScan();                         
}

// ===== ULTRASONIC =====
float readOnce() {
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);

  long duration = pulseIn(ECHO_PIN, HIGH, 25000);
  if (duration == 0) return 400.0;    // no echo
  return (duration * 0.0343) / 2.0;
}

float measureDistance() {
  float a = readOnce(); delay(8);
  float b = readOnce(); delay(8);
  float c = readOnce();
  if ((a <= b && b <= c) || (c <= b && b <= a)) return b;
  if ((b <= a && a <= c) || (c <= a && a <= b)) return a;
  return c;
}

// ===== MOTOR CONTROL =====
void moveForward() {
  ledcWrite(4, MOTOR_SPEED); digitalWrite(25, HIGH); digitalWrite(26, LOW);
  ledcWrite(5, MOTOR_SPEED); digitalWrite(27, HIGH); digitalWrite(32, LOW);
  ledcWrite(6, MOTOR_SPEED); digitalWrite(18, LOW);  digitalWrite(21, HIGH);
  ledcWrite(7, MOTOR_SPEED); digitalWrite(22, LOW);  digitalWrite(23, HIGH);
}

void moveBackward() {
  ledcWrite(4, MOTOR_SPEED); digitalWrite(25, LOW);  digitalWrite(26, HIGH);
  ledcWrite(5, MOTOR_SPEED); digitalWrite(27, LOW);  digitalWrite(32, HIGH);
  ledcWrite(6, MOTOR_SPEED); digitalWrite(18, HIGH); digitalWrite(21, LOW);
  ledcWrite(7, MOTOR_SPEED); digitalWrite(22, HIGH); digitalWrite(23, LOW);
}

void turnLeft() {
  ledcWrite(4, TURN_SPEED); digitalWrite(25, LOW);  digitalWrite(26, HIGH);
  ledcWrite(5, TURN_SPEED); digitalWrite(27, LOW);  digitalWrite(32, HIGH);
  ledcWrite(6, TURN_SPEED); digitalWrite(18, LOW);  digitalWrite(21, HIGH);
  ledcWrite(7, TURN_SPEED); digitalWrite(22, LOW);  digitalWrite(23, HIGH);
}

void turnRight() {
  ledcWrite(4, TURN_SPEED); digitalWrite(25, HIGH); digitalWrite(26, LOW);
  ledcWrite(5, TURN_SPEED); digitalWrite(27, HIGH); digitalWrite(32, LOW);
  ledcWrite(6, TURN_SPEED); digitalWrite(18, HIGH); digitalWrite(21, LOW);
  ledcWrite(7, TURN_SPEED); digitalWrite(22, HIGH); digitalWrite(23, LOW);
}

void stopMotors() {
  ledcWrite(4, 0);
  ledcWrite(5, 0);
  ledcWrite(6, 0);
  ledcWrite(7, 0);
}