import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch

fig, ax = plt.subplots(1, 1, figsize=(22, 28))
ax.set_xlim(0, 22)
ax.set_ylim(0, 28)
ax.axis('off')
fig.patch.set_facecolor('#F8F9FA')
ax.set_facecolor('#F8F9FA')

C = {
    'pink':     '#F9D0DC', 'pink_b':   '#E91E63',
    'purple':   '#EDE7F6', 'purple_b': '#7C3AED',
    'blue':     '#DBEAFE', 'blue_b':   '#2563EB',
    'green':    '#D1FAE5', 'green_b':  '#059669',
    'yellow':   '#FEF9C3', 'yellow_b': '#D97706',
    'cyan':     '#CFFAFE', 'cyan_b':   '#0891B2',
    'orange':   '#FFEDD5', 'orange_b': '#EA580C',
    'gray':     '#F1F5F9', 'gray_b':   '#64748B',
    'red':      '#FEE2E2', 'red_b':    '#DC2626',
    'mint':     '#ECFDF5', 'mint_b':   '#10B981',
    'indigo':   '#E0E7FF', 'indigo_b': '#4338CA',
    'header':   '#1e293b', 'text':     '#1e293b',
}

def box(ax, x, y, w, h, label, sublabel='', fill=C['blue'], edge=C['blue_b'],
        fontsize=10, subfontsize=8, bold=True):
    rect = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.08",
                           facecolor=fill, edgecolor=edge, linewidth=2)
    ax.add_patch(rect)
    cy = y + h/2 + (0.15 if sublabel else 0)
    ax.text(x+w/2, cy, label, ha='center', va='center',
            fontsize=fontsize, fontweight='bold' if bold else 'normal', color=C['text'])
    if sublabel:
        ax.text(x+w/2, y+h/2-0.18, sublabel, ha='center', va='center',
                fontsize=subfontsize, color=C['gray_b'], style='italic')

def section_bg(ax, x, y, w, h, fill, edge):
    rect = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.1",
                           facecolor=fill, edgecolor=edge, linewidth=1.5, linestyle='--')
    ax.add_patch(rect)

def header(ax, x, y, w, label, color):
    rect = FancyBboxPatch((x, y), w, 0.52, boxstyle="round,pad=0.05",
                           facecolor=color, edgecolor=color)
    ax.add_patch(rect)
    ax.text(x+w/2, y+0.26, label, ha='center', va='center',
            fontsize=11, fontweight='bold', color='white')

def arr(ax, x1, y1, x2, y2, label='', color='#64748B', rad=0):
    style = f'arc3,rad={rad}' if rad else 'arc3,rad=0'
    ax.annotate('', xy=(x2,y2), xytext=(x1,y1),
                arrowprops=dict(arrowstyle='->', color=color, lw=2,
                                connectionstyle=style))
    if label:
        mx, my = (x1+x2)/2+0.1, (y1+y2)/2
        ax.text(mx, my, label, fontsize=7.5, color=color, va='center')

# ──────────────────────────────────────────────────────────────
# TITLE
# ──────────────────────────────────────────────────────────────
ax.text(11, 27.5, 'SVSU INTELLIGENT — COMPLETE ADMIN PANEL ARCHITECTURE',
        ha='center', fontsize=17, fontweight='bold', color=C['header'])
ax.text(11, 27.05, 'Admin Access → Dashboard → Lead Management → Monitoring → Config',
        ha='center', fontsize=9.5, color=C['gray_b'])
ax.plot([0.4, 21.6], [26.8, 26.8], color=C['gray_b'], lw=1.2, alpha=0.4)

# ──────────────────────────────────────────────────────────────
# SECTION 1 — ADMIN ACCESS
# ──────────────────────────────────────────────────────────────
section_bg(ax, 0.3, 24.1, 21.4, 2.4, '#FFF1F2', C['pink_b'])
header(ax, 0.3, 26.1, 21.4, '① ADMIN ACCESS', C['pink_b'])

