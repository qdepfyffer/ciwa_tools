import argparse
import cv2
import json
import numpy as np
import pathlib
from pycocotools import mask as mask_utils
from file_utils import get_images, get_matching_image
import sys

"""
Builds COCO JSON annotations for a dataset. Your dataset should be in the following format:

dataset/
├── train/
│   └── (image files)
├── train_label/
│   └── (corresponding label  files)
├── valid/
│   └── (image files)
├── valid_label/
│   └── (corresponding label  files)
├── test/
│   └── (image files)
└── test_label/
    └── (corresponding label files)
    
Notes:
- Generated COCO JSON will be written to <split_name>/_annotations.coco.json by default.

- An image's corresponding label is expected to contain the filename of the image it is labeling, for example:
  Image: 'example_1234.png'
  Label: 'example_1234.png' or 'example_1234_L.png', etc.
    
- If the script warns you about not finding any instances for a specific image, try running the script again with a
  lower `min_area` (default is 250). If it's still warning you, the label image probably lacks any segments. 

CLI Args:
    dataset_dir:    Path to the dataset root directory
    --min_area:     Minimum area of objects to count as an instance mask for COCO annotations
    --no_rle:       Disable use of RLE encoding for segmentation masks. This will not preserve holes in the mask segments.
    --iscrowd:      Mark annotations as crowd segments
"""


def encode_mask_rle(instance_mask: np.ndarray) -> dict:
    """
    Read a binary mask and return the COCO RLE encoding, bounding box, and area.
    Preserves holes exactly.
    """
    # Encode the mask using RLE
    binary = np.asfortranarray(instance_mask)
    rle = mask_utils.encode(binary)
    rle["counts"] = rle["counts"].decode("utf-8")

    # Get the area and bounding box
    area = int(mask_utils.area(rle))
    bbox = mask_utils.toBbox(rle).tolist()

    # Return structured data
    return {"segmentation": rle, "bbox": bbox, "area": area}


