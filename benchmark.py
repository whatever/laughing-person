#!/usr/bin/env python3


import argparse
import cv2
import laughing_person as lp
import logging
import json
import matplotlib.pyplot as plot
import os.path
import numpy as np
import random
import signal
import torch


from datetime import timedelta
from datetime import datetime
from glob import glob
from train import dataset, get_label_fname, load_label
from PIL import Image

face_cascade = cv2.CascadeClassifier('capture-images/haarcascade_frontalface_default.xml')


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def cleanup(signum, frame):
    raise SystemExit


def fix_bb(bb):
    return [
        min(bb[0], bb[2]),
        min(bb[1], bb[3]),
        max(bb[0], bb[2]),
        max(bb[1], bb[3]),
    ]

def calc_iou(bb1, bb2):
    bb1 = fix_bb(bb1)
    bb2 = fix_bb(bb2)

    # determine the coordinates of the intersection rectangle
    x_left = max(bb1[0], bb2[0])
    y_top = max(bb1[1], bb2[1])
    x_right = min(bb1[2], bb2[2])
    y_bottom = min(bb1[2], bb2[2])

    if x_right < x_left or y_bottom < y_top:
        return 0.0

    # The intersection of two axis-aligned bounding boxes is always an
    # axis-aligned bounding box
    intersection_area = (x_right - x_left) * (y_bottom - y_top)

    # compute the area of both AABBs
    bb1_area = (bb1[2] - bb1[0]) * (bb1[2] - bb1[1])
    bb2_area = (bb2[2] - bb2[0]) * (bb2[2] - bb2[1])

    # compute the intersection over union by taking the intersection
    # area and dividing it by the sum of prediction + ground-truth
    # areas - the interesection area
    iou = intersection_area / float(bb1_area + bb2_area - intersection_area)
    assert iou >= 0.0
    assert iou <= 1.0
    return iou

if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoints", nargs="+", type=str)
    parser.add_argument("--validate-dir", type=str, required=True)
    args = parser.parse_args()


    model = lp.IsMattModule()

    for model_fname in args.checkpoints:


        raise Exception("Seems like the image being sent to predict(...) is incorrect...")

        # logger.info("Loading model %s", model_fname)
        checkpoint = torch.load(model_fname)
        model.load_state_dict(checkpoint['model_state_dict'])
        model.eval()
        model = model.cuda()

        # logging.info("Validating model %s", model_fname)

        examples = sorted(fname for fname in glob(f"{args.validate_dir}/*.jpg"))
        random.shuffle(examples)
        examples = examples[0:10]


        images = []

        for image_fname in examples:
            label_fname = get_label_fname(image_fname)

            if os.path.exists(label_fname):
                with open(label_fname, "r") as fi:
                    label = json.load(fi)
                    print(json.dumps(label, indent=4))
            else:
                label = {
                    "class": 0,
                    "bbox": [0, 0, 0, 0],
                }

            img = Image.open(image_fname)
            o = lp.crop(img)
            o = np.array(o)

            face, predicted_bb, _ = model.predict(img)
            actual_bb = label["bbox"]
            actual_bb = actual_bb if len(actual_bb) == 4 else actual_bb[0]

            is_face_actual = label["class"]

            w, h = img.size
            w, h, _ = o.shape

            y = [
                int(v)
                for v in (np.array(actual_bb)*np.array([w, h, w, h])).tolist()
            ]

            y_hat = [
                int(v)
                for v in (predicted_bb[0].cpu().numpy()*np.array([w, h, w, h])).tolist()
            ]


            o = lp.crop(img)
            o = np.array(o)
            cv2.rectangle(o, (y[0], y[1]), (y[2], y[3]), (0, 255, 0), 2)
            cv2.rectangle(o, (y_hat[0], y_hat[1]), (y_hat[2], y_hat[3]), (0, 255, 255), 2)

            images.append(o.copy())


        arr = images[0]

        for i in range(1, len(images)):
            arr = np.concatenate((arr, images[i]), axis=1)

        arr = cv2.cvtColor(arr, cv2.COLOR_BGR2RGB)
        cv2.imshow("img", arr)

        print(o.shape)


        print(f"image .... {image_fname}")
        print(f"y ........ {y}")
        print(f"y_hat .... {y_hat}")
        print()
        cv2.waitKey(0)

    cv2.destroyAllWindows()
