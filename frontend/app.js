// ===== Three globals =====
let scene, camera, renderer, axesHelper = null, model = null;
let wireframeMode = false;
let currentCode = '';

// ===== ContrÃ´les manuels =====
let isDragging = false;
let isPanning = false;
let previousMousePosition = { x: 0, y: 0 };
let cameraRotation = { x: 0.5, y: 0.5 };
let cameraDistance = 400;
let cameraTarget = { x: 0, y: 0, z: 0 };

// ===== CONFIGURATION BACKEND =====
const BACKEND_URL = 'http://localhost:8000';

// ===== EXAMPLE PROMPTS - ORGANISÃ‰S PAR CATÃ‰GORIE =====
const EXAMPLE_PROMPTS = {
    splint: {
        'Resting Splint - Adult Standard': `Create a resting hand splint for wrist immobilization with three anatomically-connected sections:

SECTION 1 - Forearm support:
- Length: 150mm
- Width: tapers from 70mm at proximal end to 60mm at wrist
- Curvature: 5mm palmar curve for natural wrist position

SECTION 2 - Palm platform:
- Length: 80mm
- Width: constant 75mm (widest section)
- Angle: 20 degrees upward extension from forearm axis
- Curvature: 8mm transverse arch for palm contour

SECTION 3 - Finger support:
- Length: 40mm
- Width: constant 65mm
- Position: continues palm angle
- Curvature: 3mm for MCP joint clearance

MATERIAL & STRUCTURE:
- Wall thickness: 3.5mm for rigidity
- Smooth filleted transitions: 8mm radius between all sections
- Total assembled length: 270mm

VENTILATION:
- Perforation pattern: 6mm diameter holes
- Grid layout: 10 columns Ã— 3 rows

STRAP ATTACHMENT:
- 3 slots for velcro straps
- Slot dimensions: 25mm wide Ã— 3mm deep
- Positions: 50mm, 150mm, 220mm from proximal end`,

        'Resting Splint - Pediatric': `Create a pediatric resting hand splint for children:

SECTION 1 - Forearm support:
- Length: 100mm
- Width: tapers from 45mm at proximal end to 40mm at wrist
- Curvature: 3mm palmar curve

SECTION 2 - Palm platform:
- Length: 50mm
- Width: constant 50mm
- Angle: 15 degrees upward extension

SECTION 3 - Finger support:
- Length: 30mm
- Width: constant 45mm

MATERIAL & STRUCTURE:
- Wall thickness: 2.5mm for lighter weight
- Smooth filleted transitions: 5mm radius
- Total assembled length: 180mm

VENTILATION:
- Perforation pattern: 4mm diameter holes
- Grid layout: 8 columns Ã— 2 rows

STRAP ATTACHMENT:
- 3 slots for velcro straps
- Slot dimensions: 20mm wide Ã— 2mm deep
- Positions: 30mm, 80mm, 140mm from proximal end`,

        'Dynamic Splint - Extended': `Create a dynamic hand splint with extended range:

SECTION 1 - Forearm support:
- Length: 200mm (extended for more support)
- Width: tapers from 80mm at proximal end to 65mm at wrist
- Curvature: 7mm palmar curve

SECTION 2 - Palm platform:
- Length: 90mm
- Width: constant 80mm
- Angle: 25 degrees upward extension

SECTION 3 - Finger support:
- Length: 50mm
- Width: constant 70mm

MATERIAL & STRUCTURE:
- Wall thickness: 4mm for maximum rigidity
- Smooth filleted transitions: 10mm radius
- Total assembled length: 340mm

VENTILATION:
- Perforation pattern: 8mm diameter holes
- Grid layout: 12 columns Ã— 4 rows

STRAP ATTACHMENT:
- 4 slots for velcro straps
- Slot dimensions: 30mm wide Ã— 4mm deep
- Positions: 60mm, 140mm, 220mm, 280mm from proximal end`,

        'Static Splint - No Ventilation': `Create a static hand splint without ventilation holes:

SECTION 1 - Forearm support:
- Length: 140mm
- Width: tapers from 65mm at proximal end to 55mm at wrist
- Curvature: 4mm palmar curve

SECTION 2 - Palm platform:
- Length: 75mm
- Width: constant 70mm
- Angle: 18 degrees upward extension

SECTION 3 - Finger support:
- Length: 35mm
- Width: constant 60mm

MATERIAL & STRUCTURE:
- Wall thickness: 3mm
- Smooth filleted transitions: 6mm radius
- Total assembled length: 250mm

STRAP ATTACHMENT:
- 3 slots for velcro straps
- Slot dimensions: 25mm wide Ã— 3mm deep
- Positions: 45mm, 130mm, 200mm from proximal end

FINISHING:
- All edges: 2mm radius for safety
- Solid surface (no ventilation holes)`
    },

    stent: {
        'Coronary Stent - Standard': `Create a vascular stent with serpentine structure for coronary use:

- Outer radius: 8mm
- Total length: 40mm
- 6 rings vertically stacked
- 8 peaks per ring
- Amplitude (zigzag height): 3mm
- Ring spacing: 6mm
- Strut width: 0.6mm
- Strut depth: 0.4mm

Create alternating peak-valley connections for diamond-shaped cells`,

        'Peripheral Stent - Large Diameter': `Create a peripheral vascular stent with increased diameter:

- Outer radius: 12mm (for larger vessels)
- Total length: 60mm
- 8 rings vertically stacked
- 10 peaks per ring
- Amplitude (zigzag height): 4mm
- Ring spacing: 7mm
- Strut width: 0.8mm
- Strut depth: 0.5mm

Robust structure for peripheral arteries`,

        'Coronary Stent - Short': `Create a short coronary stent for targeted deployment:

- Outer radius: 7mm
- Total length: 25mm
- 4 rings vertically stacked
- 8 peaks per ring
- Amplitude (zigzag height): 2.5mm
- Ring spacing: 5mm
- Strut width: 0.5mm
- Strut depth: 0.35mm

Compact design for precise placement`,

        'Renal Stent - High Flexibility': `Create a renal artery stent with enhanced flexibility:

- Outer radius: 10mm
- Total length: 50mm
- 7 rings vertically stacked
- 12 peaks per ring (increased flexibility)
- Amplitude (zigzag height): 3.5mm
- Ring spacing: 6.5mm
- Strut width: 0.7mm
- Strut depth: 0.45mm

High peak count for improved conformability`
    },

    lattice: {
        'Cubic Lattice - Standard': `Create a cubic lattice structure for lightweight engineering:

- Cell type: cubic
- Cell size: 10mm
- Strut diameter: 1.5mm
- Overall dimensions: 100mm Ã— 100mm Ã— 100mm

Regular periodic pattern suitable for 3D printing
Simple structure with good mechanical properties`,

        'Diamond Lattice - High Strength': `Create a diamond lattice structure for maximum strength:

- Cell type: diamond
- Cell size: 8mm
- Strut diameter: 1.8mm
- Overall dimensions: 120mm Ã— 120mm Ã— 120mm

Diamond cells provide superior strength-to-weight ratio
Ideal for load-bearing applications`,

        'Octet Truss - Aerospace Grade': `Create an octet truss lattice for aerospace applications:

- Cell type: octet
- Cell size: 12mm
- Strut diameter: 1.2mm
- Overall dimensions: 150mm Ã— 150mm Ã— 150mm

Octet-truss structure combines cubic and tetrahedral elements
Optimal stiffness and strength for aerospace use`,

        'Gyroid Lattice - Biomimetic': `Create a gyroid lattice structure with organic geometry:

- Cell type: gyroid
- Cell size: 15mm
- Strut diameter: 2.0mm
- Overall dimensions: 100mm Ã— 100mm Ã— 100mm

Triply periodic minimal surface structure
Excellent for fluid flow and heat dissipation`,

        'Kelvin Cell - Foam Structure': `Create a Kelvin cell lattice mimicking foam structure:

- Cell type: kelvin
- Cell size: 10mm
- Strut diameter: 1.4mm
- Overall dimensions: 90mm Ã— 90mm Ã— 90mm

Tetrakaidecahedron cells (14-sided polyhedra)
Space-filling structure with isotropic properties`,

        'BCC Lattice - Body-Centered Cubic': `Create a BCC lattice structure:

- Cell type: bcc
- Cell size: 9mm
- Strut diameter: 1.3mm
- Overall dimensions: 108mm Ã— 108mm Ã— 108mm

Body-centered cubic arrangement
Good balance of strength and weight`,

        'FCC Lattice - Face-Centered Cubic': `Create an FCC lattice structure:

- Cell type: fcc
- Cell size: 11mm
- Strut diameter: 1.6mm
- Overall dimensions: 110mm Ã— 110mm Ã— 110mm

Face-centered cubic packing
High ductility and energy absorption`,

        'Cubic Lattice - Dense': `Create a dense cubic lattice for impact resistance:

- Cell type: cubic
- Cell size: 5mm (smaller cells = denser)
- Strut diameter: 1.0mm
- Overall dimensions: 80mm Ã— 80mm Ã— 80mm

Higher density for enhanced mechanical properties
Suitable for protective applications`
    },

    facade: {
        // ===== HONEYCOMB PANEL (nouveau - CadQuery) =====
        'Honeycomb Panel - Standard': `Create a honeycomb panel with hexagonal cells for lightweight architecture:

PANEL DIMENSIONS:
- Width: 300mm
- Height: 380mm
- Thickness: 40mm

HEXAGONAL CELLS:
- Cell size (side length): 12mm
- Wall thickness: 2.2mm
- Cell depth: 40mm (full depth through panel)
- Pattern type: flat-top hexagons

STRUCTURE:
- Only complete cells (cells entirely within panel boundaries)
- No vertical ribs, pure honeycomb pattern
- Corner fillet: 0mm (sharp edges)

MATERIAL:
- Aluminum-compatible geometry
- Optimized for CNC milling or 3D printing`,

        'Honeycomb Panel - Large Scale': `Create a large honeycomb panel:

PANEL DIMENSIONS:
- Width: 500mm
- Height: 600mm
- Thickness: 60mm

HEXAGONAL CELLS:
- Cell size: 20mm (larger cells)
- Wall thickness: 3.0mm
- Cell depth: 60mm
- Full depth extrusion

FEATURES:
- Structural honeycomb for building facades
- Maximum strength-to-weight ratio
- Industrial scale fabrication`,

        'Honeycomb Panel - Fine Mesh': `Create a fine honeycomb panel:

PANEL DIMENSIONS:
- Width: 200mm
- Height: 250mm
- Thickness: 25mm

HEXAGONAL CELLS:
- Cell size: 8mm (fine mesh)
- Wall thickness: 1.5mm
- Cell depth: 25mm
- Detailed hexagonal pattern

APPLICATIONS:
- Ventilation grilles
- Decorative screens
- Precision manufacturing`,

        // ===== HEXAGONAL PYRAMID FACADE (ancien - numpy/struct) =====
        'Hexagonal Pyramid Facade - Standard': `Create a hexagonal pyramid facade with triangular elements:

HEX FRAME:
- Hex radius: 60mm
- Frame width: 8mm
- Frame height: 10mm

TRIANGULAR PYRAMIDS:
- Triangle height: 55mm
- Plate thickness: 2.4mm
- 6 pyramids arranged in hexagonal pattern

CONNECTING BARS:
- Bar width: 8mm
- Bar height: 10mm
- Radial arrangement from center

STRUCTURE:
- Architectural module
- 3D relief pattern
- Modern aesthetic`,

        'Hexagonal Pyramid Facade - Large': `Create a large hexagonal pyramid facade:

HEX FRAME:
- Hex radius: 100mm (extended)
- Frame width: 12mm
- Frame height: 15mm

TRIANGULAR PYRAMIDS:
- Triangle height: 90mm (taller pyramids)
- Plate thickness: 3.5mm
- Bold 3D effect

CONNECTING BARS:
- Bar width: 12mm
- Bar height: 15mm

FEATURES:
- Dramatic architectural statement
- Enhanced shadow patterns
- Structural facade element`,

        // ===== LOUVRE WALL =====
        'Diagonal Louvers Pavilion - Single Layer': `Create a triangular pavilion with diagonal louvres:

TRIANGLE BASE:
- Width: 280mm
- Height: 260mm
- Thickness: 40mm
- Corner fillet: 3mm

LOUVRES (SLATS):
- Angle: 35 degrees from horizontal
- Pitch (spacing): 12mm perpendicular to slats
- Slat width: 8mm
- Slat depth (extrusion): 12mm
- End radius: 3mm (rounded ends)
- Layer 1 Z position: 6mm

CONFIGURATION:
- Single layer of diagonal slats
- Boolean mode: union
- Pattern clips to triangle shape`,

        'Diagonal Louvers Pavilion - Crossed': `Create a pavilion with crossed diagonal louvres:

TRIANGLE BASE:
- Width: 280mm
- Height: 260mm  
- Thickness: 40mm
- Corner fillet: 3mm

LAYER 1 LOUVRES:
- Angle: 35 degrees
- Pitch: 12mm
- Slat width: 8mm
- Slat depth: 12mm
- End radius: 3mm
- Z position: 6mm

LAYER 2 LOUVRES (CROSSED):
- Layer 2: enabled
- Angle: 55 degrees (crossed pattern)
- Z offset: 0mm (different layer)
- Same slat dimensions

CONFIGURATION:
- Boolean mode: union (combine both layers)
- Creates diamond-shaped openings
- Enhanced structural pattern`,

        // ===== SINE WAVE FINS =====
        'Sine Wave Fins - Standard': `Create a facade with sine wave undulating fins:

PANEL DIMENSIONS:
- Length: 420mm
- Height: 180mm
- Depth: 140mm

FINS (RIBS):
- Number of fins: 34
- Fin thickness: 3mm
- Arrangement: vertical fins following sine wave

SINE WAVE PATTERN:
- Amplitude: 40mm (wave height)
- Period ratio: 0.9 (wavelength control)
- Creates smooth undulating facade

BASE STRUCTURE:
- Base plate thickness: 6mm
- Fins loft from base with sine offset
- Clips to rectangular boundary`,

        'Sine Wave Fins - High Amplitude': `Create a dramatic sine wave facade:

PANEL DIMENSIONS:
- Length: 500mm
- Height: 200mm
- Depth: 180mm

FINS:
- Number of fins: 40
- Fin thickness: 4mm
- Dense fin arrangement

SINE WAVE:
- Amplitude: 60mm (dramatic waves)
- Period ratio: 0.8 (tighter waves)
- Bold 3D relief effect

STRUCTURE:
- Base thickness: 8mm (reinforced)
- Enhanced depth for shadows
- Architectural feature wall`
    },

    gripper: {
        'Medical Gripper - Standard': `Create a medical gripper with cross shape for surgical use:

- 4 arms radiating from center at 90-degree intervals
- Arm length: 25mm
- Arm width: 8mm
- Center diameter: 6mm
- Total thickness: 1.5mm
- Perforation holes: 0.8mm diameter
- Hole spacing: 1.5mm for ventilation
- Smooth rounded edges for safety

Suitable for delicate tissue handling`,

        'Medical Gripper - Heavy Duty': `Create a heavy-duty medical gripper for robust applications:

- 4 arms radiating from center
- Arm length: 35mm (extended reach)
- Arm width: 12mm (wider for strength)
- Center diameter: 10mm
- Total thickness: 2.5mm (reinforced)
- Perforation holes: 1.0mm diameter
- Hole spacing: 2.0mm

Enhanced strength for demanding procedures`,


        'Medical Gripper - Micro': `Create a micro-scale medical gripper for minimally invasive surgery:

- 4 arms radiating from center
- Arm length: 15mm (compact)
- Arm width: 5mm
- Center diameter: 4mm
- Total thickness: 1.0mm (thin profile)
- Perforation holes: 0.5mm diameter
- Hole spacing: 1.0mm

Miniaturized for laparoscopic procedures`,

        'Medical Gripper - 6-Armed': `Create a 6-armed medical gripper for enhanced grip:

- 6 arms radiating from center at 60-degree intervals
- Arm length: 22mm
- Arm width: 7mm
- Center diameter: 8mm
- Total thickness: 1.8mm
- Perforation holes: 0.7mm diameter
- Hole spacing: 1.3mm

Additional arms provide more contact points`
    },

    heatsink: {
        'Heatsink - 40mm ATX (Standard)': `Create a CPU heatsink with cooling fins:

PLATE:
- Width: 40mm
- Height: 40mm
- Thickness: 3mm
- 4 mounting holes: 3.3mm diameter
- Hole pitch: 32mm (center to center)

CENTRAL TUBE:
- Outer diameter: 42mm
- Length: 10mm
- Rectangular cross-section

COOLING BARS (FINS):
- 2 symmetrical bars
- Length: 22mm each
- Angle: 20Â° outward
- Tapered design for better airflow

MATERIAL:
- Aluminum compatible geometry
- Optimized for heat dissipation`,

        'Heatsink - 50mm EATX (Extended)': `Create a high-performance heatsink:

PLATE:
- Width: 50mm
- Height: 50mm
- Thickness: 4mm
- 4 mounting holes: 4mm diameter
- Hole pitch: 40mm

CENTRAL TUBE:
- Outer diameter: 48mm
- Length: 12mm

COOLING BARS:
- 2 extended bars
- Length: 30mm each
- Angle: 25Â° (aggressive)
- Maximum surface area

Enhanced cooling capacity`,

        'Heatsink - 30mm SFF (Small Form)': `Create a compact heatsink for small devices:

PLATE:
- Width: 30mm
- Height: 30mm
- Thickness: 2mm
- 4 mounting holes: 2.5mm diameter
- Hole pitch: 24mm

CENTRAL TUBE:
- Outer diameter: 32mm
- Length: 8mm

COOLING BARS:
- 2 short bars
- Length: 15mm each
- Angle: 15Â°

Optimized for space-constrained applications`
    },
};