def encode_mask_poly(instance_mask: np.ndarray) -> dict | None:
    """
    Read a binary mask and return the COCO polygon encoding, bounding box, and area.
    Probably won't preserve holes.
    """
    # Find contours w/ OpenCV
    contours, _ = cv2.findContours(instance_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    segmentation = []
    for contour in contours:
        # Valid polys require 3 points minimum (which works out to 6 points in a 2D coordinate system)
        if contour.size >= 6:
            segmentation.append(contour.flatten().tolist())

    if not segmentation:
        return None

    # Get bbox
    x, y, w, h = cv2.boundingRect(instance_mask)
    bbox = [int(x), int(y), int(w), int(h)]

    # Get area
    area = int(np.sum(instance_mask))

    return {"segmentation": segmentation, "bbox": bbox, "area": area}


def build_coco(img_files: list[pathlib.Path], labels: pathlib.Path, category_id: int=1, min_area: int=250, iscrowd: int=0, use_rle: bool=True) -> dict:
    """
    Builds complete COCO formatted JSON for the given image files and the generated instance masks.
    If for whatever reason we need more information in our annotations, we can add it here in the COCO skeleton.
    """
    # Overall COCO skeleton
    coco = {
        "images": [],
        "annotations": [],
        "categories": [{"id": category_id, "name": "sunlit"}]
    }

    # This isn't strictly necessary in terms of COCO format, but it could help track down annotations w/ issues.
    annotation_id = 1

    for img_id, img_path in enumerate(img_files, start=1):
        im = cv2.imread(str(img_path))
        if im is None:
            print(f"WARN: Could not read {img_path}.")
            continue
        height, width = im.shape[:2]

        # Per-image COCO skeleton.
        coco["images"].append({
            "id": img_id,
            "file_name": img_path.name,
            "height": height,
            "width": width,
        })

        # Find the mask for this specific image.
        mask_path = get_matching_image(labels, img_path)
        if mask_path is None:
            print(f"WARN: No mask found for {img_path}.")
            continue

        # Read the mask and binarize it.
        mask_gray = cv2.imread(str(mask_path), cv2.IMREAD_GRAYSCALE)
        if mask_gray is None:
            print(f"WARN: Could not read mask {mask_path}.")
            continue
        # We binarize the mask using Otsu's thresholding method to help clean up any artifacting.
        _, binary = cv2.threshold(mask_gray, 127, 255, cv2.THRESH_BINARY)

        # Split into per-instance masks.
        num_labels, label_map = cv2.connectedComponents(binary)
        instances_saved = 0

        # Process each instance found by connected components.
        for instance_idx in range(1, num_labels):
            instance_mask = (label_map == instance_idx).astype(np.uint8)

            # Skip any tiny instances
            if instance_mask.sum() < min_area:
                continue

            # Encode the instance mask into COCO data.
            if use_rle:
                info = encode_mask_rle(instance_mask)
            else:
                info = encode_mask_poly(instance_mask)

            if info is None:
                print(f"WARN: Could not encode mask for {img_path}.")
                continue

            instances_saved += 1
            coco["annotations"].append({
                "id": annotation_id,
                "image_id": img_id,
                "category_id": category_id,
                "segmentation": info["segmentation"],
                "bbox": info["bbox"],
                "area": info["area"],
                "iscrowd": iscrowd,
            })
            annotation_id += 1

        if instances_saved == 0:
            print(f"WARN: No instances found for {img_path}.")

    return coco


def process_split(split: str, root: pathlib.Path, min_area: int, iscrowd: int=0, use_rle: bool=True) -> dict | None:
    """
    Process a single split, build COCO JSON, and write it to root/annotations/.
    Returns either the COCO JSON or None if no images were found or the directory doesn't exist.
    """
    img_dir = root / split
    label_dir = root / f"{split}_label"

    if not img_dir.is_dir():
        print(f"WARN: {img_dir} does not exist.")
        return None
    if not label_dir.is_dir():
        print(f"WARN: {label_dir} does not exist.")
        return None

    # Get all images for the given split.
    image_files = get_images(img_dir)
    if not image_files:
        print(f"WARN: No images found in {img_dir}.")
        return None

    print(f"\n[{split.capitalize()}]\n\tImages: {len(image_files)}")

    # Build and write the COCO JSON for the given split.
    coco = build_coco(image_files, label_dir, min_area=min_area, iscrowd=iscrowd, use_rle=use_rle)

    json_path = img_dir / "_annotations.coco.json"

    with open(json_path, "w") as f:
        json.dump(coco, f)
    print(f"\tWrote {json_path} ({len(coco['annotations'])} annotations)")

    return coco


def main():

    # Set up argument parser.
    parser = argparse.ArgumentParser(
        description="Generate COCO-formatted annotations for a dataset, optionally using RLE to preserve holes in masks."
    )
    parser.add_argument("dataset_dir", type=str, help="Path to the dataset directory")
    parser.add_argument("--min_area", type=int, default=250, help="Minimum pixels for an instance mask")
    parser.add_argument("--no_rle", action="store_false", dest="use_rle", help="Use RLE encoding for instance masks (preserves holes)")
    parser.add_argument("--iscrowd", type=int, default=0, help="Set to 1 to mark all instances as crowd.")
    args = parser.parse_args()

    root = pathlib.Path(args.dataset_dir)
    if not root.is_dir():
        print(f"ERROR: {root} is not a valid directory.")
        sys.exit(1)


    # Echo CLI args
    print(f"\nBeginning processing of dataset: {root.resolve()}")
    print(f"Min area: {args.min_area} px")
    print(f"Use RLE: {args.use_rle}")
    print(f"Is crowd: {args.iscrowd}")


    # Process all the splits
    results = {}
    for split in {"train", "valid", "test"}:
        coco = process_split(f"{split}", root, args.min_area, args.iscrowd, args.use_rle)
        if coco is not None:
            results[split] = coco

    # Exit if there weren't any valid splits found
    if not results:
        print("ERROR: No valid splits found. Exiting.")
        sys.exit(1)

    # Quick summary of the data
    print(f"\n[Summary]")
    for split, coco in results.items():
        num_images = len(coco["images"])
        num_annotations = len(coco["annotations"])
        print(f"\t{split.capitalize()}: {num_images} images, {num_annotations} annotations")

    print("Finished!")

if __name__ == "__main__":
    main()
