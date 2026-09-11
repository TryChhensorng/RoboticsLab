3. EXPLANATION DESCRIBING:
Demo Video:
Watch the video here: https://drive.google.com/file/d/1WA7I3801kx1-bJNHVE4vSKxyo8JpwXNP/view?usp=drive_link
3a. The purpose of using two different speeds:
The robot needs a different speed for going straight and for turning, so there are two separate numbers: forwardSpeed for forward/backward, and rotationSpeed for turning. This way turning can be slower and easier to control without changing how fast it drives straight.
3b. The deadzone uses in this robot:
A joystick never sits at the exact same number when you let go of it — it wiggles a tiny bit on its own. So the code ignores small movements near the center and only reacts once you push the stick far enough. This stops the robot from moving by itself when nobody is touching it.
3c. Concepts of increasing and decreasing the speed
Both speeds start at 50. Each button press adds or takes away 5 (UP/DOWN for forward speed, LEFT/RIGHT for turning speed). The number can never go below 0 or above 100, and one press only changes it once, not over and over while held.
