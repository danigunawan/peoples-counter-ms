"""
This script analyzes video, detects and specifies person movement direction.
If someone crosses the line the script saves this event in database
and, depends on admin and users properties, it saves photo of the event and sends email
to everyone who wants it.
Note:
The part of detecting
and tracking people is inspired by tutorial: http://www.femb.com.mx/people-counter/
-----------------------------------------------------------------------------
"""
import thread
import numpy as np
import cv2
import Person
import config
import datetime
import smtplib
from database import *
from email.mime.text import MIMEText
 
def send_email(direction, save_photo, receivers):
    # SMTP settings
    sender = config.GMAIL_USERNAME
    username = config.GMAIL_USERNAME
    password = config.GMAIL_PASSWORD

    print "Sending email..."
    # Prepare email's message
    # Date of the event
    date = datetime.datetime.now()
    SUBJECT = "Someone just walked %s!" % direction
    msg = "Date of the event: %s. " % date.strftime('%d %b %Y %H:%M:%S')
    if save_photo:
        msg += "Photo was taken."
    TO = ','.join(receivers)
    FROM = sender
    msg = MIMEText(msg)
    msg['Subject'] = SUBJECT
    msg['To'] = TO
    msg['From'] = FROM

    # Login to SMTP server
    server = smtplib.SMTP('smtp.gmail.com:587')
    server.ehlo()
    server.starttls()
    server.login(username, password)

    # Send email to receivers
    server.sendmail(FROM, receivers, msg.as_string())

    # Close connection with SMTP server
    server.quit()
    print "Email was sent"


