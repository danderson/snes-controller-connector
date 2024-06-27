import contextlib
import math
import copy
from build123d import *
from ocp_vscode import *

def loud(x):
    log("=======================================")
    log("=========: {}".format(x))
    log("=======================================")

#show = show_object

set_defaults(reset_camera=False)

class SemiStadium(BaseSketchObject):
    def __init__(self, width, height, fillet_radius=0, align=(Align.CENTER, Align.CENTER), mode=Mode.ADD):
        radius = height/2
        halfwidth = width/2
        halfheight = height/2
        circle_center_x = halfwidth-radius
        with BuildSketch() as sk:
            with BuildLine() as ln:
                Line(
                    (-halfwidth,-halfheight),
                    (circle_center_x, -halfheight),
                )
                ThreePointArc(
                    (circle_center_x, -halfheight),
                    (halfwidth, 0),
                    (circle_center_x, halfheight),
                )
                Line(
                    (circle_center_x, halfheight),
                    (-halfwidth, halfheight),
                )
                Line(
                    (-halfwidth, halfheight),
                    (-halfwidth, -halfheight),
                )
            make_face()
            if fillet_radius > 0:
                fillet(sk.edges().sort_by(Axis.X).first.vertices(), fillet_radius)
        super().__init__(obj=sk.sketch, align=align, mode=mode)

# Verified dimensions on a real part
body_width = 38.7
body_height = 12.0
body_depth = 11.4 # not including front flange
body_thickness = 1.4
body_fillet_radius = 1.75

flange_stickout = 1.95
flange_thickness = 2

pin_spacing = 4
pin_4_to_5_extra_spacing = 2.5 # RAPHNET
pin_diameter = 1.2
pin_radius = pin_diameter/2
pin_recess_depth = 1.5 # from top surface of insert
pin_elbow_radius = pin_diameter
pin_pcb_stickout = 8

insert_horizontal_margin = 0.6
insert_vertical_margin = 0.8
insert_drill_diameter = 3.6
insert_fillet_radius = 0.5 # MADE UP
insert_drill_radius = insert_drill_diameter/2
insert_width = 6*pin_spacing + pin_4_to_5_extra_spacing + 2*insert_horizontal_margin + insert_drill_diameter
insert_height = insert_drill_diameter + 2*insert_vertical_margin
insert_depth = 13.1 # from top surface to bottom of housing cavity
insert_edge_to_pin_center = insert_horizontal_margin + insert_drill_radius

grip_margin = pin_diameter # TODO: confirm if right
grip_depth = 2.4 # pin_grip_depth
grip_notch_width = pin_diameter
grip_notch_depth = pin_diameter
grip_width = 6*pin_spacing + pin_4_to_5_extra_spacing + 2*pin_radius + 2*grip_margin
grip_height = pin_diameter + 2*grip_margin
grip_fillet_radius = 0.1

body_width = 38.7
body_height = 12.0
body_depth = 11.4
body_thickness = 1.4

showboating_fillet_radius = 0.1

## Mathed shit

class vec(object):
    def __init__(self, *, x=0, y=0):
        self.x, self.y = x, y

    @classmethod
    def between(cls, a, b):
        return (a+b)/2

    def __repr__(self):
        return self.tuple().__repr__()

    def __add__(self, other):
        return vec(x=self.x+other.x, y=self.y+other.y)

    def __sub__(self, other):
        return vec(x=self.x-other.x, y=self.y-other.y)

    def __truediv__(self, num):
        return vec(x=self.x/num, y=self.y/num)

    def magnitude(self):
        return math.sqrt(math.pow(self.x, 2)+math.pow(self.y, 2))

    def tuple(self):
        return (self.x, self.y)

    def location(self):
        return Locations(self.tuple())

def pin_offset_vec(n):
    if n < 0 or n >= 7:
        raise ValueError("non-existent pin")
    elif n == 0:
        return vec()
    elif n < 4:
        return vec(x=n*pin_spacing)
    else:
        return vec(x=n*pin_spacing + pin_4_to_5_extra_spacing)

pin_1_vec = vec(x=-insert_width/2 + insert_edge_to_pin_center)

pin_vecs = [pin_1_vec+pin_offset_vec(n) for n in range(7)]

def pin_locations():
    return Locations(*[pin.tuple() for pin in pin_vecs])

# The reference orientation is looking into the connector (where the
# controller plug would go), with the 4-pin rectangular shroud on the
# left-hand side. In that orientation, the part (X,Y) origin is in the
# center of the frame. The front of the connector is towards positive
# Z, whereas the pins that come out the back of the connector for the
# PCB are in negative Z.
#
# Connector terminology:
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

