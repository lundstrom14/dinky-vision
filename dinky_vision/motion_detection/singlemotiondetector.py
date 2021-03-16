##
## Code from pyimagesearch.com
##
import numpy as numpy
import imutils
import cv2


class SingleMotionDetector:
    def __init__(self, accumWeight=0.5): # accumWeight=0.5 weights the background and foreground evenly
        # store the accumulated weight factor
        self.accumWeight = accumWeight

        # initialize the background model
        self.bg = None

    def update(self, image):
        # if the background model is None, initialize it
        if self.bg is None:
            self.bg = image.copy().astype("float")
            return
        
        # update the background model by accumulating the weighted average
        cv2.accumulateWeighted(image, self.bg, self.accumWeight)

    def detect (self, image, tVal=25):  # tVal: the threshold value used to mark a particular pixel as motion or not
        #comute the absolute difference between the background model and the image passed in, then thershold the delta image
        delta = cv2.absdiff(self.bg.astype("uint8"), image)
        thresh = cv2.threshold(delta, tVal, 255, cv2.THRESH_BINARY)[1]

        # perform a series of erosions and dilations to remove small blombs
        thresh = cv2.erode(thresh, None, iterations=2)
        thresh = cv2.dilate(thresh, None, iterations=2)

        
        # find contours in the thresholded image and initialize the minimum and maximum bounding box regions for motion
        cnts = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cnts = imutils.grab_contours(cnts)
        
        # bounding boxes bookmarking
        (minX, minY) = (np.inf, np.inf)
        (maxX, maxY) = (-np.inf, -np.inf)

        # if no contours were found, return None
        if len(cnts) == 0:
            return None
         
        # otherwhise, loop over the contours
        for c in cnts:
            # compute the bounding box of the contour and use it to update the minimum and maximum bounding box regions
            (x,y,w,h) = cv2.boundingRect(c)
            (minX, minY) = (min(minX, x), min(minY, y))
            (maxX, maxY) = (max(maxX, x+w), max(maxY, y+h))
        
        # otherwhise, return a tuple of the thresholded image along with bounding box
        return (thresh, (minX, minY, maxX, maxY))