box(ax, 0.6,  24.5, 2.8, 0.85, '🔐 Admin User', 'Browser Login', C['pink'], C['pink_b'])
arr(ax, 3.4, 24.93, 4.2, 24.93)
box(ax, 4.2,  24.5, 3.4, 0.85, 'admin_login.html', 'Username + Password\nAuth Check', C['pink'], C['pink_b'], fontsize=9)
arr(ax, 7.6, 24.93, 8.4, 24.93, 'Session ✓')
box(ax, 8.4,  24.5, 3.8, 0.85, 'admin_dashboard.html', 'Main Dashboard View', C['indigo'], C['indigo_b'], fontsize=9)
arr(ax, 12.2, 24.93, 13.0, 24.93)
box(ax, 13.0, 24.5, 2.5, 0.85, 'dashboard.html', 'Analytics Page', C['indigo'], C['indigo_b'], fontsize=9)
arr(ax, 15.5, 24.93, 16.2, 24.93)
box(ax, 16.2, 24.5, 2.5, 0.85, 'admin.html', 'Full Admin Panel', C['indigo'], C['indigo_b'], fontsize=9)
arr(ax, 18.7, 24.93, 19.4, 24.93)
box(ax, 19.4, 24.5, 2.0, 0.85, 'chatbot.html', 'Bot Interface', C['pink'], C['pink_b'], fontsize=9)

# ──────────────────────────────────────────────────────────────
# SECTION 2 — DASHBOARD ANALYTICS
# ──────────────────────────────────────────────────────────────
section_bg(ax, 0.3, 20.6, 10.2, 3.2, '#EFF6FF', C['blue_b'])
header(ax, 0.3, 23.4, 10.2, '② ANALYTICS DASHBOARD', C['blue_b'])

kpis = [
    (0.6,  21.95, 'Total Leads', '📊 All-time'),
    (3.0,  21.95, "Today's Inquiries", '📅 Daily count'),
    (5.4,  21.95, 'Course Interests', '🎓 Distribution'),
    (7.8,  21.95, 'Conversion Rate', '✅ % contacted'),
]
for bx, by, bl, bsl in kpis:
    box(ax, bx, by, 2.2, 0.75, bl, bsl, C['blue'], C['blue_b'], fontsize=8.5)

charts = [
    (0.6,  20.8, 3.0, 'Pie Chart', 'Course Distribution'),
    (3.9,  20.8, 3.0, 'Line Chart', 'Daily Inquiries Trend'),
    (7.2,  20.8, 3.0, 'Bar Chart', 'Lead Source Breakdown'),
]
for bx, by, bw, bl, bsl in charts:
    box(ax, bx, by, bw, 0.62, bl, bsl, C['cyan'], C['cyan_b'], fontsize=8.5)

# ──────────────────────────────────────────────────────────────
# SECTION 3 — LEAD MANAGEMENT
# ──────────────────────────────────────────────────────────────
section_bg(ax, 10.8, 20.6, 10.9, 3.2, '#F0FDF4', C['green_b'])
header(ax, 10.8, 23.4, 10.9, '③ LEAD MANAGEMENT', C['green_b'])

box(ax, 11.1, 21.9, 3.2, 0.72, 'chatbot.html Lead Form',
    'Name, Email, Phone, College,\nCourse, Date', C['green'], C['green_b'], fontsize=8.5)
arr(ax, 14.3, 22.25, 15.0, 22.25)
box(ax, 15.0, 21.9, 2.5, 0.72, 'POST /api/leads',
    'FastAPI endpoint', C['mint'], C['mint_b'], fontsize=8.5)
arr(ax, 17.5, 22.25, 18.2, 22.25)
box(ax, 18.2, 21.9, 2.3, 0.72, 'leads.csv',
    'Appended row', C['green'], C['green_b'], fontsize=8.5)

box(ax, 11.1, 20.8, 9.4, 0.62, 'Lead Table: Name | Email | Phone | College | Course | Date | Status | Actions',
    '', C['gray'], C['gray_b'], fontsize=8, bold=False)

actions = ['🔍 Search & Filter', '📥 Export CSV', '✅ Mark Converted', '🗑️ Delete Lead']
for i, a in enumerate(actions):
    bx = 11.1 + i * 2.5
    box(ax, bx, 20.75, 2.3, 0.0, '', '', C['gray'], C['gray_b'])
    ax.text(bx+1.15, 20.75, a, ha='center', fontsize=7.5, color=C['gray_b'])

