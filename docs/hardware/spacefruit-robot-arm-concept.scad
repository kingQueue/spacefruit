// SpaceFruit robot arm concept, modeled separately from the rover chassis.
// Millimetres; illustrative dimensions only, not a fabrication-ready design.
// The mounting plate represents the center roof interface on the robot.

$fn = 48;

module link_between(p1, p2, radius, material) {
    v = [p2[0]-p1[0], p2[1]-p1[1], p2[2]-p1[2]];
    len = norm(v);
    axis = [-v[1], v[0], 0];
    angle = acos(v[2] / len);
    color(material)
        translate(p1)
            rotate(a=angle, v=axis)
                cylinder(h=len, r=radius, center=false);
}

module joint(p, r=19) {
    color([0.26,0.36,0.31]) translate(p) sphere(r=r);
    color([0.82,0.65,0.44]) translate(p) sphere(r=r*0.42);
}

// Mount face is at Z=264 mm, matching the chassis roof in the companion file.
color([0.65,0.70,0.66])
    translate([0, 10, 268]) cube([86, 90, 8], center=true);
color([0.34,0.42,0.37])
    translate([0, 10, 288]) cylinder(h=40, r=38, center=true);

// Central rooftop base with a three-link arm reaching toward the front (-Y).
p0 = [0, 10, 308];
p1 = [0, -24, 373];
p2 = [0, -105, 333];
p3 = [0, -163, 243];
link_between(p0, p1, 23, [0.38,0.48,0.41]);
link_between(p1, p2, 18, [0.50,0.59,0.51]);
link_between(p2, p3, 12, [0.38,0.46,0.40]);
joint(p0, 25); joint(p1, 22); joint(p2, 17); joint(p3, 13);

// Simple two-finger end effector.
link_between(p3, [ 24, -194, 210], 5, [0.82,0.65,0.44]);
link_between(p3, [-24, -194, 210], 5, [0.82,0.65,0.44]);
link_between([ 24, -194, 210], [ 20, -204, 189], 4, [0.82,0.65,0.44]);
link_between([-24, -194, 210], [-20, -204, 189], 4, [0.82,0.65,0.44]);

// Preview ground plane; comment out before exporting a clean mesh.
%color([0.85,0.87,0.84], 0.45)
    translate([0, -70, -8]) cube([450, 500, 8], center=true);