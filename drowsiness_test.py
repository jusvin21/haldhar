import cv2
import mediapipe as mp
import math
import time


LEFT_EYE = [362, 385, 387, 263, 373, 380]
RIGHT_EYE = [33, 160, 158, 133, 153, 144]

EAR_THRESHOLD = 0.25
WARNING_TIME = 0.8
DROWSY_TIME = 2.0


def distance(point_a, point_b):
    return math.hypot(
        point_a.x - point_b.x,
        point_a.y - point_b.y
    )


def calculate_ear(landmarks, eye_indices):
    p1 = landmarks[eye_indices[0]]
    p2 = landmarks[eye_indices[1]]
    p3 = landmarks[eye_indices[2]]
    p4 = landmarks[eye_indices[3]]
    p5 = landmarks[eye_indices[4]]
    p6 = landmarks[eye_indices[5]]

    vertical_1 = distance(p2, p6)
    vertical_2 = distance(p3, p5)
    horizontal = distance(p1, p4)

    if horizontal == 0:
        return 0.0

    return (vertical_1 + vertical_2) / (2.0 * horizontal)


camera = cv2.VideoCapture(0)

if not camera.isOpened():
    print("Error: Could not open webcam.")
    exit()

mp_face_mesh = mp.solutions.face_mesh

eyes_closed_since = None
previous_state = "NO_FACE"

with mp_face_mesh.FaceMesh(
    max_num_faces=1,
    refine_landmarks=True,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
) as face_mesh:

    while True:
        success, frame = camera.read()

        if not success:
            print("Could not read camera frame.")
            break

        frame = cv2.flip(frame, 1)
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = face_mesh.process(rgb_frame)

        current_time = time.time()
        state = "NO_FACE"
        average_ear = 0.0
        closed_duration = 0.0

        if results.multi_face_landmarks:
            landmarks = results.multi_face_landmarks[0].landmark

            left_ear = calculate_ear(landmarks, LEFT_EYE)
            right_ear = calculate_ear(landmarks, RIGHT_EYE)
            average_ear = (left_ear + right_ear) / 2.0

            if average_ear < EAR_THRESHOLD:
                if eyes_closed_since is None:
                    eyes_closed_since = current_time

                closed_duration = current_time - eyes_closed_since

                if closed_duration >= DROWSY_TIME:
                    state = "ALARM+VIBRATION"
                elif closed_duration >= WARNING_TIME:
                    state = "BEEP"
                else:
                    state = "AWAKE"
            else:
                eyes_closed_since = None
                state = "AWAKE"

        else:
            eyes_closed_since = None
            state = "NO_FACE"

        if state != previous_state:
            print(f"State changed: {previous_state} -> {state}")
            previous_state = state

        if state == "AWAKE":
            color = (0, 255, 0)
        elif state == "WARNING":
            color = (0, 165, 255)
        elif state == "DROWSY":
            color = (0, 0, 255)
        else:
            color = (255, 0, 255)

        cv2.putText(
            frame,
            f"EAR: {average_ear:.3f}",
            (20, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (255, 255, 0),
            2
        )

        cv2.putText(
            frame,
            f"State: {state}",
            (20, 80),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.9,
            color,
            2
        )

        cv2.putText(
            frame,
            f"Closed: {closed_duration:.1f}s",
            (20, 120),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            color,
            2
        )

        cv2.imshow("AlertRide Drowsiness Test", frame)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

camera.release()
cv2.destroyAllWindows()
