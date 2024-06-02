// Exterior width of the main plastic connector body.
body_width = 38.5;
// Exterior height of the main plastic connector body.
body_height = 12.3;
// Exterior depth of the main plastic connector body.
body_depth = 13.2;
// Interior depth from the surface of the outer flange to the bottom of the connector cavity.
body_inner_depth = 11.8; // VERIFIED
// Outside corner radius on the square side of the connector body.
body_corner_radius = 1.0;
// Thickness of the outer shell, not including the front flange or standoff rails.
body_thickness = 1.4;

// Height of the front flange, as measured from the top of the main body shell when looking into the connector.
flange_offset = 1;
// Front-to-back thickness of the front flange.
flange_thickness = 1.4;

// Width of the standoff rails on the top and bottom of the body.
standoff_width = 1;
// Height of the standoff rails on the top and bottom of the body, relative to the body shell.
standoff_height = 0.5;
// Distance from the left/right outside of the body shell to the center of the closest standoff rail.
standoff_distance_from_edge = 10;

// Diameter of the pin holes in the connector's central pin shroud.
pin_hole_diameter = 3.30;
// Closest spacing between the centers of adjacent connector pins.
pin_spacing = 4;
// Diameter of the pins.
pin_diameter = 1.20;
// Spacing between the centers of pins 4 and 5 (the ones that span the gap between the two pin shrouds).
pin_4_to_5_spacing = 6.50;
// Outside corner radius on the square corners of the pin shroud.
pin_shroud_corner_radius = 0.5;
// Interior depth from the surface of the pin shrouds to the bottom of the connector cavity.
pin_shroud_depth = 13.1; // VERIFIED
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

$fn=100;

// The reference orientation is looking into the connector (where the controller plug would go), with the 4-pin rectangular shroud on the left-hand side. In that orientation, the part origin is the lower-left corner of the front flange, if you imagine that the corner isn't rounded.

module connector_body() {
    module outline() {
        translate([body_corner_radius, 0, 0])
        hull() {
            translate([0, (body_height)/2-body_corner_radius, 0])
                circle(r=body_corner_radius);
            translate([0, -body_height/2+body_corner_radius, 0])
                circle(r=body_corner_radius);
            translate([body_width-outer_big_corner_radius, 0, 0])
                circle(r=outer_big_corner_radius);
        }
    }
    
    module outline_with_guides() {
        outline();
        for (dir_x=[+1, -1])
            for (dir_y=[+1,-1])
                translate([body_width/2, 0, 0])
                translate([dir_x*standoff_distance_from_center, 0, 0])
                translate([0, dir_y*((body_height+standoff_height)/2-epsilon), 0])
                    square([standoff_width, standoff_height], center=true);
    }
    
    // The fancy outer shape of the connector body
    translate([0,0,epsilon])
    linear_extrude(body_depth - 2*epsilon)
    difference() {
        outline_with_guides();
        offset(delta=-body_thickness)
        outline();
    }
    
    // Close off the back near the pins
    linear_extrude(body_depth - body_inner_depth)
    offset(delta=-epsilon)
    outline();
    
    // Flange at the front of the connector
    translate([0,0,body_depth-flange_thickness+epsilon])
    linear_extrude(flange_thickness)
    difference() {
        offset(delta=flange_offset)
        outline();
        
        offset(delta=-body_thickness-epsilon)
        outline();
    }
}

module each_pin() {
    group_gap = pin_4_to_5_spacing - pin_spacing;
    function pin_offset(i) = i*pin_spacing + (i>3 ? group_gap : 0);
    for (i=[0:6])
        translate([pin_offset(i), 0, 0])
            children();
}

module connector_interior() {
    hole_radius = pin_hole_diameter/2;
    gap_between_holes = pin_spacing - pin_hole_diameter;
    square_group_width = 3*pin_spacing + 2*hole_radius + 2*gap_between_holes;
    oblong_group_width = 2*pin_spacing + 2*hole_radius + 2*gap_between_holes;
    oblong_offset = 3*pin_spacing + pin_4_to_5_spacing;
    group_height = pin_hole_diameter + 2*gap_between_holes;
    
    module rounded_side_scaffold(h, r) {
        for (dir=[-1,+1])
            translate([r, dir*(h/2-r), 0])
            circle(r);
    }
    
    module rounded_square(w, h, r) {
        hull() {
            rounded_side_scaffold(h, r);
            translate([w-2*r, 0, 0]) rounded_side_scaffold(h, r);
        }
    }
    
    module semi_oblong(w, h, r) {
        hull() {
            rounded_side_scaffold(h, r);
            translate([h/2 + w - h, 0, 0])
            circle(d=h);
        }
    }

    module body() {
        rounded_square(square_group_width, group_height, pin_shroud_corner_radius);
        translate([oblong_offset, 0, 0])
        semi_oblong(oblong_group_width, group_height, pin_shroud_corner_radius);
    }
    
    module holes() {
        translate([hole_radius + gap_between_holes, 0, 0])
        each_pin() {
            circle(d=pin_hole_diameter);
        }
    }
    
    linear_extrude(body_depth)
    difference() {
        body();
        holes();
    }
}

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

module connector(flip=false) {
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

connector_interior();