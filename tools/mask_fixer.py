import argparse
import cv2
import numpy as np
import pathlib
from skimage.segmentation import slic
from util.file_utils import get_images, get_matching_image
import time

"""
Now I am become mask_fixer.py, fixer of masks.
"""

def get_temp_mask(file_path: pathlib.Path, save: bool=False) -> np.ndarray:
    """
    Get the temporary mask for the given file path.
    """

    im = cv2.imread(str(file_path))
    hsv = cv2.cvtColor(im, cv2.COLOR_BGR2HSV)

    # We want to ONLY keep pixels that are fully green, so we need to do some thresholding.
    # If the output we get isn't super close to the original, this probably needs tweaking.
    # Dropped segments are probably okay, wrongly included segments are not.
    lower_tsh = np.array([35, 100, 100])
    upper_tsh = np.array([85, 255, 255])

    # Apply the thresholding
    mask = cv2.inRange(hsv, lower_tsh, upper_tsh)

    # Erode the image
    kernel = np.ones((4,4),np.uint8)
    mask = cv2.erode(mask, kernel)

    if save:
        cv2.imwrite(f"tempmask/{file_path.stem}.png", mask)

    return mask

def validate(original: np.ndarray, new: np.ndarray) -> tuple[float, float]:
    """
    Calculates the percentage of original green pixels that are preserved in the new image.
    Returns 0.0 if there are no original green pixels.
    """
    # Get all the new green pixels
    new_green = np.all(new == [0, 255, 0], axis=-1)

    # Find only those pixels from the image that were 100% green (
    original_green = (original == 255)
    total_original_green = np.sum(original_green)
    if total_original_green == 0:
        pf = 0.0
    else:
        # Calculate the ratio of preserved green pixels
        preserved = np.sum(original_green & new_green)
        pf = (float(preserved) / float(total_original_green)) * 100.0

    total_new_green = np.sum(new_green)
    if total_new_green == 0:
        nf = 0.0
    else:
        # Calculate the ratio of new green pixels
        introduced = np.sum(new_green & ~original_green)
        nf = (float(introduced) / float(total_new_green)) * 100.0

    return pf, nf

def main():

    # Set up argument parser
    parser = argparse.ArgumentParser(
        description="Fixes/regenerates masks for images in a directory. "
    )
    parser.add_argument("img_dir", type=str, help="Path to the directory containing images.")
    parser.add_argument("label_dir", type=str, help="Path to the directory containing labels.")
    args = parser.parse_args()

    image_dir = pathlib.Path(args.img_dir)
    label_dir = pathlib.Path(args.label_dir)
    output_dir = label_dir.parent / pathlib.Path(str(label_dir) + "_fixed")
    output_dir.mkdir(exist_ok=True)
    images = get_images(image_dir)

    total_time = 0

    img_idx = 1
    for image_path in images:
        start_overall = time.perf_counter()
        image_stem = image_path.stem
        print(f"[INFO]\tBegan processing of {image_stem}. ({img_idx}/{len(images)})")
        image = cv2.imread(str(image_path))
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        # Find the corresponding mask for each image
        mask_path = get_matching_image(label_dir, image_path)
        if mask_path is None:
            print(f"[WARN]\tNo mask found for {image_stem}")
            continue
        else:
            print(f"[INFO]\tFound mask for {image_stem}, beginning segmentation.")

        new_mask = np.zeros(image.shape, dtype=np.uint8)
        new_mask[:] = (42, 42, 165) # Set the new mask to be red (BGR)

        segments = slic(image, n_segments=800, sigma=1.5, compactness=50.0)
        unique_segments = np.unique(segments)

        good_segments = set()
        threshold = 0.45  # What percentage of pixels needs to be good for a segment to be good

        print(f"[INFO]\tFound {len(unique_segments)} segments for {image_stem}")
        print(f"[INFO]\tGenerating mask for {image_stem}.")
        start_mask = time.perf_counter()

        good_mask = get_temp_mask(mask_path)

        for idx in unique_segments:
            segment_mask = (segments == idx)
            segment_good_pixels = np.sum(good_mask[segment_mask] == 255)
            total_segment_pixels = np.sum(segment_mask)

            if total_segment_pixels > 0 and (int(segment_good_pixels) / total_segment_pixels) > threshold:
                good_segments.add(idx)

        print(f"[INFO]\tFinished identifying {len(good_segments)} good segments.")

        good_segments_list = list(good_segments)
        mask = np.isin(segments, good_segments_list)
        new_mask[mask] = (0, 255, 0) # Set good pixels to green (BGR)
        cv2.imwrite(str(output_dir / f"{image_stem}_L.png"), new_mask)
        end_mask = time.perf_counter()
        elapsed_mask = end_mask - start_mask
        print(f"[INFO]\tGenerate fixed mask for {image_stem} in {elapsed_mask:.2f} seconds.")
        print(f"[INFO]\tSaving fixed mask to {output_dir / f'{image_stem}_L.png'}")

        print(f"[INFO]\tValidating fixed mask for {image_stem}.")
        # We don't calculate these using the OG masks because the pixel values are all over the place. We need an actual
        # binary mask.
        preserved, introduced = validate(good_mask, new_mask)
        print(f"[INFO]\tRough percentage of green pixels preserved: {preserved:.2f}% (Calculated from pre-processed mask)")
        print(f"[INFO]\tRough percentage of green pixels introduced: {introduced:.2f}% (Calculated from pre-processed mask)")


        end_overall = time.perf_counter()
        elapsed_overall = end_overall - start_overall
        total_time += elapsed_overall
        print(f"[INFO]\tFinished processing of {image_stem} in {elapsed_overall:.2f} seconds.\n")
        img_idx += 1

        print(f"[INFO]\tDone! Total processing time: {total_time:.2f} seconds.")

if __name__ == "__main__":
    main()