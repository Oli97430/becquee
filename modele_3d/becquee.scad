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
//  Pièces (variable piece) — toutes ≤ 235 mm :
//    socle, corps, facade, toit, perchoir, cale, support_poteau
//    améliorations (s'ajoutent sans rien réimprimer) :
//      fond            écran derrière le perchoir : plus de contre-jour
//      visiere         auvent au-dessus de la vitre : pas de gouttes devant l'objectif
//      grille          plancher surélevé à fentes : graines au sec
//      perchoir_regle  crochets x2 : perchoir à 40, 60, 80 ou 100 mm de la vitre
//      garde_poteau    cône sous la mangeoire, sur le poteau Ø25 : rats, chats, écureuils
//      bras_mc510 + bras_mc510_bride  bras serré sur le poteau Ø25 (4 vis M4 x 16 + écrous)
//                      pour une caméra Wi-Fi Mercusys MC510 : son support d'origine se visse
//                      sur la plaque (gabarit autocollant fourni avec la caméra, avant-trous Ø2,5)
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

piece = "assemblage"; // [assemblage, socle, corps, facade, toit, perchoir, cale, support_poteau, fond, visiere, grille, perchoir_regle, garde_poteau, bras_mc510, bras_mc510_bride]
ameliorations = true;  // montrer les améliorations dans l'assemblage

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

// ============================================================
//  Améliorations — repère de l'assemblage ; chaque pièce se pose
//  sur la mangeoire déjà imprimée, sans vis ni colle
// ============================================================
jeu = 0.3;
poteau_x = larg/2 - 3;          // poteaux du perchoir (socle) : 10 x 10, x ±97, y = y3 - 3
poteau_y = y3 - 3;
rebord_av = y3 + 5;             // face avant du rebord du plateau

// Fond : écran mat derrière le perchoir. L'oiseau se détache sur un fond uni au lieu du ciel
// (contre-jour : un Bulbul de Bourbon sombre pris pour une Perruche à collier) et les feuilles
// qui bougent derrière ne déclenchent plus d'enregistrement. Deux manchons coiffent les poteaux
// du perchoir ; une fente laisse passer la barre.
fond_h = 150;
fond_e = 3;
fond_y = rebord_av + jeu;       // dos de l'écran, juste devant le rebord
module fond() {
    manchon_y0 = poteau_y - 5 - jeu - 2;
    difference() {
        union() {
            translate([-(larg + 10)/2, fond_y, 0]) cube([larg + 10, fond_e, fond_h]);
            // nervures au dos (au-dessus du rebord, devant la barre du perchoir)
            for (x = [-50, 0, 50]) translate([x - 1.5, poteau_y + perch_d/2 + 0.5, 14]) cube([3, fond_y - poteau_y - perch_d/2 - 0.5 + 0.01, fond_h - 14]);
            for (z = [90, fond_h - 4]) translate([-(larg + 10)/2, poteau_y + perch_d/2 + 0.5, z]) cube([larg + 10, fond_y - poteau_y - perch_d/2 - 0.5 + 0.01, 4]);
            // manchons des poteaux
            for (s = [-1, 1]) translate([s*poteau_x - 7.3, manchon_y0, perch_z - 7]) cube([14.6, fond_y - manchon_y0 + 0.01, 17]);
        }
        for (s = [-1, 1]) translate([s*poteau_x, poteau_y, 0]) {
            translate([-5.3, -5.3, perch_z - 8]) cube([10.6, 10.6, perch_z + 8 + jeu - (perch_z - 8)]);   // poteau
            hull() {                                                   // passage de la barre, par dessous
                translate([0, 0, perch_z]) rotate([0, 90, 0]) cylinder(d = perch_d + 0.6, h = 20, center = true);
                translate([0, 0, perch_z - 10]) rotate([0, 90, 0]) cylinder(d = perch_d + 0.6, h = 20, center = true);
            }
        }
    }
}

// Visière : auvent au-dessus de la vitre, tenu par deux pattes qui pincent l'avant des flancs du
// corps et descendent jusqu'au plateau. Hors du champ de la caméra (elle vise vers le bas).
vis_z  = fen_z0 + fen_h + 9;    // au-dessus de l'encadrement gravé de la façade
vis_av = 28;                    // avancée
module visiere() {
    xe = larg/2;                // face extérieure des flancs
    xi2 = xi - 0.2;             // face intérieure des flancs (jeu)
    yb = -2.4;                  // derrière : entre la façade et l'avant des flancs
    for (s = [-1, 1]) mirror([s < 0 ? 1 : 0, 0, 0]) {
        translate([xe + 0.2, yb, 0]) cube([1.6, 2 - yb, vis_z + 3]);              // mâchoire extérieure
        translate([xe - 2.2, 0, 0]) cube([4, 2, vis_z + 3]);                       // pont devant le flanc (bas)
        translate([xi2 - 2.6, 0, 30]) cube([xe + 1.8 - (xi2 - 2.6), 2, vis_z + 3 - 30]);   // pont complet (haut)
        translate([xi2 - 2.6, yb, 30]) cube([2.6, -yb, vis_z + 3 - 30]);           // mâchoire intérieure
    }
    translate([-(xi2 - 2.6), yb, vis_z]) cube([2*(xi2 - 2.6), -yb + 0.01, 3]);    // traverse devant la façade
    translate([-(xe + 1.8), 0, vis_z]) cube([2*(xe + 1.8), 2, 3]);
    // auvent incliné de 10° vers l'avant, avec goutte d'eau au bord
    translate([0, 2, vis_z + 3]) rotate([-10, 0, 0]) {
        translate([-(xe + 1.8), 0, -2.4]) cube([2*(xe + 1.8), vis_av, 2.4]);
        translate([-(xe + 1.8), vis_av - 2, -6]) cube([2*(xe + 1.8), 2, 6]);
    }
}

