// ============================================================
//  BECQUÉE — la mangeoire qui reconnaît ses visiteurs
//  Mangeoire-maison à caméra (esprit "mangeoire caméra" Denver)
//  - trémie à graines à l'arrière, rampe + arcades vers le plateau
//  - fenêtre de niveau des graines sur le flanc gauche
//  - compartiment caméra : smartphone (paysage) ou webcam USB,
//    derrière une façade vitrée ; cale d'inclinaison 10° pour viser
//    le perchoir
//  - toit à deux pentes tenu par 4 aimants : remplissage sans outil
//  - fixation murale (trous de serrure) ou sur poteau Ø25 mm
//
//  Pièces (variable piece) — toutes ≤ 256 mm (Centauri Carbon 2) :
//    socle, corps, facade, toit, perchoir, cale, support_poteau
//    assemblage : vue d'ensemble
//
//  Impression : PETG ou ASA (extérieur, UV), 0.2 mm, 4 périmètres,
//  sans supports.
//  Quincaillerie : 8 aimants néodyme Ø6 x 3 mm (collés), 4 vis à tôle
//  Ø3 x 12 (socle -> corps), plexiglas 2 mm 178 x 88 mm (façade),
//  bande transparente 1 mm 20 x 110 mm (niveau des graines) ;
//  option poteau : 4 vis Ø3 x 12 + 1 vis M4 x 12 de blocage.
//  Repère : X = largeur, Y+ = avant (vers le perchoir), Z = haut.
// ============================================================

piece = "assemblage"; // [assemblage, socle, corps, facade, toit, perchoir, cale, support_poteau]

/* [Dimensions générales] */
larg     = 200;   // largeur extérieure du corps
ep       = 3.2;   // épaisseur des parois
h_corps  = 150;   // hauteur du corps
tremie_p = 70;    // profondeur de la trémie
cam_p    = 32;    // profondeur du compartiment caméra
plateau_p = 120;  // profondeur du plateau devant le corps

/* [Compartiment caméra] */
z_plancher = 22;  // hauteur du plancher de l'appareil (les graines passent dessous)
fen_l   = 170;    // fenêtre : largeur
fen_z0  = 35;     // fenêtre : bas (au-dessus du socle)
fen_h   = 80;     // fenêtre : hauteur
passe_cable = 12; // trou pour le câble USB (flanc droit)
inclinaison = 10; // angle de la cale (degrés) : l'appareil vise vers le bas

/* [Perchoir] */
perch_z = 45;
perch_d = 8;      // tourillon bois Ø8 ou barre imprimée

/* [Aimants / poteau] */
aimant_d = 6.2;   // aimant Ø6 x 3
aimant_h = 3.2;
poteau_d = 25.5;  // manche à balai / tube PVC Ø25

$fn = 40;

// ------------------------------------------------------------
y0 = -(tremie_p + cam_p);    // dos du corps
y1 = y0 + tremie_p;          // face avant de la trémie
y2 = y1 + cam_p;             // avant du compartiment caméra (= 0)
y3 = y2 + plateau_p;         // bord avant du plateau
xi = larg/2 - ep;            // intérieur
rainure_y = y2 - 4;          // rainure de la façade
fac_ep = 2.6;
col_d = 12;                  // colonnes d'angle (vis du socle + aimants du toit)

function colonnes() = [[-xi + col_d/2, y0 + ep + col_d/2], [xi - col_d/2, y0 + ep + col_d/2],
                       [-xi + col_d/2, y1 + col_d/2],      [xi - col_d/2, y1 + col_d/2]];
// fixation sur poteau : 4 trous pilotes dans la rampe (pas de fuite de graines)
function trous_poteau() = [[-24, -50], [24, -50], [-24, -85], [24, -85]];

// ------------------------------------------------------------
module rrect(w, l, r) { offset(r) square([w - 2*r, l - 2*r], center = true); }
module ogive(l, h) {          // ouverture à sommet pointu (imprimable sans support)
    polygon([[-l/2, -1], [l/2, -1], [l/2, h - l/2], [0, h], [-l/2, h - l/2]]);
}