# ──────────────────────────────────────────────────────────────
# SECTION 4 — ADMIN BACKEND (Express.js)
# ──────────────────────────────────────────────────────────────
section_bg(ax, 0.3, 17.1, 10.2, 3.2, '#FEF3C7', C['yellow_b'])
header(ax, 0.3, 19.9, 10.2, '④ ADMIN BACKEND  (server.js — Express.js Port 3000)', C['yellow_b'])

routes = [
    (0.6,  18.15, 'GET /dashboard', 'Serve HTML'),
    (3.0,  18.15, 'GET /api/leads', 'Read leads.csv'),
    (5.4,  18.15, 'POST /api/leads', 'Append new lead'),
    (7.8,  18.15, 'Proxy → :8000', 'Forward to FastAPI'),
]
for bx, by, bl, bsl in routes:
    box(ax, bx, by, 2.2, 0.72, bl, bsl, C['yellow'], C['yellow_b'], fontsize=8.5)

deps = [
    (0.6,  17.3, 'express', 'HTTP server framework'),
    (3.0,  17.3, 'cors', 'Cross-origin support'),
    (5.4,  17.3, 'csv-parser', 'Read leads.csv'),
    (7.8,  17.3, 'fs module', 'File read/write'),
]
for bx, by, bl, bsl in deps:
    box(ax, bx, by, 2.2, 0.62, bl, bsl, C['orange'], C['orange_b'], fontsize=8.5)

# ──────────────────────────────────────────────────────────────
# SECTION 5 — CHATBOT CONFIG
# ──────────────────────────────────────────────────────────────
section_bg(ax, 10.8, 17.1, 10.9, 3.2, '#F5F3FF', C['purple_b'])
header(ax, 10.8, 19.9, 10.9, '⑤ CHATBOT CONFIGURATION PANEL', C['purple_b'])

configs = [
    (11.1, 18.15, 'Knowledge Base Status', 'FAISS Index + BM25 loaded'),
    (14.2, 18.15, 'Model Config', 'gemini-1.5-flash | Groq Whisper'),
    (17.3, 18.15, 'API Key Status', 'Groq ✓ | Google ✓'),
]
for bx, by, bl, bsl in configs:
    box(ax, bx, by, 2.9, 0.72, bl, bsl, C['purple'], C['purple_b'], fontsize=8.5)

config2 = [
    (11.1, 17.3, 'FAISS Vectors', 'Document chunks count'),
    (14.2, 17.3, 'BM25 Docs', 'bm25_docs.pkl size'),
    (17.3, 17.3, 'core_facts.txt', 'Static SVSU facts'),
]
for bx, by, bl, bsl in config2:
    box(ax, bx, by, 2.9, 0.62, bl, bsl, C['indigo'], C['indigo_b'], fontsize=8.5)

# ──────────────────────────────────────────────────────────────
# SECTION 6 — DEPLOYMENT MONITORING
# ──────────────────────────────────────────────────────────────
section_bg(ax, 0.3, 13.6, 21.4, 3.2, '#F8FAFC', C['gray_b'])
header(ax, 0.3, 16.4, 21.4, '⑥ DEPLOYMENT & MONITORING  (Azure VM: 98.70.37.219)', C['gray_b'])

monitors = [
    (0.6,  14.0, 3.5, 'VM Status', 'Azure West US\nUbuntu 22.04 LTS'),
    (4.4,  14.0, 3.5, 'FastAPI Service', 'Port 8000 ✓\nUvicorn running'),
    (8.2,  14.0, 3.5, 'Node.js Server', 'Port 3000 ✓\nAdmin backend'),
    (12.0, 14.0, 3.5, 'Log Viewer', 'api.log\nerror.log'),
    (15.8, 14.0, 3.5, 'Restart Control', 'restart_vm_services.py\npkill + nohup'),
    (19.6, 14.0, 1.8, 'SSH Access', 'Paramiko\nSSH deploy'),
]
for bx, by, bw, bl, bsl in monitors:
    box(ax, bx, by, bw, 1.7, bl, bsl, C['gray'], C['gray_b'], fontsize=9)

