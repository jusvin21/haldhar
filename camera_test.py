import cv2

camera = cv2.VideoCapture(0)

if not camera.isOpened():
    print("Error: webcam could not be opened.")
    exit()

print("Webcam started. Press q to close.")

while True:
    success, frame = camera.read()

    if not success:
        print("Error: could not read a frame.")
        break

    cv2.imshow("AlertRide Camera Test", frame)

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

camera.release()
cv2.destroyAllWindows()
