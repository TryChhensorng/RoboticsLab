const int joyX = 34;
const int joyY = 35;
int xValue = 0;
int yValue = 0;

int forwardSpeed = 50;    
int rotationSpeed = 50;   
const int SPEED_STEP = 5;

const int JOY_CENTER = 2048;
const int JOY_DEADZONE = 400;


void setup() {
  pinMode(16, INPUT);
  pinMode(15, INPUT);
  pinMode(2, INPUT);
  pinMode(4, INPUT);
  Serial.begin(115200);

  pinMode(25, OUTPUT);
  pinMode(26, OUTPUT);
  ledcSetup(0, 20000, 8);
  ledcAttachPin(33, 0);

  pinMode(27, OUTPUT);
  pinMode(32, OUTPUT);
  ledcSetup(1, 20000, 8);
  ledcAttachPin(14, 1);

  pinMode(18, OUTPUT);
  pinMode(21, OUTPUT);
  ledcSetup(2, 20000, 8);
  ledcAttachPin(5, 2);

  pinMode(22, OUTPUT);
  pinMode(23, OUTPUT);
  ledcSetup(3, 20000, 8);
  ledcAttachPin(19, 3);

  Serial.begin(115200);
  Serial.println("ESP32 Joystick Reading Started");
}

void loop() {
  int button_up = digitalRead(16);
  int button_down = digitalRead(15);
  int button_left = digitalRead(2);
  int button_right = digitalRead(4);

  xValue = analogRead(joyX);  // 0 - 4095
  yValue = analogRead(joyY);  // 0 - 4095

  int xOffset = xValue - JOY_CENTER;
  int yOffset = yValue - JOY_CENTER;

  Serial.print("X: ");
  Serial.print(xValue);
  Serial.print(" | Y: ");
  Serial.print(yValue);
  Serial.print(" | forwardSpeed: ");
  Serial.print(forwardSpeed);
  Serial.print(" | rotationSpeed: ");
  Serial.println(rotationSpeed);

  if (button_up == LOW) {
    Serial.println("Button Up is pressed");
    moveForward();
  } else if (button_down == LOW) {
    Serial.println("Button Down is pressed");
    moveBackward();
  } else if (button_left == LOW) {
    Serial.println("Button Left is pressed");
    turnLeft();
  } else if (button_right == LOW) {
    Serial.println("Button Right is pressed");
    turnRight();
  } else if (abs(yOffset) > JOY_DEADZONE) {
    if (yOffset < 0) {
      moveForward();
    } else {
      moveBackward();
    }
  } else if (abs(xOffset) > JOY_DEADZONE) {
    if (xOffset < 0) {
      turnRight();
    } else {
      turnLeft();
    }
  } else {
    Serial.println("Button isn't pressed");
    stopMotors();
  }

  delay(50);
}

void moveForward(){
  int pwm = map(forwardSpeed, 0, 100, 0, 255);
  ledcWrite(0, pwm);
  digitalWrite(25, LOW);
  digitalWrite(26, HIGH);
  ledcWrite(1, pwm);
  digitalWrite(27, HIGH);
  digitalWrite(32, LOW);
  ledcWrite(2, pwm);
  digitalWrite(18, HIGH);
  digitalWrite(21, LOW);
  ledcWrite(3, pwm);
  digitalWrite(22, HIGH);
  digitalWrite(23, LOW);
}

void moveBackward(){
  int pwm = map(forwardSpeed, 0, 100, 0, 255);
  ledcWrite(0, pwm);
  digitalWrite(25, HIGH);
  digitalWrite(26, LOW);
  ledcWrite(1, pwm);
  digitalWrite(27, LOW);
  digitalWrite(32, HIGH);
  ledcWrite(2, pwm);
  digitalWrite(18, LOW);
  digitalWrite(21, HIGH);
  ledcWrite(3, pwm);
  digitalWrite(22, LOW);
  digitalWrite(23, HIGH);
}
void turnLeft(){
  int pwm = map(rotationSpeed, 0, 100, 0, 255);
  ledcWrite(0, pwm);
  digitalWrite(25, LOW);
  digitalWrite(26, HIGH);
  ledcWrite(1, pwm);
  digitalWrite(27, HIGH);
  digitalWrite(32, LOW);
  ledcWrite(2, pwm);
  digitalWrite(18, LOW);
  digitalWrite(21, HIGH);
  ledcWrite(3, pwm);
  digitalWrite(22, LOW);
  digitalWrite(23, HIGH);
}

void turnRight(){
  int pwm = map(rotationSpeed, 0, 100, 0, 255);
  ledcWrite(0, pwm);
  digitalWrite(25, HIGH);
  digitalWrite(26, LOW);
  ledcWrite(1, pwm);
  digitalWrite(27, LOW);
  digitalWrite(32, HIGH);
  ledcWrite(2, pwm);
  digitalWrite(18, HIGH);
  digitalWrite(21, LOW);
  ledcWrite(3, pwm);
  digitalWrite(22, HIGH);
  digitalWrite(23, LOW);
}
void stopMotors(){
  ledcWrite(0, 0);
  digitalWrite(25, LOW);
  digitalWrite(26, LOW);
  ledcWrite(1, 0);
  digitalWrite(27, LOW);
  digitalWrite(32, LOW);
  ledcWrite(2, 0);
  digitalWrite(18, LOW);
  digitalWrite(21, LOW);
  ledcWrite(3, 0);
  digitalWrite(22, LOW);
  digitalWrite(23, LOW);
}
