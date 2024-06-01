// Exterior width of the main plastic connector body.
body_width = 38.5;
// Exterior height of the main plastic connector body.
body_height = 12.3;
// Exterior depth of the main plastic connector body.
body_depth = 13.3;
// Corner radius on the square side of the connector body.
body_corner_radius = 1.0;
body_thickness = 1.4;

flange_offset = 1;
flange_thickness = 1;

standoff_width = 1;
standoff_height = 0.5;
standoff_distance_from_edge = 10;

pin_hole_diameter = 3.30;
pin_spacing = 4;
pin_diameter = 1.20;
pin_4_to_5_spacing = 6.50;
pin_housing_corner_radius = 0.5;

outer_big_corner_radius = body_height/2;

standoff_distance_from_center = body_width/2 - standoff_distance_from_edge;

/* [Hidden] */
epsilon = 0.01;

$fn=100;

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
    linear_extrude(body_depth)
    difference() {
        outline_with_guides();
        offset(delta=-body_thickness) outline();
    }
    // Close off the back near the pins
    linear_extrude(body_thickness) outline();
    
    // Flange at the front of the connector
    translate([0,0,body_depth-flange_thickness+epsilon])
    linear_extrude(flange_thickness)
    difference() {
        offset(delta=flange_offset) outline();
        offset(delta=-body_thickness) outline();
    }
}

module connector_interior() {
    margin = pin_spacing - pin_hole_diameter;
    square_group_width = 3*pin_spacing + pin_hole_diameter + 2*margin;
    oblong_group_width = 2*pin_spacing + pin_hole_diameter + 2*margin;
    group_height = pin_hole_diameter + 2*margin;
    hole_radius = pin_hole_diameter/2;
    
    module pin_array(n) {
        for (i=[0:n-1])
            translate([hole_radius + margin + i*pin_spacing, 0, 0])
            circle(d=pin_hole_diameter);
    }
    
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

    module square_group() {
        difference() {
            rounded_square(square_group_width, group_height, pin_housing_corner_radius);
            pin_array(4);
        }
    }
    
    module round_group() {
        difference() {
            semi_oblong(oblong_group_width, group_height, pin_housing_corner_radius);
            pin_array(3);
        }
    }
    
    module outline() {
        square_group();
        translate([3*pin_spacing + pin_4_to_5_spacing, 0, 0])
        round_group();
    }
    
    linear_extrude(body_depth)
    outline();
}

module connector() {
    interior_width = 6*pin_spacing + pin_4_to_5_spacing + pin_diameter;
    connector_body();
    translate([(body_width-interior_width)/2,0,0]) connector_interior();
}

color("gray")
rotate([90, 0, 0])
connector();