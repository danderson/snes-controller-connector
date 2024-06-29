#!/usr/bin/env python3
#
# A Build123d (https://build123d.readthedocs.io/en/latest/) CAD
# program that generate models for the controller connectors of the
# Super NES/Super Famicom. Or rather, one specific aftermarket variant
# that is widely available in 2024, with a right-angle through-hole
# pin mounting style.
#
# It was originally built for the Sentinel 65X project
# (https://git.sentinel65x.com/Sentinel65X/), though if you find it
# useful you are most welcome to it, subject to the license and the
# usual absolutely no warranty expressed or implied.
#
# Running this script produces two STEP files, snes_connector_left.stp
# and snes_connector_right.stp. They are mirrored versions of each
# other, with the rounded part of the connector facing in opposite
# directions when mounted to a board.
#
# In the exported file, the connector assumes the PCB is at Z=0 and
# its bottom standoffs sit flush on top of it. The row of pins is
# aligned along the X axis, the front of the connector (where you'd
# plug in a gamepad) faces towards negative Y.
#
# Note that due to limitations of Build123d's export function, there
# is no material applied to the part, only a colour. They are an
# approximation of looking good, but for better results you'll want to
# open the stp files in FreeCAD with the KiCAD StepUp plugin, which
# will let you set more accurate-looking materials and export to VRML
# for slick rendered views.
#
# If StepUp doesn't provide materials that work, here's my guess at a
# combo that might work, taken from a combo of KiCAD material settings
# (https://gitlab.com/kicad/libraries/kicad-packages3D-generator/-/blob/master/_tools/shaderColors.py),
# and some guesstimates of the right shade of blue-gray for the
# plastic connector body.
#
#  - Body: start with plastic preset, then:
#          diffuse:  #a8aaaa (guess based on photos of the connectors)
#          specular: #0f0f0f (default)
#          emissive: #000000 (default)
#          ambient: #191919 (default)
#          shininess: 0%
#
#  - Pins: gold
#          diffuse: #dbbc7e (from kicad-generator materials)
#          specular: #23252f (default)
#          emissive: #000000 (default)
#          ambient: #4c3a18 (default)
#          shininess: 40%

__author__ = "David Anderson"
__contact__ = "dave@natulte.net"
__license__ = "CERN-OHL-P-2.0"

import contextlib
import math
import copy
import enum
from build123d import *

# If true, show(...) sends the geometry over to the cadquery vscode
# viewer for interactive rendering.
dev = False

def show(obj, stop=False):
    if not dev:
        print("dev mode off, not talking to interactive viewer")
        return

    from ocp_vscode import set_defaults, show
    set_defaults(reset_camera=False)
    show(obj)
    if stop:
        raise ValueError("Debug stop")

# In this file, the reference orientation is looking into the
# connector (where the controller plug would go), with the group of 4
# pins on the left-hand side. In that orientation, the axes during
# part construction are:
#
#  - X: "width", left-right. The rounded side of the connector body is
#       to the right.
#  - Y: "height", up-down. The pins you solder into the board go down.
#  - Z: "depth", forward-back. The place opening where you plug the
#       controller is forward.
#
# After all the construction is done, the connector gets rotated and
# moved around so that it's sitting as if the XY plane were the PCB it
# mounts to.
#
# Some general connector terminology that I use:
#
#  - The connector: the whole device that facilitates breakable
#    electrical contact between conductors. It is composed of:
#
#    - The contacts: the bits that form the electrical connection.
#    - The connector body: the rest of the connector, which defines
#      the shape the mating connector needs to have, as well as
#      things like insulation ratings and ease of use. The body is
#      composed of:
#      - The insert: the insulating elements into which the contacts
#        are inserted. It provides electrical insulation between
#        neighboring contacts, mechanical protection of fragile
#        contacts, and helps align and guide the mating connector to
#        make a good connection.
#      - The housing: the outer body of the connector that contains
#        and protects the insert and contacts.
#
# Okay, on to building. All dimensions are in millimeters.

#################################################################
###          Verified dimensions on a real part               ###
###                                                           ###
###   These all come from the connectors used in one of the   ###
###         Prototype 4 designs of the Sentinal 65X.          ###
#################################################################

# The body is the basic outer shell of the connector, before you add
# all the frills to it. These dimensions to not include the front
# flange bit, pretend that gets glued on later.
body_width = 38.7
body_height = 12.0
body_depth = 11.4

# TODO: once thickness is verified, maybe redundant, can derive from depth+thickness.
body_cavity_depth = 9.8 # 11.8 if measuring from front of flange

# This is the flange ring bit that gets glued to the front of the
# body. It it sticks out by this much up, down, left and right of the
# main shell.
flange_stickout = 1.95
flange_depth = 2

