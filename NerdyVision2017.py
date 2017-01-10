import cv2
import numpy as np
import math
import sys
import time
from networktables import NetworkTable
import logging
logging.basicConfig(level=logging.DEBUG)

"""2017 FRC Vision testing on laptop with webcam"""
__author__ = "tedfoodlin"

# Capture video from camera
cap = cv2.VideoCapture(0)

# Set modes (if you don't want user input)
CAL_MODE_ON = False
TRACK_MODE_ON = True
SHOOTING = True
GEARS = False

# HSV range values for different colors
LOWER_GREEN = np.array([70, 20, 20])
UPPER_GREEN = np.array([90, 230, 230])

# Set HSV range
LOWER_LIM = LOWER_GREEN
UPPER_LIM = UPPER_GREEN

# Mac webcam dimensions (approx)
MAC_FRAME_X = 1280
MAC_FRAME_Y = 720
MAC_FOV_ANGLE = 60
MAC_FOCAL_LENGTH = 15.118110236

# Dimensions in use
FRAME_X = MAC_FRAME_X
FRAME_Y = MAC_FRAME_Y
FOV_ANGLE = MAC_FOV_ANGLE
FOCAL_LENGTH = MAC_FOCAL_LENGTH
FRAME_CX = FRAME_X / 2
FRAME_CY = FRAME_Y / 2

# Calibration box dimensions
CAL_AREA = 1600
CAL_SIZE = int(math.sqrt(CAL_AREA))
CAL_UP = FRAME_CY + (CAL_SIZE / 2)
CAL_LO = FRAME_CY - (CAL_SIZE / 2)
CAL_R = FRAME_CX - (CAL_SIZE / 2)
CAL_L = FRAME_CX + (CAL_SIZE / 2)
CAL_UL = (CAL_L, CAL_UP)
CAL_LR = (CAL_R, CAL_LO)

# Gear dimensions
MAX_AREA = 2000
MIN_AREA = 4000


def check_modes():
    """Check which modes are on based on user input."""
    cal = False
    track = False
    shooting = False
    gears = False
    if raw_input("Calibration mode on? (y/n)") == "y":
        cal = True
    if raw_input("Tracking mode on? (y/n)") == "y":
        track = True
        if raw_input("Shooting mode on? (y/n)") == "y":
            shooting = True
        if raw_input("Gears mode on? (y/n)") == "y":
            gears = True
    return cal, track, shooting, gears


def calibration_box(img):
    """Return HSV color in the calibration box."""
    cv2.rectangle(img, CAL_UL, CAL_LR, (0, 255, 0), thickness=1)
    roi = img[CAL_LO:CAL_UP, CAL_R:CAL_L]
    average_color_per_row = np.average(roi, axis=0)
    average_color = np.average(average_color_per_row, axis=0)
    average_color = np.uint8([[average_color]])
    hsv = cv2.cvtColor(average_color, cv2.COLOR_BGR2HSV)
    return hsv


def masking(lower, upper, frame):
    """Mask for specified color ranges."""
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, lower, upper)
    res = cv2.bitwise_and(frame, frame, mask=mask)
    return res, mask


def draw_static(img):
    """Draw references on frame."""
    # draw center of frame
    cv2.circle(img, (FRAME_CX, FRAME_CY), 5,
               (0, 0, 255), -1)
    # draw reference line for x position
    cv2.line(img, (FRAME_CX, 0), (FRAME_CX, FRAME_Y),
             (0, 0, 255), 2)


def polygon(c):
    """Remove concavities from a contour and turn it into a polygon."""
    hull = cv2.convexHull(c)
    epsilon = 0 * cv2.arcLength(hull, True)
    goal = cv2.approxPolyDP(hull, epsilon, True)
    return goal


def calc_center(M):
    """Detect the center given the moment of a contour."""
    cx = int(M['m10'] / M['m00'])
    cy = int(M['m01'] / M['m00'])
    return cx, cy


def calc_horiz_angle(error):
    """Calculates the horizontal angle from pixel error"""
    return math.atan(error / FOCAL_LENGTH)


def is_aligned(angle_to_turn):
    """Check if shooter is aligned and ready to shoot."""
    if 1 > angle_to_turn > -1:
        return True
    else:
        return False


def average(x1, x2):
    """"Take average of 2 numbers"""
    return (x1 + x2) / 2


def report_command(error):
    """Testing - show robot commands in terminal."""
    if 1 > error > -1:
        print("X Aligned")
    else:
        if error > 10:
            print("Turn Right")
        elif error < -10:
            print("Turn Left")


def report_y(cy):
    """Report state of y to terminal."""
    # Maybe useful but not necessary if you have a nice set shooter angle
    if FRAME_CY + 10 > cy > FRAME_CY - 10:
        print("Y Aligned")
    else:
        if cy > FRAME_CY + 10:
            print("Aim Lower")
        elif cy < FRAME_CY - 10:
            print("Aim Higher")


