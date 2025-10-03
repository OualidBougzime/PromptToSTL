// src/templates/advancedTemplates.ts

export interface TemplateCategory {
    name: string
    icon: string
    description: string
    templates: Template[]
}

export interface Template {
    id: string
    name: string
    description: string
    prompt: string
    tags: string[]
    difficulty: 'Débutant' | 'Intermédiaire' | 'Avancé'
    estimatedTime: string
    parameters?: TemplateParameter[]
}

export interface TemplateParameter {
    name: string
    description: string
    defaultValue: number | string
    type: 'number' | 'string' | 'boolean'
    min?: number
    max?: number
    unit?: string
}

export const ADVANCED_TEMPLATES: TemplateCategory[] = [
    {
        name: 'Mécanique',
        icon: '⚙️',
        description: 'Pièces mécaniques et engrenages',
        templates: [
            {
                id: 'gear-basic',
                name: 'Engrenage Simple',
                description: 'Engrenage droit avec paramètres ajustables',
                prompt: 'Create a gear with {teeth} teeth, outer radius {outerRadius}mm, inner radius {innerRadius}mm, thickness {thickness}mm, and center hole radius {holeRadius}mm',
                tags: ['engrenage', 'mécanique', 'rotation'],
                difficulty: 'Débutant',
                estimatedTime: '2 min',
                parameters: [
                    { name: 'teeth', description: 'Nombre de dents', defaultValue: 12, type: 'number', min: 6, max: 60 },
                    { name: 'outerRadius', description: 'Rayon extérieur', defaultValue: 15, type: 'number', min: 5, max: 50, unit: 'mm' },
                    { name: 'innerRadius', description: 'Rayon intérieur', defaultValue: 8, type: 'number', min: 3, max: 30, unit: 'mm' },
                    { name: 'thickness', description: 'Épaisseur', defaultValue: 4, type: 'number', min: 1, max: 20, unit: 'mm' },
                    { name: 'holeRadius', description: 'Rayon du trou central', defaultValue: 3, type: 'number', min: 0.5, max: 15, unit: 'mm' }
                ]
            },
            {
                id: 'gear-planetary',
                name: 'Système Planétaire',
                description: 'Engrenage planétaire complet avec solaire et couronne',
                prompt: 'Create a planetary gear system with sun gear {sunTeeth} teeth radius {sunRadius}mm, {planetCount} planet gears with {planetTeeth} teeth radius {planetRadius}mm, and ring gear {ringTeeth} teeth inner radius {ringRadius}mm, thickness {thickness}mm',
                tags: ['engrenage', 'planétaire', 'complexe'],
                difficulty: 'Avancé',
                estimatedTime: '5 min',
                parameters: [
                    { name: 'sunTeeth', description: 'Dents engrenage solaire', defaultValue: 8, type: 'number', min: 6, max: 20 },
                    { name: 'sunRadius', description: 'Rayon solaire', defaultValue: 8, type: 'number', min: 4, max: 15, unit: 'mm' },
                    { name: 'planetCount', description: 'Nombre de planètes', defaultValue: 3, type: 'number', min: 2, max: 6 },
                    { name: 'planetTeeth', description: 'Dents par planète', defaultValue: 12, type: 'number', min: 8, max: 25 },
                    { name: 'planetRadius', description: 'Rayon des planètes', defaultValue: 12, type: 'number', min: 6, max: 20, unit: 'mm' },
                    { name: 'ringTeeth', description: 'Dents couronne', defaultValue: 32, type: 'number', min: 20, max: 60 },
                    { name: 'ringRadius', description: 'Rayon couronne', defaultValue: 32, type: 'number', min: 20, max: 60, unit: 'mm' },
                    { name: 'thickness', description: 'Épaisseur', defaultValue: 6, type: 'number', min: 2, max: 15, unit: 'mm' }
                ]
            },
            {
                id: 'bearing-housing',
                name: 'Logement de Roulement',
                description: 'Boîtier pour roulement à billes avec trous de montage',
                prompt: 'Create a bearing housing for {bearingDiameter}mm bearing, outer diameter {outerDiameter}mm, height {height}mm, wall thickness {wallThickness}mm, with {boltHoles} mounting holes of {boltDiameter}mm diameter on {boltCircleDiameter}mm bolt circle',
                tags: ['roulement', 'logement', 'montage'],
                difficulty: 'Intermédiaire',
                estimatedTime: '3 min'
            },
            {
                id: 'pulley-timing',
                name: 'Poulie de Distribution',
                description: 'Poulie crantée pour courroie de distribution',
                prompt: 'Create a timing pulley with {teeth} teeth, {pitch}mm pitch, outer diameter {outerDiameter}mm, inner diameter {innerDiameter}mm, width {width}mm, and hub diameter {hubDiameter}mm with keyway',
                tags: ['poulie', 'courroie', 'transmission'],
                difficulty: 'Avancé',
                estimatedTime: '4 min'
            }
        ]
    },
    {
        name: 'Supports & Fixations',
        icon: '🔧',
        description: 'Équerres, supports et pièces de fixation',
        templates: [
            {
                id: 'l-bracket-basic',
                name: 'Équerre Simple',
                description: 'Équerre en L avec trous de montage',
                prompt: 'Create an L-bracket {width}mm x {height}mm, thickness {thickness}mm, with {holeCount} mounting holes of {holeDiameter}mm diameter, spaced {holeSpacing}mm apart',
                tags: ['équerre', 'support', 'montage'],
                difficulty: 'Débutant',
                estimatedTime: '2 min',
                parameters: [
                    { name: 'width', description: 'Largeur', defaultValue: 50, type: 'number', min: 20, max: 200, unit: 'mm' },
                    { name: 'height', description: 'Hauteur', defaultValue: 40, type: 'number', min: 20, max: 200, unit: 'mm' },
                    { name: 'thickness', description: 'Épaisseur', defaultValue: 4, type: 'number', min: 2, max: 10, unit: 'mm' },
                    { name: 'holeCount', description: 'Nombre de trous', defaultValue: 4, type: 'number', min: 2, max: 12 },
                    { name: 'holeDiameter', description: 'Diamètre des trous', defaultValue: 4, type: 'number', min: 2, max: 12, unit: 'mm' },
                    { name: 'holeSpacing', description: 'Espacement des trous', defaultValue: 15, type: 'number', min: 8, max: 50, unit: 'mm' }
                ]
            },
            {
                id: 'corner-bracket',
                name: 'Équerre d\'Angle',
                description: 'Équerre pour assemblage à 90° avec nervures',
                prompt: 'Create a corner bracket for {angle}° joint, {size}mm sides, thickness {thickness}mm, with {ribCount} reinforcement ribs and {holeCount} mounting holes',
                tags: ['angle', 'assemblage', 'nervures'],
                difficulty: 'Intermédiaire',
                estimatedTime: '3 min'
            },
            {
                id: 'universal-mount',
                name: 'Support Universel',
                description: 'Support réglable multi-positions',
                prompt: 'Create a universal mounting bracket with base {baseLength}mm x {baseWidth}mm, adjustable arm length {armLength}mm, {adjustmentSlots} adjustment slots, and universal joint',
                tags: ['réglable', 'universel', 'articulé'],
                difficulty: 'Avancé',
                estimatedTime: '5 min'
            }
        ]
    },
    {
        name: 'Boîtiers & Enclosures',
        icon: '📦',
        description: 'Boîtiers électroniques et enclosures',
        templates: [
            {
                id: 'electronics-box',
                name: 'Boîtier Électronique',
                description: 'Boîtier avec couvercle et ventilation',
                prompt: 'Create an electronics enclosure {width}mm x {height}mm x {depth}mm, wall thickness {wallThickness}mm, lid height {lidHeight}mm, with ventilation holes and {standoffCount} PCB standoffs',
                tags: ['électronique', 'boîtier', 'ventilation'],
                difficulty: 'Intermédiaire',
                estimatedTime: '4 min',
                parameters: [
                    { name: 'width', description: 'Largeur', defaultValue: 80, type: 'number', min: 40, max: 200, unit: 'mm' },
                    { name: 'height', description: 'Hauteur', defaultValue: 50, type: 'number', min: 20, max: 100, unit: 'mm' },
                    { name: 'depth', description: 'Profondeur', defaultValue: 60, type: 'number', min: 30, max: 150, unit: 'mm' },
                    { name: 'wallThickness', description: 'Épaisseur parois', defaultValue: 2.5, type: 'number', min: 1.5, max: 5, unit: 'mm' },
                    { name: 'lidHeight', description: 'Hauteur couvercle', defaultValue: 8, type: 'number', min: 5, max: 20, unit: 'mm' },
                    { name: 'standoffCount', description: 'Nombre de supports PCB', defaultValue: 4, type: 'number', min: 2, max: 8 }
                ]
            },
            {
                id: 'din-rail-case',
                name: 'Boîtier Rail DIN',
                description: 'Enclosure pour montage sur rail DIN',
                prompt: 'Create a DIN rail enclosure, {modules} modules wide, height {height}mm, depth {depth}mm, with DIN rail clips, terminal openings and cable entries',
                tags: ['DIN', 'rail', 'industriel'],
                difficulty: 'Avancé',
                estimatedTime: '6 min'
            },
            {
                id: 'weatherproof-box',
                name: 'Boîtier Étanche',
                description: 'Enclosure résistant aux intempéries avec joint',
                prompt: 'Create a weatherproof enclosure {width}mm x {height}mm x {depth}mm, IP65 rating, with gasket groove, cable glands for {cableCount} cables, and locking mechanism',
                tags: ['étanche', 'extérieur', 'IP65'],
                difficulty: 'Avancé',
                estimatedTime: '7 min'
            }
        ]
    },
    {
        name: 'Connecteurs & Raccords',
        icon: '🔌',
        description: 'Connecteurs, raccords et pièces de jonction',
        templates: [
            {
                id: 'pipe-connector',
                name: 'Raccord de Tuyau',
                description: 'Connecteur pour tuyaux avec filetage',
                prompt: 'Create a pipe connector for {pipeDiameter}mm pipes, total length {totalLength}mm, with {threadPitch}mm thread pitch, flange diameter {flangeDiameter}mm, and {sealGrooves} seal grooves',
                tags: ['tuyau', 'raccord', 'étanchéité'],
                difficulty: 'Intermédiaire',
                estimatedTime: '3 min'
            },
            {
                id: 'quick-connect',
                name: 'Raccord Rapide',
                description: 'Connecteur rapide push-to-connect',
                prompt: 'Create a quick-connect fitting for {tubeDiameter}mm tube, body diameter {bodyDiameter}mm, release collar diameter {collarDiameter}mm, with internal gripping ring and O-ring seals',
                tags: ['rapide', 'pneumatique', 'étanchéité'],
                difficulty: 'Avancé',
                estimatedTime: '5 min'
            },
            {
                id: 'cable-gland',
                name: 'Presse-étoupe',
                description: 'Presse-étoupe pour passage de câbles',
                prompt: 'Create a cable gland M{threadSize} thread, for cable diameter {cableDiameterMin}mm to {cableDiameterMax}mm, with compression nut, sealing ring and strain relief',
                tags: ['câble', 'étanchéité', 'métrique'],
                difficulty: 'Intermédiaire',
                estimatedTime: '4 min'
            }
        ]
    },
    {
        name: 'Outillage',
        icon: '🔨',
        description: 'Outils et accessoires d\'atelier',
        templates: [
            {
                id: 'custom-wrench',
                name: 'Clé Sur Mesure',
                description: 'Clé plate ou à fourche personnalisée',
                prompt: 'Create a custom wrench for {nutSize}mm nut, handle length {handleLength}mm, thickness {thickness}mm, with ergonomic grip and hanging hole',
                tags: ['clé', 'outil', 'personnalisé'],
                difficulty: 'Intermédiaire',
                estimatedTime: '3 min'
            },
            {
                id: 'drill-jig',
                name: 'Guide de Perçage',
                description: 'Gabarit pour perçage précis',
                prompt: 'Create a drilling jig for {holeSpacing}mm spacing, {holeCount} holes of {holeDiameter}mm diameter, base {baseLength}mm x {baseWidth}mm, with alignment features',
                tags: ['perçage', 'gabarit', 'précision'],
                difficulty: 'Intermédiaire',
                estimatedTime: '4 min'
            },
            {
                id: 'go-no-go-gauge',
                name: 'Calibre Passe/Ne-passe-pas',
                description: 'Calibre de contrôle dimensionnel',
                prompt: 'Create a go/no-go gauge for {dimension}mm ± {tolerance}mm, length {length}mm, with clear marking and handling area',
                tags: ['calibre', 'contrôle', 'qualité'],
                difficulty: 'Avancé',
                estimatedTime: '3 min'
            }
        ]
    },
    {
        name: 'Artistique & Déco',
        icon: '🎨',
        description: 'Objets décoratifs et artistiques',
        templates: [
            {
                id: 'parametric-vase',
                name: 'Vase Paramétrique',
                description: 'Vase avec forme paramétrable',
                prompt: 'Create a parametric vase {height}mm tall, base diameter {baseDiameter}mm, top diameter {topDiameter}mm, with {twistAngle}° twist, {wallThickness}mm wall thickness and decorative pattern',
                tags: ['vase', 'décoratif', 'paramétrique'],
                difficulty: 'Intermédiaire',
                estimatedTime: '3 min',
                parameters: [
                    { name: 'height', description: 'Hauteur', defaultValue: 150, type: 'number', min: 50, max: 300, unit: 'mm' },
                    { name: 'baseDiameter', description: 'Diamètre base', defaultValue: 60, type: 'number', min: 30, max: 150, unit: 'mm' },
                    { name: 'topDiameter', description: 'Diamètre sommet', defaultValue: 80, type: 'number', min: 20, max: 200, unit: 'mm' },
                    { name: 'twistAngle', description: 'Angle de torsion', defaultValue: 45, type: 'number', min: 0, max: 180, unit: '°' },
                    { name: 'wallThickness', description: 'Épaisseur paroi', defaultValue: 2, type: 'number', min: 1, max: 5, unit: 'mm' }
                ]
            },
            {
                id: 'geometric-sculpture',
                name: 'Sculpture Géométrique',
                description: 'Sculpture abstraite basée sur des formes géométriques',
                prompt: 'Create an abstract geometric sculpture with {elementCount} elements, overall size {size}mm, based on {geometryType} geometry with {complexityLevel} complexity level',
                tags: ['sculpture', 'abstrait', 'géométrie'],
                difficulty: 'Avancé',
                estimatedTime: '5 min'
            },
            {
                id: 'voronoi-lamp',
                name: 'Abat-jour Voronoi',
                description: 'Abat-jour avec motif voronoi',
                prompt: 'Create a lamp shade {diameter}mm diameter, {height}mm height, with Voronoi pattern, {cellCount} cells, wall thickness {wallThickness}mm, and mounting ring',
                tags: ['luminaire', 'voronoi', 'motif'],
                difficulty: 'Avancé',
                estimatedTime: '6 min'
            }
        ]
    },
    {
        name: 'Automobile',
        icon: '🚗',
        description: 'Pièces et accessoires automobiles',
        templates: [
            {
                id: 'engine-mount',
                name: 'Support Moteur',
                description: 'Support moteur vibration-damped avec inserts caoutchouc',
                prompt: 'Create an engine mount bracket 120mm x 80mm x 15mm thick, with 4 M10 mounting holes spaced 100mm x 60mm, central cavity 50mm diameter for rubber insert, reinforcement ribs 8mm thick',
                tags: ['moteur', 'support', 'vibration'],
                difficulty: 'Intermédiaire',
                estimatedTime: '3 min',
                parameters: [
                    { name: 'length', description: 'Longueur', defaultValue: 120, type: 'number', min: 80, max: 200, unit: 'mm' },
                    { name: 'width', description: 'Largeur', defaultValue: 80, type: 'number', min: 60, max: 150, unit: 'mm' },
                    { name: 'thickness', description: 'Épaisseur', defaultValue: 15, type: 'number', min: 10, max: 30, unit: 'mm' },
                    { name: 'holeCount', description: 'Nombre de trous', defaultValue: 4, type: 'number', min: 2, max: 8 }
                ]
            },
            {
                id: 'oil-pan',
                name: 'Carter d\'Huile',
                description: 'Carter avec bossages de vidange et capteur',
                prompt: 'Create an oil pan 300mm long, 200mm wide, 80mm depth, wall thickness 4mm, drain plug boss 20mm diameter, oil level sensor boss 15mm diameter, with sealing flange 8mm wide',
                tags: ['carter', 'huile', 'étanche'],
                difficulty: 'Avancé',
                estimatedTime: '5 min'
            },
            {
                id: 'intake-manifold',
                name: 'Collecteur d\'Admission',
                description: 'Collecteur 4 cylindres avec plénum',
                prompt: 'Create an intake manifold with plenum chamber 150mm x 100mm x 80mm, 4 runners 40mm diameter, 180mm length, evenly spaced 80mm apart, throttle body flange 70mm diameter, with smooth internal radius transitions',
                tags: ['admission', 'collecteur', 'performance'],
                difficulty: 'Avancé',
                estimatedTime: '6 min'
            },
            {
                id: 'valve-cover',
                name: 'Cache Culbuteurs',
                description: 'Couvre-culasse avec joints et bossages',
                prompt: 'Create a valve cover 400mm x 150mm x 60mm height, wall thickness 5mm, sealing groove 6mm wide 4mm deep around perimeter, oil filler neck 50mm diameter, 4 bolt bosses M8 with integrated washers',
                tags: ['culasse', 'couvercle', 'joint'],
                difficulty: 'Intermédiaire',
                estimatedTime: '4 min'
            },
            {
                id: 'alternator-bracket',
                name: 'Support Alternateur',
                description: 'Équerre réglable pour alternateur',
                prompt: 'Create an alternator bracket with L-shape, vertical arm 150mm height, horizontal arm 120mm length, thickness 10mm, adjustment slot 80mm long 12mm wide, 3 M10 mounting holes, reinforcement rib at corner',
                tags: ['alternateur', 'réglable', 'tension'],
                difficulty: 'Intermédiaire',
                estimatedTime: '3 min'
            },
            {
                id: 'oil-cooler',
                name: 'Refroidisseur d\'Huile',
                description: 'Corps de refroidisseur avec canaux internes',
                prompt: 'Create an oil cooler housing 200mm x 100mm x 40mm, 10 internal cooling fins 2mm thick spaced 8mm apart, inlet port 20mm diameter, outlet port 20mm diameter on opposite side, mounting tabs with M8 holes',
                tags: ['refroidissement', 'huile', 'canaux'],
                difficulty: 'Avancé',
                estimatedTime: '5 min'
            },
            {
                id: 'air-filter-box',
                name: 'Boîtier Filtre à Air',
                description: 'Airbox custom avec tubulure',
                prompt: 'Create an air filter housing box 250mm x 200mm x 150mm, wall thickness 3mm, circular filter seat 150mm diameter, intake tube 75mm diameter extending 100mm, drain holes 5mm diameter at bottom, lid with 6 snap clips',
                tags: ['filtre', 'admission', 'airbox'],
                difficulty: 'Intermédiaire',
                estimatedTime: '4 min'
            },
            {
                id: 'turbo-spacer',
                name: 'Entretoise de Turbo',
                description: 'Spacer thermique turbo-collecteur',
                prompt: 'Create a turbo spacer gasket 180mm x 120mm, thickness 10mm, 4 exhaust ports 45mm diameter positioned in rectangle 140mm x 80mm, 6 M10 bolt holes around perimeter, with thermal barrier grooves',
                tags: ['turbo', 'thermique', 'joint'],
                difficulty: 'Avancé',
                estimatedTime: '4 min'
            },
            {
                id: 'throttle-body-adapter',
                name: 'Adaptateur de Papillon',
                description: 'Adaptateur entre différents diamètres de papillon',
                prompt: 'Create a throttle body adapter flange from 70mm diameter to 80mm diameter, total length 50mm, tapered transition, mounting holes 4x M6 on 85mm bolt circle at each end, wall thickness 4mm',
                tags: ['papillon', 'adaptateur', 'admission'],
                difficulty: 'Débutant',
                estimatedTime: '2 min'
            },
            {
                id: 'timing-cover',
                name: 'Cache Distribution',
                description: 'Protection courroie de distribution',
                prompt: 'Create a timing belt cover 250mm x 180mm curved surface following 150mm radius, wall thickness 3mm, inspection window 80mm x 60mm with mounting tabs, 8 M6 mounting holes, cable routing cutouts',
                tags: ['distribution', 'protection', 'courroie'],
                difficulty: 'Avancé',
                estimatedTime: '5 min'
            },
            {
                id: 'fuel-rail',
                name: 'Rampe d\'Injection',
                description: 'Rampe commune pour injecteurs',
                prompt: 'Create a fuel rail 400mm long, main tube 20mm outer diameter 16mm inner diameter, 4 injector ports 14mm diameter spaced 100mm apart at 45° angle, fuel inlet M12 thread at end, pressure sensor port M10',
                tags: ['injection', 'carburant', 'rampe'],
                difficulty: 'Avancé',
                estimatedTime: '5 min'
            },
            {
                id: 'bell-housing-adapter',
                name: 'Adaptateur Cloche',
                description: 'Adaptateur moteur-boîte de vitesses',
                prompt: 'Create a bellhousing adapter plate 300mm diameter, thickness 15mm, central pilot hole 100mm diameter, 8 M10 bolt holes on 280mm bolt circle, 4 M12 mounting holes on opposite side 250mm bolt circle',
                tags: ['transmission', 'adaptateur', 'cloche'],
                difficulty: 'Avancé',
                estimatedTime: '4 min'
            }
        ]
    },
    {
        name: 'Biomédical',
        icon: '🏥',
        description: 'Dispositifs médicaux et implants',
        templates: [
            {
                id: 'drug-capsule',
                name: 'Capsule de Délivrance',
                description: 'Capsule médicale avec canaux micro-release',
                prompt: 'Create a drug delivery capsule with cylindrical body 20mm long, 8mm diameter, hemispherical caps at both ends, internal cavity 18mm x 6mm, wall thickness 1mm, with 12 micro-release channels 0.5mm diameter distributed around the circumference, and threaded assembly interface',
                tags: ['médical', 'capsule', 'drug-delivery'],
                difficulty: 'Avancé',
                estimatedTime: '5 min'
            },
            {
                id: 'vascular-stent',
                name: 'Stent Vasculaire',
                description: 'Stent expandable avec motif zigzag',
                prompt: 'Create a vascular stent with zigzag pattern, 25mm length, 8mm expanded diameter, 3mm collapsed diameter, strut thickness 0.3mm, 8 circumferential rings connected by 3 longitudinal bridges, radial expansion slots, and smooth flared ends',
                tags: ['stent', 'vasculaire', 'expandable'],
                difficulty: 'Avancé',
                estimatedTime: '6 min'
            },
            {
                id: 'bone-scaffold',
                name: 'Scaffold Osseux',
                description: 'Structure poreuse pour régénération osseuse',
                prompt: 'Create a bone scaffold with gyroid lattice structure, 40mm diameter, 30mm height, unit cell 5mm, strut thickness 0.8mm, 65% porosity for bone ingrowth, interconnected pores 2-4mm, suitable for titanium 3D printing',
                tags: ['scaffold', 'os', 'lattice'],
                difficulty: 'Avancé',
                estimatedTime: '7 min'
            }
        ]
    },
    {
        name: 'Soft Robotics',
        icon: '🤖',
        description: 'Robots souples et actuateurs pneumatiques',
        templates: [
            {
                id: 'pneumatic-actuator',
                name: 'Actuateur Pneumatique',
                description: 'Actuateur souple avec chambres expansibles',
                prompt: 'Create a pneumatic soft actuator with rectangular body 60mm x 15mm x 10mm, 6 expandable chambers 8mm x 8mm spaced 10mm apart, connecting walls 1.5mm thick, pneumatic input port 3mm diameter, flexible bellows structure allowing 30° bending',
                tags: ['actuateur', 'pneumatique', 'soft'],
                difficulty: 'Intermédiaire',
                estimatedTime: '4 min'
            },
            {
                id: 'soft-gripper',
                name: 'Pince Souple',
                description: 'Préhenseur adaptatif avec doigts flexibles',
                prompt: 'Create a soft gripper with 3 flexible fingers 80mm long, 20mm wide, inflatable chambers for gripping, compliant structure, mounting base 40mm diameter, pneumatic connections',
                tags: ['gripper', 'soft', 'préhension'],
                difficulty: 'Avancé',
                estimatedTime: '5 min'
            }
        ]
    },
    {
        name: 'Metamaterials',
        icon: '🔬',
        description: 'Structures à propriétés mécaniques avancées',
        templates: [
            {
                id: 'auxetic-structure',
                name: 'Structure Auxétique',
                description: 'Matériau avec ratio de Poisson négatif',
                prompt: 'Create an auxetic honeycomb structure panel 100mm x 100mm x 10mm, re-entrant hexagonal cells 8mm width, strut thickness 1.5mm, creating negative Poisson ratio, with mounting holes 4mm diameter at corners',
                tags: ['auxetic', 'metamaterial', 'honeycomb'],
                difficulty: 'Avancé',
                estimatedTime: '6 min'
            },
            {
                id: 'gyroid-lattice',
                name: 'Lattice Gyroïde',
                description: 'Structure lattice triply periodic minimal surface',
                prompt: 'Create a gyroid lattice structure cube 50mm size, unit cell 5mm, surface thickness 0.8mm, triply periodic minimal surface geometry, 70% porosity, smooth transitions between cells',
                tags: ['gyroid', 'lattice', 'TPMS'],
                difficulty: 'Avancé',
                estimatedTime: '7 min'
            }
        ]
    },
    {
        name: 'Dispositifs Biomédicaux',
        icon: '🩺',
        description: 'Implants, capsules et dispositifs médicaux',
        templates: [
            {
                id: 'drug-delivery-capsule',
                name: 'Capsule de Délivrance',
                description: 'Capsule médicale avec hémisphères et canaux micro-release',
                prompt: 'Create a drug delivery capsule with cylindrical body 20mm long, 8mm diameter, hemispherical caps at both ends, internal cavity 18mm x 6mm, wall thickness 1mm, with 12 micro-release channels 0.5mm diameter distributed around the circumference, and threaded assembly interface',
                tags: ['médical', 'capsule', 'drug-delivery'],
                difficulty: 'Avancé',
                estimatedTime: '5 min'
            },
            {
                id: 'subcutaneous-implant',
                name: 'Implant Sous-cutané',
                description: 'Réservoir ellipsoïdal avec membrane de diffusion',
                prompt: 'Create a subcutaneous implant drug reservoir with ellipsoidal shape 30mm x 15mm x 10mm, smooth rounded edges radius 2mm, central drug chamber with 2mm wall thickness, diffusion membrane area with 0.3mm thickness, and surgical insertion tab 5mm x 3mm with anchor holes',
                tags: ['implant', 'ellipsoïde', 'réservoir'],
                difficulty: 'Avancé',
                estimatedTime: '6 min'
            },
            {
                id: 'zigzag-stent',
                name: 'Stent Zigzag',
                description: 'Stent vasculaire avec motif zigzag expandable',
                prompt: 'Create a vascular stent with zigzag pattern, 25mm length, 8mm expanded diameter, 3mm collapsed diameter, strut thickness 0.3mm, 8 circumferential rings connected by 3 longitudinal bridges, radial expansion slots, and smooth flared ends for vessel integration',
                tags: ['stent', 'vasculaire', 'zigzag'],
                difficulty: 'Avancé',
                estimatedTime: '6 min'
            },
            {
                id: 'braided-stent',
                name: 'Stent Tressé',
                description: 'Stent auto-expandable avec fils tressés',
                prompt: 'Create a self-expanding mesh stent with braided wire pattern, 40mm length, 10mm diameter, diamond cell structure 3mm x 4mm, wire diameter 0.2mm, 16 wires braided at 45° angle, with radiopaque markers at ends',
                tags: ['stent', 'tressé', 'auto-expandable'],
                difficulty: 'Avancé',
                estimatedTime: '7 min'
            }
        ]
    },
    {
        name: 'Robotique Souple',
        icon: '🤖',
        description: 'Actuateurs souples et robots bio-inspirés',
        templates: [
            {
                id: 'pneumatic-soft-actuator',
                name: 'Actuateur Pneumatique',
                description: 'Actuateur souple avec chambres expansibles',
                prompt: 'Create a pneumatic soft actuator with rectangular body 60mm x 15mm x 10mm, 6 expandable chambers 8mm x 8mm spaced 10mm apart, connecting walls 1.5mm thick, pneumatic input port 3mm diameter, flexible bellows structure with 0.8mm wall thickness allowing 30° bending',
                tags: ['actuateur', 'pneumatique', 'souple'],
                difficulty: 'Intermédiaire',
                estimatedTime: '4 min'
            },
            {
                id: 'mckibben-muscle',
                name: 'Muscle Artificiel McKibben',
                description: 'Actuateur musculaire avec manchon tressé',
                prompt: 'Create a McKibben artificial muscle actuator with braided mesh sleeve 100mm long, 20mm diameter, internal bladder cavity, helical fiber pattern at 30° angle, 45 braided filaments 0.5mm thick, end caps with threaded connections M8, allowing 25% contraction',
                tags: ['muscle', 'McKibben', 'tressé'],
                difficulty: 'Avancé',
                estimatedTime: '6 min'
            },
            {
                id: 'caterpillar-robot',
                name: 'Robot Chenille',
                description: 'Segment de robot bio-inspiré avec ondulations',
                prompt: 'Create a caterpillar-inspired soft robot segment 80mm long, 25mm wide, 15mm height, with 4 undulating chambers creating wave motion, anchor protrusions 3mm high spaced 15mm apart, flexible silicone-like structure with graduated stiffness, connection ports for adjacent segments',
                tags: ['robot', 'bio-inspiré', 'chenille'],
                difficulty: 'Avancé',
                estimatedTime: '5 min'
            },
            {
                id: 'earthworm-robot',
                name: 'Robot Ver de Terre',
                description: 'Robot péristaltique segmenté',
                prompt: 'Create an earthworm-inspired peristaltic robot with 5 annular segments 30mm diameter, 20mm length each, radial expansion chambers, circumferential gripping ridges 2mm height, tapered connecting sections, and integrated sensing bumps',
                tags: ['robot', 'péristaltique', 'segmenté'],
                difficulty: 'Avancé',
                estimatedTime: '6 min'
            }
        ]
    },
    {
        name: 'Dispositifs Orthopédiques',
        icon: '🦴',
        description: 'Attelles, prothèses et supports médicaux',
        templates: [
            {
                id: 'wrist-splint',
                name: 'Attelle de Poignet',
                description: 'Attelle adaptative avec ventilation',
                prompt: 'Create an adaptive wrist splint with anatomical curve following 180mm length, adjustable width 60-80mm, ventilated mesh pattern with 5mm hexagonal holes, 3 adjustable straps with ratchet mechanism, ergonomic palm rest with 15° dorsiflexion angle, padding channels 2mm deep',
                tags: ['attelle', 'poignet', 'ventilée'],
                difficulty: 'Intermédiaire',
                estimatedTime: '4 min'
            },
            {
                id: 'finger-splint',
                name: 'Attelle de Doigt',
                description: 'Attelle articulée pour doigt avec charnières',
                prompt: 'Create a finger splint with articulated joints for PIP and DIP, 70mm total length, 18mm width, tubular structure 3mm wall thickness, ventilation slots 2mm x 15mm, integrated hinge allowing 0-90° flexion, velcro attachment points, and malleable aluminum core for custom bending',
                tags: ['doigt', 'articulé', 'charnière'],
                difficulty: 'Avancé',
                estimatedTime: '5 min'
            },
            {
                id: 'prosthetic-socket',
                name: 'Socket Prothétique',
                description: 'Socket modulaire pour membre avec renforts carbone',
                prompt: 'Create a modular limb prosthetic socket with conical shape 300mm height, proximal diameter 120mm, distal diameter 80mm, inner silicone liner interface with 8 pressure relief windows 30mm x 40mm, adjustable vacuum valve port, carbon fiber reinforcement ribs 5mm wide, and quick-release mechanism',
                tags: ['prothèse', 'socket', 'carbone'],
                difficulty: 'Avancé',
                estimatedTime: '7 min'
            }
        ]
    },
    {
        name: 'Structures Avancées',
        icon: '🔬',
        description: 'Lattices, métamatériaux et structures poreuses',
        templates: [
            {
                id: 'lattice-cube',
                name: 'Lattice Cubique',
                description: 'Structure en treillis pour ingénierie tissulaire',
                prompt: 'Create a cubic lattice structure 50mm size, unit cell 5mm, strut thickness 0.8mm, 70% porosity for bone ingrowth',
                tags: ['lattice', 'treillis', 'poreux'],
                difficulty: 'Intermédiaire',
                estimatedTime: '3 min'
            },
            {
                id: 'bcc-lattice',
                name: 'Lattice BCC',
                description: 'Structure cubique centrée',
                prompt: 'Create a BCC lattice structure 40mm size, unit cell 4mm, strut thickness 0.6mm',
                tags: ['lattice', 'BCC', 'centré'],
                difficulty: 'Avancé',
                estimatedTime: '5 min'
            },
            {
                id: 'fcc-lattice',
                name: 'Lattice FCC',
                description: 'Structure cubique faces centrées',
                prompt: 'Create a FCC lattice structure 45mm size, unit cell 5mm, strut thickness 0.7mm',
                tags: ['lattice', 'FCC', 'faces'],
                difficulty: 'Avancé',
                estimatedTime: '5 min'
            },
            {
                id: 'octet-lattice',
                name: 'Lattice Octet',
                description: 'Treillis tétraèdres-octaèdres',
                prompt: 'Create an octet truss lattice 50mm size, unit cell 5mm, strut thickness 0.8mm',
                tags: ['lattice', 'octet', 'truss'],
                difficulty: 'Avancé',
                estimatedTime: '6 min'
            },
            {
                id: 'kelvin-lattice',
                name: 'Lattice Kelvin',
                description: 'Mousse de Kelvin (14 faces)',
                prompt: 'Create a Kelvin foam lattice 50mm size, unit cell 6mm, strut thickness 0.9mm',
                tags: ['lattice', 'Kelvin', 'mousse'],
                difficulty: 'Avancé',
                estimatedTime: '6 min'
            },
            {
                id: 'diamond-lattice',
                name: 'Lattice Diamant',
                description: 'Structure cubique diamant',
                prompt: 'Create a diamond cubic lattice 45mm size, unit cell 5mm, strut thickness 0.7mm',
                tags: ['lattice', 'diamant', 'cubique'],
                difficulty: 'Avancé',
                estimatedTime: '5 min'
            },
            {
                id: 'voronoi-scaffold',
                name: 'Scaffold Voronoi',
                description: 'Structure poreuse avec cellules aléatoires',
                prompt: 'Create a Voronoi-based porous scaffold 40mm diameter, 30mm height, random seed pattern with 200 cells, strut thickness 1-2mm gradient, 60% porosity, interconnected pores 2-5mm diameter for tissue engineering, with solid mounting plate 3mm thick at base',
                tags: ['Voronoi', 'scaffold', 'aléatoire'],
                difficulty: 'Avancé',
                estimatedTime: '6 min'
            },
            {
                id: 'auxetic-honeycomb',
                name: 'Nid d\'Abeille Auxétique',
                description: 'Structure avec ratio de Poisson négatif',
                prompt: 'Create an auxetic honeycomb structure panel 100mm x 100mm x 10mm, re-entrant hexagonal cells 8mm width, strut thickness 1.5mm, creating negative Poisson\'s ratio, with mounting holes 4mm diameter at corners',
                tags: ['auxetic', 'honeycomb', 'métamatériau'],
                difficulty: 'Avancé',
                estimatedTime: '6 min'
            },
            {
                id: 'chiral-metamaterial',
                name: 'Métamatériau Chiral',
                description: 'Structure avec nœuds rotatifs et ligaments courbés',
                prompt: 'Create a chiral mechanical metamaterial tile 60mm x 60mm, with 9 rotating nodes connected by curved ligaments 2mm thick, node diameter 8mm, designed for programmable stiffness and shape morphing',
                tags: ['chiral', 'métamatériau', 'programmable'],
                difficulty: 'Avancé',
                estimatedTime: '7 min'
            }
        ]
    },
    {
        name: 'Microstructures',
        icon: '🧬',
        description: 'Puces microfluidiques et scaffolds cellulaires',
        templates: [
            {
                id: 'microfluidic-chip',
                name: 'Puce Microfluidique',
                description: 'Puce avec canaux serpentins pour mélange',
                prompt: 'Create a microfluidic mixing chip 75mm x 50mm x 5mm, with serpentine mixing channel 0.3mm wide, 0.2mm deep, 8 mixing loops creating chaotic advection, inlet/outlet ports 2mm diameter, observation window 20mm x 20mm with 1mm depth, and channel intersection angles optimized for laminar flow',
                tags: ['microfluidique', 'mélange', 'canaux'],
                difficulty: 'Avancé',
                estimatedTime: '6 min'
            },
            {
                id: 'cell-culture-scaffold',
                name: 'Scaffold Culture Cellulaire',
                description: 'Structure 3D pour culture de cellules',
                prompt: 'Create a 3D cell culture scaffold with interconnected pore network, 20mm diameter, 5mm thickness, pore size 300-500 microns, strut diameter 200 microns, octahedral unit cell structure, surface area to volume ratio 15 mm⁻¹, with nutrient diffusion channels',
                tags: ['cellules', 'culture', 'octaédral'],
                difficulty: 'Avancé',
                estimatedTime: '7 min'
            }
        ]
    },
    {
        name: 'Mécanismes Compliants',
        icon: '⚙️',
        description: 'Mécanismes flexibles et bistables',
        templates: [
            {
                id: 'compliant-gripper',
                name: 'Pince Compliante',
                description: 'Pince parallèle avec charnières vivantes',
                prompt: 'Create a compliant parallel jaw gripper with living hinge mechanism, jaw length 60mm, flexure thickness 0.5mm at hinge, jaw opening 0-40mm, grip force distribution ribs, mounting base 30mm x 30mm with 4x M4 holes, optimized for 3D printing in one piece',
                tags: ['pince', 'compliant', 'charnière-vivante'],
                difficulty: 'Avancé',
                estimatedTime: '5 min'
            },
            {
                id: 'bistable-mechanism',
                name: 'Mécanisme Bistable',
                description: 'Mécanisme snap-through avec deux positions stables',
                prompt: 'Create a snap-through bistable mechanism with curved beam 80mm length, 10mm width, 3mm thickness, pre-curved with 15mm rise, stable positions at 0° and 30°, actuation force 5N, with mounting tabs and travel limit stops',
                tags: ['bistable', 'snap-through', 'positions-stables'],
                difficulty: 'Avancé',
                estimatedTime: '4 min'
            }
        ]
    }
]

