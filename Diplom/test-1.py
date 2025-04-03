import serial 
import cv2 
import mediapipe as mp 

# конфігурація
write_video = True
debug = False
cam_source = 0 

if not debug:
    ser = serial.Serial('COM4', 115200)

x_min = 0
x_mid = 75
x_max = 150
# використовуємо кут між зап'ястям і вказівним пальцем для керування віссю X
palm_angle_min = -50
palm_angle_mid = 20

y_min = 0
y_mid = 90
y_max = 180
# використовуємо координату Y зап'ястя для керування віссю Y
wrist_y_min = 0.3
wrist_y_max = 0.9

z_min = 10
z_mid = 90
z_max = 180
# використовуємо розмір долоні для керування віссю Z
plam_size_min = 0.1
plam_size_max = 0.3

claw_open_angle = 60
claw_close_angle = 0

servo_angle = [x_mid, y_mid, z_mid, claw_open_angle]  # [x, y, z, claw]
prev_servo_angle = servo_angle
fist_threshold = 7

mp_drawing = mp.solutions.drawing_utils
mp_drawing_styles = mp.solutions.drawing_styles
mp_hands = mp.solutions.hands

cap = cv2.VideoCapture(cam_source)

# запис відео
if write_video:
    fourcc = cv2.VideoWriter_fourcc(*'XVID')
    out = cv2.VideoWriter('output.avi', fourcc, 60.0, (640, 480))

clamp = lambda n, minn, maxn: max(min(maxn, n), minn)
map_range = lambda x, in_min, in_max, out_min, out_max: abs((x - in_min) * (out_max - out_min) // (in_max - in_min) + out_min)

# Перевірка, чи є fist (кулак)
def is_fist(hand_landmarks, palm_size):
    # обчислюємо відстань між зап'ястям і кінчиками кожного пальця
    distance_sum = 0
    WRIST = hand_landmarks.landmark[0]
    for i in [7, 8, 11, 12, 15, 16, 19, 20]:
        distance_sum += ((WRIST.x - hand_landmarks.landmark[i].x)**2 + \
                         (WRIST.y - hand_landmarks.landmark[i].y)**2 + \
                         (WRIST.z - hand_landmarks.landmark[i].z)**2)**0.5
    return distance_sum/palm_size < fist_threshold

def landmark_to_servo_angle(hand_landmarks):
    servo_angle = [x_mid, y_mid, z_mid, claw_open_angle]
    WRIST = hand_landmarks.landmark[0]
    INDEX_FINGER_MCP = hand_landmarks.landmark[5]
    # обчислюємо відстань між зап'ястям і вказівним пальцем
    palm_size = ((WRIST.x - INDEX_FINGER_MCP.x)**2 + (WRIST.y - INDEX_FINGER_MCP.y)**2 + (WRIST.z - INDEX_FINGER_MCP.z)**2)**0.5

    if is_fist(hand_landmarks, palm_size):
        servo_angle[3] = claw_close_angle
    else:
        servo_angle[3] = claw_open_angle

    # обчислюємо кут для осі X
    distance = palm_size
    angle = (WRIST.x - INDEX_FINGER_MCP.x) / distance  # обчислюємо радіан між зап'ястям і вказівним пальцем
    angle = int(angle * 180 / 3.1415926)               # перетворюємо радіан в градуси
    angle = clamp(angle, palm_angle_min, palm_angle_mid)
    servo_angle[0] = map_range(angle, palm_angle_min, palm_angle_mid, x_max, x_min)

    # обчислюємо кут для осі Y
    wrist_y = clamp(WRIST.y, wrist_y_min, wrist_y_max)
    servo_angle[1] = map_range(wrist_y, wrist_y_min, wrist_y_max, y_max, y_min)

    # обчислюємо кут для осі Z
    palm_size = clamp(palm_size, plam_size_min, plam_size_max)
    servo_angle[2] = map_range(palm_size, plam_size_min, plam_size_max, z_max, z_min)

    # перетворення значень в int
    servo_angle = [int(i) for i in servo_angle]

    return servo_angle

# ініціалізація моделі MediaPipe для виявлення рук
with mp_hands.Hands(model_complexity=0, min_detection_confidence=0.5, min_tracking_confidence=0.5) as hands:
    while cap.isOpened():
        success, image = cap.read()
        if not success:
            print("Ігноруємо порожній кадр камери.")
            continue

        # Для покращення продуктивності можна помітити, що зображення не записується
        image.flags.writeable = False
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        results = hands.process(image)

        # малюємо позначки рук на зображенні
        image.flags.writeable = True
        image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
        if results.multi_hand_landmarks:
            if len(results.multi_hand_landmarks) == 1:
                # Виявлено одну руку
                hand_landmarks = results.multi_hand_landmarks[0]
                servo_angle = landmark_to_servo_angle(hand_landmarks)

                if servo_angle != prev_servo_angle:
                    print("Кути сервоприводів: ", servo_angle)
                    prev_servo_angle = servo_angle
                    if not debug:
                        ser.write(bytearray(servo_angle))
            else:
                print("Виявлено більше ніж одну руку")
            for hand_landmarks in results.multi_hand_landmarks:
                mp_drawing.draw_landmarks(
                    image,
                    hand_landmarks,
                    mp_hands.HAND_CONNECTIONS,
                    mp_drawing_styles.get_default_hand_landmarks_style(),
                    mp_drawing_styles.get_default_hand_connections_style())
        # перевертаємо зображення для відображення в режимі "себе"
        image = cv2.flip(image, 1)
        # показуємо кути сервоприводів
        cv2.putText(image, str(servo_angle), (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2, cv2.LINE_AA)
        cv2.imshow('MediaPipe Hands', image)

        if write_video:
            out.write(image)
        if cv2.waitKey(5) & 0xFF == 27:
            if write_video:
                out.release()
            break
cap.release()
