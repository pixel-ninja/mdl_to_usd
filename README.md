# Description
This is a simple, hacky little python script for converting Evermotion VRay MDL materials to MaterialX USD materials.

# Script Usage
Pass the script a path to either an MDL file or a directory containing multiple MDL files and it will save out USD files next to the input files with the same names.

# Material Usage
Sublayer in the USD assembly and reference all of the USD materials over the existing ones. i.e. via a Reference LOP in Houdini with a glob pattern ("*.usd").
The MDL material connections will remain intact as the MaterialX materials will overlay as an alternative render delegate option.
