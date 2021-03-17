from typing import Optional
from fastapi import FastAPI
from fastapi.responses import StreamingResponse, HTMLResponse
from imutils.video import VideoStream
import threading
import datetime
import imutils
import time
import cv2
from motion_detection.singlemotiondetector import SingleMotionDetector

# initialize the output frame and a lock used to ensure thread-safe exchanges of the output frame
outputFrame = None
lock = threading.Lock()

app = FastAPI()

# initialize the video stream and allow the camer sensor to warmup
vs = VideoStream(usePiCamera=1).start()
#vs = VideoStream(src=0).start()
time.sleep(2.0)


def detect_motion(frameCount):
    # grab the global references to the video stream, output feed, and lock variables
    global vs, outputFrame, lock

    # initialize the motion detector and the totaol number of frames read thus far
    md = SingleMotionDetector(accumWeight=0.1)
    total = 0
    print("performing motion detection")
    # loop over frames from the video stream
    while True:
        # read the net frame from the video stream, resize it, convert to grayscale and blur
        frame = vs.read()
        frame = imutils.resize(frame, width=400)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (7,7), 0)

        # grab the current timestamp and draw it on the frame
        timestamp = datetime.datetime.now()
        cv2.putText(frame, timestamp.strftime("%A %d %B %Y %I:%M:%S%p"), (10, frame.shape[0] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 0, 255), 1)

        # if the total number of frames has reached a sufficient
        # number to construct a reasonable background model, then
        # continue to process the frame
        if total > frameCount:
            # detect motion in the image
            motion = md.detect(gray)
            # check to see if motion was found in the frame
            if motion is not None:
                # unpack the tuple and draw the box surrounding the
                # "motion area" on the output frame
                (thresh, (minX, minY, maxX, maxY)) = motion
                cv2.rectangle(frame, (minX, minY), (maxX, maxY), (0, 0, 255), 2)
            
        # update the background model and increment the total number
        # of frames read thus far
        md.update(gray)
        total += 1
        # acquire the lock, set the output frame, and release the
        # lock
        with lock:
            outputFrame = frame.copy()

def generate():
    # grab global references to the output frame and lock variables
    global outputFrame, lock
    # loop over frames from the output stream
    while True:
        # wait until the lock is acquired
        with lock:
            # check if the output frame is available, otherwise skip
            # the iteration of the loop
            if outputFrame is None:
                continue
            # encode the frame in JPEG format
            (flag, encodedImage) = cv2.imencode(".jpg", outputFrame)
            # ensure the frame was successfully encoded
            if not flag:
                continue
        # yield the output frame in the byte format
        yield(b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + bytearray(encodedImage) + b'\r\n')
        

@app.get("/")
async def read_index():
    html_content = """
    <html>
        <head>
            <title>Some HTML in here</title>
        </head>
        <body>
            <h1>HTML!</h1>
            <h1>Video</h1>
            <img src="http://localhost:8080/video_feed">
         </body>
    </html>
    """
    return HTMLResponse(content=html_content, status_code=200)

@app.get("/ping")
def read_root():
    return {"pong"}




@app.get("/items/{item_id}")
def read_item(item_id: int, q: Optional[str] = None):
    return {"item_id": item_id, "q": q}


@app.get("/video_feed")
def video_feed():
    # return the response generated along with the specific media
    # type (mime type)
    # return StreamingResponse(generate())
    return StreamingResponse(generate(), media_type="multipart/x-mixed-replace;boundary=frame")


#if __name__ == '__main__':
    
# start a thread that will perform motion detection
t = threading.Thread(target=detect_motion, args=(32,))
t.deamon = True
t.start()

# needed? release the video pointer()
