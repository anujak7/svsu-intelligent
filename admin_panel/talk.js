// talk.js

const container = document.getElementById('avatar-container');
const loaderOverlay = document.getElementById('loader-overlay');
const subtitleText = document.getElementById('subtitleText');
const micBtn = document.getElementById('micBtn');
const statusText = document.getElementById('statusText');

// Three.js Globals
let scene, camera, renderer, mixer, clock;
let avatarGltf, jawBone, headBone;
let isModelLoaded = false;

// Audio Globals
let audioContext, analyser, dataArray;
let isAudioPlaying = false;
let currentAudioSource = null;

// Recording Globals
let mediaRecorder;
let audioChunks = [];
let isRecording = false;

function initThreeJS() {
    scene = new THREE.Scene();

    camera = new THREE.PerspectiveCamera(45, window.innerWidth / window.innerHeight, 0.1, 10000);
    camera.position.set(0, 1.4, 2.8); // Framed roughly waist-up

    renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.setPixelRatio(window.devicePixelRatio);
    renderer.outputEncoding = THREE.sRGBEncoding;
    container.appendChild(renderer.domElement);

    const ambientLight = new THREE.AmbientLight(0xffffff, 1.2);
    scene.add(ambientLight);

    const dirLight = new THREE.DirectionalLight(0xffffff, 1.0);
    dirLight.position.set(2, 5, 5);
    scene.add(dirLight);

    const hemiLight = new THREE.HemisphereLight(0xffffff, 0x444444, 1.0);
    hemiLight.position.set(0, 20, 0);
    scene.add(hemiLight);

    clock = new THREE.Clock();

    const loader = new THREE.GLTFLoader();
    // GLB file provided by the user
    loader.load('/assets/models/avatar.glb', function (gltf) {
        avatarGltf = gltf.scene;

        const box = new THREE.Box3().setFromObject(avatarGltf);
        const size = box.getSize(new THREE.Vector3());
        const center = box.getCenter(new THREE.Vector3());

        // Center the model relative to itself
        avatarGltf.position.sub(center);
        scene.add(avatarGltf);

        // Calculate maximum dimension for framing
        const maxDim = Math.max(size.x, size.y, size.z);

        // Configure camera correctly to avoid clipping while preserving depth precision
        camera.near = 0.1;
        camera.far = maxDim * 20;

        // Calculate correct camera distance using FOV
        const fov = camera.fov * (Math.PI / 180);
        let cameraZ = Math.abs(maxDim / 2 / Math.tan(fov / 2));
        cameraZ *= 1.5; // Back up slightly more for waist framing

        // Set waist-up framing (roughly 60% up the height)
        camera.position.set(0, size.y * 0.1, cameraZ);
        camera.lookAt(0, size.y * 0.1, 0);

        // Crucial: update projection matrix after changing near/far limits
        camera.updateProjectionMatrix();

        // Map bones to enable lip sync
        avatarGltf.traverse((child) => {
            if (child.isBone) {
                const name = child.name.toLowerCase();
                if (name.includes('jaw')) jawBone = child;
                if (!headBone && name.includes('head')) headBone = child;
            }
            if (child.isMesh) {
                child.frustumCulled = false; // Prevent unwanted culling
            }
        });

        // Setup the animation mixer
        mixer = new THREE.AnimationMixer(avatarGltf);
        if (gltf.animations && gltf.animations.length > 0) {
            const action = mixer.clipAction(gltf.animations[0]); // Typically Idle
            action.play();
        }

        isModelLoaded = true;
        loaderOverlay.style.opacity = '0';
        setTimeout(() => loaderOverlay.style.display = 'none', 500);

        animate();
    }, undefined, function (error) {
        console.error("Error loading avatar:", error);
        subtitleText.innerText = "Error: Avatar model not found at /assets/models/avatar.glb";
        loaderOverlay.style.display = 'none';

        // Even if missing, let the loop run for debugging
        animate();
    });

    window.addEventListener('resize', onWindowResize, false);
}

function onWindowResize() {
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
}

// Lip Sync Variables
let targetJawRotation = 0;
let defaultJawRotation = null;
let targetHeadRotation = 0;
let defaultHeadRotation = null;

