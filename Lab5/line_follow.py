from flask import Flask, Response
import cv2
import numpy as np
import serial
import glob
import threading
import time

# ================= CONFIG =================
# ---- normal line following ----
BASE_SPEED = 7           # forward speed (%), no wheel goes above this
TURN_GAIN = 1.6          # steering strength (lower = calmer)
REVERSE = 0.2            # 0 = inner wheel only slows, >0 = inner wheel can reverse on bends
DEADZONE = 1 / 3         # centre zone = middle third (red line at 1/3, blue at 2/3), like the lesson
FAR_WEIGHT = 0.45        # how much the far half of the ROI counts (look-ahead)
ROI_START = 0.5          # ROI starts at this fraction of the frame height
SMOOTHING = 0.5          # 0 = no smoothing, closer to 1 = more lag
SLEW = 60                # max wheel change per second while following (% / s)
LOST_HOLD = 0.8          # seconds to keep the last move before recovering (ignores brief dropouts)
RECOVER_TIME = 1.0      # seconds to pivot toward the last known side before zig-zag
SIDE_MIN = 0.15          # only trust last_side when the line was clearly off-centre

# ---- zig-zag search (when recover fails) ----
ZIG_SPEED = 7            # turning speed of each swing (%)
ZIG_FORWARD = 2          # small forward creep during swings (%), 0 = pivot in place
ZIG_STEP_TIME = 0.35     # seconds for the first swing
ZIG_GROWTH = 0.6         # each next swing is this much wider
ZIG_SWEEPS = 6           # number of swings before giving up and stopping
ZIG_SLEW = 300           # fast speed changes allowed while searching (% / s)

# ---- motors ----
MIN_PWM = 0              # if motors twitch but do not move, set to their stall power (e.g. 15)
SWAP_STEERING = False    # True if the robot turns the wrong way physically

SEND_HZ = 20
MIN_LINE_PIXELS = 60     # minimum contour area (pixels) to count as the line
V_MAX = 80               # HSV brightness ceiling for "black"
STREAM_EVERY = 3
# ==========================================

app = Flask(__name__)

cap = cv2.VideoCapture(0)
cap.set(3, 640)
cap.set(4, 480)
cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

esp32 = None


def open_serial():
    global esp32
    try:
        if esp32:
            esp32.close()
    except Exception:
        pass
    esp32 = None
    ports = sorted(glob.glob("/dev/serial/by-id/*")) + sorted(glob.glob("/dev/ttyUSB*"))
    for port in ports:
        try:
            esp32 = serial.Serial(port, 115200, timeout=0, write_timeout=0.2)
            time.sleep(2)
            print("Serial connected on", port)
            return True
        except (serial.SerialException, OSError):
            continue
    return False


open_serial()

lock = threading.Lock()
state = {"left": 0.0, "right": 0.0, "label": "STOP", "jpeg": None, "searching": False}
kernel = np.ones((5, 5), np.uint8)

# latest camera frame, filled by the grabber thread (avoids stale buffered frames)
cam = {"frame": None, "id": 0}
cam_lock = threading.Lock()


def grab_loop():
    while True:
        ret, frame = cap.read()
        if not ret:
            time.sleep(0.05)
            continue
        with cam_lock:
            cam["frame"] = frame
            cam["id"] += 1


def get_mask(roi):
    blur = cv2.GaussianBlur(roi, (5, 5), 0)
    hsv = cv2.cvtColor(blur, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, (0, 0, 0), (180, 255, V_MAX))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    return mask