# The inserts are the two plastic bits inside the main body, that
# surround and protect the pins and help quite the controller plug
# into position.
#
# Their dimensions are mostly defined by reference to the positions of
# the pins (see below), we just need to specify how big the pin holes
# are, how much plastic there is on the sides of the holes, and how
# deep the inserts are.
insert_drill_diameter = 3.6
insert_horizontal_margin = 0.65
insert_vertical_margin = 0.8
insert_depth = 13.1 # from its front surface to bottom of body cavity

# The pins are grouped into four and three, with a slightly wider gap
# than normal to separate the two groups. Aside from that, they're
# recessed into the body inserts a little, and otherwise quite
# standard.
pin_diameter = 1.2
pin_spacing = 4
pin_extra_spacing_between_groups = 2.5
pin_recess_depth = 1.5 # from front surface of insert
pin_pcb_stickout = 8 # starting from surface of PCB
pin_stickout_from_back = 0.2 # how much they protrude from the plastic grip

#################################################################
###          Less verified, eyeballed dimensions              ###
###                                                           ###
###   There are either educated guesses, or came from other   ###
###    drawings of slightly different parts, but hopefully    ###
###                similar enough to work.                    ###
#################################################################

# https://www.raphnet-tech.com/ used to sell a different style of SNES
# controller, and published a technical drawing. These numbers are
# taken from there.

# The square side of the body shell has a generous outside fillet for
# aesthetics.
body_outer_fillet_radius = 1.75
body_inner_fillet_radius = 1.0

# Once you carve the cavity out of the body, this is how much shell
# wall remains. Measurements from the 65X part suggest the dimension
# there may be 1.6mm, but Raphnet says 1.4mm.
#
# TODO: need to request inner dimensions of the body cavity, to
# cross-check.
body_thickness = 1.6

# The following numbers are eyeballed from photos.

# The body shell has little standoff strips on the top and bottom,
# designed, so that when it's sitting on a PCB the connector body can
# flex a bit without transferring excessive force to the board. These
# dimensions are currently all eyeballed from 65X photos.
#
# TODO: get measurements? Or good enough to pass inspection?
standoff_width = 1
standoff_height = 0.5
standoff_distance_from_edge = 7

# The pins have to make a 90 degree turn. A turn radius of twice the
# pin's own radius looks okay.
pin_elbow_radius = pin_diameter

# The back of the body has a "grip" that protrudes from the main body,
# and holds the pins in the correct vertical orientation. I don't have
# dimensions for these, this is eyeballed from photos.
#
# TODO: get measurements. grip_depth is critical to position the pins
# correctly so everything lines up.
grip_margin = pin_diameter # Extra material to the left/right of the pins
grip_depth = 2.4

# The inserts don't have perfectly square corners, there's a little
# filleting on there. This is a guess that "looks okay" vs. photos.
insert_fillet_radius = 0.5

#################################################################
###         Bling: pretty, expensive, unnecessary             ###
###                                                           ###
###    It's a well known scientific fact that CAD drawings    ###
###   look more professional when you fillet the shit out of  ###
###        every edge you can find. And it's true, the        ###
###   connector looks much prettier! It also burns 24 cores   ###
###     for a solid 10 seconds to calculate, and makes no     ###
###       difference to the looks of the kicad render.        ###
#################################################################

burn_more_cpu = False
showboating_fillet_radius = 0.2

#################################################################
###                      Derived values                       ###
###                                                           ###
###     Precalculate some stuff that comes in handy later.    ###
#################################################################

# Because the connector is centered in XY, we end up dividing by two a
# lot. In denser lines of math, this helps readability.
half = lambda n: n/2

pin_radius = half(pin_diameter)
insert_drill_radius = half(insert_drill_diameter)

# If you look at the centerline of pin 1, how far to the left is the
# outside edge of the insert body?
insert_edge_to_pin_center = insert_horizontal_margin + insert_drill_radius

# Pretend for a moment the two inserts were a single piece. This is
# the width/height of that.
insert_width = 6*pin_spacing + pin_extra_spacing_between_groups + 2*insert_edge_to_pin_center
insert_height = insert_drill_diameter + 2*insert_vertical_margin

# A lot of the inside details are built with reference to the pattern
# of the positions of the seven pins. This builds out an array with
# the offset from the origin to the center of every pin.
#
# We're using the CAD kernel's vectors. Their constructor takes x/y/z
# values, and assumes any values you don't pass are 0. This is handy
# because we do a lot of work purely in X.
pin_vectors = [Vector(-half(insert_width) + insert_edge_to_pin_center)]
for n in range(1,7):
    v = Vector(pin_spacing)
    if n == 4:
        v += Vector(pin_extra_spacing_between_groups)
    pin_vectors.append(pin_vectors[-1] + v)

