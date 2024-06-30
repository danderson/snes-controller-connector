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
import sys
from types import SimpleNamespace
from build123d import *

# If true, show(...) sends the geometry over to the cadquery vscode
# viewer for interactive rendering.
dev = len(sys.argv) == 2 and sys.argv[1] == "dev"

def show(obj, *, stop=False):
    if not dev:
        return

    from ocp_vscode import set_defaults, show, Camera
    set_defaults(reset_camera=Camera.KEEP)

    if isinstance(obj, list):
        if len(obj) == 1:
            objs = obj
            obj = objs[0]
        else:
            objs = obj
            # Pack objects into a grid and center them
            obj = Compound(children=pack(objs, padding=20))
            adjust = obj.center().project_to_plane(Plane.XY).reverse()
            obj.locate(Pos(adjust))
    else:
        objs = [obj]
    show(obj)

    # Print outer dimensions for each object, as a way to quickly
    # validate critical dimensions.
    print("")
    for o in objs:
        s = o.bounding_box().size
        r = lambda v: round(v, 2)
        print(f"w={r(s.X)}, h={r(s.Z)}, d={r(s.Y)}")

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
# Okay, on to building. All dimensions are in millimeters. Unless
# otherwise pointed out, values were measured on a real 65X connector
# part.

#################################################################
###                 Parametric settings                       ###
###                                                           ###
###    A mix of real measurements and derived values that     ###
###           get used in the drawing further down.           ###
#################################################################

