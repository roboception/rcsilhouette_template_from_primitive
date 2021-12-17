# Template Generation for RCSilhouette

The scripts in this repository can be used to generate templates from primitives
(without a CAD model). Possible shapes are rectangles, circles and hexagons. They
can be combined.

## Usage

To use the script, you need a python3 (>= 3.6) interpreter. Install the required dependencies
with `pip install -r requirements.txt`.

To start generating templates, in a terminal run `python3 rcsilhouette_template_from_primitive.py --help`.

Example for circle:

    python3 rcsilhouette_template_from_primitive.py my_object_name --circle 0.1 --object-height 0.01

Example for rectangle (no space after comma in rectangle size!):

    python3 rcsilhouette_template_from_primitive.py my_object_name --rect 0.1,0.2 --object-height 0.01

Example for hexagon sitting on its flat side (30 degree rotation):

    python3 rcsilhouette_template_from_primitive.py my_object_name --hex-diameter 0.1,30 --object-height 0.02

It is also possible to add multiple objects:

    python3 rcsilhouette_template_from_primitive.py my_object_name --circle 0.1 --circle 0.05 --object-height 0.01 --hex-diameter 0.1

If you want to have a look at the generated template, or edit the template images, use the
`--write-folder` option to get an output folder instead of an `.rcsmt` template file.

All templates will be created with the reference frame on the top plane of the object.

## Packing and Unpacking Templates

If you wish to edit a template, for example because your real part is not a perfect
 circle or hexagon, and you wish to remove some lines, you can do so by unpacking the template.
 This gives you a folder with the template contents, which you can then edit with
 an image editor (e.g. Gimp, Photoshop).

To unpack:

    python3 unpack_template.py my_template.rcsmt

To pack the folder back into a template:

    python3 pack_template.py my_template

## Virtual Focal Length and Virtual Plane Distance

These two optional arguments normally don't need to be tweaked. However if you do, they should roughly
 mirror your real-world setup. The focal length of the rc_visard is around `1080`px for the normal version
 and around `1600`px for the 6mm lens.