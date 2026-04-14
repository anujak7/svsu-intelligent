import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

fig, ax = plt.subplots(1, 1, figsize=(24, 32))
ax.set_xlim(0, 24)
ax.set_ylim(0, 32)
ax.axis('off')
fig.patch.set_facecolor('#F8F9FA')
ax.set_facecolor('#F8F9FA')

# ─────────────────────────────────────────────
# COLOUR PALETTE
# ─────────────────────────────────────────────
C = {
    'header':   '#1e293b',
    'pink':     '#F9D0DC',
    'pink_b':   '#E91E63',
    'purple':   '#EDE7F6',
    'purple_b': '#7C3AED',
    'blue':     '#DBEAFE',
    'blue_b':   '#2563EB',
    'green':    '#D1FAE5',
    'green_b':  '#059669',
    'yellow':   '#FEF9C3',
    'yellow_b': '#D97706',
    'cyan':     '#CFFAFE',
    'cyan_b':   '#0891B2',
    'orange':   '#FFEDD5',
    'orange_b': '#EA580C',
    'gray':     '#F1F5F9',
    'gray_b':   '#64748B',
    'red':      '#FEE2E2',
    'red_b':    '#DC2626',
    'mint':     '#ECFDF5',
    'mint_b':   '#10B981',
    'white':    '#FFFFFF',
    'text':     '#1e293b',
}

def box(ax, x, y, w, h, label, sublabel='', fill=C['blue'], edge=C['blue_b'], fontsize=10, subfontsize=8, bold=True):
    rect = FancyBboxPatch((x, y), w, h, 
                           boxstyle="round,pad=0.08",
                           facecolor=fill, edgecolor=edge, linewidth=2)
    ax.add_patch(rect)
    cy = y + h/2 + (0.18 if sublabel else 0)
    weight = 'bold' if bold else 'normal'
    ax.text(x + w/2, cy, label, ha='center', va='center',
            fontsize=fontsize, fontweight=weight, color=C['text'], wrap=True)
    if sublabel:
        ax.text(x + w/2, y + h/2 - 0.22, sublabel, ha='center', va='center',
                fontsize=subfontsize, color=C['gray_b'], style='italic')

def section_header(ax, x, y, w, label, color=C['header']):
    rect = FancyBboxPatch((x, y), w, 0.55,
                           boxstyle="round,pad=0.05",
                           facecolor=color, edgecolor=color, linewidth=0)
    ax.add_patch(rect)
    ax.text(x + w/2, y + 0.275, label, ha='center', va='center',
            fontsize=11, fontweight='bold', color='white')

def arr(ax, x1, y1, x2, y2, label='', color='#64748B'):
    ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle='->', color=color, lw=2))
    if label:
        mx, my = (x1+x2)/2, (y1+y2)/2
        ax.text(mx + 0.12, my, label, fontsize=7.5, color=color, va='center')

def section_bg(ax, x, y, w, h, fill, edge, title=''):
    rect = FancyBboxPatch((x, y), w, h,
                           boxstyle="round,pad=0.1",
                           facecolor=fill, edgecolor=edge, linewidth=1.5, linestyle='--')
    ax.add_patch(rect)
    if title:
        ax.text(x + 0.18, y + h - 0.05, title, fontsize=8.5,
                color=edge, fontweight='bold', va='top')

# ══════════════════════════════════════════════════════
# TITLE
# ══════════════════════════════════════════════════════
ax.text(12, 31.4, 'SVSU INTELLIGENT — COMPLETE BOT ARCHITECTURE',
        ha='center', va='center', fontsize=18, fontweight='bold', color=C['header'])
ax.text(12, 31.0, 'Full System Flow: Data Ingestion → AI Engine → Voice → 3D Avatar → API → Infrastructure',
        ha='center', va='center', fontsize=10, color=C['gray_b'])
ax.plot([0.5, 23.5], [30.75, 30.75], color=C['gray_b'], lw=1.5, alpha=0.4)

# ══════════════════════════════════════════════════════
# SECTION A — DATA SOURCES & INGESTION (left column top)
# ══════════════════════════════════════════════════════
section_bg(ax, 0.3, 26.5, 7.2, 4.0, '#FFFBEB', C['yellow_b'], '')
section_header(ax, 0.3, 30.05, 7.2, '① DATA INGESTION  (ingest.py / CRAWLER)', C['yellow_b'])

box(ax, 0.7, 28.9, 3.0, 0.85, 'SVSU Website', 'www.svsu.ac.in', C['pink'], C['pink_b'])
box(ax, 4.1, 28.9, 3.0, 0.85, 'PDF Documents', 'Prospectus, Brochures', C['pink'], C['pink_b'])

arr(ax, 2.2, 28.9, 2.2, 28.05)
arr(ax, 5.6, 28.9, 5.6, 28.05)

