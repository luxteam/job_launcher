import argparse
import sys
import numpy as np
import cv2
from numpy.lib.function_base import percentile


class CompareMetrics(object):

    def __init__(self, file1, file2):

        self.file1 = file1
        self.file2 = file2
        self.diff_pixels = 0
        self.img1 = 0
        self.img2 = 0
        self.readImages()

    def readImages(self):
        self.img1 = cv2.imread(self.file1).astype(np.float32)
        self.img2 = cv2.imread(self.file2).astype(np.float32)

    def getDiffPixeles(self, tolerance=3):

        img1R = self.img1[:, :, 0]
        img1G = self.img1[:, :, 1]
        img1B = self.img1[:, :, 2]
        # img1A = self.img1[:, :, 3]

        img2R = self.img2[:, :, 0]
        img2G = self.img2[:, :, 1]
        img2B = self.img2[:, :, 2]
        # img2A = self.img2[:, :, 3]

        if img1R.shape != img2R.shape:
            self.diff_pixels = -1
            return self.diff_pixels

        diffR = abs(img1R - img2R)
        diffG = abs(img1G - img2G)
        diffB = abs(img1B - img2B)
        # diffA = abs(img1A - img2A)

        self.diff_pixels = len(list(filter(
            lambda x: x[0] <= tolerance and x[1] <= tolerance and x[2] <= tolerance,
            zip(diffR.ravel(), diffG.ravel(), diffB.ravel())
        )))

        # get percent
        self.diff_pixels = len(diffR.ravel()) - self.diff_pixels
        self.diff_pixels = float(self.diff_pixels / len(diffR.ravel())) * 100

        return round(self.diff_pixels, 2)

    def getPrediction(self, max_size=1000, div_image_path=False, mark_failed_if_black=True):

        if self.img1.shape != self.img2.shape:
            return -1

        # if img1 is full black - mark as different
        if not np.any(self.img1) and mark_failed_if_black:
            return 2

        img_1 = cv2.GaussianBlur(self.img1, (5, 5), 0)
        img_2 = cv2.GaussianBlur(self.img2, (5, 5), 0)

        sub = np.abs(img_1 - img_2).astype(np.uint8)

        median = cv2.medianBlur(sub, 9)

        kernel = np.ones((5, 5), np.uint8)
        median = cv2.morphologyEx(median, cv2.MORPH_CLOSE, kernel)

        median = cv2.cvtColor(median, cv2.COLOR_BGR2GRAY)
        ret, median = cv2.threshold(median, 10, 255, cv2.THRESH_BINARY)

        if div_image_path:
            cv2.imwrite(div_image_path, median)

        labels = cv2.connectedComponents(median)[1]
        stat = np.unique(labels, return_counts=True)

        # number of objects
        # print("Count:", max(stat[0]))

        a = np.delete(stat[1], np.where(stat[1] == max(stat[1])))

        try:

            # maximum object size
            # print("Max:", max(a))

            # 1 - there is a difference. 0 - there isn't a difference
            return 0 if max(a) <= max_size and median[0][0] != 255 else 1

        except ValueError:

            # maximum object = 0. No blobs
            # print("Max: 0")

            # 1 - there is a difference. 0 - there isn't a difference
            return 0 if median[0][0] != 255 else 1


# Commandline interface for CompareMetrics. Return percentage of images diffrence. 0 - the same, 100 - completely different
if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--img1', required=True, help='First image for comparison')
    p.add_argument('--img2', required=True, help='Second image for comparison')
    args = p.parse_args()
    pixDiff = CompareMetrics(args.img1, args.img2).getDiffPixeles()
    # if images are completely different, getDiffPixeles returns -1
    print(100.0 if pixDiff == -1 else pixDiff)