with BuildPart() as body:
    # Base connector housing
    with BuildSketch() as housing:
        SemiStadium(body_width, body_height, body_fillet_radius)
    extrude(amount=body_depth)
    offset(amount=-body_thickness, openings=body.faces().sort_by(Axis.Z).last)

    # Front flange
    with BuildSketch(Plane.XY.offset(body_depth)):
        SemiStadium(body_width, body_height)
        offset(amount=flange_stickout, kind=Kind.ARC)
        with BuildSketch(mode=Mode.SUBTRACT):
            SemiStadium(body_width, body_height, body_fillet_radius)
            offset(amount=-body_thickness)
    extrude(amount=flange_thickness)

    # Inserts
    with BuildSketch(Plane.XY.offset(body_thickness)) as inserts:
        # Outer insert shape
        SemiStadium(insert_width, insert_height)

        # Cut out between the two pin groups
        punchout_center = (pin_vecs[3] + pin_vecs[4])/2
        punchout_width = pin_vecs[4] - pin_vecs[3] - vec(x=2*insert_edge_to_pin_center)
        with punchout_center.location():
            Rectangle(punchout_width.magnitude(), insert_height, mode=Mode.SUBTRACT)

        # Fillet the not yet rounded edges, before we punch more holes
        # into stuff.
        fillet(inserts.edges().filter_by(Axis.Y).vertices(), insert_fillet_radius)

        # Insert holes for the pins
        with pin_locations():
            Circle(insert_drill_radius, mode=Mode.SUBTRACT)
    extrude(amount=insert_depth)

    # Pin grip on the rear side
    Box(grip_width, grip_height, grip_depth, align=(Align.CENTER, Align.CENTER, Align.MAX))
    with BuildSketch(Plane.XY.offset(-grip_depth)):
        with pin_locations():
            Rectangle(grip_notch_width, grip_height)
    extrude(amount=grip_notch_depth, mode=Mode.SUBTRACT)

    # Holes through the body for pins
    with pin_locations():
        Hole(pin_radius)

with BuildPart() as pin:
    with BuildLine(Plane.YZ):
        connector_tip = vec(y=body_thickness + insert_depth - pin_recess_depth)
        elbow_start = vec(y=-(grip_depth - grip_notch_depth))
        elbow_end = elbow_start + vec(x=pin_elbow_radius) - vec(y=pin_elbow_radius)
        board_tip = elbow_end + vec(x=body_height/2 - pin_elbow_radius + pin_pcb_stickout)
        Line(
            connector_tip.tuple(),
            elbow_start.tuple(),
        )
        TangentArc([elbow_start.tuple(), elbow_end.tuple()], tangent=(0, -1))
        Line(
            elbow_end.tuple(),
            board_tip.tuple(),
        )
    with BuildSketch(Plane.XY):
        Circle(pin_radius)
    sweep()

body.part.label = "Body"
body.part.color = Color(0.666, 0.666, 0.666)

components = [body.part]
for i, loc in enumerate(pin_locations().local_locations):
    p = copy.copy(pin.part)
    p.label = f"Pin {i+1}"
    p.color = Color(0.859, 0.737, 0.494)
    components.append(p.locate(loc))

final = Compound(children=components)

export_step(final, 'snes_connector.step')

# Material corrections in freecad:
#  - Body: plastic
#          diffuse:  #a8aaaa
#          specular: #0f0f0f (default)
#          emissive: 0
#          ambient: #191919 (default)
#          shininess: 0%
#
#  - Pins: gold
#          diffuse: #dbbc7e (kicad shader)
#          specular: #23252f (default)
#          emissive: 0
#          ambient: #4c3a18 (default)
#          shininess: 41%


#show_all()
show(final)

# with BuildPart() as part:
#     ss=semistadium(body_width, body_height)
#     add(ss)
#     extrude(amount=body_depth)
#     offset(amount=-body_thickness, openings=part.faces().sort_by(Axis.Z)[-1])
#     topface_inner = faces().sort_by(Axis.Z)[-1].inner_wires()[0]
#     with BuildSketch(Plane.XY.offset(body_depth)) as s:
#         add(ss)
#         offset(amount=2)
#     extrude(amount=1)
#     with BuildSketch(Plane.XY.offset(body_depth)) as s2:
#         add(topface_inner)
#         make_face()
#     extrude(amount=1,mode=Mode.SUBTRACT)
