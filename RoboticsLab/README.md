# RoboticsLab

RoboticsLab is an Arduino robot-control project. It uses joystick input to drive the robot, adjust movement speeds, and control turning.

## Project Files

### Arduino Program

`RoboticsLab/roboticcl.ino` contains the Arduino code that reads the joystick and controls the robot's movement.

### Flowchart

`RoboticsLab/flowchart (1).png` shows the program's control flow and the decisions used to operate the robot.

## Explanation

### Demo Video

Watch the robot demonstration here: [Demo video](https://drive.google.com/file/d/1WA7I3801kx1-bJNHVE4vSKxyo8JpwXNP/view?usp=drive_link)

### Why Two Different Speeds Are Used

The robot uses one speed for driving forward or backward and another speed for turning. `forwardSpeed` controls straight movement, while `rotationSpeed` controls turning. Turning can therefore be slower and easier to control without changing the robot's straight-line speed.

### Joystick Deadzone

A joystick can report small, unintentional movements even when it is released. The deadzone ignores values near the joystick's center so the robot does not move by itself. The robot responds only after the joystick is moved far enough from the center.

### Increasing and Decreasing Speed

Both speeds start at 50. Each button press changes the relevant speed by 5: UP and DOWN adjust forward speed, while LEFT and RIGHT adjust turning speed. Speed values stay between 0 and 100, and each press changes the value only once.