function animate() {
    requestAnimationFrame(animate);

    const delta = clock.getDelta();
    if (mixer) mixer.update(delta);

    if (isAudioPlaying && analyser) {
        analyser.getByteFrequencyData(dataArray);

        // Calculate the root mean square (RMS) or average volume
        let sum = 0;
        for (let i = 0; i < dataArray.length; i++) {
            sum += dataArray[i];
        }
        const average = sum / dataArray.length;

        // Create an active normalized factor 0.0 -> 1.0 based on intensity
        const volumeFactor = Math.min(average / 100, 1.0);

        if (jawBone) {
            if (defaultJawRotation === null) defaultJawRotation = jawBone.rotation.x;
            // A Mixamo jaw rotation typically acts around the X-axis mapping to opening mouth downwards
            targetJawRotation = defaultJawRotation + (volumeFactor * 0.35);
            jawBone.rotation.x = THREE.MathUtils.lerp(jawBone.rotation.x, targetJawRotation, 0.4);
        }

        if (headBone) {
            if (defaultHeadRotation === null) defaultHeadRotation = headBone.rotation.x;
            // Slight natural head bounce when talking
            targetHeadRotation = defaultHeadRotation + (volumeFactor * 0.05);
            headBone.rotation.x = THREE.MathUtils.lerp(headBone.rotation.x, targetHeadRotation, 0.1);
        }
    } else {
        // Return jaw and head to default resting position
        if (jawBone && defaultJawRotation !== null) {
            jawBone.rotation.x = THREE.MathUtils.lerp(jawBone.rotation.x, defaultJawRotation, 0.2);
        }
        if (headBone && defaultHeadRotation !== null) {
            headBone.rotation.x = THREE.MathUtils.lerp(headBone.rotation.x, defaultHeadRotation, 0.1);
        }
    }

    renderer.render(scene, camera);
}

// Audio Initializer
function initAudio() {
    if (!audioContext) {
        audioContext = new (window.AudioContext || window.webkitAudioContext)();
        analyser = audioContext.createAnalyser();
        analyser.fftSize = 256;
        dataArray = new Uint8Array(analyser.frequencyBinCount);
    }
}

// Play Received TTS
async function playBase64Audio(base64Data, text) {
    if (audioContext && audioContext.state === 'suspended') {
        await audioContext.resume();
    }

    // Interrupt existing voice response smoothly
    if (currentAudioSource) {
        currentAudioSource.stop();
        currentAudioSource.disconnect();
    }

    // Convert Base64 back to AudioBuffer
    const binaryString = window.atob(base64Data);
    const len = binaryString.length;
    const bytes = new Uint8Array(len);
    for (let i = 0; i < len; i++) {
        bytes[i] = binaryString.charCodeAt(i);
    }

    subtitleText.innerText = text;

    audioContext.decodeAudioData(bytes.buffer, function (buffer) {
        const source = audioContext.createBufferSource();
        source.buffer = buffer;

        // Pass source through our Analyser to get the data for Lip Sync
        source.connect(analyser);
        analyser.connect(audioContext.destination);

        source.onended = () => {
            isAudioPlaying = false;
            subtitleText.innerText = "Tap the mic and speak...";
        };

        currentAudioSource = source;
        isAudioPlaying = true;
        source.start(0);

    }, function (err) {
        console.error("Error decoding audio buffer:", err);
    });
}

// Interacting - Voice Recording Loop
micBtn.addEventListener('click', async () => {
    initAudio();
    if (audioContext.state === 'suspended') await audioContext.resume();

    if (!isRecording) {
        startRecording();
    } else {
        stopRecording();
    }
});

async function startRecording() {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        mediaRecorder = new MediaRecorder(stream);
        audioChunks = [];

        mediaRecorder.ondataavailable = event => {
            if (event.data.size > 0) audioChunks.push(event.data);
        };

        mediaRecorder.onstop = processRecording;
        mediaRecorder.start();

        isRecording = true;
        micBtn.classList.add('recording');
        statusText.innerText = 'LISTENING...';
        subtitleText.innerText = '';

        // Interrupt bot instantly if recording anew
        if (currentAudioSource) {
            currentAudioSource.stop();
            isAudioPlaying = false;
        }

    } catch (err) {
        console.error("Microphone access denied:", err);
        statusText.innerText = 'MIC ERROR';
        subtitleText.innerText = 'Please allow microphone permissions to use Voice Mode.';
    }
}

function stopRecording() {
    if (mediaRecorder && mediaRecorder.state !== 'inactive') {
        mediaRecorder.stop();
        // Close media tracks perfectly
        mediaRecorder.stream.getTracks().forEach(track => track.stop());
    }
    isRecording = false;
    micBtn.classList.remove('recording');
    micBtn.classList.add('processing');
    statusText.innerText = 'ANALYZING...';
    subtitleText.innerText = '';
}

async function processRecording() {
    if (audioChunks.length === 0) return;
    const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
    const formData = new FormData();
    formData.append("audio_file", audioBlob, "recording.webm");

    try {
        const res = await fetch('/api/voice-chat', {
            method: 'POST',
            body: formData
        });

        micBtn.classList.remove('processing');
        statusText.innerText = 'TAP TO TALK';

        if (!res.ok) throw new Error("API Exception on STT/TTS Server");

        const data = await res.json();

        if (data.audio) {
            playBase64Audio(data.audio, data.response);
        } else {
            subtitleText.innerText = "I didn't quite catch that. Could you repeat?";
        }

    } catch (e) {
        console.error("Voice chat execution error:", e);
        micBtn.classList.remove('processing');
        statusText.innerText = 'TAP TO TALK';
        subtitleText.innerText = 'Connection disconnected. Please retry.';
    }
}

// Initial Boot of system
initThreeJS();
