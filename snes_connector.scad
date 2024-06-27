// Exterior width of the main plastic connector body.
body_width = 38.7; // VERIFIED
// Exterior height of the main plastic connector body.
body_height = 12.0; // VERIFIED
// Exterior depth of the main plastic connector body.
body_depth = 13.4; // VERIFIED - including front flange or not? Currently assumes yes.
// Outside corner radius on the square side of the connector body.
body_corner_radius = 1.75;
// Thickness of the outer shell, not including the front flange or standoff rails.
body_thickness = 1.4;
// Interior depth from the surface of the outer flange to the bottom of the connector cavity.
body_inner_depth = 11.8; // VERIFIED
body_inner_corner_radius = 1.0;

// Height of the front flange, as measured from the top of the main body shell when looking into the connector.
flange_offset = 1.95; // 1.975 measured horizontally, 1.935 vertically. Splitting the difference.
// Front-to-back thickness of the front flange.
flange_thickness = 2;

// Width of the standoff rails on the top and bottom of the body.
standoff_width = 1;
// Height of the standoff rails on the top and bottom of the body, relative to the body shell.
standoff_height = 0.5;
// Distance from the left/right outside of the body shell to the center of the closest standoff rail.
standoff_distance_from_edge = 7;

// Extra plastic on the outside edges of the pin grip, around the pins.
pin_grip_margin = 1.2; // TODO: same as pin_diameter
// How much the pin grip protrudes out from the rear of the connector
// body.
pin_grip_depth = 2.4; // TODO: same as pin_diameter?
pin_grip_notch_depth = 1.2; // TODO: same as pin_diameter for now

__4pin_shroud_width = 16.8; // VERIFIED
__3pin_shroud_width = 12.8; // VERIFIED

pin_shroud_height = 5.2; // VERIFIED

pin_shroud_horizontal_margin = 0.6; // DERIVED from verified
pin_shroud_vertical_margin = 0.8; // DERIVED from verified

// Interior depth from the surface of the pin shrouds to the bottom of the connector cavity.
pin_shroud_depth = 13.1; // VERIFIED
// Outside corner radius on the square corners of the pin shroud.
pin_shroud_corner_radius = 0.5;

// Diameter of the pin holes in the connector's central pin shroud.
pin_hole_diameter = 3.6; // VERIFIED
// Diameter of the pins.
pin_diameter = 1.2; // VERIFIED, rounded to standard size 1.18 -> 1.2
// Closest spacing between the centers of adjacent connector pins.
pin_spacing = 4; // RAPHNET
// Spacing between the centers of pins 4 and 5 (the ones that span the gap between the two pin shrouds).
pin_4_to_5_extra_spacing = 2.5; // RAPHNET

// Distance from the flat underside of the connector body to the bottom of the vertical portion of the pins.
pin_pcb_stickout = 8;
// How far the pins are recessed into the pin shroud holes.
pin_recess_depth = 1.5; // VERIFIED

/* [Hidden] */
epsilon = 0.01;
$fn=100;

// The reference orientation is looking into the connector (where the
// controller plug would go), with the 4-pin rectangular shroud on the
// left-hand side. In that orientation, the part origin is the lower
// left rear corner of the body shell. The front of the connector is
// towards positive Z, whereas the pins that come out the back of the
// connector for the PCB are in negative Z.

// Connector terminology:

//  - The connector: the whole device that facilitates breakable
//    electrical contact between conductors. It is composed of:

//    - The contacts: the bits that form the electrical connection.
//    - The connector body: the rest of the connector, which defines
//      the shape the mating connector needs to have, as well as
//      things like insulation ratings and ease of use. The body is
//      composed of:
//      - The insert: the insulating elements into which the contacts
//        are inserted. It provides electrical insulation between
//        neighboring contacts, mechanical protection of fragile
//        contacts, and helps align and guide the mating connector to
//        make a good connection.
//      - The housing: the outer body of the connector that contains
//        and protects the insert and contacts.

// A lot of parts in this connector have to be positioned relative to
// where the pins are in the connector. Pre-calculate the x/y
// positions of the centerline of all pins, so that all definitions
// can reference them.