// ------------------------------------------------------------
//  Socle
// ------------------------------------------------------------
module socle() {
    difference() {
        union() {
            translate([0, (y0 + y3)/2, -4]) linear_extrude(4) rrect(larg + 10, y3 - y0 + 10, 6);
            // rebord du plateau (avant + côtés)
            translate([0, 0, -0.01]) linear_extrude(12) difference() {
                translate([0, (y2 - 6 + y3 + 5)/2]) square([larg + 10, y3 + 5 - (y2 - 6)], center = true);
                translate([0, (y2 - 6 + y3 - 1)/2]) square([larg + 10 - 6, y3 - 1 - (y2 - 6) + 0.01], center = true);
            }
            // rampe à graines (pente ~32°), dégagée autour des colonnes
            difference() {
                hull() {
                    translate([-xi + 0.3, y0 + ep + 0.3, 0]) cube([2*xi - 0.6, 0.1, 40]);
                    translate([-xi + 0.3, y1 - ep - 0.4, 0]) cube([2*xi - 0.6, 0.1, 0.5]);
                }
                for (p = colonnes()) translate([p[0], p[1], -1]) cylinder(d = col_d + 0.6, h = 50);
            }
            // poteaux du perchoir
            for (s = [-1, 1]) translate([s*(larg/2 - 3), y3 - 3, 0])
                difference() {
                    linear_extrude(perch_z + 8) rrect(10, 10, 2);
                    translate([0, 0, perch_z]) rotate([0, 90, 0]) cylinder(d = perch_d + 0.5, h = 20, center = true);
                }
        }
        // drainage du plateau
        for (x = [-80 : 16 : 80], y = [y2 + 12 : 16 : y3 - 10])
            translate([x, y, -5]) cylinder(d = 3.5, h = 10);
        // vis du corps (par dessous)
        for (p = colonnes()) translate([p[0], p[1], -5]) { cylinder(d = 3.4, h = 20); cylinder(d = 6.5, h = 3.5); }
        // trous pilotes du support de poteau
        for (p = trous_poteau()) translate([p[0], p[1], -5]) cylinder(d = 2.6, h = 10);
        // nom gravé sur le rebord avant
        translate([0, y3 + 5 - 0.6, 6]) rotate([90, 0, 180]) linear_extrude(2)
            text("BECQUÉE", size = 6, halign = "center", valign = "center", font = "Liberation Sans:style=Bold");
    }
}

// ------------------------------------------------------------
//  Corps (trémie + compartiment caméra)
// ------------------------------------------------------------
module corps() {
    yf = (y0 + y1)/2;   // milieu de la trémie (fenêtre de niveau)
    difference() {
        union() {
            linear_extrude(h_corps) difference() {
                translate([0, (y0 + y2)/2]) square([larg, y2 - y0], center = true);
                translate([0, (y0 + ep + y1 - ep)/2]) square([2*xi, y1 - y0 - 2*ep], center = true);  // trémie
                translate([0, (y1 + y2 + 1)/2]) square([2*xi, y2 - y1 + 1.01], center = true);         // compartiment
            }
            for (p = colonnes()) translate([p[0], p[1], 0]) cylinder(d = col_d, h = h_corps);
            // butées de la façade (fin de rainure)
            for (s = [-1, 1]) translate([s*(xi - 1), rainure_y, z_plancher/2]) cube([2, 6, z_plancher], center = true);
            // ergots de centrage du toit
            for (sx = [-1, 1], y = [y0 + 24, y2 - 12])
                translate([sx*(larg/2 - ep/2), y, h_corps - 0.01]) cylinder(d = 3, h = 4);
        }
        // trous pilotes (vis du socle) + logements d'aimants (toit)
        for (p = colonnes()) {
            translate([p[0], p[1], -1]) cylinder(d = 2.6, h = 30);
            translate([p[0], p[1], h_corps - aimant_h]) cylinder(d = aimant_d, h = aimant_h + 1);
        }
        // arcades de sortie des graines
        for (x = [-72 : 36 : 72]) translate([x, y1 - ep/2, 0]) rotate([90, 0, 0])
            linear_extrude(ep + 2, center = true) ogive(28, 18);
        // rainures de la façade
        for (s = [-1, 1]) translate([s*(larg/2 - ep/2 - 0.2), rainure_y, z_plancher + h_corps/2])
            cube([ep - 1.2 + 0.4, fac_ep + 0.5, h_corps], center = true);
        // fenêtre de niveau des graines (flanc gauche) + logement de la bande transparente
        translate([-larg/2, yf, 30]) rotate([90, 0, 90]) {
            linear_extrude(ep*3, center = true) translate([0, 0]) ogive(10, 96);
            translate([0, 0, -0.01]) linear_extrude(1.21) translate([-11, -6]) square([22, 112]);
        }
        // graduations à côté de la fenêtre
        for (z = [40 : 20 : 120]) translate([-larg/2 - 0.01, yf + 13, z]) cube([0.6, 6, 1.2], center = false);
        // passe-câble
        translate([larg/2, (y1 + y2)/2, h_corps - 30]) rotate([0, 90, 0]) cylinder(d = passe_cable, h = 20, center = true);
        // fixation murale : trous de serrure au dos
        for (x = [-50, 50]) translate([x, y0, 110]) rotate([90, 0, 0]) linear_extrude(20, center = true) {
            circle(d = 9);
            translate([0, 6]) square([4.5, 12], center = true);
            translate([0, 12]) circle(d = 4.5);
        }
        // aération du compartiment caméra (chaleur du téléphone)
        for (s = [-1, 1], z = [60 : 12 : 120]) translate([s*larg/2, (y1 + y2)/2 + 6, z]) cube([20, 10, 3], center = true);
    }
}