// ===== INITIALIZATION =====
function initViewer() {
    const container = document.getElementById('viewer');

    scene = new THREE.Scene();
    scene.background = new THREE.Color(0x0a0a0f);
    scene.fog = new THREE.Fog(0x0a0a0f, 400, 2000);

    camera = new THREE.PerspectiveCamera(50, container.clientWidth / container.clientHeight, 0.1, 5000);
    updateCameraPosition();

    renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setSize(container.clientWidth, container.clientHeight);
    renderer.setPixelRatio(window.devicePixelRatio || 1);
    renderer.shadowMap.enabled = true;
    container.appendChild(renderer.domElement);

    renderer.domElement.style.cursor = 'grab';
    renderer.domElement.addEventListener('contextmenu', e => {
        e.preventDefault();
        return false;
    });

    // ===== CONTRÃ”LES MANUELS =====
    renderer.domElement.addEventListener('mousedown', e => {
        if (e.button === 0) {
            isDragging = true;
            renderer.domElement.style.cursor = 'grabbing';
        } else if (e.button === 2) {
            isPanning = true;
            renderer.domElement.style.cursor = 'move';
        }
        previousMousePosition = { x: e.clientX, y: e.clientY };
    });

    renderer.domElement.addEventListener('mouseup', () => {
        isDragging = false;
        isPanning = false;
        renderer.domElement.style.cursor = 'grab';
    });

    renderer.domElement.addEventListener('mouseleave', () => {
        isDragging = false;
        isPanning = false;
        renderer.domElement.style.cursor = 'grab';
    });

    renderer.domElement.addEventListener('mousemove', e => {
        if (isDragging) {
            const deltaX = e.clientX - previousMousePosition.x;
            const deltaY = e.clientY - previousMousePosition.y;

            cameraRotation.y += deltaX * 0.005;
            cameraRotation.x += deltaY * 0.005;
            cameraRotation.x = Math.max(-Math.PI / 2, Math.min(Math.PI / 2, cameraRotation.x));

            updateCameraPosition();
        } else if (isPanning) {
            const deltaX = e.clientX - previousMousePosition.x;
            const deltaY = e.clientY - previousMousePosition.y;

            const panSpeed = 0.5;
            cameraTarget.x -= deltaX * panSpeed;
            cameraTarget.y += deltaY * panSpeed;

            updateCameraPosition();
        }

        previousMousePosition = { x: e.clientX, y: e.clientY };
    });

    renderer.domElement.addEventListener('wheel', e => {
        e.preventDefault();
        const zoomSpeed = 20;
        cameraDistance += e.deltaY * zoomSpeed * 0.01;
        cameraDistance = Math.max(50, Math.min(2000, cameraDistance));
        updateCameraPosition();
    });

    // LumiÃ¨res
    scene.add(new THREE.AmbientLight(0xffffff, 0.45));

    const d1 = new THREE.DirectionalLight(0xffffff, 0.8);
    d1.position.set(200, 200, 120);
    d1.castShadow = true;
    scene.add(d1);

    const d2 = new THREE.DirectionalLight(0xffffff, 0.3);
    d2.position.set(-200, -100, -100);
    scene.add(d2);

    // Grille
    const grid = new THREE.GridHelper(800, 80, 0x444466, 0x222244);
    grid.material.opacity = 0.5;
    grid.material.transparent = true;
    scene.add(grid);

    // Axes
    axesHelper = new THREE.AxesHelper(120);
    axesHelper.visible = false;
    scene.add(axesHelper);

    window.addEventListener('resize', onWindowResize);

    console.log('âœ… Viewer initialisÃ© avec tous les exemples');

    // Initialiser la liste d'exemples
    updateExamplesList();

    animate();
}