def params():
    # Don't worry about this nonsense, it's just so I can structure
    # the parameters how I like it below. Skip down if you're here for
    # the CAD.
    class cfg(SimpleNamespace):
        def __getattr__(self, k):
            setattr(self, k, self.__class__())
            return getattr(self, k)

        def __repr__(self):
            def ind(s):
                return ["  "+x for x in s.split("\n")]
            ret = []
            for k,v in sorted(vars(self).items()):
                if isinstance(v, self.__class__):
                    ret.append(f"{k}:")
                    ret.extend(ind(repr(v)))
                elif isinstance(v, list):
                    ret.append(f"{k}: [")
                    for elem in v:
                        ret.extend(ind(repr(elem)))
                    ret.append("]")
                else:
                    ret.append(f"{k}: {repr(v)}")
            return "\n".join(ret)

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            self.__setattr__ = 4
            return False

    cfg = cfg()

    # The pins are the whole point of having a connector.
    with cfg.pin as p:
        p.diameter = 1.2
        p.radius = p.diameter/2
        # The pins are recessed from the insert's front surface.
        p.insert_recess = 1.5
        # Starting from the PCB surface, how far do the pins go down
        # through the board when the connector is mounted?
        p.pcb_stickout = 3
        # After the elbow where they head towards the PCB, the pins
        # sit a tiny bit proud of the rearmost surface of the plastic
        # body.
        p.rear_stickout = 0.2
        # The pins have to make a 90 degree turn. A turn radius of twice
        # the pin's own radius looks decent.
        p.elbow_radius = p.diameter
        # A lot of the inside details of the connector are built by
        # reference to the positions of the pin centerlines as they go
        # through the connector body. Precalculate those positions here as
        # 1D vectors so the rest of the code needn't math as much.
        gaps = [4, 4, 4, 6.5, 4, 4]
        p0 = -sum(gaps)/2
        p.pos = [Vector(p0+sum(gaps[:i])) for i in range(7)]


    # The body is the basic outer shell of the connector, before you
    # add all the frills to it. These dimensions do not include the
    # front flange ring, pretend that's a separate piece that gets
    # press-fit onto the basic body shape later on.
    with cfg.body as b:
        b.width = 38.7
        b.height = 12.0
        b.depth = 13.4
        # Purely aesthetic fillet on the square side of the
        # shell. From the tech drawing of the defunct product at
        # https://www.raphnet-tech.com/.
        b.fillet = 1.75


    # The cavity that gets carved out of the body, to house the rest
    # of the connector gubbins.
    with cfg.body.cavity as c:
        shell_thickness = 1.6
        c.width = b.width - 2*shell_thickness
        c.height = b.height - 2*shell_thickness
        c.depth = b.depth - shell_thickness
        # Also from the discontinued raphnet part.
        c.fillet = 1.0


    # The body shell has little standoff strips on the top and bottom,
    # designed, so that when it's sitting on a PCB the connector body
    # can flex a bit without transferring excessive force to the
    # board. These dimensions are currently all eyeballed from 65X
    # photos.
    with cfg.body.standoffs as s:
        s.width = p.diameter
        s.height = 0.5
        s.depth = b.depth
        distance_from_edge = 7.5
        s.spacing = b.width - 2*distance_from_edge - s.width


    # This is the flange that gets press-fit onto the front of the
    # part and sticks out up/down/left/right from the body shell.
    with cfg.body.flange as f:
        stickout = 1.95
        f.depth = 2
        f.width = b.width + 2*stickout
        f.height = b.height + 2*stickout
        f.fillet = b.fillet


    # The inserts are the two plastic bits inside the main body, that
    # surround and protect the pins and help quite the controller plug
    # into position.
    #
    # Their dimensions are mostly defined by reference to the pins and
    # the cavity geometry.
    with cfg.body.inserts as i:
        i.big.width = 16.9
        i.small.width = 12.9
        i.gap = 1.6
        i.height = 5.2
        i.hole_diameter = 3.6
        # The insert protrudes from the front surface of the body.
        i.stickout = 1.3
        # Guesstimate based on photos of the connectors.
        i.fillet = 0.5
        i.hole_radius = i.hole_diameter/2
        i.width = i.big.width + i.gap + i.small.width


    # The back of the body has a "grip" that protrudes from the main
    # body, and holds the pins in the correct vertical orientation.
    with cfg.body.grip as g:
        g.depth = 2.9
        # How much extra material to the left/right/top/bottom of the
        # pins does the grip have? This is just cosmetic, and
        # eyeballing photos looks like about one pin width.
        diam = cfg.pin.diameter
        margin = diam
        g.width = (cfg.pin.pos[6] - cfg.pin.pos[0]).length + cfg.pin.diameter + 2*margin
        g.height = diam + 2*margin
        g.notch.width = diam
        g.notch.height = g.height
        g.notch.depth = diam


    # It's a well known scientific fact that CAD drawings look more
    # professional when you fillet the shit out of every edge you can
    # find. And it's true, the connector looks much prettier! It also
    # burns 24 cores for a solid 10 seconds to calculate, and makes no
    # difference to the looks of the kicad render. Keep it around for
    # vanity renders only.
    with cfg.bling as b:
        b.fillet_everything = False
        b.fillet = 0.2

    return cfg

cfg = params()