box(ax, 0.7, 27.1, 6.4, 0.85, 'Document Loaders',
    'WebBaseLoader, PyMuPDFLoader', C['yellow'], C['yellow_b'])

arr(ax, 3.9, 27.1, 3.9, 26.3)

box(ax, 0.7, 26.6, 2.9, 0.6, 'Text Splitter', 'Chunk:1000, Overlap:150', C['yellow'], C['yellow_b'], fontsize=9)
arr(ax, 2.15, 26.6, 3.55, 26.6, '')
box(ax, 3.6, 26.6, 3.5, 0.6, 'Embeddings', 'HuggingFace all-MiniLM-L6-v2', C['yellow'], C['yellow_b'], fontsize=9)

# ══════════════════════════════════════════════════════
# SECTION B — KNOWLEDGE STORE (left mid)
# ══════════════════════════════════════════════════════
section_bg(ax, 0.3, 23.8, 7.2, 2.5, '#F0FDF4', C['green_b'], '')
section_header(ax, 0.3, 25.9, 7.2, '② KNOWLEDGE BASE', C['green_b'])

box(ax, 0.7, 24.85, 2.9, 0.85, 'FAISS Vector DB', 'faiss_db/', C['green'], C['green_b'])
box(ax, 4.1, 24.85, 3.0, 0.85, 'BM25 Index', 'bm25_docs.pkl', C['green'], C['green_b'])
box(ax, 1.2, 23.95, 5.5, 0.65, 'core_facts.txt  — Static SVSU facts', '', C['mint'], C['mint_b'], fontsize=9)

arr(ax, 2.15, 26.6, 2.15, 25.7)
arr(ax, 5.85, 26.6, 5.85, 25.7)

# ══════════════════════════════════════════════════════
# SECTION C — AI CHATBOT ENGINE (center)
# ══════════════════════════════════════════════════════
section_bg(ax, 8.2, 22.5, 7.4, 8.1, '#EFF6FF', C['blue_b'], '')
section_header(ax, 8.2, 30.2, 7.4, '③ AI CHATBOT ENGINE  (chatbot_engine.py)', C['blue_b'])

box(ax, 8.6, 29.1, 6.6, 0.85, 'User Query / Transcribed Text', '', C['blue'], C['blue_b'])
arr(ax, 11.9, 29.1, 11.9, 28.25)

box(ax, 8.6, 27.4, 2.9, 0.75, 'FAISS Retriever', 'k=5 similar chunks', C['blue'], C['blue_b'], fontsize=9)
box(ax, 12.3, 27.4, 3.0, 0.75, 'BM25 Retriever', 'Keyword match', C['blue'], C['blue_b'], fontsize=9)

arr(ax, 11.9, 28.25, 10.05, 28.15)
arr(ax, 11.9, 28.25, 13.8, 28.15)
arr(ax, 10.05, 27.4, 11.3, 26.8)
arr(ax, 13.8, 27.4, 12.5, 26.8)

box(ax, 8.6, 25.9, 6.6, 0.8, 'Re-Rank & Merge Context', 'Combine top-k results', C['cyan'], C['cyan_b'])
arr(ax, 11.9, 25.9, 11.9, 25.1)

box(ax, 8.6, 24.2, 6.6, 0.8, 'Prompt Template', 'Context + core_facts.txt + User Question', C['purple'], C['purple_b'])
arr(ax, 11.9, 24.2, 11.9, 23.4)

box(ax, 8.6, 22.6, 6.6, 0.85, 'Google Gemini LLM', 'gemini-1.5-flash  |  Groq Fallback', C['green'], C['green_b'])

arr(ax, 11.9, 22.6, 11.9, 21.9, 'Response')

# ══════════════════════════════════════════════════════
# SECTION D — BACKEND API (center bottom)
# ══════════════════════════════════════════════════════
section_bg(ax, 8.2, 19.0, 7.4, 2.75, '#F5F3FF', C['purple_b'], '')
section_header(ax, 8.2, 21.4, 7.4, '⑤ BACKEND API  (api_server.py | FastAPI Port 8000)', C['purple_b'])

box(ax, 8.5, 20.35, 1.9, 0.72, 'GET /', 'chatbot.html', C['purple'], C['purple_b'], fontsize=8.5)
box(ax, 10.6, 20.35, 2.2, 0.72, 'GET /talk.html', '3D Talk Mode', C['purple'], C['purple_b'], fontsize=8.5)
box(ax, 13.0, 20.35, 2.3, 0.72, 'GET /admin', 'Admin Login', C['purple'], C['purple_b'], fontsize=8.5)