def main():
    # Open video file
    cap = cv2.VideoCapture(0)

    # Camera view is in resolution 640x480
    w = 640
    h = 480

    # Define points coordinates
    dw = int(w/8) # Width divided by 8
    _80 = dw
    _160 = 2*dw
    _240 = 3*dw
    _320 = 4*dw
    _400 = 5*dw
    _480 = 6*dw
    _560 = 7*dw
    _640 = 8*dw

    # Define lines and texts and their coordinates
    # Line 'left border'
    pt1 = [_80, 0]
    pt2 = [_80, _480]
    left_border = np.array([pt1, pt2]).reshape((-1, 1, 2))

    # Line 'right border'
    pt1 = [_560, 0]
    pt2 = [_560, _480]
    right_border = np.array([pt1, pt2]).reshape((-1, 1, 2))

    # Line 'in'
    pt1 = [_400, 0]
    pt2 = [_400, _480]
    line_in = np.array([pt1, pt2]).reshape((-1, 1, 2))

    # Line 'out'
    pt1 = [_240, 0]
    pt2 = [_240, _480]
    line_out = np.array([pt1, pt2]).reshape((-1, 1, 2))

    # Arrow 'In'
    pt1 = [0, _320]
    pt2 = [_160, _320]
    pt3 = [_80, _240]
    pt4 = [_80, _400]
    arrow_in1 = np.array([pt1, pt2]).reshape((-1, 1, 2))
    arrow_in2 = np.array([pt2, pt3]).reshape((-1, 1, 2))
    arrow_in3 = np.array([pt2, pt4]).reshape((-1, 1, 2))

    # Arrow 'Out'
    pt1 = [_640, _320]
    pt2 = [_480, _320]
    pt3 = [_560, _240]
    pt4 = [_560, _400]
    arrow_out1 = np.array([pt1, pt2]).reshape((-1, 1, 2))
    arrow_out2 = np.array([pt2, pt3]).reshape((-1, 1, 2))
    arrow_out3 = np.array([pt2, pt4]).reshape((-1, 1, 2))

    # Text 'In'
    textIN = (_480, _400)

    # Text 'Out'
    textOUT = (_160, _400)

    # Colors:
    red = (0, 0, 255)
    green = (0, 255, 0)
    blue = (255, 0, 0)
    white = (255, 255, 255)

    # Create the background substractor - black background, white elements
    fgbg = cv2.createBackgroundSubtractorMOG2(detectShadows=True)

    # Create morphology kernels
    kernel_opening = np.ones((7, 7), np.uint8)
    kernel_closing = np.ones((7, 7), np.uint8)

    # Set minimum area
    areaMinimum = 10000

    # Variables
    people = []
    person_id = 1
    line_in_x = _400
    line_out_x = _240
    left_border_x = 50
    right_border_x = 610

    # Connect to database
    db.connect()

    # Start analyzing camera view
    while cap.isOpened():

        # Get admin's 'save photo' property
        admin = Users.select().where(Users.admin == True)
        save_photo = admin[0].save_photo

        # Create array of receivers
        query = Users.select().where(Users.send_notification == True)
        receivers = []
        for user in query:
            receivers.append(user.email)

        # Read a frame
        ret, frame = cap.read()

        # Increase person's time
        for person in people:
            person.time_to_delete()
            if person.delete:
                index = people.index(person)
                people.pop(index)
                del person

        # Use subtractor
        fgmask = fgbg.apply(frame)

        try:
            # Morphology
            ret, imBin = cv2.threshold(fgmask, 200, 255, cv2.THRESH_BINARY)
            # Opening to remove noise
            mask = cv2.morphologyEx(imBin, cv2.MORPH_OPEN, kernel_opening)
            # Closing to join white regions
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel_closing)

        except:
            # If no more frames to show
            print "Camera is off"
            # Close db connection
            db.close()
            break

        # Detect contours
        _, contours0, __ = cv2.findContours(mask, cv2.RETR_EXTERNAL,
                                            cv2.CHAIN_APPROX_SIMPLE)
        for cnt in contours0:
            # Calculate area of the countours
            area = cv2.contourArea(cnt)
            # print area
            if area > areaMinimum:
                # Calculate center point of the area
                M = cv2.moments(cnt)
                cx = int(M['m10']/M['m00'])
                cy = int(M['m01']/M['m00'])

                # Calculate area's width and height
                x, y, w, h = cv2.boundingRect(cnt)

                # Track person and specify direction of movements
                new_person = True
                for person in people:
                    # Check if there is any person, who has simillar contours
                    if abs(cx-person.x) <= w and abs(cy-person.y) <= h:
                        new_person = False
                        person.update_coords(cx, cy)
                        # If person cross the 'out' or 'in' line
                        if person.specify_direction(line_in_x, line_out_x):
                            # Date of the event
                            date = datetime.datetime.now()
                            if save_photo:
                                print 'Save image'
                                # Photo name of the event
                                date_converted = date.strftime('%d%m%Y%H%M%S')
                                photo_name = 'photo_' + date_converted + '.jpeg'
                                # Save photo
                                path = config.PHOTO_PATH + photo_name
                                cv2.imwrite(path, frame)
                            else:
                                print "Don't save image"
                                photo_name = 'no photo'

                            # Direction of the event
                            walked_in = True if person.direction == 'in' else False

                            # Save event in database
                            Events.create(walked_in=walked_in, created_at=date,
                                          updated_at=date, photo=photo_name)

                            # Send email to every who wants notifications
                            if any(receivers):
                                thread.start_new_thread(send_email,
                                                        (person.direction, save_photo, receivers))
                            else:
                                print "There are no receivers"

                        # If the person goes out of the specified area
                        if person.direction == 'in' and person.x >= right_border_x:
                            index = people.index(person)
                            people.pop(index)
                            del person
                        elif person.direction == 'out' and person.x <= left_border_x:
                            index = people.index(person)
                            people.pop(index)
                            del person
                        break

                if new_person:
                    person = Person.Person(person_id, cx, cy)
                    people.append(person)
                    person_id += 1

                # Draw countours and center point
                cv2.circle(frame, (cx, cy), 5, (255, 255, 255), -1)
                cv2.drawContours(frame, cnt, -1, (255, 0, 0), 3, 8)
                cv2.rectangle(frame, (x, y), (x+w, y+h), blue, 2)

        # Draw GUI

        # Line 'In'
        cv2.polylines(frame, [line_in], False, green, 2)

        # Line 'Out'
        cv2.polylines(frame, [line_out], False, red, 2)

        # Left border
        cv2.polylines(frame, [left_border], False, white, 1)

        # Right border
        cv2.polylines(frame, [right_border], False, white, 1)

        # Text 'In'
        cv2.putText(frame, 'In', textIN, cv2.FONT_HERSHEY_SIMPLEX, 1,
                    green, 2, cv2.LINE_AA)

        # Text 'Out'
        cv2.putText(frame, 'Out', textOUT, cv2.FONT_HERSHEY_SIMPLEX, 1,
                    red, 2, cv2.LINE_AA)

        # Arrow 'In'
        cv2.polylines(frame, [arrow_in1], False, green, 1)
        cv2.polylines(frame, [arrow_in2], False, green, 1)
        cv2.polylines(frame, [arrow_in3], False, green, 1)

        # Arrow 'Out'
        cv2.polylines(frame, [arrow_out1], False, red, 1)
        cv2.polylines(frame, [arrow_out2], False, red, 1)
        cv2.polylines(frame, [arrow_out3], False, red, 1)

        # Show camera view
        cv2.imshow('Monitoring system', frame)

        # Show mask
        # cv2.imshow('Mask', mask)

        # Abort and exit with 'Q' or ESC
        k = cv2.waitKey(30) & 0xff
        if k == 27:
            break

    # Release video
    cap.release()

    # Close all OpenCV windows
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
