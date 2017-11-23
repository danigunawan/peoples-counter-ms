# Program based on http://www.femb.com.mx/people-counter/ tutorial
# by Federico Mejia
# -----------------------------------------------------------------------------
import cv2
import numpy as np

# Open video file
cap = cv2.VideoCapture('video.h264')

# Camera view is in resolution 360p - 480x360
w = 480
h = 360

# Define points coordinates of the lines and texts
dw = int(w/12) # Width divided by 12
_40 = dw
_80 = 2*dw
_120 = 3*dw
_160 = 4*dw
_200 = 5*dw
_240 = 6*dw
_280 = 7*dw
_320 = 8*dw
_360 = 9*dw
_400 = 10*dw
_440 = 11*dw
_480 = 12*dw

# Line 'left border'
pt1 = [_40, 0]
pt2 = [_40, _480]
left_border = np.array([pt1, pt2]).reshape((-1, 1, 2))

# Line 'right border'
pt1 = [_440, 0]
pt2 = [_440, _480]
right_border = np.array([pt1, pt2]).reshape((-1, 1, 2))

# Line 'in'
pt1 = [_280, 0]
pt2 = [_280, _480]
line_in = np.array([pt1, pt2]).reshape((-1, 1, 2))

# Line 'out'
pt1 = [_200, 0]
pt2 = [_200, _480]
line_out = np.array([pt1, pt2]).reshape((-1, 1, 2))

# Arrow 'In'
pt1 = [0, _280]
pt2 = [_80, _280]
pt3 = [_40, _240]
pt4 = [_40, _320]
arrow_in1 = np.array([pt1, pt2]).reshape((-1, 1, 2))
arrow_in2 = np.array([pt2, pt3]).reshape((-1, 1, 2))
arrow_in3 = np.array([pt2, pt4]).reshape((-1, 1, 2))

# Arrow 'Out'
pt1 = [_480, _280]
pt2 = [_400, _280]
pt3 = [_440, _240]
pt4 = [_440, _320]
arrow_out1 = np.array([pt1, pt2]).reshape((-1, 1, 2))
arrow_out2 = np.array([pt2, pt3]).reshape((-1, 1, 2))
arrow_out3 = np.array([pt2, pt4]).reshape((-1, 1, 2))

# Text 'Set camera'
textSC = (_160, _40)

# Text 'In'
textIN = (_320, _320)

# Text 'Out'
textOUT = (_120, _320)

# Colors:
red = (0, 0, 255)
green = (0, 255, 0)
blue = (255, 0, 0)
white = (255, 255, 255)

# Create the background substractor - black background, white elements
fgbg = cv2.createBackgroundSubtractorMOG2(detectShadows = True)

# Create morphology kernels
kernel_opening = np.ones((3,3),np.uint8)
kernel_closing = np.ones((11,11),np.uint8)

# Set minimum area
areaMinimum = 10000

# Variables
persons = []
pid = 1
max_p_age = 5

while(cap.isOpened()):
    # Read a frame
    ret, frame = cap.read()
  
    # Use subtractor
    fgmask = fgbg.apply(frame) 

    try:
        # Morphology
        ret,imBin= cv2.threshold(fgmask,200,255,cv2.THRESH_BINARY)
        # Opening to remove noise
        mask = cv2.morphologyEx(imBin, cv2.MORPH_OPEN, kernel_opening)
        # Closing to join white regions
        mask = cv2.morphologyEx(mask , cv2.MORPH_CLOSE, kernel_closing)
    except:
        # If no more frames to show
        print "Camera is off"
        break

    
    # Detect contours
    _, contours0, hierarchy = cv2.findContours(mask,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
    for cnt in contours0:
        
        area = cv2.contourArea(cnt)
        if area > areaMinimum:
            # Calculate center point of the area
            M = cv2.moments(cnt)
            cx = int(M['m10']/M['m00'])
            cy = int(M['m01']/M['m00'])

            # Draw countours and center point
            cv2.circle(frame,(cx,cy), 5, (255,255,255), -1)
            cv2.drawContours(frame, cnt, -1, (255,0,0), 3, 8)
           
            # Todo
            # PEOPLE TRACKING
            
    # Draw GUI

    # Line 'In'
    frame = cv2.polylines(frame, [line_in], False, green, 2)

    # Line 'Out'
    frame = cv2.polylines(frame, [line_out], False, red, 2)

    # Left border
    frame = cv2.polylines(frame, [left_border], False, white, 1)
    
    # Right border
    frame = cv2.polylines(frame, [right_border], False, white, 1)

    # Text 'In'
    cv2.putText(frame, 'In', textIN, cv2.FONT_HERSHEY_SIMPLEX, 1,
                green, 2, cv2.LINE_AA)

    # Text 'Out'
    cv2.putText(frame, 'Out', textOUT, cv2.FONT_HERSHEY_SIMPLEX, 1,
                red, 2, cv2.LINE_AA)

    # Arrow 'In'
    frame = cv2.polylines(frame, [arrow_in1], False, green, 1)
    frame = cv2.polylines(frame, [arrow_in2], False, green, 1)
    frame = cv2.polylines(frame, [arrow_in3], False, green, 1)

    # Arrow 'Out'
    frame = cv2.polylines(frame, [arrow_out1], False, red, 1)
    frame = cv2.polylines(frame, [arrow_out2], False, red, 1)
    frame = cv2.polylines(frame, [arrow_out3], False, red, 1)

    cv2.imshow('Monitoring system', frame)

    # Show mask
    # cv2.imshow('Mask', mask)

    # Abort and exit with 'Q' or ESC
    k = cv2.waitKey(30) & 0xff
    if k == 27:
        break

# Release video file
cap.release()

# Close all openCV windows
cv2.destroyAllWindows()