def main():
    # set modes (default without user input)
    cal_mode_on = CAL_MODE_ON
    track_mode_on = TRACK_MODE_ON

    shooting = SHOOTING
    gears = GEARS

    # turn on modes specified by user
    # comment out next line if this feature is not desired
    cal_mode_on, track_mode_on, shooting, gears = check_modes()

    # network table setup
    NetworkTable.setIPAddress("127.0.0.1")
    NetworkTable.setClientMode()
    NetworkTable.initialize()
    SmartDashboard = NetworkTable.getTable("NerdyVision")

    # adjust camera settings
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_X)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_Y)
    # cap.set(cv2.CAP_PROP_FPS,30)
    cap.set(cv2.CAP_PROP_EXPOSURE, -8.0)

    # set up FPS list and iterator
    times = [0] * 25
    time_idx = 0
    time_start = time.time()
    camfps = 0

    while 687:
        ret, frame = cap.read()

        # compute FPS information
        time_end = time.time()
        times[time_idx] = time_end - time_start
        time_idx += 1
        if time_idx >= len(times):
            camfps = 1 / (sum(times) / len(times))
            time_idx = 0
        if time_idx > 0 and time_idx % 5 == 0:
            camfps = 1 / (sum(times) / len(times))
        time_start = time_end
        print("FPS: " + str(camfps))
        print("Time: " + str(time.time()))

        # calibration
        if cal_mode_on:
            print(np.array_str(calibration_box(frame)))
            cv2.imshow("NerdyCalibration", frame)

        # tracking
        elif track_mode_on:
            # init values (for x)
            angle_to_turn = 0
            aligned = False

            # gaussian blur to remove noise
            blur = cv2.GaussianBlur(frame, (11, 11), 0)

            # remove everything but specified color
            res, mask = masking(LOWER_LIM, UPPER_LIM, blur)

            # draw references
            draw_static(res)

            # find contour of goal
            cnts = cv2.findContours(mask.copy(), cv2.RETR_EXTERNAL,
                                    cv2.CHAIN_APPROX_SIMPLE)[-2]
            center = None

            if shooting:
                # only proceed if at least one contour was found
                if len(cnts) > 0:
                    # find the largest contour (closest goal) in the mask
                    c = max(cnts, key=cv2.contourArea)

                    # make sure the largest contour is significant
                    area = cv2.contourArea(c)

                    goal = polygon(c)

                    # draw the contour
                    cv2.drawContours(res, [goal], 0, (255, 0, 0), 5)

                    # calculate centroid
                    M = cv2.moments(goal)
                    if M['m00'] > 0:
                        cx, cy = calc_center(M)
                        center = (cx, cy)

                        # draw centroid
                        cv2.circle(res, center, 5, (255, 0, 0), -1)

                        # calculate error in degrees
                        error = cx - FRAME_CX
                        angle_to_turn = calc_horiz_angle(error)
                        print("Angle to turn: " + str(angle_to_turn))

                        # check if shooter is aligned
                        aligned = is_aligned(angle_to_turn)
                        print("Aligned: " + str(aligned))

                        report_command(error)
                        report_y(cy)

            elif gears:
                # only proceed if at least two contours (two blocks around peg) was found
                if len(cnts) > 1:
                    goals = [0]
                    # find the two blocks in the mask based on areas
                    for c in cnts:
                        area = cv2.contourArea(c)
                        if MIN_AREA < area < MAX_AREA:
                            goals.append(c)

                    # draw the contours
                    cv2.drawContours(res, [goals], 0, (255, 0, 0), 5)

                    centers_x = [0]
                    centers_y = [0]

                    # calculate centroids of two separate contours
                    for goal in goals:
                        M = cv2.moments(goal)
                        if M['m00'] > 0:
                            cx, cy = calc_center(M)
                            center = (cx, cy)

                            # draw centroid
                            cv2.circle(res, center, 5, (255, 0, 0), -1)

                            centers_x.append(cx)
                            centers_y.append(cy)

                    # calculate center of two contours (blocks next to peg)
                    if centers_x.len() == 2 && centers_y.len() == 2:
                        target_x = average((centers_x[0] + centers_x[1])/2)
                        target_y = average((centers_y[0] + centers_y[1])/2)
                        cv2.circle(res, (target_x, target_y), (0, 255, 0), -1)

                        # calculate angle to turn
                        error = target_x - FRAME_CX
                        angle_to_turn = calc_horiz_angle(error)
                        print("Angle to turn: " + str(angle_to_turn))

                        # check if gear mechanism is aligned
                        aligned = is_aligned(angle_to_turn)
                        print("Aligned: " + str(aligned))

                        report_command(error)
                        report_y(target_y)

            # results
            cv2.imshow("NerdyVision", res)
            try:
                # send to network tables
                SmartDashboard.putNumber('ANGLE_TO_TURN', angle_to_turn)
                SmartDashboard.putBoolean('IS_ALIGNED', aligned)
            except:
                print("DATA NOT SENDING...")

        # capture a keypress
        key = cv2.waitKey(20) & 0xFF
        # escape key
        if key == 27:
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == '__main__':
    main()