# CIWA Tools
This repository contains a collection of tools or scripts that I have written to aid in research / data processing for the CIWA+ project with the AIIS Lab at California State University Fresno.

# Note
The original versions of these tools or scripts were not written to be flexible, understandable, or maintainable. They were written to solve a specific, immediate problem at the moment with no regard for any further use they might have. I'll try to update this as I rewrite / consolidate things and get them to a state where I'm okay with other people seeing and using them. 

# Contents

*This section will (hopefully) be updated as I fix more of the things I've written and upload them here.*

## utilities

- **util/file_utils.py**: Contains functions used in the processing of images / labels to make handling CIWA+ datasets easier and cut down on repetitive code
- **util/get_weather_data.py**: Contains a function to retrieve local weather data based on a set of passed coordinates and the embedded creation time of the image being processed. Some images in the dataset had erroneous values for weather-related metadata, so this was meant to provide a way to fetch more accurate data for those images.
- **util/flir_image_extractor.py**: Does (almost) all the work of dealing with FLIR images. Copied (with slight modifications) from https://github.com/Nervengift/read_thermal.py/blob/master/flir_image_extractor.py

## tools

- **tools/mask2coco.py**: Builds COCO JSON annotations for a binary mask dataset. See the file for a more detailed explanation of its function and how to use it.
- **tools/mask_fixer.py**: Fixes the masks generated with the old and broken version of our segmentation tool. Will only fix masks created using SLIC image segmentation, which is the default in our tool. If someone else breaks the program and we need a way to re-generate masks that were made using a different segmentation algorithm, it can *probably* be adjusted to work with said algorithm.