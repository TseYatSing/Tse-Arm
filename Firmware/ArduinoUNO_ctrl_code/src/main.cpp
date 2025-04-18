#include <Arduino.h>
#include <Adafruit_PWMServoDriver.h>

#define MIN_PULSE_WIDTH   500
#define MAX_PULSE_WIDTH   2500
#define PWM_FREQ          50
#define MAX_CMD_LENGTH    30

Adafruit_PWMServoDriver pwm = Adafruit_PWMServoDriver();

const uint8_t SERVO_PINS[5] = {15, 14, 13, 12, 11}; // BASE, SHOULDER, ELBOW, WRIST, GRIPPER

float angleToPulse(float angle) {
  angle = constrain(angle, 0.0, 180.0);
  return map(angle, 0.0, 180.0, MIN_PULSE_WIDTH, MAX_PULSE_WIDTH);
}

void setServoAngle(uint8_t servoPin, float angle) {
  pwm.writeMicroseconds(servoPin, angleToPulse(angle));
  
  Serial.print("Servo[");
  Serial.print(servoPin);
  Serial.print("] ");
  Serial.print(angle);
  Serial.println("°");
}

void moveArm(float angles[4], bool gripperOpen) {
  for(int i=0; i<4; i++){
    setServoAngle(SERVO_PINS[i], angles[i]);
  }
  setServoAngle(SERVO_PINS[4], gripperOpen ? 90 : 0);
  Serial.println("OK");
}

bool validateAngles(float angles[4]) {
  for(int i=0; i<4; i++){
    if(angles[i] < 0 || angles[i] > 180) return false;
  }
  return true;
}

void processCommand(String input) {
  if(input.length() == 0) return;

  // 格式验证
  int spaceIndex = input.indexOf(' ');
  if(spaceIndex == -1 || input.substring(spaceIndex+1).length() == 0){
    Serial.println("ERROR:INVALID_FORMAT");
    return;
  }

  // 分割角度和状态
  String anglePart = input.substring(0, spaceIndex);
  String statePart = input.substring(spaceIndex+1);

  // 解析角度
  float angles[4];
  int commaPos[3];
  int commaCount = 0;
  
  for(int i=0; i<anglePart.length() && commaCount<3; i++){
    if(anglePart[i] == ','){
      if(commaCount < 3) commaPos[commaCount] = i;
      commaCount++;
    }
  }

  if(commaCount != 3){
    Serial.println("ERROR:ANGLE_FORMAT");
    return;
  }

  angles[0] = anglePart.substring(0, commaPos[0]).toFloat();
  angles[1] = anglePart.substring(commaPos[0]+1, commaPos[1]).toFloat();
  angles[2] = anglePart.substring(commaPos[1]+1, commaPos[2]).toFloat();
  angles[3] = anglePart.substring(commaPos[2]+1).toFloat();

  // 验证角度
  if(!validateAngles(angles)){
    Serial.println("ERROR:ANGLE_RANGE");
    return;
  }

  // 解析状态
  statePart.toLowerCase();
  bool gripper = (statePart == "on" || statePart == "1");

  moveArm(angles, gripper);
}

void setup() {
  Serial.begin(115200);
  pwm.begin();
  pwm.setPWMFreq(PWM_FREQ);
  Serial.println("READY");
}

void loop() {
  static String inputBuffer = "";
  
  while(Serial.available() > 0){
    char c = Serial.read();
    
    if(c == '\n'){
      inputBuffer.trim();
      processCommand(inputBuffer);
      inputBuffer = "";
    }else if(inputBuffer.length() < MAX_CMD_LENGTH){
      inputBuffer += c;
    }else{
      Serial.println("ERROR:CMD_TOO_LONG");
      inputBuffer = "";
      while(Serial.available()) Serial.read(); // 清空缓冲区
    }
  }
}
