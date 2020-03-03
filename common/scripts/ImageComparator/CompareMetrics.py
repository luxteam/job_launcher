import numpy as np
import cv2


class CompareMetrics(object):

    def __init__(self, file1, file2):

        self.file1 = file1
        self.file2 = file2

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
            self.diff_pixeles = -1
            return self.diff_pixeles

        diffR = abs(img1R - img2R)
        diffG = abs(img1G - img2G)
        diffB = abs(img1B - img2B)
        # diffA = abs(img1A - img2A)

        self.diff_pixeles = len(list(filter(
            lambda x: x[0] <= tolerance and x[1] <= tolerance and x[2] <= tolerance,
            zip(diffR.ravel(), diffG.ravel(), diffB.ravel())
        )))

        # get percent
        self.diff_pixeles = len(diffR.ravel()) - self.diff_pixeles
        self.diff_pixeles = float(self.diff_pixeles / len(diffR.ravel())) * 100

        return round(self.diff_pixeles, 2)

    def getPrediction(self, max_size=1000, div_image_path=False):

        if self.img1.shape != self.img2.shape:
            return -1

        kernel_size = (5, 5)

        img_1 = cv2.GaussianBlur(self.img1, kernel_size, 0)
        img_2 = cv2.GaussianBlur(self.img2, kernel_size, 0)

        sub = np.abs(img_1 - img_2).astype(np.uint8)

        median = cv2.medianBlur(sub, 9)

        kernel = np.ones(kernel_size, np.uint8)
        median = cv2.morphologyEx(median, cv2.MORPH_CLOSE, kernel)

        median = cv2.cvtColor(median, cv2.COLOR_BGR2GRAY)
        ret, median = cv2.threshold(median, 10, 255, cv2.THRESH_BINARY)

        if div_image_path:
            cv2.imwrite(div_image_path, median)

        labels = cv2.connectedComponents(median)[1]
        stat = np.unique(labels, return_counts=True)

        # number of objects
        # print("Count:", max(stat[0]))

        new_list = sorted(stat[1], reverse=True)
        new_list[0] = 0

        # maximum object size
        # print("Max:", max(new_list))

        # 1 - there is a difference. 0 - there isn't a difference
        return 1 if max(new_list) >= max_size else 0