// Abstract X positions of the pins, if pin 1 (left-most) is at x=0.
pins_x_offset_from_pin_1 = [ for (i = [0:6]) i*pin_spacing + (i>3 ? pin_4_to_5_extra_spacing : 0) ];
// overall X width from the center of pin 1 to the center of pin
// 7. The pins center horizontally within the connector body, so we
// can use this to calculate the absolute X position of all the pins.
pin_group_overall_x_width = 6*pin_spacing + pin_4_to_5_extra_spacing;
pin_1_x_offset = (body_width - pin_group_overall_x_width)/2;
// The Y offset of pins in our coordinate system is much easier: they
// center vertically in the connector body.
pins_y_offset = body_height/2;
// Finally, this is a vector of (x,y) coordinates for the center of
// each pin.
pin_coordinates = [ for (x_rel = pins_x_offset_from_pin_1) [x_rel + pin_1_x_offset, pins_y_offset] ];
// Due to the above coordinates being the center of pins, math often
// requires offsetting by radius instead of diameter.
pin_radius = pin_diameter/2;

// From the reference dimensions, we know the overall exterior depth
// of the body, as well as the depth from the front face to the bottom
// of the interior cavity. But for a bunch of operations, we'd really
// rather know the Z position of that inner bottom face (which in this
// coordinate system is also the thickness of that surface). Calculate
// it now so that later modules can have nice things.
body_pocket_z_offset = body_depth - body_inner_depth;

// for_pins instantiates a copy of children for each pin, and places
// each one at the pin's x/y coordinates.
module for_pins(start=0, end=6) {
  for (i=[start:end])
    translate([pin_coordinates[i][0], pin_coordinates[i][1], 0])
      children();
}

// rounded_rectangle constructs a rectangle with rounded corners. the
// bottom-left corner of the rectangle (prior to rounding) is placed
// at the origin.
module rounded_rectangle(width, height, radius) {
  assert(width >= 2*radius, "rounded rectangle width is too small for corner radius");
  assert(height >= 2*radius, "rounded rectangle height is too small for corner radius");

  // To make the shape, we put circles at each corner to define the
  // corner arc, then use hull() to vacuum form a rectangle around
  // them. These are the X/Y coordinates of the _centers_ of the
  // corner circles.
  left_x = radius;
  right_x = width - radius;
  bottom_y = radius;
  top_y = height - radius;

  hull() {
    for (x=[left_x, right_x], y=[bottom_y, top_y])
      translate([x, y])
        circle(r=radius);
  }
}

// rounded_semistadium constructs a semistadium, which is a with the
// right-hand edge replaced with a semicircle. The SNES controller
// port uses this shape a lot.
//
// Like rounded_rectangle, the remaining corners on the left side are
// rounded, and the bottom-left corner (prior to rounding) is placed
// at the origin.
module rounded_semistadium(width, height, radius) {
  semicircle_diameter = height;
  semicircle_radius = semicircle_diameter/2;

  assert(width >= radius+semicircle_radius, "semistadium length is too small given the height and corner radius");
  assert(height >= 2*radius, "semistadium height is too small given the corner radius");

  // Similar to rounded_rectangle, we build the shapes of the corners
  // and then use hull() to do the rest. But this time the corner
  // shape is irregular enough that we don't bother with a for loop.
  hull() {
    // bottom left radius
    translate([radius, radius])
      circle(r=radius);

    // top left radius
    translate([radius, height-radius])
      circle(r=radius);

    // right semicircle
    translate([width-semicircle_radius, semicircle_radius])
      circle(r=semicircle_radius);
  }
}

///// Finally, start making connector parts!

// The outer shell, with its front flange and standoffs. It doesn't
// have the rear "pin grip" caboose, or any interior features. Those
// get defined separately and combined later.
module shell() {
  // Start with getting the outer shape right, then we'll carve out
  // the inside.
  module solid() {
    // The connector's basic outer shape is a big semistadium. Extrude
    // slightly short in Z so that the front flange combines cleanly
    // below.
    linear_extrude(body_depth - flange_thickness + epsilon)
      rounded_semistadium(body_width, body_height, body_corner_radius);

    // The front face has a flange that comes outwards, to give a
    // clean look when panel-mounting.
    translate([0, 0, body_depth - flange_thickness])
      linear_extrude(flange_thickness)
      offset(r=flange_offset)
      rounded_semistadium(body_width, body_height, body_corner_radius);

    // The top and bottom of the connector body have a pair of
    // standoff rails. These seem to be so that the connector sits a
    // little off the PCB, and thus can flex a little during
    // plugging/unplugging without transferring that force to the PCB.
    //
    // To play nice with CSG, draw the 4 standoffs as 2 big rectangles
    // that slice "through" the connector body top-to-bottom. Only the
    // ends of the rectangles peek out of the overall shape.
    for (x=[standoff_distance_from_edge, body_width - standoff_distance_from_edge])
      translate([x, body_height/2, epsilon])
        linear_extrude(body_depth - 2*epsilon)
        square([standoff_width, body_height + 2*standoff_height], center=true);
  }