def centroid_x(mask_part, w, prev_x=None):
    """Centroid (0..1) of the best dark blob: the largest one, or the one
    closest to prev_x when several are comparable in size."""
    cnts, _ = cv2.findContours(mask_part, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    best = None
    best_score = None
    for c in cnts:
        area = cv2.contourArea(c)
        if area < MIN_LINE_PIXELS:
            continue
        M = cv2.moments(c)
        if M["m00"] == 0:
            continue
        cx = (M["m10"] / M["m00"]) / w
        score = area
        if prev_x is not None:
            score = area * (1.0 - min(abs(cx - prev_x), 1.0) * 0.6)
        if best_score is None or score > best_score:
            best_score = score
            best = cx
    return best


def zigzag_command(t, first_dir):
    """
    Returns (left, right, sweep_index) for t seconds since the search began,
    or None when all sweeps are done.
    first_dir: +1 = start by turning right, -1 = start by turning left.
    """
    start = 0.0
    prev_a = 0.0
    for k in range(ZIG_SWEEPS):
        a_k = ZIG_STEP_TIME * (1 + ZIG_GROWTH * k)
        dur = a_k if k == 0 else prev_a + a_k
        if t < start + dur:
            d = first_dir if k % 2 == 0 else -first_dir
            l = ZIG_FORWARD + d * ZIG_SPEED
            r = ZIG_FORWARD - d * ZIG_SPEED
            return float(l), float(r), k + 1
        start += dur
        prev_a = a_k
    return None


def vision_loop():
    x_s = None
    last_seen = 0.0
    last_side = 1
    search_t0 = None
    left = right = 0.0
    label = "STOP"
    searching = False
    n = 0
    last_id = -1
    lost_logged = False

    while True:
        with cam_lock:
            frame = cam["frame"]
            fid = cam["id"]
        if frame is None:
            with lock:
                state.update(left=0.0, right=0.0, label="STOP", searching=False)
            time.sleep(0.05)
            continue
        if fid == last_id:
            time.sleep(0.005)
            continue
        last_id = fid
        frame = frame.copy()

        h, w = frame.shape[:2]
        top = int(ROI_START * h)
        roi = frame[top:h, :]
        mask = get_mask(roi)
        mh = mask.shape[0]
        mid = mh // 2

        x_far = centroid_x(mask[:mid, :], w, x_s)
        x_near = centroid_x(mask[mid:, :], w, x_s)
        now = time.time()

        if x_near is not None and x_far is not None:
            x = (1 - FAR_WEIGHT) * x_near + FAR_WEIGHT * x_far
        else:
            x = x_near if x_near is not None else x_far

        if x is not None:
            # ---------- line visible: proportional steering ----------
            search_t0 = None
            searching = False
            lost_logged = False
            x_s = x if x_s is None else SMOOTHING * x_s + (1 - SMOOTHING) * x
            err = (x_s - 0.5) / 0.5
            if abs(err) > SIDE_MIN:
                last_side = 1 if err > 0 else -1

            e = max(0.0, abs(err) - DEADZONE) / (1 - DEADZONE)
            turn = float(np.clip(e * TURN_GAIN, 0.0, 1.0))
            zone = "CENTER" if e == 0 else ("RIGHT" if err > 0 else "LEFT")

            outer = BASE_SPEED
            inner = BASE_SPEED * (1 - (1 + REVERSE) * turn)

            if zone == "LEFT":
                l, r = inner, outer
            elif zone == "RIGHT":
                l, r = outer, inner
            else:
                l, r = outer, outer

            if SWAP_STEERING:
                l, r = r, l

            left, right = l, r
            label = f"{zone} L{left:.0f} R{right:.0f}"
            last_seen = now
            cv2.circle(frame, (int(x_s * w), top + mh // 2), 8, (0, 0, 255), -1)

        elif now - last_seen <= LOST_HOLD:
            if not lost_logged:                     # debug: why was the line lost?
                lost_logged = True
                print(f"[LOST] last x_s={x_s if x_s is None else round(x_s, 2)} "
                      f"last_side={last_side} dark_px={int(cv2.countNonZero(mask))} "
                      f"left={left:.0f} right={right:.0f}")
            # lost briefly: keep last values

        elif now - last_seen <= LOST_HOLD + RECOVER_TIME:
            # ---------- line probably slid out of view: pivot toward last side ----------
            x_s = None
            l = ZIG_FORWARD + last_side * ZIG_SPEED
            r = ZIG_FORWARD - last_side * ZIG_SPEED
            if SWAP_STEERING:
                l, r = r, l
            left, right = l, r
            searching = True
            label = f"RECOVER L{left:.0f} R{right:.0f}"

        else:
            # ---------- still lost: zig-zag search ----------
            x_s = None
            if search_t0 is None:
                search_t0 = now
            cmd = zigzag_command(now - search_t0, last_side)
            if cmd is not None:
                l, r, k = cmd
                if SWAP_STEERING:
                    l, r = r, l
                left, right = l, r
                searching = True
                label = f"ZIGZAG {k}/{ZIG_SWEEPS} L{left:.0f} R{right:.0f}"
            else:
                left = right = 0.0
                searching = False
                label = "NO LINE"

        n += 1
        if n % STREAM_EVERY == 0:
            cl = int(w * (0.5 - DEADZONE / 2))   # red line  (= w/3 when DEADZONE = 1/3)
            cr = int(w * (0.5 + DEADZONE / 2))   # blue line (= 2w/3)
            cv2.rectangle(frame, (0, top), (w, h), (0, 255, 0), 2)
            cv2.line(frame, (0, top + mid), (w, top + mid), (0, 255, 255), 1)
            cv2.line(frame, (cl, top), (cl, h), (0, 0, 255), 2)
            cv2.line(frame, (cr, top), (cr, h), (255, 0, 0), 2)
            cv2.putText(frame, label, (10, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
            small = cv2.resize(mask, (160, 48))
            frame[0:48, w - 160:w] = cv2.cvtColor(small, cv2.COLOR_GRAY2BGR)
            ok, buf = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 60])
            if ok:
                with lock:
                    state["jpeg"] = buf.tobytes()

        with lock:
            state.update(left=left, right=right, label=label, searching=searching)


def kick(v):
    """Lift small non-zero speeds to MIN_PWM so the motors actually move."""
    iv = int(round(v))
    if MIN_PWM <= 0 or iv == 0:
        return iv
    return int(np.sign(iv) * max(abs(iv), MIN_PWM))


def sender_loop():
    """Sends wheel speeds. Smooth while following, fast while recovering/zig-zagging."""
    cur_l = cur_r = 0.0
    last = None
    dt = 1.0 / SEND_HZ
    while True:
        with lock:
            tl, tr = state["left"], state["right"]
            label, searching = state["label"], state["searching"]

        step = (ZIG_SLEW if searching else SLEW) * dt
        cur_l += float(np.clip(tl - cur_l, -step, step))
        cur_r += float(np.clip(tr - cur_r, -step, step))

        try:
            if esp32 is None:
                raise serial.SerialException("not connected")
            esp32.write(f"DRIVE,{kick(cur_l)},{kick(cur_r)}\n".encode())
        except (serial.SerialException, OSError):
            print("Serial lost, reconnecting...")
            time.sleep(0.5)
            open_serial()

        key = label.split(" L")[0]
        if key != last:
            print(label)
            last = key
        time.sleep(dt)


def generate_frames():
    while True:
        with lock:
            jpg = state["jpeg"]
        if jpg:
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + jpg + b'\r\n')
        time.sleep(0.05)


@app.route('/')
def video():
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


if __name__ == "__main__":
    threading.Thread(target=grab_loop, daemon=True).start()
    threading.Thread(target=vision_loop, daemon=True).start()
    threading.Thread(target=sender_loop, daemon=True).start()
    try:
        app.run(host='0.0.0.0', port=5000, threaded=True)
    finally:
        try:
            esp32.write(b"DRIVE,0,0\n")
        except Exception:
            pass