box(ax, 8.5, 19.2, 2.5, 0.75, 'POST /api/chat', 'Text Chat', C['blue'], C['blue_b'], fontsize=8.5)
box(ax, 11.2, 19.2, 2.5, 0.75, 'POST /api/voice', 'Voice + TTS', C['blue'], C['blue_b'], fontsize=8.5)
box(ax, 13.9, 19.2, 1.5, 0.75, '/assets\n/admin_panel', '', C['gray'], C['gray_b'], fontsize=7.5)

# ══════════════════════════════════════════════════════
# SECTION E — USER INTERFACE (right column top)
# ══════════════════════════════════════════════════════
section_bg(ax, 16.3, 27.0, 7.2, 3.6, '#FFF1F2', C['pink_b'], '')
section_header(ax, 16.3, 30.2, 7.2, '④ USER INTERFACE  (Browser / Mobile)', C['pink_b'])

box(ax, 16.6, 29.1, 6.6, 0.85, '👤 Student / User', 'Chrome / Safari / Edge', C['pink'], C['pink_b'])
arr(ax, 19.9, 29.1, 19.9, 28.25)

box(ax, 16.6, 27.25, 2.9, 0.85, 'chatbot.html', 'Lead Form: Name, Email,\nPhone, College, Course', C['pink'], C['pink_b'], fontsize=9)
box(ax, 20.1, 27.25, 3.0, 0.85, 'talk.html', 'Voice Mode +\n3D Avatar', C['pink'], C['pink_b'], fontsize=9)

arr(ax, 18.05, 29.1, 18.05, 28.1)
arr(ax, 21.6, 29.1, 21.6, 28.1)

# ══════════════════════════════════════════════════════
# SECTION F — VOICE PIPELINE (right mid)
# ══════════════════════════════════════════════════════
section_bg(ax, 16.3, 23.5, 7.2, 3.4, '#ECFDF5', C['mint_b'], '')
section_header(ax, 16.3, 26.5, 7.2, '⑥ VOICE PIPELINE', C['mint_b'])

box(ax, 16.6, 25.45, 2.2, 0.72, '🎤 Microphone', 'getUserMedia()', C['mint'], C['mint_b'], fontsize=8.5)
arr(ax, 17.7, 25.45, 17.7, 24.8)
box(ax, 16.6, 24.0, 2.2, 0.72, 'MediaRecorder', 'audio/webm blob', C['mint'], C['mint_b'], fontsize=8.5)
arr(ax, 17.7, 24.0, 17.7, 23.6, 'POST /api/voice')

box(ax, 19.2, 25.45, 2.0, 0.72, 'Whisper STT', 'Groq API', C['green'], C['green_b'], fontsize=8.5)
arr(ax, 20.2, 25.45, 20.2, 24.75)
box(ax, 19.2, 24.0, 2.0, 0.72, 'Edge-TTS', 'MP3 → Base64', C['green'], C['green_b'], fontsize=8.5)

box(ax, 21.5, 24.75, 1.8, 0.72, 'AudioContext\nPlayback', '', C['cyan'], C['cyan_b'], fontsize=8)

arr(ax, 20.2, 24.0, 21.4, 24.75, 'Audio')

# ══════════════════════════════════════════════════════
# SECTION G — 3D AVATAR ENGINE (right bottom)
# ══════════════════════════════════════════════════════
section_bg(ax, 16.3, 19.0, 7.2, 4.3, '#FEF3C7', C['orange_b'], '')
section_header(ax, 16.3, 22.9, 7.2, '⑦ 3D AVATAR ENGINE  (Three.js r134)', C['orange_b'])

box(ax, 16.6, 21.8, 2.9, 0.75, 'THREE.Scene', 'Camera FOV:45, Near:0.1', C['orange'], C['orange_b'], fontsize=8.5)
arr(ax, 18.05, 21.8, 18.05, 21.2)
box(ax, 16.6, 20.4, 2.9, 0.7, 'GLTFLoader', 'avatar.glb (2.7MB)', C['orange'], C['orange_b'], fontsize=8.5)
arr(ax, 18.05, 20.4, 18.05, 19.7)
box(ax, 16.6, 19.15, 2.9, 0.7, 'Scene.add(model)', 'Auto-center + Camera frame', C['orange'], C['orange_b'], fontsize=8)

box(ax, 20.1, 21.8, 3.1, 0.75, 'Procedural Idle Anim', 'Breathing via spine bone\nHead sway via headBone', C['yellow'], C['yellow_b'], fontsize=8.5)
arr(ax, 21.65, 21.8, 21.65, 21.15)
box(ax, 20.1, 20.4, 3.1, 0.7, 'Web Audio Analyser', 'FFT:256, Freq data', C['yellow'], C['yellow_b'], fontsize=8.5)
arr(ax, 21.65, 20.4, 21.65, 19.75)
box(ax, 20.1, 19.15, 3.1, 0.7, 'Lip Sync', 'Jaw bone + Morph Targets', C['yellow'], C['yellow_b'], fontsize=8)