// Grille : plancher à fentes posé sur le plateau, 3 mm au-dessus. L'eau file vers les trous
// de drainage du socle, les graines restent au sec. Rampe à l'arrière : les graines y montent.
grille_l2 = 198;                // entre les pattes de la visière et les crochets du perchoir
module grille() {
    gy0 = 3; gy1 = y3 - 1 - jeu;
    difference() {
        union() {
            translate([-grille_l2/2, gy0, 3]) cube([grille_l2, gy1 - gy0, 2]);
            for (x = [-88 : 16 : 88], y = [20 : 16 : 116]) translate([x, y, 0]) cylinder(d = 5, h = 3.01);
            translate([-grille_l2/2, gy0, 0]) rotate([90, 0, 90]) linear_extrude(grille_l2)
                polygon([[0, 0], [8, 3.01], [8, 5], [0, 0.6]]);
        }
        // fentes de 1,8 mm (le millet ne passe pas)
        for (y = [12 : 5 : gy1 - 4], x = [-84 : 28 : 84]) translate([x - 11, y - 0.9, -1]) cube([22, 1.8, 10]);
        // encoches des poteaux du perchoir
        for (s = [-1, 1]) translate([s*poteau_x - 5 - 1, poteau_y - 5 - 1, -1]) cube([12, 20, 10]);
    }
}

// Perchoir réglable : deux crochets posés sur les rebords latéraux du plateau. La barre du
// perchoir (la même) se pose dans l'encoche voulue : 40, 60, 80 ou 100 mm de la vitre au lieu de
// 120 : l'oiseau est plus grand à l'image, donc mieux reconnu. Une seule pièce, imprimée deux fois.
crans = [40, 60, 80, 100];
module perchoir_regle() {
    x0 = larg/2 + 1; x1 = larg/2 + 7.4;     // le rebord latéral va de x 102 à 105
    difference() {
        union() {
            translate([x0, 30, 12 + 0.2]) cube([x1 - x0, 80, perch_z + 10 - 12.2]);
            translate([larg/2 + 5.2, 30, 2]) cube([x1 - (larg/2 + 5.2), 80, 10.4]);      // patte extérieure
        }
        for (y = crans) hull() {
            translate([x0 - 1, y, perch_z]) rotate([0, 90, 0]) cylinder(d = perch_d + 0.6, h = 10);
            translate([x0 - 1, y - (perch_d + 0.6)/2, perch_z + 20]) cube([10, perch_d + 0.6, 1]);
        }
    }
}

// Garde : cône sur le poteau Ø25, sous la mangeoire (ouverture vers le bas) ; un rat ou un chat
// qui grimpe bute dessous. Bloqué par une vis M4 dans le collier.
garde_r = 115; garde_h = 105;
module garde_poteau() {
    r_trou = poteau_d/2 + 0.25; r_col = r_trou + 8; t = 3.4;
    difference() {
        rotate_extrude($fn = 120) polygon([[garde_r - t, 0], [garde_r, 0], [r_col, garde_h], [r_col, garde_h + 30],
                                           [r_trou, garde_h + 30], [r_trou, garde_h], [r_col - t, garde_h]]);
        translate([0, 0, garde_h + 18]) rotate([0, 90, 0]) cylinder(d = 3.4, h = 40);      // vis de blocage M4
    }
}