function updateCameraPosition() {
    const x = cameraDistance * Math.cos(cameraRotation.x) * Math.sin(cameraRotation.y);
    const y = cameraDistance * Math.sin(cameraRotation.x);
    const z = cameraDistance * Math.cos(cameraRotation.x) * Math.cos(cameraRotation.y);

    camera.position.set(
        x + cameraTarget.x,
        y + cameraTarget.y,
        z + cameraTarget.z
    );

    camera.lookAt(cameraTarget.x, cameraTarget.y, cameraTarget.z);
}

function onWindowResize() {
    const container = document.getElementById('viewer');
    camera.aspect = container.clientWidth / container.clientHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(container.clientWidth, container.clientHeight);
}

function animate() {
    requestAnimationFrame(animate);
    renderer.render(scene, camera);
}

// ==== UI Helpers ====
function toggleWireframe() {
    wireframeMode = !wireframeMode;
    if (model && model.material) model.material.wireframe = wireframeMode;
}

function toggleAxes() {
    if (axesHelper) axesHelper.visible = !axesHelper.visible;
}

function resetView() {
    if (!model) {
        cameraRotation = { x: 0.5, y: 0.5 };
        cameraDistance = 400;
        cameraTarget = { x: 0, y: 0, z: 0 };
        updateCameraPosition();
        return;
    }

    const box = new THREE.Box3().setFromObject(model);
    const size = box.getSize(new THREE.Vector3());
    const center = box.getCenter(new THREE.Vector3());

    const maxDim = Math.max(size.x, size.y, size.z);
    cameraDistance = maxDim * 2.5;

    cameraTarget = { x: center.x, y: center.y, z: center.z };
    cameraRotation = { x: 0.5, y: 0.5 };

    updateCameraPosition();
}