  // The pocket is just another semistadium, centered on the solid
  // shell and smaller by body_thickness on all sides.
  module pocket() {
    width = body_width - 2*body_thickness;
    height = body_height - 2*body_thickness;
    depth = body_inner_depth;

    translate([body_thickness, body_thickness, body_pocket_z_offset])
      linear_extrude(depth+epsilon)
      rounded_semistadium(width, height, body_inner_corner_radius);
  }

  difference() {
    solid();
    pocket();
  }
}

// The "pin grip" is the little caboose on the back side of the
// connector, through which the pins come through the body before
// turning at a right angle towards the PCB.
module pin_grip() {
  // Conveniently, this part neatly surrounds the pin positions on the
  // connector, so we can define it relative to our precalculated pin
  // coordinates.

  // The pins seem to be surrounded by a ring of plastic that's one
  // pin diameter wide on all sides. TODO: confirm this is
  // approx. right.
  pin_grip_margin = pin_diameter;

  frame_x_width = pin_group_overall_x_width + pin_diameter + 2*pin_grip_margin;
  frame_y_height = pin_diameter + 2*pin_grip_margin;

  // Main body of the pin grip, just a cube at the right (x,y)
  // coordinates relative to the rest of the connector. It's on the
  // wrong side of the Z axis, but that'll get fixed below. It's also
  // made a little taller than necessary, to ensure a good weld with
  // the rest of the connector later.
  module shell() {
    frame_x_offset = pin_coordinates[0][0] - pin_radius - pin_grip_margin;
    frame_y_offset = pin_coordinates[0][1] - pin_radius - pin_grip_margin;

    translate([frame_x_offset, frame_y_offset, 0])
      cube([frame_x_width, frame_y_height, pin_grip_depth + epsilon]);
  }

  // Lay out the notches in the right position around the locations of
  // the pins. Again the various epsilons ensure these blocks fully
  // overlap the area to be removed from the shell.
  module notches() {
    for_pins()
      translate([0, 0, -epsilon])
      linear_extrude(pin_grip_notch_depth + epsilon)
      square([pin_diameter, frame_y_height + 2*epsilon], center=true);
  }

  // Finally, cut out the notches, and move the pin grip below the XY
  // plane, leaving just epsilon of material peeking out to weld with
  // the connector shell later.
  //
  // Technically we should also drill out holes for the pins here, but
  // it makes no visual difference in the final result since the pins
  // just get unioned up anyway.
  translate([0, 0, -pin_grip_depth])
    difference() {
      shell();
      notches();
    }
}

// The pin shroud is the pair of plastic features inside the connector
// cavity that protest the fragile pins, and help guide the mating
// connector.
module shroud() {
  // Similar to the pin grip, the shroud is centered on the pins, and
  // so can be neatly defined in those terms. This time however, the
  // spacing has to use the diameter of a drill centered on the pin
  // location, rather than the diameter of the pins.

  pin_hole_radius = pin_hole_diameter/2;

  function shroud_width(num_pins) = (num_pins-1)*pin_spacing + 2*(pin_hole_radius + pin_shroud_horizontal_margin);
  shroud_height = pin_hole_diameter + 2*pin_shroud_vertical_margin;

  shroud_x_offset = pin_coordinates[0][0] - pin_hole_radius - pin_shroud_horizontal_margin;
  shroud_y_offset = pin_coordinates[0][1] - pin_hole_radius - pin_shroud_vertical_margin;

  // First the solid shell, which is in two parts: a 4-pin rectangle,
  // and a 3-pin semistadium.
  module shell() {
    translate([shroud_x_offset, shroud_y_offset]) {
      rounded_rectangle(shroud_width(4), shroud_height, pin_shroud_corner_radius);

      // Outlines created at the origin naturally align to align with
      // pins starting at 1. The second shell needs to align starting
      // with pin 5, hence the X offset.
      translate([pins_x_offset_from_pin_1[4], 0])
        rounded_semistadium(shroud_width(3), shroud_height, pin_shroud_corner_radius);
    }
  }

  // The drill holes are much easier: a cutout circle centered on
  // every pin.
  module holes() {
    for_pins()
      circle(d=pin_hole_diameter);
  }

  // Finally, punch out the holes, extrude the shrouds, and position
  // them ready for fusion with the rest of the connector.
  translate([0, 0, body_pocket_z_offset - epsilon])
  linear_extrude(pin_shroud_depth + epsilon)
  difference() {
    shell();
    holes();
  }
}