// Bras pour caméra Mercusys MC510 (orientable : elle vise seule la mangeoire). Collier en deux
// moitiés serrées sur le poteau par 4 vis M4 : il se pose sans démonter la mangeoire. Au bout,
// une plaque pleine où se visse le support d'origine de la caméra : coller le gabarit fourni
// dans la boîte, percer à Ø2,5 et visser les vis de la caméra (plaque imprimée pleine).
// Repère : axe du poteau = Z, bras vers +X ; imprimé debout tel quel, sans supports.
bras_l = 170;                   // de l'axe du poteau à la face de la plaque
bras_h = 80;                    // hauteur du collier, du bras et de la plaque
plaque_l = 100;                 // largeur de la plaque (le support MC510 y tient)
plaque_e = 8;
col_ri = poteau_d/2;            // 12,75 : poteau Ø25 + jeu
col_re = col_ri + 6;
oreille = col_re + 12;          // bout des oreilles de serrage
vis_y = col_re + 5.5;           // axe des vis M4, de chaque côté
module demi_collier(oreilles_ecrou = false) {
    difference() {
        union() {
            intersection() {
                cylinder(r = col_re, h = bras_h, $fn = 80);
                translate([0.5, -col_re, -1]) cube([col_re, 2*col_re, bras_h + 2]);
            }
            for (s = [-1, 1]) translate([0.5, s > 0 ? col_ri + 1 : -oreille, 0]) cube([7, oreille - col_ri - 1, bras_h]);
        }
        translate([0, 0, -1]) cylinder(r = col_ri, h = bras_h + 2, $fn = 80);
        for (s = [-1, 1], z = [16, bras_h - 16]) translate([-1, s*vis_y, z]) rotate([0, 90, 0]) {
            cylinder(d = 4.4, h = 20);
            if (oreilles_ecrou) translate([0, 0, 4.5]) cylinder(d = 8.1, h = 10, $fn = 6);   // écrou M4 (bride)
            else translate([0, 0, 6]) cylinder(d = 8, h = 10);                              // tête de vis
        }
    }
}
module bras_mc510() {
    demi_collier();
    difference() {
        union() {
            translate([col_re - 2, -8, 0]) cube([bras_l - (col_re - 2) + 0.01, 16, bras_h]);              // âme du bras
            translate([bras_l, -plaque_l/2, 0]) cube([plaque_e, plaque_l, bras_h]);                       // plaque
            for (s = [-1, 1]) hull() {                                                                    // goussets
                translate([bras_l - 0.01, s > 0 ? 7 : -32, 0]) cube([0.01, 25, bras_h]);
                translate([bras_l - 40, s > 0 ? 7 : -8, 0]) cube([0.01, 1, bras_h]);
            }
        }
        translate([bras_l + plaque_e - 0.6, 0, bras_h/2]) rotate([90, 0, 90]) linear_extrude(1)       // repère du centre
            square([30, 0.8], center = true);
    }
}
module bras_mc510_bride() { mirror([1, 0, 0]) demi_collier(oreilles_ecrou = true); }

// ------------------------------------------------------------
if      (piece == "socle")          socle();
else if (piece == "corps")          corps();
else if (piece == "facade")         facade();
else if (piece == "toit")           toit();
else if (piece == "perchoir")       translate([-(larg + 8)/2, 0, (perch_d - 1)/2]) perchoir();
else if (piece == "cale")           rotate([90, 0, 0]) cale();   // face arrière sur le plateau
else if (piece == "support_poteau") rotate([180, 0, 0]) support_poteau();
// améliorations, couchées pour l'impression (sans supports)
else if (piece == "fond")           translate([0, 0, fond_y + fond_e]) rotate([-90, 0, 0]) fond();   // face avant sur le plateau
else if (piece == "visiere")        translate([0, 0, 2.4]) rotate([90, 0, 0]) visiere();             // dos des pattes sur le plateau
else if (piece == "grille")         translate([0, 0, 5]) rotate([180, 0, 0]) grille();              // fentes sur le plateau, pieds en l'air
else if (piece == "perchoir_regle") translate([0, 0, larg/2 + 7.4]) rotate([0, 90, 0]) perchoir_regle();   // face extérieure sur le plateau
else if (piece == "garde_poteau")   garde_poteau();
else if (piece == "bras_mc510")     bras_mc510();
else if (piece == "bras_mc510_bride") bras_mc510_bride();
else {
    color("Peru") socle();
    color("Wheat") corps();
    color("SaddleBrown") translate([0, rainure_y, z_plancher]) rotate([90, 0, 0]) translate([0, 0, -fac_ep/2]) facade();
    color("Firebrick") translate([0, 0, h_corps]) toit();
    color("Sienna") translate([-(larg + 8)/2, ameliorations ? crans[2] : y3 - 3, perch_z]) perchoir();
    if (ameliorations) {
        color("DarkOliveGreen") fond();
        color("SteelBlue") visiere();
        color("Khaki") grille();
        color("Chocolate") { perchoir_regle(); mirror([1, 0, 0]) perchoir_regle(); }
        color("SlateGray") translate([0, (trous_poteau()[0][1] + trous_poteau()[2][1])/2, -200]) garde_poteau();
        %translate([0, (trous_poteau()[0][1] + trous_poteau()[2][1])/2, -260]) cylinder(d = 25, h = 210);   // poteau
    }
    color("Olive") translate([-80, y1, z_plancher + 3]) cale();
    color("DimGray") translate([0, 0, -9]) support_poteau();
    // fantôme : smartphone en paysage, incliné contre la cale
    %translate([-82, y1 + 3, z_plancher + 3]) rotate([-inclinaison, 0, 0]) cube([164, 9, 77]);
}
