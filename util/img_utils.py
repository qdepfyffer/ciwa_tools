import cv2
import numpy as np

def resize_to_match(img_a: np.ndarray, img_b: np.ndarray, upscale: bool=False) -> tuple[np.ndarray, np.ndarray]:
    """
    Upscales or downscales one image to match the resolution of the other.
    """
    # Get the dimensions of the images
    a_h, a_w, *_ = img_a.shape[:2]
    b_h, b_w, *_ = img_b.shape[:2]

    if upscale:
        # Upscale the smaller image to match the resolution of the larger image
        if a_h > b_h or a_w > b_w:
            img_b = cv2.resize(img_b, (a_w, a_h))
        else:
            img_a = cv2.resize(img_a, (b_w, b_h))
    else:
        # Downscale the larger image to match the resolution of the smaller image
        if a_h < b_h or a_w < b_w:
            img_b = cv2.resize(img_b, (a_w, a_h))
        else:
            img_a = cv2.resize(img_a, (b_w, b_h))

    # Return the resized images in the same order they were passed in
    return img_a, img_b

def generate_overlay(img_a: np.ndarray, img_b: np.ndarray, alpha: float=0.5) -> np.ndarray:
    return cv2.addWeighted(img_a, alpha, img_b, 1 - alpha, 0)