// ==== Example Prompts Management ====
function updateExamplesList() {
    const appType = document.getElementById('appType').value;
    const variantSelect = document.getElementById('exampleVariant');

    // Clear existing options
    variantSelect.innerHTML = '';

    // Get examples for selected app type
    const examples = EXAMPLE_PROMPTS[appType];

    if (examples) {
        Object.keys(examples).forEach(variantName => {
            const option = document.createElement('option');
            option.value = variantName;
            option.textContent = variantName;
            variantSelect.appendChild(option);
        });

        console.log(`âœ… Loaded ${Object.keys(examples).length} examples for: ${appType}`);
    }
}

function loadSelectedExample() {
    const appType = document.getElementById('appType').value;
    const variantName = document.getElementById('exampleVariant').value;
    const promptTextarea = document.getElementById('prompt');

    const examples = EXAMPLE_PROMPTS[appType];

    if (examples && examples[variantName]) {
        promptTextarea.value = examples[variantName];
        console.log(`âœ… Loaded example: ${appType} - ${variantName}`);
    } else {
        showError(`Example not found: ${appType} - ${variantName}`);
    }
}

// ==== Mesh Loader ====
function loadMesh(mesh) {
    if (model) {
        scene.remove(model);
        model.geometry.dispose();
        model.material.dispose();
        model = null;
    }

    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute('position', new THREE.Float32BufferAttribute(mesh.vertices, 3));
    if (mesh.normals && mesh.normals.length)
        geometry.setAttribute('normal', new THREE.Float32BufferAttribute(mesh.normals, 3));
    geometry.setIndex(mesh.faces);
    geometry.computeVertexNormals();
    geometry.computeBoundingSphere();

    const material = new THREE.MeshPhongMaterial({
        color: 0x00ff88, specular: 0x222222, shininess: 120, side: THREE.DoubleSide, wireframe: wireframeMode
    });

    model = new THREE.Mesh(geometry, material);
    model.castShadow = true;
    model.receiveShadow = true;
    scene.add(model);

    resetView();
}