# Because the connector is centered in XY, we end up dividing by two a
# lot. In denser lines of math, this helps readability.
half = lambda n: n/2

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
        b = cfg.body
        with BuildPart() as body:
            # Base connector shell
            with BuildSketch():
                SemiStadium(b.width, b.height, b.fillet)
            extrude(amount=b.depth)

            # The flange on the front
            with BuildSketch(Plane.XY.offset(b.depth).reverse()):
                SemiStadium(b.flange.width, b.flange.height, b.flange.fillet)
            extrude(amount=b.flange.depth)

            # Carve out the inner cavity
            with BuildSketch(Plane.XY.offset(b.depth).reverse()):
                SemiStadium(b.cavity.width, b.cavity.height, b.cavity.fillet)
            extrude(amount=b.cavity.depth, mode=Mode.SUBTRACT)

            # PCB standoff rails
            with GridLocations(x_spacing=b.standoffs.spacing,
                               y_spacing=b.height + b.standoffs.height,
                               x_count=2,
                               y_count=2):
                Box(b.standoffs.width, b.standoffs.height, b.standoffs.depth,
                    align=(Align.CENTER, Align.CENTER, Align.MIN))

            # Housing's cosmetic fillets
            if cfg.bling.fillet_everything:
                faces = body.faces().filter_by(Plane.XY).sort_by(Axis.Z)
                wires = faces[-2:].wires() + faces[0].wires()
                for wire in wires:
                    fillet(wire.edges(), cfg.bling.fillet)

            # Inserts
            with BuildSketch(Plane.XY.offset(b.depth+b.inserts.stickout).reverse()) as inserts:
                # Outer insert shape
                SemiStadium(b.inserts.width, b.inserts.height)

                # Cut out between the two pin groups
                punchout_center = (cfg.pin.pos[3] + cfg.pin.pos[4])/2
                with Locations(punchout_center):
                    Rectangle(b.inserts.gap, b.inserts.height, mode=Mode.SUBTRACT)

                # Fillet the not yet rounded edges, before we punch more holes
                # and create geometry we'd have to filter.
                fillet(inserts.edges().filter_by(Axis.Y).vertices(), b.inserts.fillet)

                # Holes for the pins
                with Locations(cfg.pin.pos):
                    Circle(b.inserts.hole_radius, mode=Mode.SUBTRACT)
            extrude(until=Until.NEXT)

            # Insert's cosmetic fillets
            if cfg.bling.fillet_everything:
                faces = body.faces().filter_by(Plane.XY).group_by(Axis.Z)[-1]
                for face in faces:
                    fillet(face.outer_wire().edges(), cfg.bling.fillet)
                    fillet(face.inner_wires().edges(), cfg.bling.fillet/2)

            # Pin grip on the rear side
            Box(b.grip.width, b.grip.height, b.grip.depth,
                align=(Align.CENTER, Align.CENTER, Align.MAX))
            with BuildSketch(Plane.XY.offset(-b.grip.depth)):
                with Locations(cfg.pin.pos):
                    Rectangle(b.grip.notch.width, b.grip.notch.height)
            extrude(amount=b.grip.notch.depth, mode=Mode.SUBTRACT)

            # A few final cosmetics for the future assembly.
            body.part.label = "Body"
            super().__init__(part=body.part)
            self.color = Color(0.666, 0.666, 0.666) # guesstimated from online listings


# One pin, including its bend.
class Pin(BasePartObject):
    def __init__(self):
        with BuildPart() as pin:
            with BuildLine(Plane.YZ):
                start_y = cfg.body.depth + cfg.body.inserts.stickout - cfg.pin.insert_recess
                below_y = -(cfg.body.grip.depth + cfg.pin.rear_stickout)
                end_x = -(cfg.body.height/2 + cfg.pin.pcb_stickout)
                FilletPolyline([
                    (0, start_y),
                    (0, below_y),
                    (end_x, below_y)
                ], radius=cfg.pin.elbow_radius)

            with BuildSketch(Plane.XY):
                Circle(cfg.pin.radius)
            sweep()

            # Round off the ends of the pins
            fillet(pin.faces().filter_by(Plane.XY).face().edges(), cfg.pin.radius)
            fillet(pin.faces().filter_by(Plane.XZ).face().edges(), cfg.pin.radius)

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
        for i, loc in enumerate(Locations(cfg.pin.pos).local_locations):
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
        x_3_to_4 = cfg.pin.pos[4] - cfg.pin.pos[3]
        x_adjust = cfg.pin.pos[3] + x_3_to_4/2
        final_pos = Pos(x_adjust.reverse())
        # If we're building the mirrored version of the connector,
        # flip the entire thing now so the pins all point in the same
        # direction and react identically to the following
        # adjustments.
        final_pos = mirror * final_pos
        # Next, the connector has to come up, so that when we rotate
        # about the X axis, the pins end up sticking down along y=0.
        pin_z_adjust = objects[1].bounding_box().min.Z + cfg.pin.radius
        final_pos = Pos(0, 0, -pin_z_adjust) * final_pos
        # Then rotate, so that Z is now "height above PCB".
        final_pos = Rot(90, 0, 0) * final_pos
        # The connector's currently half embedded in the PCB
        # "surface", raise it to final position.
        final_pos = Pos(0, 0, cfg.body.height/2 + cfg.body.standoffs.height) * final_pos

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
