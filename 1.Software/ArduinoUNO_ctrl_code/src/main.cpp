#include <Arduino.h>
#include <Adafruit_PWMServoDriver.h> // 引入Adafruit PWM伺服驱动器库
 
// 定义电机脉冲宽度的最小和最大值（微秒）
#define MIN_PULSE_WIDTH       500
#define MAX_PULSE_WIDTH       2500
#define FREQUENCY             50// 定义PWM信号的频率（赫兹）
Adafruit_PWMServoDriver pwm = Adafruit_PWMServoDriver();// 创建Adafruit PWM伺服驱动器的实例

int hand = 11;        // 夹持器（手部）
int wrist = 12;       // 腕部电机
int elbow = 13;       // 肘部电机
int shoulder = 14;    // 肩部电机
int base = 15;        // 基座电机

// 转换角度与脉冲长度
float JDtoMCCD(float Angle) {
    float MCCD;
    MCCD = (Angle / 180.0f * 2000.0f + 500.0f);
    return MCCD;
}
// 转换脉冲长度与寄存器值（这里不需要Angle，因为MCCD已经包含了角度的信息）
float MCCDtoJCQ(float MCCD) {
    float JCQ;
    JCQ = MCCD / 1000.0f * 204.0f;
    return JCQ;
}
// 控制舵机
void DJ( int arm, float Angle) { // 添加了hand参数，假设它是控制哪个舵机的标识
    float MCCD = JDtoMCCD(Angle);
    float JCQ = MCCDtoJCQ(MCCD);
    pwm.setPWM(arm, 0, static_cast<int>(JCQ)); // 假设pwm.setPWM的第三个参数需要是整型
}

void setup() {
  delay(3000); // 延迟3秒，以便用户将控制器置于起始位置
  pwm.begin(); // 初始化PWM伺服驱动器
  pwm.setPWMFreq(FREQUENCY); // 设置PWM频率
  Serial.begin(9600); // 初始化串口通信，波特率设置为9600
  DJ(base, 90);
  DJ(shoulder, 0);
  DJ(elbow, 180);
  DJ(wrist, 90);
  DJ(hand, 0);
}

void loop() {
  DJ(base, 90);
  DJ(shoulder, 0);
  DJ(elbow, 180);
  DJ(wrist, 90);
  DJ(hand, 0);
}