# The grip that holds the pins in place does so with little notches.
grip_notch_width = pin_diameter
grip_notch_depth = pin_diameter
grip_width = 6*pin_spacing + pin_extra_spacing_between_groups + 2*(pin_radius + grip_margin)
grip_height = pin_diameter + 2*grip_margin

#################################################################
###                      Parts library                        ###
###                                                           ###
###  We define separate parts first, and then assemble them.  ###
#################################################################

# The technical term for a rectangle where one side is a half circle,
# turns out, is a "semistadium", because it's half of a full stadium
# where both ends are a half circle.
#
# This shape comes up a bunch in this connector, so here's a helper
# that makes a single 2D face in that shape, with requested outside
# dimensions.
class SemiStadium(BaseSketchObject):
    def __init__(self, width, height, fillet_radius=0, mode=Mode.ADD):
        with BuildSketch() as sk:
            with BuildLine() as ln:
                radius = half(height)
                arc_x = half(width) - radius
                line_points = [
                    ( arc_x,       -half(height)),
                    (-half(width), -half(height)),
                    (-half(width),  half(height)),
                    ( arc_x,        half(height)),
                ]
                if fillet_radius > 0:
                    FilletPolyline(line_points, radius=fillet_radius)
                else:
                    Polyline(line_points)
                ThreePointArc([
                    ( arc_x,        half(height)),
                    ( half(width),  0),
                    ( arc_x,       -half(height))
                ])
            make_face()
        super().__init__(obj=sk.sketch, mode=mode)


# The entire plastic part of the connector. Everything but the pins.
class Body(BasePartObject):
    def __init__(self):
        with BuildPart() as body:
            # Base connector housing
            with BuildSketch():
                SemiStadium(body_width, body_height, body_outer_fillet_radius)
            extrude(amount=body_depth)

            # Inner cavity
            with BuildSketch(Plane.XY.offset(body_depth)):
                SemiStadium(body_width - 2*body_thickness,
                            body_height - 2*body_thickness,
                            body_inner_fillet_radius)
            extrude(amount=-body_cavity_depth, mode=Mode.SUBTRACT)

            # Housing's front flange
            with BuildSketch(Plane.XY.offset(body_depth)):
                SemiStadium(body_width + 2*flange_stickout,
                            body_height + 2*flange_stickout,
                            body_outer_fillet_radius)
                SemiStadium(body_width - 2*body_thickness,
                            body_height - 2*body_thickness,
                            body_inner_fillet_radius,
                            mode=Mode.SUBTRACT)
            extrude(amount=flange_depth)

            with GridLocations(x_spacing=body_width - 2*standoff_distance_from_edge,
                               y_spacing=body_height + standoff_height,
                               x_count=2,
                               y_count=2):
                Box(standoff_width, standoff_height, body_depth, align=(Align.CENTER, Align.CENTER, Align.MIN))

            # Housing's cosmetic fillets
            if burn_more_cpu:
                faces = body.faces().filter_by(Plane.XY).sort_by(Axis.Z)
                wires = faces[-2:].wires() + faces[0].wires()
                for wire in wires:
                    fillet(wire.edges(), showboating_fillet_radius)

            # Inserts
            with BuildSketch(Plane.XY.offset(body_thickness)) as inserts:
                # Outer insert shape
                SemiStadium(insert_width, insert_height)

                # Cut out between the two pin groups
                punchout_center = (pin_vectors[3] + pin_vectors[4])/2
                punchout_width = pin_vectors[4] - pin_vectors[3] - Vector(2*insert_edge_to_pin_center)
                with Locations(punchout_center):
                    Rectangle(punchout_width.length, insert_height, mode=Mode.SUBTRACT)

                # Fillet the not yet rounded edges, before we punch more holes
                # and create geometry we'd have to filter.
                fillet(inserts.edges().filter_by(Axis.Y).vertices(), insert_fillet_radius)

                # Insert holes for the pins
                with Locations(pin_vectors):
                    Circle(insert_drill_radius, mode=Mode.SUBTRACT)
            extrude(amount=insert_depth)

            # Insert's cosmetic fillets
            if burn_more_cpu:
                faces = body.faces().filter_by(Plane.XY).group_by(Axis.Z)[-1]
                for face in faces:
                    fillet(face.outer_wire().edges(), showboating_fillet_radius)
                    fillet(face.inner_wires().edges(), showboating_fillet_radius/2)

            # Pin grip on the rear side
            Box(grip_width, grip_height, grip_depth, align=(Align.CENTER, Align.CENTER, Align.MAX))
            with BuildSketch(Plane.XY.offset(-grip_depth)):
                with Locations(pin_vectors):
                    Rectangle(grip_notch_width, grip_height)
            extrude(amount=grip_notch_depth, mode=Mode.SUBTRACT)

            # A few final cosmetics for the future assembly.
            body.part.label = "Body"
            super().__init__(part=body.part)
            self.color = Color(0.666, 0.666, 0.666) # guesstimated from online listings


