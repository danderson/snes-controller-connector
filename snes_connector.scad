// Exterior width of the main plastic connector body.
body_width = 38.5;
// Exterior height of the main plastic connector body.
body_height = 12.3;
// Exterior depth of the main plastic connector body.
body_depth = 13.2;
// Outside corner radius on the square side of the connector body.
body_corner_radius = 1.75;
// Thickness of the outer shell, not including the front flange or standoff rails.
body_thickness = 1.4;
// Interior depth from the surface of the outer flange to the bottom of the connector cavity.
body_inner_depth = 11.8; // VERIFIED
body_inner_corner_radius = 1.0;

// Height of the front flange, as measured from the top of the main body shell when looking into the connector.
flange_offset = 1;
// Front-to-back thickness of the front flange.
flange_thickness = 1.4;

// Width of the standoff rails on the top and bottom of the body.
standoff_width = 1;
// Height of the standoff rails on the top and bottom of the body, relative to the body shell.
standoff_height = 0.5;
// Distance from the left/right outside of the body shell to the center of the closest standoff rail.
standoff_distance_from_edge = 7;

pin_grip_width = 29;
pin_grip_height = 3;
pin_grip_depth = 2;
pin_grip_notch_depth = 1;

4pin_shroud_width = 16.9; // VERIFIED
4pin_shroud_height = 5.18; // VERIFIED

3pin_shroud_width = 12.8; // VERIFIED
3pin_shroud_height = 5.18; // VERIFIED

// Interior depth from the surface of the pin shrouds to the bottom of the connector cavity.
pin_shroud_depth = 13.1; // VERIFIED
// Outside corner radius on the square corners of the pin shroud.
pin_shroud_corner_radius = 0.5;

// Diameter of the pin holes in the connector's central pin shroud.
pin_hole_diameter = 3.60; // VERIFIED
// Closest spacing between the centers of adjacent connector pins.
pin_spacing = 4;
// Diameter of the pins.
pin_diameter = 1.18; // VERIFIED
// Spacing between the centers of pins 4 and 5 (the ones that span the gap between the two pin shrouds).
pin_4_to_5_extra_spacing = 2.50;
// Distance from the flat rear body of the connector to the center of the vertical portion of the pins (the portion that connects to the PCB).
pin_rear_stickout = 3;
// Distance from the flat underside of the connector body to the bottom of the vertical portion of the pins.
pin_vertical_stickout = 3;
// How far the pins are recessed into the pin shroud holes.
pin_recessing = 1;

outer_big_corner_radius = body_height/2;

standoff_distance_from_center = body_width/2 - standoff_distance_from_edge;

/* [Hidden] */
epsilon = 0.001;

function shroud_margin(w, npins) = (w - ((npins-1)*pin_spacing + pin_hole_diameter))/2;
4pin_shroud_margin = shroud_margin(4pin_shroud_width, 4);
3pin_shroud_margin = shroud_margin(3pin_shroud_width, 3);

$fn=100;

// The reference orientation is looking into the connector (where the controller plug would go), with the 4-pin rectangular shroud on the left-hand side. In that orientation, the part origin is the lower-left corner of the front flange, if you imagine that the corner isn't rounded.

// rounded_rectangle constructs a rectangle with rounded corners. the bottom-left corner of the rectangle (prior to rounding) is placed at the origin.
module rounded_rectangle(x, y, r) {
    assert(x >= 2*r, "rounded rectangle width is too small for corner radius");
    assert(y >= 2*r, "rounded rectangle height is too small for corner radius");

    w = x - 2*r;
    h = y - 2*r;

    translate([r,r])
    hull() {
        for (dx=[0,w], dy=[0,h])
            translate([dx, dy])
            circle(r=r);
    }
}

// rounded_semistadium constructs a semistadium, which is like a rectangle except the right edge is replaced with a semicircle. The left-hand edges are rounded to the specified radius.
module rounded_semistadium(x, y, r) {
    assert(x >= y+r, "semistadium length is for height and corner radius");
    assert(y >= 2*r, "semistadium height is too small for corner radius");

    semicircle_r = y/2;

    hull() {
        // bottom left radius
        translate([r,r])
        circle(r=r);
        
        // top left radius
        translate([r,y-r])
        circle(r=r);
        
        // right semicircle
        translate([x-semicircle_r, semicircle_r])
        circle(r=semicircle_r);
    }    
}

// The solid outer shell, with front flange and standoffs.
module shell() {
    x = body_width;
    y = body_height;
    z = body_depth;
    r = body_corner_radius;
    t = body_thickness;
    
    f_off = flange_offset;
    f_z = flange_thickness;
    
    s_x = standoff_width;
    s_y = y + 2*standoff_height;
    s_z = body_depth;
    s_off = standoff_distance_from_edge;

    // Core shape
    linear_extrude(z-epsilon)
    rounded_semistadium(x, y, r);
    
    // Front flange
    translate([0, 0, z-f_z])
    linear_extrude(f_z)
    offset(r=f_off)
    rounded_semistadium(x, y, r);
        
    // Standoffs
    for (dx=[s_off, x-s_off])
    translate([dx, y/2, epsilon])
    linear_extrude(s_z - 2*epsilon)
    square([s_x, s_y], center=true);
}

module pin_grip() {
    x = pin_grip_width;
    y = pin_grip_height;
    z = pin_grip_depth;
    
    notch_x_off = (pin_grip_width - (6*pin_spacing + pin_4_to_5_extra_spacing + pin_diameter))/2;
    