# ──────────────────────────────────────────────────────────────
# SECTION 7 — DATA FLOW SUMMARY
# ──────────────────────────────────────────────────────────────
section_bg(ax, 0.3, 10.8, 21.4, 2.55, '#FFFBEB', C['orange_b'])
header(ax, 0.3, 12.95, 21.4, '⑦ STUDENT → LEAD DATA FLOW', C['orange_b'])

flow = [
    '👤 Student visits\nwebsite',
    '💬 Fills Lead Form\n(chatbot.html)',
    '📡 POST /api/leads\n(FastAPI)',
    '💾 Saved to\nleads.csv',
    '📊 Admin Dashboard\nupdates',
    '📞 Admin contacts\nstudent',
    '✅ Lead converted\n(Status updated)',
]
for i, step in enumerate(flow):
    bx = 0.6 + i * 3.05
    fill = [C['pink'], C['blue'], C['purple'], C['green'],
            C['cyan'], C['yellow'], C['mint']][i]
    edge = [C['pink_b'], C['blue_b'], C['purple_b'], C['green_b'],
            C['cyan_b'], C['yellow_b'], C['mint_b']][i]
    box(ax, bx, 11.15, 2.7, 1.55, step, '', fill, edge, fontsize=8.5)
    if i < len(flow)-1:
        arr(ax, bx+2.7, 11.93, bx+2.7+0.3, 11.93, color=C['gray_b'])

# ──────────────────────────────────────────────────────────────
# TECH STACK FOOTER
# ──────────────────────────────────────────────────────────────
ax.plot([0.4, 21.6], [10.55, 10.55], color=C['gray_b'], lw=1, alpha=0.4)
ax.text(0.5, 10.3, 'TECH STACK:', fontsize=9, fontweight='bold', color=C['header'])
tech = [
    (C['blue'],   C['blue_b'],   'HTML5 + CSS3 + Vanilla JS'),
    (C['yellow'], C['yellow_b'], 'Express.js (Node.js)'),
    (C['green'],  C['green_b'],  'FastAPI (Python)'),
    (C['orange'], C['orange_b'], 'CSV File Storage'),
    (C['cyan'],   C['cyan_b'],   'Azure VM Hosting'),
    (C['purple'], C['purple_b'], 'FAISS + BM25 + Gemini'),
]
for i, (fc, ec, lbl) in enumerate(tech):
    lx = 0.5 + i * 3.5
    rect = FancyBboxPatch((lx, 9.75), 1.0, 0.38, boxstyle="round,pad=0.04",
                           facecolor=fc, edgecolor=ec, linewidth=1.5)
    ax.add_patch(rect)
    ax.text(lx+1.12, 9.94, lbl, fontsize=8, va='center', color=C['text'])

ax.text(21.5, 9.75, 'SVSU Intelligent v2.0 | 2026',
        fontsize=8, ha='right', color=C['gray_b'], style='italic')

# ──────────────────────────────────────────────────────────────
# CONNECTING ARROWS BETWEEN SECTIONS
# ──────────────────────────────────────────────────────────────
# Access → Analytics
arr(ax, 8.4, 24.5, 5.5, 23.95, 'View', C['blue_b'])
# Access → Lead Mgmt
arr(ax, 19.4, 24.5, 17.0, 23.95, 'Manage', C['green_b'])
# Analytics → Admin Backend
arr(ax, 5.4, 20.6, 5.4, 20.3)
# Lead Mgmt → Admin Backend
arr(ax, 16.25, 20.6, 15.0, 20.3)
# Admin Backend → Monitoring
arr(ax, 5.4, 17.1, 5.4, 16.95)
# Config → Monitoring
arr(ax, 16.25, 17.1, 15.0, 16.95)
# Monitoring → Data Flow
arr(ax, 11.0, 13.6, 11.0, 13.35)

plt.tight_layout(pad=0.5)
plt.savefig(r'c:\Users\USER\Desktop\BOT-SVSU\DESIGN_FLOW\FULL-ADMIN-FLOW.png',
            dpi=150, bbox_inches='tight', facecolor='#F8F9FA')
print("FULL-ADMIN-FLOW.png saved!")
plt.close()