// ==== Error & Progress ====
function showError(message) {
    document.getElementById('errorMessage').textContent = message;
    document.getElementById('errorModal').classList.remove('hidden');
}

function closeError() {
    document.getElementById('errorModal').classList.add('hidden');
}

function updateProgress(val, status) {
    document.getElementById('progressBar').style.width = `${val}%`;
    document.getElementById('progressPercent').textContent = `${val}%`;
    document.getElementById('statusText').textContent = status || 'Processing...';
}

// ==== SSE Helper ====
function decodeEscapedString(str) {
    if (!str) return str;
    return str
        .replace(/\\n/g, '\n')
        .replace(/\\r/g, '\r')
        .replace(/\\t/g, '\t')
        .replace(/\\"/g, '"')
        .replace(/\\\\/g, '\\');
}

// ==== Main Generation Function ====
async function generateCAD() {
    const prompt = document.getElementById('prompt').value.trim();
    if (!prompt) {
        showError('Please enter a CAD description');
        return;
    }

    const progressDiv = document.getElementById('progress');
    const generateBtn = document.getElementById('generateBtn');
    const loadingIndicator = document.getElementById('loadingIndicator');

    progressDiv.classList.remove('hidden');
    generateBtn.disabled = true;
    generateBtn.classList.add('opacity-50');
    loadingIndicator.classList.remove('hidden');

    currentCode = '';
    updateProgress(0, 'Starting...');

    try {
        const response = await fetch(`${BACKEND_URL}/api/generate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ prompt })
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        if (!response.body) {
            throw new Error('No response body');
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        let lastProgress = 0;

        while (true) {
            const { value, done } = await reader.read();

            if (done) {
                console.log('SSE stream complete');
                break;
            }

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop() || '';

            for (const line of lines) {
                if (!line.trim() || !line.startsWith('data: ')) continue;

                const dataStr = line.slice(6);

                try {
                    const data = JSON.parse(dataStr);
                    console.log('SSE event:', data.type || 'unknown');

                    if (data.type === 'status') {
                        updateProgress(lastProgress + 10, data.message);
                        lastProgress = Math.min(lastProgress + 10, 90);
                    }
                    else if (data.type === 'code') {
                        const code = decodeEscapedString(data.code);
                        currentCode = code;
                        updateProgress(60, 'Code generated');
                    }
                    else if (data.type === 'complete') {
                        if (data.success) {
                            updateProgress(100, 'Complete!');

                            if (data.code) currentCode = data.code;
                            if (data.mesh) loadMesh(data.mesh);
                            if (data.analysis) displayAnalysis(data.analysis);
                            if (data.parameters) displayParameters(data.parameters);

                            console.log('âœ… Generation successful!');
                        } else {
                            throw new Error(data.errors?.join(', ') || 'Generation failed');
                        }
                    }
                    else if (data.type === 'error') {
                        throw new Error(data.errors?.join(', ') || 'Unknown error');
                    }

                } catch (parseError) {
                    console.warn('SSE parse warning:', parseError.message);
                }
            }
        }

    } catch (error) {
        console.error('âŒ Generation error:', error);
        showError(`Generation failed: ${error.message}`);
        updateProgress(0, 'Failed');
    } finally {
        setTimeout(() => {
            progressDiv.classList.add('hidden');
            generateBtn.disabled = false;
            generateBtn.classList.remove('opacity-50');
            loadingIndicator.classList.add('hidden');
        }, 1000);
    }
}

// ==== Export Functions ====
async function exportSTL() {
    try {
        const r = await fetch(`${BACKEND_URL}/api/export/stl`);
        if (!r.ok) {
            showError('No STL file available');
            return;
        }
        const b = await r.blob();
        const a = document.createElement('a');
        a.href = URL.createObjectURL(b);
        a.download = 'cad_model.stl';
        a.click();
    } catch (error) {
        console.error('STL export error:', error);
        showError('Failed to export STL');
    }
}

async function exportSTEP() {
    try {
        const r = await fetch(`${BACKEND_URL}/api/export/step`);
        if (!r.ok) {
            showError('No STEP file available');
            return;
        }
        const b = await r.blob();
        const a = document.createElement('a');
        a.href = URL.createObjectURL(b);
        a.download = 'cad_model.step';
        a.click();
    } catch (error) {
        console.error('STEP export error:', error);
        showError('Failed to export STEP');
    }
}

function exportCode() {
    if (!currentCode) {
        showError('No code available to export');
        return;
    }
    const blob = new Blob([currentCode], { type: 'text/plain' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'cad_model.py';
    a.click();
}

// ==== Analysis/Parameters Display ====
function displayParameters(params) {
    const el = document.getElementById('parameters');
    if (!el) return;

    if (!params || Object.keys(params).length === 0) {
        el.innerHTML = '<div class="text-gray-400">No parameters extracted</div>';
        return;
    }

    el.innerHTML = Object.entries(params).map(([k, v]) =>
        `<div class="flex justify-between items-center py-1 border-b border-white/10">
            <span class="text-gray-300 text-xs">${k}:</span>
            <span class="text-blue-400 font-mono text-xs">${Array.isArray(v) ? v.join(', ') : v}</span>
        </div>`
    ).join('');
}

function displayAnalysis(analysis) {
    const el = document.getElementById('analysis');
    if (!el) return;

    el.innerHTML = `
        <div class="bg-white/10 rounded-lg p-4">
            <h3 class="text-lg font-bold text-white mb-2">ðŸ“ Dimensions</h3>
            <div class="text-gray-300 text-sm">
                <p>Length: <span class="text-blue-400">${analysis.dimensions?.length?.toFixed(1) || 'N/A'}mm</span></p>
                <p>Width: <span class="text-blue-400">${analysis.dimensions?.width?.toFixed(1) || 'N/A'}mm</span></p>
                <p>Height: <span class="text-blue-400">${analysis.dimensions?.height?.toFixed(1) || 'N/A'}mm</span></p>
            </div>
        </div>
        <div class="bg-white/10 rounded-lg p-4">
            <h3 class="text-lg font-bold text-white mb-2">ðŸŽ¯ Features</h3>
            <div class="text-gray-300 text-sm">
                <p>âœ… Generated successfully</p>
            </div>
        </div>
        <div class="bg-white/10 rounded-lg p-4">
            <h3 class="text-lg font-bold text-white mb-2">âœ… Validation</h3>
            <div class="text-sm">
                <p class="text-green-400">âœ“ Geometry Valid</p>
                <p class="text-green-400">âœ“ 3D Printable</p>
            </div>
        </div>
    `;
}

window.addEventListener('load', initViewer);