# One pin, including its bend.
class Pin(BasePartObject):
    def __init__(self):
        with BuildPart() as pin:
            with BuildLine(Plane.YZ):
                start_x = body_thickness + insert_depth - pin_recess_depth
                below_y = -(grip_depth + pin_stickout_from_back)
                end_x = -(half(body_height) + pin_pcb_stickout)
                FilletPolyline([
                    (0, start_x),
                    (0, below_y),
                    (end_x, below_y)
                ], radius=pin_elbow_radius)
            with BuildSketch(Plane.XY):
                Circle(pin_radius)
            sweep()

            # Round off the ends of the pins
            fillet(pin.faces().filter_by(Plane.XY).face().edges(), pin_radius)
            fillet(pin.faces().filter_by(Plane.XZ).face().edges(), pin_radius)
        # Cosmetic touches
        pin.part.label = "Pin (template)"
        super().__init__(part=pin.part)
        self.color = Color(0.859, 0.737, 0.494) # Kicad's "gold pins" diffuse


# At last, we can assemble!
class Connector(BasePartObject):
    def __init__(self, mirror_image=False):
        # There is a mirror operation in build123d, but it seems
        # weirdly expensive, and it fuses compound objects into a
        # single solid, which we don't want.
        #
        # Instead, we can play with rotations: rotate each pin so it
        # comes out the top of the connector, then assemble the pins
        # and body, then rotate that entire thing again. The result is
        # a mirrored connector.
        angle = 180 if mirror_image else 0
        mirror = Rot(0, 0, angle)

        objects = [Body()]

        pin = Pin()
        for i, loc in enumerate(Locations(pin_vectors).local_locations):
            loc = loc * mirror # Maybe flip the pin around before moving it to final location
            p = copy.copy(pin)
            p.label = f"Pin {i+1}"
            objects.append(p.locate(loc))

        # Almost there! Now we just have to rotate and adjust the
        # connector's position, so that it lines up with how KiCAD
        # wants to see it. In KiCAD's world, the XY plane is the top
        # surface of the PCB, negative Y is "forward", and the origin
        # is coincident with the footprint's origin.
        #
        # Adjust so that X is sitting between the two pin groups,
        # rather than on the center of the bounding box.
        x_3_to_4 = pin_vectors[4] - pin_vectors[3]
        x_adjust = pin_vectors[3] + x_3_to_4/2
        final_pos = Pos(x_adjust.reverse())
        # If we're building the mirrored version of the connector,
        # flip the entire thing now so the pins all point in the same
        # direction and react identically to the following
        # adjustments.
        final_pos = mirror * final_pos
        # Next, the connector has to come up, so that when we rotate
        # about the X axis, the pins end up sticking down along y=0.
        pin_z_adjust = objects[1].bounding_box().min.Z + pin_radius
        final_pos = Pos(0, 0, -pin_z_adjust) * final_pos
        # Then rotate, so that Z is now "height above PCB".
        final_pos = Rot(90, 0, 0) * final_pos
        # The connector's currently half embedded in the PCB
        # "surface", raise it to final position.
        final_pos = Pos(0, 0, half(body_height) + standoff_height) * final_pos

        # Apply the transform, build the final element, and we're
        # done!
        objects = [final_pos * obj for obj in objects]
        final = Compound(label="Connector", children=objects)

        super().__init__(part=final)


class Projection(enum.Enum):
    FRONT = (Axis.Y, Axis.Z)
    BACK = (-Axis.Y, Axis.Z)
    LEFT = (Axis.X, Axis.Z)
    RIGHT = (-Axis.X, Axis.Z)
    TOP = (Axis.Z, Axis.Y)
    BOTTOM = (-Axis.Z, Axis.Y)

def project(obj, projection):
    camera = projection.value[0].direction*100
    up = projection.value[1].direction
    look_at = Vector()
    return obj.project_to_viewport(camera, up, look_at)

def write_dxf(obj, projection, filename):
    visible, _ = project(obj, projection)

    max_dimension = max(*Compound(children=visible).bounding_box().size)
    exp = ExportDXF(line_weight=0.1, line_type=LineType.CONTINUOUS)
    exp.add_shape(visible)
    exp.write(filename)

# All that's left is to render out to STEP and be merry. Ideally also
# apply the fancier materials, but build123d doesn't seem to know
# how. Refer to the comment right at the top for how to load these
# files into FreeCAD and fix up the materials.
variants = {
    'right': Connector(False),
    'left': Connector(True),
}

show(variants['left'])

for variant, obj in variants.items():
    print(f"exporting {variant}-handed STEP")
    export_step(obj, f"SNES Controller Connector.pretty/snes_connector_{variant}.stp")

print("done!")
