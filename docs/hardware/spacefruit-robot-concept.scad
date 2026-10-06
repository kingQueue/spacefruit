// SpaceFruit compact chassis. All dimensions are millimetres.
// Overall bumper envelope: 203.2 x 127 mm (8 x 5 in); arm remains separate.
// Open in OpenSCAD; F6 then export STL. Use -D 'show_assembly=false' for a
// body-only print mesh (hull + bumpers + camera pod; wheels omitted).

$fn = 64;
show_assembly = true;

body_width = 127;
body_length = 196.8; // shell length; 3.2 mm front/rear bumpers complete the 203.2 mm envelope
body_height = 72;
body_rounding = 22;
wheel_radius = 30;                 // Pololu 60 x 8 mm tires
wheel_width = 8;
wheel_well_clearance = 5;           // 10 mm more than tire diameter
wheel_well_depth = 14;              // 6 mm more than tire width
wheel_well_radius = wheel_radius + wheel_well_clearance;
wheel_recess = 1;
wheel_x = body_width/2 - wheel_width/2 - wheel_recess;
wheel_y = 58;
wheel_z = wheel_radius;
shell_top = wheel_z + body_height - 4;
camera_y = -65;
camera_z = shell_top - 8;
camera_tilt = -8;

module rounded_body(w, l, h, r) {
    minkowski() {
        cube([w - 2*r, l - 2*r, h - 2*r], center=true);
        sphere(r=r);
    }
}

module camera_pod() {
    // Raised, forward-tilted pod blends into the roof; only lens window rises.
    translate([0, camera_y, camera_z])
        rotate([camera_tilt, 0, 0])
            minkowski() {
                cube([48, 34, 5], center=true);
                sphere(r=5);
            }
}

module chassis() {
    difference() {
        union() {
            translate([0, 0, wheel_z + body_height/2 - 4])
                rounded_body(body_width, body_length, body_height, body_rounding);
            camera_pod();
            // Underside standoffs for a Pi 5 footprint, screw access from below.
            for (x = [-29, 29])
                for (y = [5.5, 54.5])
                    translate([x, y, 90.5]) cylinder(h=14, r=3.5, center=true);
        }
        // Hollow underside for electronics: ~2.5 mm walls and roof, open below.
        translate([0, 0, 60.5]) rounded_body(122, body_length - 5, 70, 19.5);
        // Pi mounting screws, 58 x 49 mm pattern; use M2.5 hardware.
        for (x = [-29, 29])
            for (y = [5.5, 54.5])
                translate([x, y, 88]) cylinder(h=18, r=1.35, center=true);
        // Wheel pockets: Ø70 x 14 mm, tires recessed 1 mm inside body sides.
        for (side = [-1, 1])
            for (fore_aft = [-1, 1])
                translate([side*(body_width/2 + 4 - wheel_well_depth/2), fore_aft*wheel_y, wheel_z])
                    rotate([0, 90, 0])
                        cylinder(h=wheel_well_depth, r=wheel_well_radius, center=true);
        // Camera opening follows pod angle; lens is recessed ~1 mm from pod face.
        translate([0, camera_y, camera_z])
            rotate([camera_tilt, 0, 0])
                translate([0, -18, 0])
                    rotate([90, 0, 0]) cylinder(h=20, r=8.5, center=true);
    }
}

module bumper_bar(y) {
    // Ends stop at the curved shell corners; bars do not wrap onto the sides.
    hull() {
        translate([-39, y, wheel_z + 17]) sphere(r=3.2);
        translate([ 39, y, wheel_z + 17]) sphere(r=3.2);
    }
}

module bumpers() {
    color([0.54,0.58,0.56]) {
        bumper_bar(-body_length/2);
        bumper_bar( body_length/2);
    }
}

module wheel(x, y) {
    color([0.19,0.23,0.27])
        translate([x, y, wheel_z]) rotate([0, 90, 0]) cylinder(h=wheel_width, r=wheel_radius, center=true);
    for (a = [0 : 30 : 330])
        color([0.26,0.32,0.36])
            translate([x, y + (wheel_radius-2)*sin(a), wheel_z + (wheel_radius-2)*cos(a)])
                rotate([a, 0, 0]) cube([wheel_width+0.3, 7, 4], center=true);
}

// Main shell and curved front/rear bumpers are fused where they overlap.
color([0.84,0.87,0.84]) union() {
    chassis();
    bumpers();
}

if (show_assembly) {
    // Preview wheels only; real 60 x 8 mm wheels are separate purchased parts.
    for (side = [-1, 1])
        for (fore_aft = [-1, 1])
            wheel(side*wheel_x, fore_aft*wheel_y);
    // Recessed front glass disk in the angled camera opening.
    color([0.57,0.72,0.74])
        translate([0, camera_y, camera_z]) rotate([camera_tilt, 0, 0])
            translate([0, -22.7, 0]) rotate([90, 0, 0]) cylinder(h=1.2, r=6, center=true);
}

// Preview-only ground plane is excluded from STL/OBJ exports.
%color([0.85,0.87,0.84], 0.45)
    translate([0, 0, -8]) cube([500, 500, 8], center=true);