// ------------------------------------------------------------
//  Façade (imprimée à plat, face avant sur le plateau)
//  repère local : x = largeur, y = hauteur (0 = plancher), z = profondeur vers l'arrière
// ------------------------------------------------------------
fac_l = larg - 2*ep + 2*(ep - 1.2);
fac_h = h_corps - z_plancher;
plancher_p = rainure_y + fac_ep/2 - y1 - 0.5;     // jusqu'à la trémie
encoche_z = rainure_y + fac_ep/2 - (y1 + col_d) - 0.5;   // début des colonnes
module facade() {
    difference() {
        union() {
            translate([-fac_l/2, 0, 0]) cube([fac_l, fac_h, fac_ep]);
            // plancher de l'appareil, échancré autour des colonnes
            difference() {
                translate([-xi + 0.3, 0, 0]) cube([2*xi - 0.6, 3, plancher_p]);
                for (s = [-1, 1]) translate([s > 0 ? xi - col_d - 0.6 : -xi - 1, -1, encoche_z])
                    cube([col_d + 1.6, 5, 40]);
            }
        }
        // encadrement gravé
        translate([0, fen_z0 - z_plancher + fen_h/2, -1]) linear_extrude(1.6) difference() {
            square([fen_l + 16, fen_h + 16], center = true);
            square([fen_l + 12, fen_h + 12], center = true);
        }
        // fenêtre + logement du plexi
        translate([0, fen_z0 - z_plancher + fen_h/2, -1]) linear_extrude(10) rrect(fen_l, fen_h, 4);
        translate([0, fen_z0 - z_plancher + fen_h/2, fac_ep - 1.0]) linear_extrude(5) rrect(fen_l + 8, fen_h + 8, 4);
        // nom gravé (miroir : lu depuis l'avant)
        translate([0, fen_z0 - z_plancher + fen_h + 13, -1]) linear_extrude(1.7) mirror([1, 0])
            text("BECQUÉE", size = 9, halign = "center", valign = "center", font = "Liberation Sans:style=Bold");
        // encoche de préhension
        translate([0, fac_h, -1]) cylinder(d = 24, h = 10);
    }
}

