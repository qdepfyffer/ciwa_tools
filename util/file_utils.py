import pathlib


# Add / remove extensions and stem suffixes here if we ever end up with ones not already covered.
VALID_IMG_EXTS = {".png", ".jpg", ".jpeg", ".tif", ".tiff"}
STEM_SUFFIXES = {"_L", "-Visual"}


def get_images(img_dir: pathlib.Path) -> list[pathlib.Path]:
    """Return the sorted list of valid files in the 'img_dir' directory with file extensions in VALID_IMG_EXTS"""
    return sorted(f for f in img_dir.iterdir() if f.is_file() and f.suffix.lower() in VALID_IMG_EXTS)


def get_matching_image(candidate_dir: pathlib.Path, target_image: pathlib.Path) -> pathlib.Path | None:
    """
    Returns the path to the image corresponding to the target image in the candidate_dir directory, or None if not found.
    Matches by canonical stem, so '_L' and '-Visual' markers are ignored on both sides.
    """
    target = canonical_stem(target_image)
    for candidate in candidate_dir.iterdir():
        if not candidate.is_file() or candidate.suffix.lower() not in VALID_IMG_EXTS:
            continue
        if canonical_stem(candidate) == target:
            return candidate
    return None


def canonical_stem(path: pathlib.Path) -> str:
    """
    Returns the canonical stem of a file path, stripping known markers to get a standardized name for matching.
    """
    stem = path.stem

    # Strip any potentially stacked suffixes until none are left.
    changed = True
    while changed:
        changed = False
        for suffix in STEM_SUFFIXES:
            if stem.lower().endswith(suffix.lower()):
                stem = stem[:-len(suffix)]
                changed = True
        for ext in VALID_IMG_EXTS:
            if stem.lower().endswith(ext.lower()):
                stem = stem[:-len(ext)]
                changed = True
    return stem.lower()