export class TemplateManager {
    static getAllTemplates(): Template[] {
        return ADVANCED_TEMPLATES.flatMap(category => category.templates)
    }

    static getTemplatesByCategory(categoryName: string): Template[] {
        const category = ADVANCED_TEMPLATES.find(cat => cat.name === categoryName)
        return category ? category.templates : []
    }

    static getTemplateById(id: string): Template | null {
        return this.getAllTemplates().find(template => template.id === id) || null
    }

    static getTemplatesByDifficulty(difficulty: 'Débutant' | 'Intermédiaire' | 'Avancé'): Template[] {
        return this.getAllTemplates().filter(template => template.difficulty === difficulty)
    }

    static searchTemplates(query: string): Template[] {
        const lowerQuery = query.toLowerCase()
        return this.getAllTemplates().filter(template =>
            template.name.toLowerCase().includes(lowerQuery) ||
            template.description.toLowerCase().includes(lowerQuery) ||
            template.tags.some(tag => tag.toLowerCase().includes(lowerQuery))
        )
    }

    static getRandomTemplate(): Template {
        const allTemplates = this.getAllTemplates()
        return allTemplates[Math.floor(Math.random() * allTemplates.length)]
    }

    static interpolateTemplate(template: Template, parameters: Record<string, any>): string {
        let interpolated = template.prompt

        // Remplacer les paramètres {param} par leurs valeurs
        Object.entries(parameters).forEach(([key, value]) => {
            const regex = new RegExp(`\\{${key}\\}`, 'g')
            interpolated = interpolated.replace(regex, value.toString())
        })

        return interpolated
    }

    static validateParameters(template: Template, parameters: Record<string, any>): {
        isValid: boolean
        errors: string[]
    } {
        const errors: string[] = []

        if (!template.parameters) {
            return { isValid: true, errors: [] }
        }

        template.parameters.forEach(param => {
            const value = parameters[param.name]

            if (value === undefined || value === null) {
                errors.push(`Paramètre manquant: ${param.name}`)
                return
            }

            if (param.type === 'number') {
                const numValue = Number(value)
                if (isNaN(numValue)) {
                    errors.push(`${param.name}: doit être un nombre`)
                    return
                }

                if (param.min !== undefined && numValue < param.min) {
                    errors.push(`${param.name}: minimum ${param.min}`)
                }

                if (param.max !== undefined && numValue > param.max) {
                    errors.push(`${param.name}: maximum ${param.max}`)
                }
            }
        })

        return {
            isValid: errors.length === 0,
            errors
        }
    }
}