    x_off = (body_width - x)/2;
    y_off = (body_height - y)/2;
    
    translate([x_off, y_off, -z+epsilon])
    difference() {
        cube([x,y,z+epsilon]);
        for_pins() {
            translate([notch_x_off, -epsilon, -epsilon])
            cube([pin_diameter, pin_grip_height+2*epsilon, pin_grip_notch_depth+epsilon]);
        }
    }
}

// The pocket carved out of the connector front, into which the pin shroud and pins will go.
module pocket() {
    x = body_width - 2*body_thickness;
    y = body_height - 2*body_thickness;
    z = body_inner_depth;
    r = body_inner_corner_radius;
    
    x_off = body_thickness;
    y_off = body_thickness;
    z_off = body_depth;
 
    translate([x_off, y_off, z_off + epsilon])
    mirror([0,0,1])
    linear_extrude(z + epsilon)
    rounded_semistadium(x, y, r);
}

module for_pins() {
    function gaps(i) = i * pin_spacing;
    function maybe_space(i) = i >= 4 ? pin_4_to_5_extra_spacing : 0;
    
    for (i=[0:6])
        translate([gaps(i)+maybe_space(i),0,0])
        children();
}

module shroud() {
    z = body_depth - body_inner_depth + pin_shroud_depth;
    shroud_width = 6*pin_spacing + pin_4_to_5_extra_spacing + pin_hole_diameter + 4pin_shroud_margin + 3pin_shroud_margin;
    x_off = (body_width - shroud_width)/2;
    y_off = (body_height - 4pin_shroud_height)/2;

    module shell() {
        rounded_rectangle(4pin_shroud_width,
                          4pin_shroud_height,
                          pin_shroud_corner_radius);
        
        translate([4*pin_spacing + pin_4_to_5_extra_spacing,0,0])
        rounded_semistadium(3pin_shroud_width,
                            3pin_shroud_height,
                            pin_shroud_corner_radius);
    }
    
    module holes() {
        translate([pin_hole_diameter/2 + 4pin_shroud_margin, 4pin_shroud_height/2])
        for_pins() circle(d=pin_hole_diameter);
    }
    
    translate([x_off, y_off, epsilon])
    linear_extrude(z-epsilon)
    difference() {
        shell();
        holes();
    }
}

module pins() {
    for_pins() {
        translate([3.575+pin_hole_diameter/2, body_height/2, 0])
        translate([pin_diameter/2, 0, -pin_rear_stickout])
        cylinder(h=body_depth - body_inner_depth + pin_shroud_depth - pin_recessing + pin_rear_stickout, d=pin_diameter);
    }
}

module connector() {
    difference() {
        shell();
        pocket();
    }
    pin_grip();
    shroud();
    pins();
}

!connector();

module pin_90(diameter, y, z) {
    module half_sphere(diameter) {
        difference() {
            sphere(d=diameter);
            
            translate([0, 0, -diameter/2])
            cube(diameter+epsilon, center=true);
        }
    }
    
    module domed_wire(diameter, length) {
        rotate([90, 0, 0])
        union() {
            cylinder(h=length-diameter/2+epsilon, d=diameter);
            translate([0, 0, length-diameter/2])
            half_sphere(diameter);
        }
    }
    
    module elbow(diameter, elbow_angle, elbow_radius) {
        rotate([0, sign(elbow_angle)*90, 0])
        translate([-elbow_radius, 0, 0])
        rotate_extrude(angle=abs(elbow_angle))
        translate([elbow_radius, 0, 0])
        circle(d=diameter);
    }

    depth = y;
    dir = sign(z);
    height = abs(z);
    radius = diameter/2;
    
    translate([0, y-radius, 0])
    union() {
        translate([0, -diameter+epsilon, 0])
            domed_wire(diameter, depth-1.5*diameter+epsilon);
        translate([0, -diameter, 0])
        rotate([0, (dir-1)*90, 0])
            elbow(diameter, 90, diameter);
        translate([0, 0, dir*(diameter-epsilon)])
        rotate([-dir*90, 0, 0])
            domed_wire(diameter, height-1.5*diameter+epsilon);
    }
}

module connector2(flip=false) {
    interior_width = 6*pin_spacing + pin_4_to_5_spacing + pin_diameter;
    interior_offset = (body_width - interior_width)/2;
    pin_offset = interior_offset + pin_hole_diameter/2 + (pin_spacing - pin_hole_diameter);
    pin_dir = flip ? -1 : 1;
    pin_height = body_height/2 + pin_vertical_stickout;

    module body() {
        color("gray")
        connector_body();
    
        color("gray")
        translate([interior_offset,0,epsilon]) 
        connector_interior();
    }

    module pins() {
        translate([pin_offset, -body_depth+pin_recessing, 0])
        color("khaki")
        each_pin() {
            pin_90(pin_diameter, body_depth+pin_rear_stickout-pin_recessing, pin_dir*pin_height);
        }
    }

    module connector() {
        rotate([90,0,0])
        body();
        pins();
    }
    
    translate([-body_width/2, body_depth/2, 0])
    connector();
}

module demo() {
    xpres = 0.7*body_width;
    zpres = body_height;

    module pair() {
        translate([-xpres, 0, 0])
        rotate([0, 180, 0])
        connector(false);

        translate([xpres, 0, 0])
        connector(true);
    }

    translate([0,0,zpres])
    pair();

    translate([0, 0, -zpres])
    rotate([0, 0, 180])
    pair();
}

//connector_interior();