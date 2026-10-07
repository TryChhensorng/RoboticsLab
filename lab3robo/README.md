Startup (setup())
- Sets the ultrasonic pins, attaches the servo on pin 17 and centers it at 90°.
- Starts Bluetooth (Dabble) as "Robotic", configures the 4 motors with PWM, and fills scanDist[] with 400 cm.
- Stops the motors and starts in MANUAL mode.

Main loop (loop())
- Every pass reads the gamepad and runs checkModeButtons().
- checkModeButtons() ignores presses within 500 ms of the last toggle.
  - SELECT switches to MANUAL: stops the motors and centers the servo.
  - START switches to AUTO: stops the motors and sets needScan = true.
- If autoMode is false, it runs manual control. Otherwise it runs autoMode_Navigate().

Manual mode
- D-pad: forward, back, left, right, or stop.
- Square / Circle: the servo moves +10° or −10° per press.
- Cross / Triangle: the servo goes to 30° or 140°.

AUTO mode (autoMode_Navigate())
1. First scan: if needScan is true (after entering AUTO), it stops, scans all 6 angles (30°, 52°, 74°, 96°, 118°, 140°) and sets needScan = false.
2. Sweep step: it moves the servo to SCAN_ANGLES[scanIdx], waits 70 ms, measures and stores the distance, then steps scanIdx forward or back, reversing at the ends. The robot only sees one angle per pass, so each zone is refreshed gradually.
3. Zones: Right = min of angles 30° and 52°. Center = min of 74° and 96°. Left = min of 118° and 140°.
4. Decision order:
   - Center < 25 cm → avoidFront().
   - Right < 40 cm and (Left is not close or Right ≤ Left) → steerAway to the left.
   - Left < 40 cm → steerAway to the right.
   - Otherwise → moveForward().

avoidFront() (obstacle ahead)
1. Stop, wait 100 ms, reverse 250 ms, stop, wait 100 ms.
2. Loop while in AUTO: turn left for TURN_90_MS (about 90°), stop, wait 200 ms, then scan all 6 angles.
3. If the center (74°/96°) is at least 35 cm, exit the loop and set needScan = false. If not, turn left another 90° and check again.
4. It only ever turns left. It does not compare left against right.

steerAway() (obstacle at the side)
1. Clamp the distance between 12 cm and 40 cm. Work out closeness from 0 (far) to 1 (very close).
2. Turn time runs from TURN_90_MS/8 (75 ms) up to TURN_90_MS × 2/3 (400 ms), growing with closeness.
3. Stop 60 ms, turn away from the obstacle, stop, wait 150 ms, then do a full 6-angle scan because the old readings no longer apply.

### Demo Video

Watch the robot demonstration here: [Demo video]https://drive.google.com/file/d/1husehL73dVPt1JF9JgtsznMmf6fo7Vms/view?usp=drive_link