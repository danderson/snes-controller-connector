A Build123d (https://build123d.readthedocs.io/en/latest/) CAD program
that generate models for the controller connectors of the Super
NES/Super Famicom. Or rather, one specific aftermarket variant that is
widely available in 2024, with a right-angle through-hole pin mounting
style.

It was originally built for the Sentinel 65X project
(https://git.sentinel65x.com/Sentinel65X/), though if you find it
useful you are welcome to it, subject to the license and the usual
absolutely no warranty expressed or implied.

Running this script produces two STEP files, `snes_connector_left.stp`
and `snes_connector_right.stp`. They are mirrored versions of each
other, with the rounded part of the connector facing in opposite
directions when mounted to a board.

In the exported file, the connector assumes the PCB the XY plane, with
the top surface at Z=0. It sits cleanly on the PCB surface in that
orientation. All the pins are aligned along the X axis, with Y=0. The
front of the connector (where you'd plug in a controller) faces
towards negative Y.

Build123d doesn't know how to apply materials beyond basic colour. The
colours are an approximation of looking good, but for better results
I'm told you should open the STEP files in FreeCAD's "StepUp"
workbench (it's a KiCAD-specific plugin you have to install), and from
there you can set better materials and also export to VRML to get
nicer rendering.

If StepUp doesn't provide materials that work, here's my guess at a
combo that might work, taken from a combo of KiCAD material settings
(https://gitlab.com/kicad/libraries/kicad-packages3D-generator/-/blob/master/_tools/shaderColors.py),
and some guesstimates of the right shade of blue-gray for the plastic
connector body.

- Body: start with plastic preset, then:
  - diffuse:  #a8aaaa (guess based on photos of the connectors)
  - specular: #0f0f0f (default)
  - emissive: #000000 (default)
  - ambient: #191919 (default)
  - shininess: 0%
- Pins: start with the gold preset, then:
  - diffuse: #dbbc7e (from kicad-generator materials)
  - specular: #23252f (default)
  - emissive: #000000 (default)
  - ambient: #4c3a18 (default)
  - shininess: 40%
