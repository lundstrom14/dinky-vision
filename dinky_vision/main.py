from typing import Optional
from fastapi import FastAPI, Request
from pydantic import BaseModel
from fastapi.responses import StreamingResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
# from library.helpers import openfile


from imutils.video import VideoStream
import threading
import datetime
import imutils
import time
import cv2
from motion_detection.singlemotiondetector import SingleMotionDetector


class Setting(BaseModel):
    name: str
    enabled: bool


enable_motion_detection = True
enable_edge_detection = False

# initialize the output frame and a lock used to ensure thread-safe exchanges of the output frame
outputFrame = None
lock = threading.Lock()

app = FastAPI()
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")


# initialize the video stream and allow the camer sensor to warmup
vs = VideoStream(usePiCamera=1).start()
# vs = VideoStream(src=0).start()
time.sleep(2.0)


def display_video(frameCount):
    # grab the global references to the video stream, output feed, and lock variables
    global vs, outputFrame, lock, enable_motion_detection

    # initialize the motion detector and the total number of frames read thus far
    md = SingleMotionDetector(accumWeight=0.1)
    total = 0
    nextFrame = None

    # loop over frames from the video stream
    while True:
        # read the net frame from the video stream, resize it, convert to grayscale and blur
        frame = vs.read()
        frame = imutils.resize(frame, width=400)
        
        # grab the current timestamp and draw it on the frame
        timestamp = datetime.datetime.now()
        cv2.putText(frame, timestamp.strftime("%c"), (10, frame.shape[0] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 0, 255), 1)

        # enable motion detection
        if (enable_motion_detection):
            
            # convert to grayscale and blur for the background model
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            gray = cv2.GaussianBlur(gray, (7, 7), 0)
            
            # if the total number of frames has reached a sufficient
            # number to construct a reasonable background model, then
            # continue to process the frame
            if total > frameCount:

                # detect motion in the image
                motion = md.detect(gray)
                # check to see if motion was found in the frame
                if motion is not None:
                    # unpack the tuple and draw the box surrounding the
                    # "motion area" on the output frame, and set the next frame
                    (thresh, (minX, minY, maxX, maxY)) = motion
                    cv2.rectangle(frame, (minX, minY), (maxX, maxY), (0, 0, 255), 2)
                    nextFrame = frame.copy()
                    # print("motion detected..")
        
            # update the background model and increment the total number
            # of frames read thus far
            md.update(gray)
            total += 1

        if (enable_edge_detection):
            None

        # If nextFrame has not been assigned.
        if nextFrame is None:
            nextFrame = frame.copy()

        # acquire the lock, set the output frame, and release the
        # lock
        with lock:
            outputFrame = nextFrame


def detect_motion(frameCount):
    # grab the global references to the video stream, output feed, and lock variables
    global vs, outputFrame, lock

    # initialize the motion detector and the total number of frames read thus far
    md = SingleMotionDetector(accumWeight=0.1)
    total = 0
    # loop over frames from the video stream
    while True:
        # read the net frame from the video stream, resize it, convert to grayscale and blur
        frame = vs.read()
        frame = imutils.resize(frame, width=400)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (7, 7), 0)

        # grab the current timestamp and draw it on the frame
        timestamp = datetime.datetime.now()
        cv2.putText(frame, timestamp.strftime("%c"), (10, frame.shape[0] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 0, 255), 1)

        # if the total number of frames has reached a sufficient
        # number to construct a reasonable background model, then
        # continue to process the frame
        if total > frameCount and enable_motion_detection:
            # detect motion in the image
            motion = md.detect(gray)
            # check to see if motion was found in the frame
            if motion is not None:
                # unpack the tuple and draw the box surrounding the
                # "motion area" on the output frame
                (thresh, (minX, minY, maxX, maxY)) = motion
                cv2.rectangle(frame, (minX, minY), (maxX, maxY), (0, 0, 255), 2)
                # print("motion detected..")
      
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


@app.get("/home")
async def read_index():
    html_content = """
    <html>
        <head>
            <title>Some HTML in here</title>
        </head>
        <body>
            <h1>HTML!</h1>
            <h1>Video</h1>
            <img src="../video_feed">
         </body>
    </html>
    """
    return HTMLResponse(content=html_content, status_code=200)


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    filepath = "pages/home.html"
    with open(filepath, "r", encoding="utf-8") as input_file:
        html = input_file.read()
    data = {
        "text": html
    }
    return templates.TemplateResponse("page.html", {"request": request, "data": data})


@app.get("/page/{page_name}", response_class=HTMLResponse)
async def page(request: Request, page_name: str):
    filepath = "pages/" + page_name + ".html"
    with open(filepath, "r", encoding="utf-8") as input_file:
        html = input_file.read()
    data = {
        "text": html
    }
    return templates.TemplateResponse("page.html", {"request": request, "data": data})


@app.get("/items/{item_id}")
def read_item(item_id: int, q: Optional[str] = None):
    return {"item_id": item_id, "q": q}


@app.get("/video_feed")
def video_feed():
    # return the response generated along with the specific media
    # type (mime type)
    # return StreamingResponse(generate())
    return StreamingResponse(generate(), media_type="multipart/x-mixed-replace;boundary=frame")


@app.get("/ping")
def read_root():
    return {"pong"}

@app.post("/api/motion-detection")
def setting_motion_detection(setting: Setting):
    global enable_motion_detection
    if (setting.name == "motion-detection") and setting.enabled:
        enable_motion_detection = True
    else:
        enable_motion_detection = False

    print(enable_motion_detection)
    return None

# if __name__ == '__main__':


# start a thread that will perform motion detection
try:
    t = threading.Thread(target=display_video, args=(32,))
    t.deamon = True
    t.start()
except (KeyboardInterrupt, SystemExit):
    exit()


# needed? release the video pointer()