# ══════════════════════════════════════════════════════
# SECTION H — INFRASTRUCTURE (bottom full width)
# ══════════════════════════════════════════════════════
section_bg(ax, 0.3, 15.8, 23.2, 2.85, '#F8FAFC', C['gray_b'], '')
section_header(ax, 0.3, 18.25, 23.2, '⑧ INFRASTRUCTURE  (Azure VM — Ubuntu 22.04)', C['gray_b'])

boxes_infra = [
    (0.6,  16.2, 3.5, 'Azure VM', '98.70.37.219\nWest US Region'),
    (4.4,  16.2, 3.5, 'Ubuntu Server', '22.04 LTS\nPython 3.10'),
    (8.2,  16.2, 3.5, 'Uvicorn ASGI', 'Port 8000\nnohup background'),
    (12.0, 16.2, 3.5, 'Static Files', '/assets\n/admin_panel'),
    (15.8, 16.2, 3.8, 'API Keys', 'GROQ_API_KEY\nGOOGLE_API_KEY (.env)'),
    (19.9, 16.2, 3.3, 'Auto Restart', 'restart_vm_services.py\nssh + pkill + nohup'),
]
for bx, by, bw, bl, bsl in boxes_infra:
    box(ax, bx, by, bw, 1.7, bl, bsl, C['gray'], C['gray_b'], fontsize=9)
    if bx < 19:
        arr(ax, bx+bw, by+0.85, bx+bw+0.2, by+0.85)

# ══════════════════════════════════════════════════════
# CROSS-SECTION ARROWS (connecting sections)
# ══════════════════════════════════════════════════════
# Data Ingestion → Knowledge Base
arr(ax, 3.9, 26.6, 3.9, 25.85, 'Store vectors')
# Knowledge Base → AI Engine
ax.annotate('', xy=(8.6, 24.2), xytext=(7.2, 24.6),
            arrowprops=dict(arrowstyle='->', color=C['green_b'], lw=2))
ax.text(7.4, 24.75, 'Context', fontsize=8, color=C['green_b'])

# AI Engine → Backend
arr(ax, 11.9, 22.6, 11.9, 21.75, 'Response')

# User UI → Backend
ax.annotate('', xy=(15.5, 20.7), xytext=(16.6, 20.7),
            arrowprops=dict(arrowstyle='<->', color=C['purple_b'], lw=2))
ax.text(14.8, 20.95, 'API\nCalls', fontsize=8, color=C['purple_b'], ha='center')

# Voice Pipeline → Backend
ax.annotate('', xy=(15.5, 19.55), xytext=(16.6, 24.35),
            arrowprops=dict(arrowstyle='->', color=C['mint_b'], lw=1.5,
                            connectionstyle='arc3,rad=0.2'))

# Backend → Infra
arr(ax, 11.9, 19.0, 11.9, 18.65, 'Runs on')

# ══════════════════════════════════════════════════════
# LEGEND
# ══════════════════════════════════════════════════════
ax.text(0.5, 15.5, 'LEGEND:', fontsize=9, fontweight='bold', color=C['text'])
legend_items = [
    (C['yellow'], C['yellow_b'], 'Data Ingestion'),
    (C['green'],  C['green_b'],  'Knowledge Store'),
    (C['blue'],   C['blue_b'],   'AI Engine'),
    (C['pink'],   C['pink_b'],   'User Interface'),
    (C['mint'],   C['mint_b'],   'Voice Pipeline'),
    (C['orange'], C['orange_b'], '3D Avatar Engine'),
    (C['purple'], C['purple_b'], 'Backend API'),
    (C['gray'],   C['gray_b'],   'Infrastructure'),
]
for i, (fc, ec, lbl) in enumerate(legend_items):
    lx = 0.5 + i * 2.9
    rect = FancyBboxPatch((lx, 14.9), 1.0, 0.4, boxstyle="round,pad=0.05",
                           facecolor=fc, edgecolor=ec, linewidth=1.5)
    ax.add_patch(rect)
    ax.text(lx + 1.15, 15.1, lbl, fontsize=8, va='center', color=C['text'])

ax.text(23.5, 14.9, 'SVSU Intelligent v2.0 | 2026', fontsize=8,
        ha='right', va='bottom', color=C['gray_b'], style='italic')

plt.tight_layout(pad=0.5)
plt.savefig(r'c:\Users\USER\Desktop\BOT-SVSU\DESIGN_FLOW\FULL-Bot-FLOW.png',
            dpi=150, bbox_inches='tight', facecolor='#F8F9FA')
print("FULL-Bot-FLOW.png saved!")
plt.close()
