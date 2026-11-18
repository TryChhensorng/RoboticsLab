# Black Line Following Robot: How It Moves

`line_follow.py` runs on the computer/Pi with the camera. It finds the black line, decides how to drive, and sends wheel speeds to the ESP32 over serial.

```
Camera --> HSV mask --> line position --> steering decision --> "DRIVE,left,right" --> ESP32 --> motors
```

## 1. How the robot sees the line

1. **Region of Interest (ROI):** only the bottom half of the frame is used (`ROI_START = 0.5`).
2. **HSV threshold:** a pixel counts as "black line" if its brightness is low: `V <= V_MAX (80)`. Hue and saturation are ignored, because black has no colour.
3. **Cleanup:** blur, then morphological open/close to remove specks and fill small gaps.
4. **Line position:** the ROI is split into a **far** half (top) and a **near** half (bottom). In each half the largest dark blob is found and its horizontal centre is measured. The two are blended:

   `x = 0.55 * x_near + 0.45 * x_far` (`FAR_WEIGHT = 0.45`)

   The far half lets the robot see a curve coming before it arrives.
5. **Error:** `err = (x - 0.5) / 0.5`, a value from -1 (far left) to +1 (far right). 0 means the line is exactly in the middle.

## 2. The three zones

The frame is divided into thirds by the red and blue lines drawn on the video (`DEADZONE = 1/3`).

```
|   LEFT    |   CENTER   |   RIGHT   |
          red          blue
```

| Where the line is | Zone | Robot action |
|---|---|---|
| Between red and blue | CENTER | Drive straight: both wheels at `BASE_SPEED` |
| Left of red | LEFT | Turn left: left wheel slows, right wheel stays at `BASE_SPEED` |
| Right of blue | RIGHT | Turn right: right wheel slows, left wheel stays at `BASE_SPEED` |

Goal: keep the line in the centre zone.

## 3. How hard it turns

The further the line is from the centre zone, the harder the turn:

```
turn  = clamp( (|err| - DEADZONE) / (1 - DEADZONE) * TURN_GAIN , 0 , 1 )
inner wheel = BASE_SPEED * (1 - (1 + REVERSE) * turn)
outer wheel = BASE_SPEED
```

With the current settings (`BASE_SPEED = 7`, `TURN_GAIN = 1.6`, `REVERSE = 0.2`):

| Line position (err) | Inner wheel | Outer wheel | Result |
|---|---|---|---|
| 0.33 or less (centre zone) | 7 | 7 | straight |
| 0.50 | about 3.6 | 7 | gentle curve |
| 0.75 or more | about -1.4 | 7 | sharp turn, inner wheel slightly reverses |

No wheel ever goes above `BASE_SPEED`. Wheel speeds also change gradually (`SLEW`) so the robot does not jerk.

## 4. When the line is lost

The robot goes through these stages and returns to normal following as soon as the line is seen again:

| Time since line last seen | Stage | What the robot does |
|---|---|---|
| 0 to 0.8 s | **HOLD** | Keeps the last wheel speeds. This ignores brief dropouts. |
| 0.8 to 1.8 s | **RECOVER** | Pivots toward the side where the line was last seen, since it probably slid out of view there. |
| 1.8 s onward | **ZIGZAG** | Swings left and right with growing width (6 swings, about 9 s total) until the line is found. |
| After the last swing | **NO LINE** | Stops (`DRIVE,0,0`). |

The side to search first (`last_side`) is only updated when the line was clearly off-centre, so the robot does not guess a random direction.

## 5. Status label on the video

The text at the top-left of the stream shows what the robot is doing:

| Label | Meaning |
|---|---|
| `CENTER L7 R7` | Line in the middle, driving straight |
| `LEFT` / `RIGHT` | Line in that zone, steering back toward it |
| `RECOVER` | Line lost, pivoting toward the last known side |
| `ZIGZAG k/6` | Searching, swing number k of 6 |
| `NO LINE` | Gave up and stopped |

The small black-and-white picture in the top-right corner is the mask. White is what the robot thinks is the line. If the line is broken or missing there, the problem is detection, not steering.
The terminal also prints a `[LOST]` line each time the line disappears, for debugging.

## 6. Settings to tune (top of `line_follow.py`)

| Setting | What it does | If the robot... |
|---|---|---|
| `BASE_SPEED` | forward speed (%) | is too fast, lower it |
| `TURN_GAIN` | steering strength | wobbles, lower it. Cuts corners, raise it. |
| `DEADZONE` | width of the centre zone | corrects too late, make it smaller (e.g. 0.2) |
| `FAR_WEIGHT` | how much it looks ahead | misses curves, raise it |
| `LOST_HOLD` | time before searching starts | zig-zags on straight lines, raise it |
| `V_MAX` | darkness limit for "black" | misses the line, raise it. Picks up shadows, lower it. |
| `MIN_PWM` | minimum motor power sent | motors twitch but do not move, set to their stall power |
| `SWAP_STEERING` | swap left/right | turns the wrong way physically, set `True` |

## 7. Running it

```
python3 line_follow.py
```

Then open `http://<robot-ip>:5000` in a browser to watch the camera view with the zones, the mask, and the status label. Press Ctrl+C to stop. The program sends `DRIVE,0,0` on exit.

Tip: the ESP32 firmware should also stop the motors if no `DRIVE` command arrives for about 300 ms, so the robot stops if the Python program crashes.


### Demo Video

Watch the robot demonstration here: [Demo video]https://drive.google.com/file/d/1DI158Yh1u7ws9TZ9qYXNrxkTdQ0dNGn1/view?usp=drive_link

Watch the robot demonstration here: [Demo video]https://drive.google.com/file/d/1Z4SHB3k3eTjAPt62iyhZIDAu3nHbpvrD/view?usp=drive_link