// Last but not least, the electrical bits! The pins start inside the
// connector insert, go straight out through the back of the housing,
// and after going through the pin grip block make a right-angle and
// go towards where the PCB would be. The turn direction can be
// flipped with mirror=true, allowing for under-board mounts or for a
// flipped connector with pin 1 on the right instead of the left (the
// SNES had one port in either orientation).
module pins(mirror=false) {
  // To implement the mirroring, we want to keep the part of the pin
  // that goes into the connector insert running along the Z axis, so
  // we can later do a 180 degree rotation about Z before moving the
  // pin to its proper x/y position.
  elbow_radius = pin_diameter;

  // The insert side of the pin starts a little recessed from the
  // front of the insert body, and stops just as it comes out of the
  // corresponding pin grip notch (it starts curving after that).
  pin_insert_depth = pin_shroud_depth + body_pocket_z_offset + pin_grip_depth - pin_grip_notch_depth - pin_recess_depth;
  pin_pcb_height = body_height/2 - elbow_radius + pin_pcb_stickout;

  module pin_insert() {
    linear_extrude(pin_insert_depth + epsilon)
      circle(d=pin_diameter);
  }

  module elbow() {
    // Rotational extrusions are weird in openscad. You have to define
    // a 2D sketch in the XY plane, move it out along X to define your
    // radius, extrude... And you end up with your XY plane sketch
    // extruded as if it had been in the XZ plane, and then have to
    // rotate it back to where you wanted it. Okay.
    //
    // With this set of contortions, the elbow starts at the origin,
    // extends below the XY plane, and curves along the YZ plane going
    // towards negative Y.
    rotate([-90, 0, 90])
      translate([-elbow_radius, 0, 0])
      rotate_extrude(angle=90)
      translate([elbow_radius, 0, 0])
      circle(d=pin_diameter);
  }

  module pin_pcb() {
    translate([0, -elbow_radius, -elbow_radius])
    rotate([90, 0, 0])
    linear_extrude(pin_pcb_height + epsilon)
      circle(d=pin_diameter);
  }

  // Put all the pieces together. The whole thing needs to drop down
  // in Z a little bit, because the point on the XY plane is currently
  // where the pin comes out of the pin grip body, but the rest of the
  // connector has the rear of the housing on that plane.
  //
  // This is the point where we rotate about the Z axis to implement
  // mirroring if requested.
  //
  // And finally, replicate that seven times and move it to the right
  // position in the connector.
  for_pins() {
    rotate([0, 0, mirror ? 180 : 0])
    translate([0, 0, -pin_grip_depth+pin_grip_notch_depth]) {
      pin_insert();
      elbow();
      pin_pcb();
    }
  }
}

// At last, the entire connector! At this point all the hard work is
// done, the previous modules build up the individual parts and
// position them properly in 3D space. All that's left is to union
// them all together, and move the final object to the origin in a
// good orientation.
module connector(mirror=false) {
  translate([0, 0, body_height/2 + standoff_height])
  rotate([0, mirror ? 180 : 0, 0]) // pins always point down, flip connector if needed
  translate([-body_width/2, body_depth/2, -body_height/2])
  rotate([90,0,0]) {
    color("gray") {
      shell();
      pin_grip();
      shroud();
    }

    color("khaki")
      pins(mirror);
  }
}

module demo() {
  x_off = body_width/1.25;
  z_off = body_height*2.5;

  module con(mirror) {
    translate([0, 0, -body_height/2 - standoff_height + pin_pcb_stickout/2])
      connector(mirror);
  }

  module col(mirror) {
    translate([0, 0, 1.5*z_off]) {
    translate([0, 0, 0])
      con(mirror);

    translate([0, 0, -z_off])
      rotate([0, 0, -180])
      con(mirror);
    }
  }

  translate([+x_off, 0, 0])
    col(false);

  translate([-x_off, 0, 0])
    col(true);

  // translate([0, 0, -body_height/2]) {
  //   translate([-x_off, 0, z_off])
  //     connector(true);

  //   translate([x_off, 0, z_off])
  //     connector(false);

  //   translate([-x_off, 0, -0.9*z_off])
  //     rotate([-90, 0, 0])
  //     connector(false);

  //   translate([x_off, 0, -0.9*z_off])
  //     rotate([-90, 0, 0])
  //     connector(true);

  //   translate([-x_off, 0, -3*z_off])
  //     rotate([-180, 0, 0])
  //     connector(true);

  //   translate([x_off, 0, -3*z_off])
  //     rotate([-180, 0, 0])
  //     connector(true);
  // }
}

demo();
