import argparse
import cv2
import numpy as np
import pathlib
import sys
from util.file_utils import get_images, get_matching_image
from util.img_utils import resize_to_match, generate_overlay




def main() -> None:

    # Set up argument parser.
    parser = argparse.ArgumentParser(
        description="Generate overlays of images in one folder with images in another folder. Images from the latter will be overlaid on the former. In each pair, the smaller image is upscaled to match the resolution of the larger image."
    )
    parser.add_argument("folder_a", type=str, help="Path to the 1st directory")
    parser.add_argument("folder_b", type=str, help="Path to the 2nd directory")
    parser.add_argument("alpha", type=float, default=0.5, help="Alpha value for the overlay creation")
    args = parser.parse_args()

    # Since my utils expect path objects
    f_a = pathlib.Path(args.folder_a)
    f_b = pathlib.Path(args.folder_b)

    # Make sure we actually have directories
    if not f_a.is_dir():
        print(f"ERROR: {f_a} is not a valid directory.")
        sys.exit(1)
    if not f_b.is_dir():
        print(f"ERROR: {f_b} is not a valid directory.")
        sys.exit(1)

    # Determine the output directory
    output_dir = f_a.parent / pathlib.Path(str(f_a) + "_overlays")
    output_dir.mkdir(exist_ok=True)
    print(f"INFO:\tOutput directory: {output_dir}")

    # Get the images in the first folder
    imgs_a = get_images(f_a)
    print(f"INFO:\tFound {len(imgs_a)} images in {f_a}")

    for img_a_pth in imgs_a:
        img_b_pth = get_matching_image(f_b, img_a_pth)
        if img_b_pth is None:
            print(f"WARN:\tNo matching image found for {img_a_pth}")
            continue

        # Read the images
        img_a = cv2.imread(str(img_a_pth))
        img_b = cv2.imread(str(img_b_pth))

        # Rescale the images to the same dimensions. Use the upscale argument to determine the direction of the scale matching.
        img_a, img_b = resize_to_match(img_a, img_b, upscale=True)

        # Generate and save the overlay
        overlay = generate_overlay(img_a, img_b, args.alpha)
        cv2.imwrite(str(output_dir / img_a_pth.name), overlay)


if __name__ == "__main__":

    main()