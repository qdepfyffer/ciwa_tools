import argparse
import cv2
import pathlib
from util.file_utils import get_images
from util.flir_image_extractor import FlirImageExtractor


"""
This is just to grab visual spectrum images embedded in the FLIR images from our dataset. It doesn't do any cropping or scaling or anything.
"""


def main():
    # Set up argument parser.
    parser = argparse.ArgumentParser(
        description=""
    )
    parser.add_argument("dir", type=str, help="Path to the directory containing thermal images")
    args = parser.parse_args()

    # Determine the input and output directories
    img_dir = pathlib.Path(args.dir)
    output_dir = img_dir.parent / pathlib.Path(str(img_dir) + "_visual")
    output_dir.mkdir(exist_ok=True)

    # If these don't print a path you expect, uh oh
    print(f"INFO:\tInput directory: {img_dir}")
    print(f"INFO:\tOutput directory: {output_dir}")

    # I hate object-oriented programming if I'm being completely honest
    fie = FlirImageExtractor()

    # Process all the images
    for image in get_images(img_dir):
        fie.process_image(str(image))
        # BGR is a stupid format
        cv2.imwrite(str(output_dir / image.name), cv2.cvtColor(fie.rgb_image_np, cv2.COLOR_RGB2BGR))

if __name__ == '__main__':
    main()