// ------------------------------------------------------------
//  Toit (imprimé debout ; repère : bas = z 0) — tenu par 4 aimants
// ------------------------------------------------------------
toit_y0 = y0 - 14;
toit_y1 = y2 + 46;
toit_l  = larg + 18;
toit_e  = 3;
module toit() {
    yc = (toit_y0 + toit_y1)/2;
    demi = (toit_y1 - toit_y0)/2;
    difference() {
        union() {
            difference() {
                translate([-toit_l/2, 0, 0]) rotate([90, 0, 90]) linear_extrude(toit_l)
                    polygon([[toit_y0, 0], [toit_y1, 0], [yc, demi]]);
                translate([-toit_l/2 + toit_e, 0, -0.01]) rotate([90, 0, 90]) linear_extrude(toit_l - 2*toit_e)
                    polygon([[toit_y0 + toit_e*2.4, 0], [toit_y1 - toit_e*2.4, 0], [yc, demi - toit_e*1.41]]);
            }
            // plafond : repose sur les parois et les colonnes
            linear_extrude(2.4) difference() {
                translate([0, yc]) square([toit_l, toit_y1 - toit_y0], center = true);
                translate([0, (y0 + ep + col_d + 2 + y2 - ep - 1)/2])
                    square([2*xi - 2*col_d - 4, (y2 - ep - 1) - (y0 + ep + col_d + 2)], center = true);
            }
            // bossages des aimants
            for (p = colonnes()) translate([p[0], p[1], 0]) cylinder(d = col_d, h = aimant_h + 1.6);
        }
        for (sx = [-1, 1], y = [y0 + 24, y2 - 12])
            translate([sx*(larg/2 - ep/2), y, -1]) cylinder(d = 3.6, h = 6);
        for (p = colonnes()) translate([p[0], p[1], -1]) cylinder(d = aimant_d, h = aimant_h + 1);
        // tuiles gravées
        for (i = [1 : 5]) {
            d = i*demi/6;
            for (s = [-1, 1])
                translate([0, yc + s*(demi - d), d]) rotate([s*45, 0, 0]) cube([toit_l + 2, 1.2, 1.2], center = true);
        }
        // larmier : rainure sous le bord avant (l'eau goutte avant la façade)
        translate([0, toit_y1 - 6, -0.01]) cube([toit_l - 10, 1.6, 1.2], center = true);
    }
}

// ------------------------------------------------------------
module perchoir() {   // barre hexagonale couchée sur une face plate
    rotate([0, 90, 0]) rotate(30) cylinder(d = (perch_d - 1) / cos(30), h = larg + 8, $fn = 6);
}

// cale d'inclinaison : posée sur le plancher contre la trémie ; l'appareil s'y appuie
cale_h = 60;
module cale() {   // repère : x = longueur, y = épaisseur (0 = contre la trémie), z = hauteur
    rotate([90, 0, 90]) linear_extrude(160)
        polygon([[0, 0], [2, 0], [2 + cale_h * tan(inclinaison), cale_h], [0, cale_h]]);
}

module support_poteau() {   // repère : plaque en z 0..5 (contre le socle), tube vers le bas
    cy = (trous_poteau()[0][1] + trous_poteau()[2][1])/2;
    difference() {
        union() {
            translate([0, cy, 0]) linear_extrude(5) rrect(66, 52, 6);
            translate([0, cy, -45]) cylinder(d = poteau_d + 7, h = 45.01);
            for (a = [0 : 90 : 270]) translate([0, cy, 0]) rotate(a)
                rotate([90, 0, 0]) linear_extrude(3, center = true)
                    polygon([[poteau_d/2 + 3, 0], [24, 0], [poteau_d/2 + 3, -22]]);
        }
        translate([0, cy, -46]) cylinder(d = poteau_d, h = 46);   // fond fermé (5 mm) sous le socle
        // vis par dessous (fraisage côté tube)
        for (p = trous_poteau()) translate([p[0], p[1], -1]) { cylinder(d = 3.4, h = 10); translate([0, 0, 0.9]) cylinder(d1 = 7, d2 = 3.4, h = 2); }
        translate([0, cy, -25]) rotate([0, 90, 0]) cylinder(d = 3.4, h = 40);   // vis de blocage M4
    }
}

// ------------------------------------------------------------
if      (piece == "socle")          socle();
else if (piece == "corps")          corps();
else if (piece == "facade")         facade();
else if (piece == "toit")           toit();
else if (piece == "perchoir")       translate([-(larg + 8)/2, 0, (perch_d - 1)/2]) perchoir();
else if (piece == "cale")           rotate([90, 0, 0]) cale();   // face arrière sur le plateau
else if (piece == "support_poteau") rotate([180, 0, 0]) support_poteau();
else {
    color("Peru") socle();
    color("Wheat") corps();
    color("SaddleBrown") translate([0, rainure_y, z_plancher]) rotate([90, 0, 0]) translate([0, 0, -fac_ep/2]) facade();
    color("Firebrick") translate([0, 0, h_corps]) toit();
    color("Sienna") translate([-(larg + 8)/2, y3 - 3, perch_z]) perchoir();
    color("Olive") translate([-80, y1, z_plancher + 3]) cale();
    color("DimGray") translate([0, 0, -9]) support_poteau();
    // fantôme : smartphone en paysage, incliné contre la cale
    %translate([-82, y1 + 3, z_plancher + 3]) rotate([-inclinaison, 0, 0]) cube([164, 9, 77]);
}
