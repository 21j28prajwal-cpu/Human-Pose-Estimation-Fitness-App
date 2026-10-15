import streamlit as st
import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import sqlite3
import os
from hashlib import sha256
from datetime import datetime, timedelta
import math  # Add this import
import time
import json

# Import our enhanced backend
import backend as be

# For older MediaPipe versions, try this alternative
try:
    # Try the standard import first
    mp_pose = mp.solutions.pose
    mp_drawing = mp.solutions.drawing_utils
except AttributeError:
    # If that fails, we'll need to use a different approach
    print("Using alternative MediaPipe import method")
    # For now, we'll create placeholder objects
    # You'll need to update the pose detection logic
    mp_pose = None
    mp_drawing = None

# Initialize MediaPipe Pose with error handling
if mp_pose is not None:
    pose = mp_pose.Pose(static_image_mode=False, min_detection_confidence=0.5, min_tracking_confidence=0.5)
else:
    pose = None
    st.warning("MediaPipe Pose module not available. Some features may be limited.")

# For older MediaPipe versions, try this alternative
try:
    # Try the standard import first
    mp_pose = mp.solutions.pose
    mp_drawing = mp.solutions.drawing_utils
except AttributeError:
    # If that fails, we'll need to use a different approach
    print("Using alternative MediaPipe import method")
    # For now, we'll create placeholder objects
    # You'll need to update the pose detection logic
    mp_pose = None
    mp_drawing = None

# Initialize MediaPipe Pose with error handling
if mp_pose is not None:
    pose = mp_pose.Pose(static_image_mode=False, min_detection_confidence=0.5, min_tracking_confidence=0.5)
else:
    pose = None
    st.warning("MediaPipe Pose module not available. Some features may be limited.")

# Database Configuration
DB_PATH = os.path.join(os.path.dirname(__file__), "users.db")

def initialize_database():
    """Initialize the database with secure tables"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            salt TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP
        )
        ''')
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY,
            user_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
        ''')

        # New tables for enhanced features
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE,
            display_name TEXT,
            bio TEXT DEFAULT '',
            avatar_emoji TEXT DEFAULT '🧘',
            fitness_goal TEXT DEFAULT 'Stay Healthy',
            preferred_theme TEXT DEFAULT 'light',
            total_workouts INTEGER DEFAULT 0,
            total_minutes REAL DEFAULT 0.0,
            streak_days INTEGER DEFAULT 0,
            last_workout_date TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
        ''')

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS workout_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            workout_type TEXT NOT NULL,
            workout_name TEXT NOT NULL,
            duration_seconds REAL DEFAULT 0,
            reps INTEGER DEFAULT 0,
            calories_burned REAL DEFAULT 0,
            pose_accuracy REAL DEFAULT 0,
            notes TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
        ''')

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS analytics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            metric_name TEXT NOT NULL,
            metric_value REAL NOT NULL,
            metric_unit TEXT DEFAULT '',
            category TEXT DEFAULT 'general',
            recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS achievements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            badge_name TEXT NOT NULL,
            badge_icon TEXT NOT NULL,
            description TEXT,
            earned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
        ''')
        
        conn.commit()
    except sqlite3.Error as e:
        st.error(f"Database initialization error: {e}")
    finally:
        if conn:
            conn.close()

def get_db_connection():
    """Get a secure database connection"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def hash_password(password, salt=None):
    """Hash password with salt using SHA-256"""
    salt = salt or os.urandom(16).hex()
    return sha256((password + salt).encode()).hexdigest(), salt


# ═══════════════════════════════════════════════════════════════
# DARK MODE CSS
# ═══════════════════════════════════════════════════════════════

DARK_MODE_CSS = """
    :root {
        --primary-color: #818cf8;
        --secondary-color: #a78bfa;
        --accent-color: #22d3ee;
        --background-color: #0f172a;
        --surface-color: rgba(30, 41, 59, 0.85);
        --text-primary: #f1f5f9;
        --text-secondary: #94a3b8;
        --success-color: #34d399;
        --danger-color: #f87171;
        --border-color: rgba(148, 163, 184, 0.15);
        --shadow-sm: 0 4px 10px rgba(0,0,0,0.3);
        --shadow-md: 0 10px 25px rgba(0,0,0,0.4);
        --shadow-lg: 0 18px 40px rgba(0,0,0,0.5);
        --glass-bg: rgba(30, 41, 59, 0.6);
        --glass-border: rgba(148, 163, 184, 0.12);
    }

    .stApp {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #0f172a 100%) !important;
    }

    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1e1b4b, #312e81) !important;
    }

    .dark-title {
        background: linear-gradient(135deg, #6366f1, #8b5cf6) !important;
    }

    .exercise-card, .exercise-title {
        background: var(--surface-color) !important;
        border: 1px solid var(--glass-border) !important;
        backdrop-filter: blur(16px) !important;
        -webkit-backdrop-filter: blur(16px) !important;
    }

    .exercise-card h4 {
        color: var(--accent-color) !important;
    }

    .exercise-card p, .exercise-title h3 {
        color: var(--text-primary) !important;
    }

    .stTextInput input, .stTextArea textarea {
        background: rgba(30, 41, 59, 0.8) !important;
        border-color: var(--glass-border) !important;
        color: var(--text-primary) !important;
    }

    .stSelectbox div[data-baseweb="select"] > div {
        background: rgba(30, 41, 59, 0.8) !important;
        border-color: var(--glass-border) !important;
        color: var(--text-primary) !important;
    }

    div[role="radiogroup"] {
        background: var(--surface-color) !important;
        border-color: var(--glass-border) !important;
    }

    .stButton > button {
        background: linear-gradient(135deg, #6366f1, #8b5cf6) !important;
    }

    .stButton > button:hover {
        background: linear-gradient(135deg, #4f46e5, #7c3aed) !important;
    }

    /* Glass metric cards */
    .glass-card {
        background: rgba(30, 41, 59, 0.6) !important;
        backdrop-filter: blur(16px) !important;
        -webkit-backdrop-filter: blur(16px) !important;
        border: 1px solid rgba(148, 163, 184, 0.12) !important;
    }

    .stMetric {
        background: rgba(30, 41, 59, 0.6) !important;
        border-radius: 18px !important;
        padding: 12px !important;
        border: 1px solid rgba(148, 163, 184, 0.12) !important;
    }

    /* Fix text colors in dark mode */
    .stMarkdown, .stMarkdown p, .stMarkdown li, .stMarkdown h1,
    .stMarkdown h2, .stMarkdown h3, .stMarkdown h4, label, span {
        color: var(--text-primary) !important;
    }
"""


def set_page_config():
    st.set_page_config(
        page_title="Human Pose Estimation",
        page_icon="💪",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # Check dark mode preference
    dark_mode = st.session_state.get('dark_mode', False)

    st.markdown("""
    <style>

    /* =========================================================
       IMPORT FONT
    ========================================================= */

    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700;800&display=swap');
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

    /* =========================================================
       ROOT VARIABLES
    ========================================================= */

    :root {

        --primary-color: #2563eb;
        --secondary-color: #7c3aed;
        --accent-color: #06b6d4;

        --background-color: #f4f7fb;
        --surface-color: #ffffff;

        --text-primary: #111827;
        --text-secondary: #6b7280;

        --success-color: #16a34a;
        --danger-color: #dc2626;

        --border-color: #e5e7eb;

        --shadow-sm: 0 4px 10px rgba(0,0,0,0.05);
        --shadow-md: 0 10px 25px rgba(0,0,0,0.08);
        --shadow-lg: 0 18px 40px rgba(0,0,0,0.12);

        --radius-sm: 12px;
        --radius-md: 18px;
        --radius-lg: 28px;

        --transition: all 0.3s ease;

        --glass-bg: rgba(255, 255, 255, 0.7);
        --glass-border: rgba(255, 255, 255, 0.3);
    }

    /* =========================================================
       GLOBAL STYLES
    ========================================================= */

    html,
    body,
    [class*="css"] {
        font-family: 'Inter', 'Poppins', sans-serif;
    }

    body {
        background: var(--background-color);
    }

    .stApp {
        background:
            linear-gradient(
                135deg,
                #f4f7fb 0%,
                #eef4ff 35%,
                #f8fbff 100%
            );
        color: var(--text-primary);
    }

    /* =========================================================
       REMOVE STREAMLIT DEFAULTS
    ========================================================= */

    #MainMenu,
    footer,
    header {
        visibility: hidden;
    }

    /* =========================================================
       SIDEBAR
    ========================================================= */

    section[data-testid="stSidebar"] {
        background: linear-gradient(
            180deg,
            #2563eb,
            #4f46e5
        );
        border-right: none;
        padding-top: 20px;
    }

    section[data-testid="stSidebar"] * {
        color: white;
    }

    /* =========================================================
       MAIN TITLE
    ========================================================= */

    .dark-title {
        background:
            linear-gradient(
                135deg,
                #2563eb,
                #7c3aed
            );
        border-radius: var(--radius-lg);
        padding: 35px;
        margin-bottom: 30px;
        box-shadow: var(--shadow-lg);
        position: relative;
        overflow: hidden;
    }

    .dark-title::before {
        content: '';
        position: absolute;
        top: -50%;
        left: -50%;
        width: 200%;
        height: 200%;
        background: radial-gradient(circle, rgba(255,255,255,0.1) 0%, transparent 70%);
        animation: shimmer 6s ease-in-out infinite;
    }

    @keyframes shimmer {
        0%, 100% { transform: translate(0, 0); }
        50% { transform: translate(20%, 20%); }
    }

    .dark-title h1 {
        margin: 0;
        color: white;
        font-size: clamp(2.2rem, 5vw, 4rem);
        font-weight: 800;
        text-align: center;
        letter-spacing: -1px;
        position: relative;
        z-index: 1;
    }

    /* =========================================================
       SECTION HEADER
    ========================================================= */

    .exercise-title {
        background: white;
        border-left: 6px solid var(--primary-color);
        border-radius: var(--radius-md);
        padding: 18px 24px;
        margin-bottom: 20px;
        box-shadow: var(--shadow-sm);
    }

    .exercise-title h3 {
        margin: 0;
        color: var(--text-primary);
        font-size: 1.3rem;
        font-weight: 700;
    }

    /* =========================================================
       CARDS
    ========================================================= */

    .exercise-card {
        background: white;
        border-radius: var(--radius-lg);
        padding: 30px;
        margin-bottom: 30px;
        border: 1px solid var(--border-color);
        box-shadow: var(--shadow-md);
        transition: var(--transition);
    }

    .exercise-card:hover {
        transform: translateY(-4px);
        box-shadow: 0 20px 40px rgba(37,99,235,0.12);
    }

    .exercise-card h4 {
        margin-bottom: 10px;
        color: var(--primary-color);
        font-size: 1.6rem;
        font-weight: 700;
    }

    .exercise-card p {
        color: var(--text-secondary);
        font-size: 1rem;
        line-height: 1.7;
    }

    /* =========================================================
       GLASS MORPHISM CARDS (NEW)
    ========================================================= */

    .glass-card {
        background: var(--glass-bg);
        backdrop-filter: blur(16px);
        -webkit-backdrop-filter: blur(16px);
        border-radius: var(--radius-lg);
        padding: 28px;
        margin-bottom: 20px;
        border: 1px solid var(--glass-border);
        box-shadow: var(--shadow-md);
        transition: var(--transition);
    }

    .glass-card:hover {
        transform: translateY(-3px);
        box-shadow: var(--shadow-lg);
    }

    .glass-card h3 {
        margin: 0 0 8px 0;
        font-weight: 700;
        font-size: 1.1rem;
    }

    .glass-card .metric-value {
        font-size: 2.4rem;
        font-weight: 800;
        background: linear-gradient(135deg, #2563eb, #7c3aed);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }

    .glass-card .metric-label {
        font-size: 0.85rem;
        color: var(--text-secondary);
        margin-top: 4px;
    }

    /* =========================================================
       STAT BADGE (NEW)
    ========================================================= */

    .stat-badge {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        background: linear-gradient(135deg, rgba(37,99,235,0.1), rgba(124,58,237,0.1));
        border: 1px solid rgba(37,99,235,0.2);
        border-radius: 50px;
        padding: 8px 18px;
        font-size: 0.9rem;
        font-weight: 600;
        margin: 4px;
        transition: var(--transition);
    }

    .stat-badge:hover {
        transform: scale(1.05);
        box-shadow: 0 4px 12px rgba(37,99,235,0.15);
    }

    /* =========================================================
       ACHIEVEMENT CARD (NEW)
    ========================================================= */

    .achievement-card {
        background: linear-gradient(135deg, rgba(255,215,0,0.08), rgba(255,165,0,0.08));
        border: 1px solid rgba(255,215,0,0.3);
        border-radius: var(--radius-md);
        padding: 16px 20px;
        margin: 8px 0;
        display: flex;
        align-items: center;
        gap: 14px;
        transition: var(--transition);
    }

    .achievement-card:hover {
        transform: translateX(5px);
        box-shadow: 0 4px 15px rgba(255,215,0,0.15);
    }

    .achievement-icon {
        font-size: 2rem;
    }

    .achievement-info h4 {
        margin: 0;
        font-size: 1rem;
        font-weight: 700;
        color: var(--text-primary);
    }

    .achievement-info p {
        margin: 2px 0 0 0;
        font-size: 0.8rem;
        color: var(--text-secondary);
    }

    /* =========================================================
       COST CARD (NEW)
    ========================================================= */

    .cost-breakdown {
        background: var(--glass-bg);
        backdrop-filter: blur(12px);
        border-radius: var(--radius-lg);
        padding: 28px;
        border: 1px solid var(--glass-border);
        box-shadow: var(--shadow-md);
    }

    .cost-row {
        display: flex;
        justify-content: space-between;
        padding: 10px 0;
        border-bottom: 1px solid var(--border-color);
        font-size: 0.95rem;
    }

    .cost-row:last-child {
        border-bottom: none;
    }

    .cost-total {
        display: flex;
        justify-content: space-between;
        padding: 14px 0;
        font-size: 1.3rem;
        font-weight: 800;
        border-top: 2px solid var(--primary-color);
        margin-top: 10px;
        background: linear-gradient(135deg, #2563eb, #7c3aed);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }

    /* =========================================================
       PROFILE AVATAR (NEW)
    ========================================================= */

    .profile-avatar {
        width: 120px;
        height: 120px;
        border-radius: 50%;
        background: linear-gradient(135deg, #2563eb, #7c3aed);
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 3.5rem;
        margin: 0 auto 20px auto;
        box-shadow: 0 8px 30px rgba(37,99,235,0.3);
        border: 4px solid rgba(255,255,255,0.4);
        animation: float 3s ease-in-out infinite;
    }

    @keyframes float {
        0%, 100% { transform: translateY(0px); }
        50% { transform: translateY(-8px); }
    }

    /* =========================================================
       COUNTER DISPLAY
    ========================================================= */

    .counter-display {
        background:
            linear-gradient(
                135deg,
                #06b6d4,
                #2563eb
            );
        color: white;
        padding: 35px;
        border-radius: var(--radius-lg);
        text-align: center;
        font-size: clamp(2rem, 5vw, 4rem);
        font-weight: 800;
        margin-bottom: 30px;
        box-shadow:
            0 20px 40px rgba(37,99,235,0.25);
    }

    /* =========================================================
       BUTTONS
    ========================================================= */

    .stButton > button {
        width: 100%;
        min-height: 54px;
        border: none;
        border-radius: var(--radius-md);
        background:
            linear-gradient(
                135deg,
                #2563eb,
                #7c3aed
            );
        color: white;
        font-size: 1rem;
        font-weight: 700;
        transition: var(--transition);
        box-shadow:
            0 10px 20px rgba(37,99,235,0.18);
    }

    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow:
            0 16px 30px rgba(37,99,235,0.25);
        background:
            linear-gradient(
                135deg,
                #1d4ed8,
                #6d28d9
            );
    }

    .stButton > button:active {
        transform: scale(0.98);
    }

    .stButton > button:focus {
        outline: 3px solid rgba(37,99,235,0.2);
    }

    /* =========================================================
       INPUT FIELDS
    ========================================================= */

    .stTextInput input {
        background: white;
        border: 2px solid var(--border-color);
        border-radius: var(--radius-md);
        min-height: 54px;
        padding: 0 16px;
        color: var(--text-primary);
        transition: var(--transition);
    }

    .stTextInput input:hover {
        border-color: #93c5fd;
    }

    .stTextInput input:focus {
        border-color: var(--primary-color);
        box-shadow:
            0 0 0 4px rgba(37,99,235,0.12);
    }

    /* =========================================================
       SELECT BOX
    ========================================================= */

    .stSelectbox div[data-baseweb="select"] > div {
        background: white;
        border: 2px solid var(--border-color);
        border-radius: var(--radius-md);
        min-height: 54px;
        transition: var(--transition);
    }

    .stSelectbox div[data-baseweb="select"] > div:hover {
        border-color: #93c5fd;
    }

    /* =========================================================
       RADIO BUTTONS
    ========================================================= */

    div[role="radiogroup"] {
        background: white;
        padding: 14px;
        border-radius: var(--radius-md);
        border: 1px solid var(--border-color);
        box-shadow: var(--shadow-sm);
    }

    /* =========================================================
       WEBCAM CONTAINER
    ========================================================= */

    .webcam-container {
        background: white;
        padding: 20px;
        border-radius: var(--radius-lg);
        border: 1px solid var(--border-color);
        box-shadow: var(--shadow-lg);
        margin-top: 25px;
    }

    /* =========================================================
       FEEDBACK BOX
    ========================================================= */

    .pose-feedback {
        padding: 18px;
        border-radius: var(--radius-md);
        text-align: center;
        font-size: 1.2rem;
        font-weight: 700;
        margin-top: 20px;
        background: #ffffff;
        border: 2px solid #dbeafe;
        box-shadow: var(--shadow-sm);
    }

    .feedback-good {
        color: var(--success-color);
    }

    .feedback-warning {
        color: #d97706;
    }

    .feedback-bad {
        color: var(--danger-color);
    }

    /* =========================================================
       SUCCESS / ERROR ALERTS
    ========================================================= */

    .stSuccess {
        background: #dcfce7;
        border-radius: var(--radius-md);
        color: #166534;
    }

    .stError {
        background: #fee2e2;
        border-radius: var(--radius-md);
        color: #991b1b;
    }

    /* =========================================================
       RESPONSIVE DESIGN
    ========================================================= */

    @media (max-width: 768px) {
        .dark-title {
            padding: 25px;
        }
        .exercise-card {
            padding: 20px;
        }
        .counter-display {
            padding: 25px;
        }
        .stButton > button {
            min-height: 50px;
        }
    }

    /* =========================================================
       SCROLLBAR
    ========================================================= */

    ::-webkit-scrollbar {
        width: 10px;
    }

    ::-webkit-scrollbar-track {
        background: #e5e7eb;
    }

    ::-webkit-scrollbar-thumb {
        background:
            linear-gradient(
                #2563eb,
                #7c3aed
            );
        border-radius: 20px;
    }

    /* =========================================================
       PULSE ANIMATION (NEW)
    ========================================================= */

    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.7; }
    }

    .pulse {
        animation: pulse 2s ease-in-out infinite;
    }

    /* =========================================================
       FADE IN ANIMATION (NEW)
    ========================================================= */

    @keyframes fadeInUp {
        from { opacity: 0; transform: translateY(20px); }
        to { opacity: 1; transform: translateY(0); }
    }

    .fade-in {
        animation: fadeInUp 0.6s ease-out forwards;
    }

    </style>
    """, unsafe_allow_html=True)

    # Apply dark mode CSS if enabled
    if dark_mode:
        st.markdown(f"<style>{DARK_MODE_CSS}</style>", unsafe_allow_html=True)

def calculate_angle(a, b, c):
    """Calculate angle between three points"""
    ang = math.degrees(math.atan2(c.y - b.y, c.x - b.x) - math.atan2(a.y - b.y, a.x - b.x))
    return ang + 360 if ang < 0 else ang

def calculate_distance(a, b):
    """Calculate Euclidean distance between two points"""
    return math.sqrt((a.x - b.x)**2 + (a.y - b.y)**2)

def authenticate_user(username, password):
    """Secure user authentication with hashed passwords"""
    try:
        conn = get_db_connection()
        user = conn.execute(
            "SELECT * FROM users WHERE username = ?", 
            (username,)
        ).fetchone()
        
        if user:
            input_hash = sha256((password + user['salt']).encode()).hexdigest()
            if input_hash == user['password_hash']:
                conn.execute(
                    "UPDATE users SET last_login = ? WHERE id = ?",
                    (datetime.now(), user['id'])
                )
                conn.commit()
                return True
        return False
    except sqlite3.Error as e:
        st.error(f"Authentication error: {e}")
        return False
    finally:
        if conn:
            conn.close()

def register_user(username, password):
    """Secure user registration with password hashing"""
    try:
        conn = get_db_connection()
        
        if conn.execute(
            "SELECT 1 FROM users WHERE username = ?", 
            (username,)
        ).fetchone():
            return False
            
        password_hash, salt = hash_password(password)
        
        conn.execute(
            "INSERT INTO users (username, password_hash, salt) VALUES (?, ?, ?)",
            (username, password_hash, salt)
        )
        user_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

        # Create default profile
        conn.execute(
            "INSERT OR IGNORE INTO user_profiles (user_id, display_name) VALUES (?, ?)",
            (user_id, username)
        )
        conn.commit()
        return True
    except sqlite3.Error as e:
        st.error(f"Registration error: {e}")
        return False
    finally:
        if conn:
            conn.close()

def users_exist():
    """Check if any users exist in database"""
    try:
        conn = get_db_connection()
        return conn.execute("SELECT 1 FROM users").fetchone() is not None
    except sqlite3.Error:
        return False
    finally:
        if conn:
            conn.close()


# ═══════════════════════════════════════════════════════════════
# SIDEBAR NAVIGATION (NEW)
# ═══════════════════════════════════════════════════════════════

def render_sidebar():
    """Render the enhanced sidebar with navigation and dark mode toggle."""
    with st.sidebar:
        # User avatar and greeting
        user_id = be.get_user_id(st.session_state.username)
        profile = be.get_user_profile(user_id) if user_id else None
        avatar = profile['avatar_emoji'] if profile else '🧘'
        display = profile['display_name'] if profile and profile['display_name'] else st.session_state.username

        st.markdown(f"""
        <div style="text-align:center; padding: 20px 0;">
            <div style="font-size:3rem; margin-bottom:8px;">{avatar}</div>
            <div style="font-size:1.2rem; font-weight:700;">{display}</div>
            <div style="font-size:0.8rem; opacity:0.8;">Welcome back!</div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("---")

        # Dark mode toggle
        dark = st.toggle("🌙 Dark Mode", value=st.session_state.get('dark_mode', False), key="dark_toggle")
        if dark != st.session_state.get('dark_mode', False):
            st.session_state.dark_mode = dark
            # Save preference to DB
            if user_id:
                be.update_user_profile(user_id, preferred_theme='dark' if dark else 'light')
            st.rerun()

        st.markdown("---")

        # Navigation
        nav = st.radio(
            "📍 Navigation",
            ["🏋️ Workout", "👤 Profile", "📊 Dashboard", "💰 Cost Estimator", "🏆 Achievements"],
            key="nav_radio"
        )

        st.markdown("---")

        # Quick stats
        if profile:
            st.markdown(f"""
            <div style="padding: 10px; opacity: 0.9;">
                <div style="font-size:0.8rem; font-weight:600; margin-bottom:8px;">📈 Quick Stats</div>
                <div style="font-size:0.75rem;">🏋️ Workouts: {profile.get('total_workouts', 0)}</div>
                <div style="font-size:0.75rem;">⏱️ Minutes: {round(profile.get('total_minutes', 0), 1)}</div>
                <div style="font-size:0.75rem;">🔥 Streak: {profile.get('streak_days', 0)} days</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("---")

        # Logout button
        if st.button("🚪 Logout", key="sidebar_logout"):
            # Save workout if in progress
            _save_current_workout()
            st.session_state.logged_in = False
            st.session_state.username = None
            st.success("Logged out!")
            st.rerun()

    return nav


def _save_current_workout():
    """Save current workout data before logout."""
    user_id = be.get_user_id(st.session_state.get('username', ''))
    if not user_id:
        return

    # Save exercise data if any
    counter = st.session_state.get('counter', 0)
    total_time = st.session_state.get('total_exercise_time', 0)
    if counter > 0 or total_time > 0:
        be.save_workout(
            user_id=user_id,
            workout_type='Exercise',
            workout_name=st.session_state.get('current_exercise', 'Unknown'),
            duration_seconds=total_time,
            reps=counter,
            calories_burned=counter * 5,
        )

    # Save yoga data if any
    yoga_time = st.session_state.get('yoga_total_time', 0)
    if yoga_time > 0:
        be.save_workout(
            user_id=user_id,
            workout_type='Yoga',
            workout_name=st.session_state.get('current_yoga_pose', 'Unknown'),
            duration_seconds=yoga_time,
            reps=0,
            calories_burned=yoga_time * 0.06,
        )


# ═══════════════════════════════════════════════════════════════
# LOGIN & REGISTER PAGES
# ═══════════════════════════════════════════════════════════════

def login_page():
    """Login page with secure authentication"""
    st.markdown('<div class="dark-title"><h1>Welcome to Human Pose Estimation 🏋️</h1></div>', unsafe_allow_html=True)
    st.markdown("---")
    
    with st.container():
        col1, col2 = st.columns([1, 2])
        with col1:
            st.image("https://deeplobe.ai/wp-content/uploads/2023/04/Deeplobe-Pose-Detection-Yoga-Image-1024x683.png", 
                    width=300)
        with col2:
            st.markdown('<div class="exercise-title"><h3>Login to Your Account</h3></div>', unsafe_allow_html=True)
            username = st.text_input("👤 Username")
            password = st.text_input("🔒 Password", type="password")
            
            if st.button("Login", key="login_btn"):
                if authenticate_user(username, password):
                    st.session_state.logged_in = True
                    st.session_state.username = username

                    # Load theme preference
                    uid = be.get_user_id(username)
                    if uid:
                        prof = be.get_user_profile(uid)
                        if prof:
                            st.session_state.dark_mode = (prof.get('preferred_theme', 'light') == 'dark')

                    st.success("Logged in successfully!")
                    st.rerun()
                else:
                    st.error("Invalid credentials. Please try again.")
            
            st.markdown("---")
            st.markdown("Don't have an account?")
            if st.button("Register Now", key="go_to_register"):
                st.session_state.register_mode = True
                st.rerun()

def register_page():
    """Secure user registration page"""
    st.markdown('<div class="dark-title"><h1>Create Your Account 🏆</h1></div>', unsafe_allow_html=True)
    st.markdown("---")
    
    with st.container():
        col1, col2 = st.columns([1, 2])
        with col1:
            st.image("https://images.unsplash.com/photo-1545205597-3d9d02c29597?w=500", 
                    width=300)
        with col2:
            st.markdown('<div class="exercise-title"><h3>Account Registration</h3></div>', unsafe_allow_html=True)
            username = st.text_input("👤 Choose a username")
            password = st.text_input("🔒 Choose a password", type="password")
            confirm_password = st.text_input("🔒 Confirm password", type="password")
            
            if st.button("Register", key="register_btn"):
                if password != confirm_password:
                    st.error("Passwords don't match!")
                elif len(password) < 8:
                    st.error("Password must be at least 8 characters")
                elif register_user(username, password):
                    st.success("Account created! Please login.")
                    st.session_state.register_mode = False
                    st.rerun()
                else:
                    st.error("Username already exists")
            
            st.markdown("---")
            st.markdown("Already have an account?")
            if st.button("Back to Login", key="go_to_login"):
                st.session_state.register_mode = False
                st.rerun()


# ═══════════════════════════════════════════════════════════════
# PROFILE PAGE (NEW)
# ═══════════════════════════════════════════════════════════════

def profile_page():
    """User profile page with avatar, bio, and stats."""
    user_id = be.get_user_id(st.session_state.username)
    profile = be.get_user_profile(user_id)

    st.markdown('<div class="dark-title"><h1>👤 Your Profile</h1></div>', unsafe_allow_html=True)

    if not profile:
        st.warning("Profile not found. Creating default profile...")
        be.update_user_profile(user_id, display_name=st.session_state.username)
        st.rerun()
        return

    col1, col2 = st.columns([1, 2])

    with col1:
        # Avatar display
        st.markdown(f"""
        <div class="fade-in" style="text-align:center;">
            <div class="profile-avatar">{profile.get('avatar_emoji', '🧘')}</div>
            <h2 style="margin:0; font-weight:800;">{profile.get('display_name', st.session_state.username)}</h2>
            <p style="color: var(--text-secondary); margin:4px 0;">@{st.session_state.username}</p>
            <p style="font-style:italic; color: var(--text-secondary);">{profile.get('bio', '') or 'No bio yet...'}</p>
        </div>
        """, unsafe_allow_html=True)

        # Stats badges
        st.markdown(f"""
        <div style="text-align:center; margin-top:20px;">
            <span class="stat-badge">🏋️ {profile.get('total_workouts', 0)} workouts</span>
            <span class="stat-badge">⏱️ {round(profile.get('total_minutes', 0), 1)} min</span>
            <span class="stat-badge">🔥 {profile.get('streak_days', 0)} day streak</span>
            <span class="stat-badge">🎯 {profile.get('fitness_goal', 'Stay Healthy')}</span>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="exercise-title"><h3>✏️ Edit Profile</h3></div>', unsafe_allow_html=True)

        new_display = st.text_input("Display Name", value=profile.get('display_name', ''), key="profile_display")
        new_bio = st.text_area("Bio", value=profile.get('bio', ''), key="profile_bio", max_chars=250)

        avatar_options = ['🧘', '🏋️', '🧗', '🏃', '🤸', '💪', '🥷', '🦸', '🧙', '🎯', '⚡', '🔥', '🌟', '👑', '🦅']
        current_idx = avatar_options.index(profile.get('avatar_emoji', '🧘')) if profile.get('avatar_emoji', '🧘') in avatar_options else 0
        new_avatar = st.selectbox("Avatar Emoji", avatar_options, index=current_idx, key="profile_avatar")

        goal_options = ['Stay Healthy', 'Build Muscle', 'Lose Weight', 'Improve Flexibility', 'Reduce Stress', 'Train for Competition']
        current_goal_idx = goal_options.index(profile.get('fitness_goal', 'Stay Healthy')) if profile.get('fitness_goal', 'Stay Healthy') in goal_options else 0
        new_goal = st.selectbox("Fitness Goal", goal_options, index=current_goal_idx, key="profile_goal")

        if st.button("💾 Save Profile", key="save_profile"):
            be.update_user_profile(
                user_id,
                display_name=new_display,
                bio=new_bio,
                avatar_emoji=new_avatar,
                fitness_goal=new_goal
            )
            st.success("✅ Profile updated successfully!")
            st.rerun()

    # Recent workout history
    st.markdown("---")
    st.markdown('<div class="exercise-title"><h3>📜 Recent Workout History</h3></div>', unsafe_allow_html=True)

    history = be.get_workout_history(user_id, limit=10)
    if history:
        for w in history:
            emoji = "🧘" if w['workout_type'] == 'Yoga' else "🏋️"
            duration_min = round(w['duration_seconds'] / 60, 1) if w['duration_seconds'] else 0
            st.markdown(f"""
            <div class="glass-card fade-in">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <div>
                        <span style="font-size:1.3rem;">{emoji}</span>
                        <strong>{w['workout_name']}</strong>
                        <span style="color:var(--text-secondary); font-size:0.85rem;"> — {w['workout_type']}</span>
                    </div>
                    <div style="text-align:right;">
                        <span class="stat-badge">⏱️ {duration_min} min</span>
                        <span class="stat-badge">💪 {w.get('reps', 0)} reps</span>
                        <span class="stat-badge">🔥 {round(w.get('calories_burned', 0), 1)} cal</span>
                    </div>
                </div>
                <div style="font-size:0.75rem; color:var(--text-secondary); margin-top:6px;">{w['created_at']}</div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("No workout history yet. Start exercising to see your progress! 🏋️")


# ═══════════════════════════════════════════════════════════════
# DASHBOARD PAGE (NEW)
# ═══════════════════════════════════════════════════════════════

def dashboard_page():
    """Analytics dashboard with workout stats and charts."""
    user_id = be.get_user_id(st.session_state.username)
    stats = be.get_workout_stats(user_id)
    app_stats = be.get_app_stats()

    st.markdown('<div class="dark-title"><h1>📊 Analytics Dashboard</h1></div>', unsafe_allow_html=True)

    # Top-level metric cards
    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.markdown(f"""
        <div class="glass-card fade-in">
            <h3>🏋️ Workouts</h3>
            <div class="metric-value">{stats.get('total_workouts', 0)}</div>
            <div class="metric-label">Total sessions</div>
        </div>
        """, unsafe_allow_html=True)

    with c2:
        st.markdown(f"""
        <div class="glass-card fade-in">
            <h3>⏱️ Duration</h3>
            <div class="metric-value">{stats.get('total_minutes', 0)}</div>
            <div class="metric-label">Total minutes</div>
        </div>
        """, unsafe_allow_html=True)

    with c3:
        st.markdown(f"""
        <div class="glass-card fade-in">
            <h3>💪 Reps</h3>
            <div class="metric-value">{stats.get('total_reps', 0)}</div>
            <div class="metric-label">Total repetitions</div>
        </div>
        """, unsafe_allow_html=True)

    with c4:
        st.markdown(f"""
        <div class="glass-card fade-in">
            <h3>🔥 Calories</h3>
            <div class="metric-value">{stats.get('total_calories', 0)}</div>
            <div class="metric-label">Estimated burned</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # Charts
    col_left, col_right = st.columns(2)

    with col_left:
        st.markdown('<div class="exercise-title"><h3>📈 Weekly Activity</h3></div>', unsafe_allow_html=True)
        weekly = stats.get('weekly', [])
        if weekly:
            import pandas as pd
            df = pd.DataFrame(weekly)
            df.columns = ['Date', 'Workouts', 'Duration (s)']
            df['Duration (min)'] = df['Duration (s)'] / 60
            st.bar_chart(df.set_index('Date')[['Workouts']])
        else:
            st.info("No data yet. Complete workouts to see your weekly activity!")

    with col_right:
        st.markdown('<div class="exercise-title"><h3>🏆 Top Exercises</h3></div>', unsafe_allow_html=True)
        by_name = stats.get('by_name', [])
        if by_name:
            import pandas as pd
            df = pd.DataFrame(by_name)
            df.columns = ['Exercise', 'Sessions', 'Total Reps']
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("No data yet. Start working out to see your favorites!")

    # App-wide stats
    st.markdown("---")
    st.markdown('<div class="exercise-title"><h3>🌍 Platform Stats</h3></div>', unsafe_allow_html=True)

    p1, p2, p3 = st.columns(3)
    with p1:
        st.metric("👥 Total Users", app_stats.get('total_users', 0))
    with p2:
        st.metric("🏋️ Total Workouts (Platform)", app_stats.get('total_workouts', 0))
    with p3:
        st.metric("⏱️ Total Minutes (Platform)", app_stats.get('total_minutes', 0))


# ═══════════════════════════════════════════════════════════════
# COST ESTIMATOR PAGE (NEW)
# ═══════════════════════════════════════════════════════════════

def cost_estimator_page():
    """Interactive cost estimation page for yoga/exercise sessions."""
    st.markdown('<div class="dark-title"><h1>💰 Session Cost Estimator</h1></div>', unsafe_allow_html=True)

    col1, col2 = st.columns([1, 1])

    with col1:
        st.markdown('<div class="exercise-title"><h3>⚙️ Configure Your Session</h3></div>', unsafe_allow_html=True)

        session_type = st.radio("Session Type", ["Yoga", "Exercise"], horizontal=True, key="cost_type")

        if session_type == "Yoga":
            options = ["Tree Pose", "Warrior II", "Downward Dog", "Cobra Pose", "Bridge Pose", "Child's Pose"]
        else:
            options = ["Squats", "Hand Raises", "Push-ups", "Lunges", "Bicep Curls", "Jumping Jacks"]

        session_name = st.selectbox("Session Name", options, key="cost_session")
        duration = st.slider("Duration (minutes)", 5, 120, 30, key="cost_duration")
        instructor = st.selectbox("Instructor Type",
                                  ["Self-Guided", "AI-Assisted", "Personal Trainer", "Group Class"],
                                  key="cost_instructor")
        difficulty = st.selectbox("Difficulty Level",
                                  ["Beginner", "Intermediate", "Advanced", "Expert"],
                                  index=1, key="cost_difficulty")
        equipment = st.checkbox("Include Equipment Rental", key="cost_equipment")

    with col2:
        st.markdown('<div class="exercise-title"><h3>💵 Cost Breakdown</h3></div>', unsafe_allow_html=True)

        result = be.estimate_cost(
            session_type=session_type,
            session_name=session_name,
            duration_minutes=duration,
            instructor_type=instructor,
            difficulty=difficulty,
            include_equipment=equipment
        )

        st.markdown(f"""
        <div class="cost-breakdown fade-in">
            <div class="cost-row">
                <span>📋 Session</span>
                <span><strong>{result['session_name']}</strong> ({result['session_type']})</span>
            </div>
            <div class="cost-row">
                <span>⏱️ Duration</span>
                <span>{result['duration_minutes']} minutes</span>
            </div>
            <div class="cost-row">
                <span>💲 Rate</span>
                <span>${result['per_minute_rate']:.2f}/min</span>
            </div>
            <div class="cost-row">
                <span>📦 Base Cost</span>
                <span>${result['base_cost']:.2f}</span>
            </div>
            <div class="cost-row">
                <span>👨‍🏫 Instructor ({result['instructor_type']})</span>
                <span>+${result['instructor_fee']:.2f}</span>
            </div>
            <div class="cost-row">
                <span>📊 Difficulty ({result['difficulty']})</span>
                <span>{'+' if result['difficulty_adjustment'] >= 0 else ''}${result['difficulty_adjustment']:.2f}</span>
            </div>
            <div class="cost-row">
                <span>🧰 Equipment</span>
                <span>${result['equipment_fee']:.2f}</span>
            </div>
            <div class="cost-row">
                <span>📄 Subtotal</span>
                <span>${result['subtotal']:.2f}</span>
            </div>
            <div class="cost-row">
                <span>🏛️ Tax (8%)</span>
                <span>${result['tax']:.2f}</span>
            </div>
            <div class="cost-total">
                <span>TOTAL</span>
                <span>${result['total']:.2f}</span>
            </div>
            <div style="margin-top:16px; padding:12px; background: linear-gradient(135deg, rgba(6,182,212,0.1), rgba(37,99,235,0.1)); border-radius:12px; text-align:center;">
                <span style="font-size:1.1rem;">🔥 Estimated Calories: <strong>{result['estimated_calories']}</strong> kcal</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # Log cost estimation as an analytics metric
    be.record_metric('cost_estimate', result['total'], 'USD', 'cost')


# ═══════════════════════════════════════════════════════════════
# ACHIEVEMENTS PAGE (NEW)
# ═══════════════════════════════════════════════════════════════

def achievements_page():
    """Display user achievements and badges."""
    user_id = be.get_user_id(st.session_state.username)

    st.markdown('<div class="dark-title"><h1>🏆 Achievements</h1></div>', unsafe_allow_html=True)

    earned = be.get_user_achievements(user_id)
    earned_names = {a['badge_name'] for a in earned}

    # Show earned badges
    st.markdown('<div class="exercise-title"><h3>🌟 Earned Badges</h3></div>', unsafe_allow_html=True)

    if earned:
        for a in earned:
            st.markdown(f"""
            <div class="achievement-card fade-in">
                <div class="achievement-icon">{a['badge_icon']}</div>
                <div class="achievement-info">
                    <h4>{a['badge_name']}</h4>
                    <p>{a['description']}</p>
                    <p style="font-size:0.7rem; color:var(--accent-color);">Earned: {a['earned_at']}</p>
                </div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("No badges earned yet. Start working out to unlock achievements! 💪")

    # Show locked badges
    st.markdown("---")
    st.markdown('<div class="exercise-title"><h3>🔒 Locked Badges</h3></div>', unsafe_allow_html=True)

    for badge in be.BADGE_DEFINITIONS:
        if badge['name'] not in earned_names:
            st.markdown(f"""
            <div class="achievement-card" style="opacity:0.5; filter:grayscale(0.6);">
                <div class="achievement-icon">{badge['icon']}</div>
                <div class="achievement-info">
                    <h4>{badge['name']}</h4>
                    <p>{badge['desc']} (Need {badge['threshold']} workouts)</p>
                </div>
            </div>
            """, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════
# POSE ESTIMATION (EXISTING — preserved)
# ═══════════════════════════════════════════════════════════════

def pose_estimation_page():
    """Main pose estimation interface"""
    st.markdown(f'<div class="dark-title"><h1>Hello, {st.session_state.username}! 👋</h1></div>', unsafe_allow_html=True)
    st.markdown("---")
    
    # Category selection - CHANGE THIS KEY
    category = st.radio("Select Category:", ["Exercise", "Yoga"], horizontal=True, key="category_selector_main")
    
    if category == "Exercise":
        exercise_page()
    else:
        yoga_page()

def yoga_page():
    """Yoga category page"""
    with st.container():
        st.markdown('<div class="exercise-title"><h3>🧘 Choose Your Yoga Pose</h3></div>', unsafe_allow_html=True)
        yoga_pose = st.selectbox("", ["Tree Pose", "Warrior II", "Downward Dog", "Cobra Pose", "Bridge Pose", "Child's Pose"], key="yoga_pose_select")
        st.session_state.current_yoga_pose = yoga_pose
        st.markdown(f"<div class='exercise-card'>"
                   f"<h4>Current Pose: {yoga_pose}</h4>"
                   f"<p>Hold the pose and check your form</p></div>", 
                   unsafe_allow_html=True)
    
    # Initialize yoga timer session variables
    if 'yoga_start_time' not in st.session_state:
        st.session_state.yoga_start_time = None
    if 'yoga_total_time' not in st.session_state:
        st.session_state.yoga_total_time = 0
    if 'yoga_is_holding' not in st.session_state:
        st.session_state.yoga_is_holding = False
    
    # Display timer for Tree Pose
    if yoga_pose == "Tree Pose":
        # Calculate total time
        total_time = st.session_state.yoga_total_time
        
        # Add current session time if holding pose
        if st.session_state.yoga_is_holding and st.session_state.yoga_start_time is not None:
            current_time = time.time()
            elapsed = current_time - st.session_state.yoga_start_time
            display_time = total_time + elapsed
        else:
            display_time = total_time
        
        seconds = int(display_time)
        
        # Display timer prominently
        st.markdown(f"""
        <div class='counter-display' style="background: linear-gradient(135deg, #7c3aed, #06b6d4);">
            🧘 Tree Pose Hold Time
            <br><span style="font-size: 3rem;">{seconds} seconds</span>
            <br><span style="font-size: 1rem; font-weight: 400;">
                { '🟢 Holding Pose' if st.session_state.yoga_is_holding else '⏸️ Not in position' }
            </span>
        </div>
        """, unsafe_allow_html=True)
    
    if 'webcam_active' not in st.session_state:
        st.session_state.webcam_active = False
    
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("🎥 Start Webcam" if not st.session_state.webcam_active else "🛑 Stop Webcam", key="yoga_webcam"):
            st.session_state.webcam_active = not st.session_state.webcam_active
    with col2:
        if st.button("🔄 Reset Timer", key="yoga_reset"):
            st.session_state.yoga_total_time = 0
            st.session_state.yoga_start_time = None
            st.session_state.yoga_is_holding = False
            st.success("Timer reset!")
            st.rerun()
    with col3:
        if st.button("💾 Save Workout", key="yoga_save"):
            user_id = be.get_user_id(st.session_state.username)
            if user_id and st.session_state.yoga_total_time > 0:
                be.save_workout(
                    user_id=user_id,
                    workout_type='Yoga',
                    workout_name=yoga_pose,
                    duration_seconds=st.session_state.yoga_total_time,
                    reps=0,
                    calories_burned=st.session_state.yoga_total_time * 0.06,
                )
                st.success("✅ Workout saved!")
                st.session_state.yoga_total_time = 0
                st.session_state.yoga_start_time = None
                st.session_state.yoga_is_holding = False
            else:
                st.warning("No workout data to save.")
    
    if st.session_state.webcam_active:
        process_yoga_feed(yoga_pose)    

def exercise_page():
    """Exercise category page"""
    with st.container():
        st.markdown('<div class="exercise-title"><h3>🏋️ Choose Your Exercise</h3></div>', unsafe_allow_html=True)
        exercise = st.selectbox("", ["Squats", "Hand Raises", "Push-ups", "Lunges", "Bicep Curls", "Jumping Jacks"], key="exercise_select_main")
        st.session_state.current_exercise = exercise
        st.markdown(f"<div class='exercise-card'>"
                   f"<h4>Current Exercise: {exercise}</h4>"
                   f"<p>Follow the on-screen guidance</p></div>", 
                   unsafe_allow_html=True)
    
    # Initialize session variables
    if 'counter' not in st.session_state:
        st.session_state.counter = 0
    if 'webcam_active' not in st.session_state:
        st.session_state.webcam_active = False
    if 'exercise_stage' not in st.session_state:
        st.session_state.exercise_stage = "start"
    if 'exercise_start_time' not in st.session_state:
        st.session_state.exercise_start_time = None
    if 'total_exercise_time' not in st.session_state:
        st.session_state.total_exercise_time = 0
    if 'is_exercising' not in st.session_state:
        st.session_state.is_exercising = False
    
    # Display counter and timer in two columns
    col_counter, col_timer = st.columns(2)
    
    with col_counter:
        st.markdown(f"<div class='counter-display'>"
                   f"🏋️ Rep Count: {st.session_state.counter}"
                   f"</div>", unsafe_allow_html=True)
    
    with col_timer:
        # Calculate total time
        total_time = st.session_state.total_exercise_time
        
        # Add current session time if exercising
        if st.session_state.is_exercising and st.session_state.exercise_start_time is not None:
            current_time = time.time()
            elapsed = current_time - st.session_state.exercise_start_time
            display_time = total_time + elapsed
        else:
            display_time = total_time
        
        minutes = int(display_time // 60)
        seconds = int(display_time % 60)
        
        if exercise == "Hand Raises":
            timer_color = "linear-gradient(135deg, #f59e0b, #f97316)"
        else:
            timer_color = "linear-gradient(135deg, #06b6d4, #2563eb)"
        
        status_text = ""
        if st.session_state.is_exercising:
            status_text = "🟢 Active"
        elif total_time > 0:
            status_text = "⏸️ Paused"
        else:
            status_text = "Raise hands to start"
        
        st.markdown(f"""
        <div class='counter-display' style="background: {timer_color};">
            ⏱️ Time: {minutes:02d}:{seconds:02d}
            <br><span style="font-size: 1rem; font-weight: 400;">{status_text}</span>
        </div>
        """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("🎥 Start Webcam" if not st.session_state.webcam_active else "🛑 Stop Webcam", key="exercise_webcam_toggle"):
            st.session_state.webcam_active = not st.session_state.webcam_active
    with col2:
        if st.button("🔁 Reset Counter & Timer", key="exercise_reset"):
            st.session_state.counter = 0
            st.session_state.exercise_stage = "start"
            st.session_state.total_exercise_time = 0
            st.session_state.exercise_start_time = None
            st.session_state.is_exercising = False
            st.success("Counter and timer reset!")
    with col3:
        if st.button("💾 Save Workout", key="exercise_save"):
            user_id = be.get_user_id(st.session_state.username)
            if user_id and (st.session_state.counter > 0 or st.session_state.total_exercise_time > 0):
                be.save_workout(
                    user_id=user_id,
                    workout_type='Exercise',
                    workout_name=exercise,
                    duration_seconds=st.session_state.total_exercise_time,
                    reps=st.session_state.counter,
                    calories_burned=st.session_state.counter * 5,
                )
                st.success("✅ Workout saved!")
                st.session_state.counter = 0
                st.session_state.exercise_stage = "start"
                st.session_state.total_exercise_time = 0
                st.session_state.exercise_start_time = None
                st.session_state.is_exercising = False
            else:
                st.warning("No workout data to save.")
    
    if st.session_state.webcam_active:
        process_exercise_feed(exercise)

def process_exercise_feed(exercise):
    """Process real-time webcam feed for exercises"""
    st.markdown("---")
    st.markdown('<div class="exercise-title"><h3>🎥 Live Exercise Detection</h3></div>', unsafe_allow_html=True)
    
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    cap.set(cv2.CAP_PROP_FPS, 30)
    
    video_placeholder = st.empty()
    
    while st.session_state.webcam_active:
        ret, frame = cap.read()
        if not ret:
            st.error("Camera error")
            break
        
        image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = pose.process(image)
        image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
        
        if results.pose_landmarks:
            if exercise == "Squats":
                process_squats(results.pose_landmarks, image)
            elif exercise == "Hand Raises":
                process_hand_raises(results.pose_landmarks, image)
            elif exercise == "Push-ups":
                process_pushups(results.pose_landmarks, image)
            elif exercise == "Lunges":
                process_lunges(results.pose_landmarks, image)
            elif exercise == "Bicep Curls":
                process_bicep_curls(results.pose_landmarks, image)
            elif exercise == "Jumping Jacks":
                process_jumping_jacks(results.pose_landmarks, image)
            
            mp_drawing.draw_landmarks(image, results.pose_landmarks, mp_pose.POSE_CONNECTIONS)
        
        cv2.putText(image, f"Reps: {st.session_state.counter}", (10, 30), 
                   cv2.FONT_HERSHEY_TRIPLEX, 1, (255, 0, 0), 2)
        
        video_placeholder.image(image, channels="BGR")
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

# d
def process_yoga_feed(yoga_pose):
    """Process real-time webcam feed for yoga poses"""
    st.markdown("---")
    st.markdown('<div class="exercise-title"><h3>🎥 Live Pose Feedback</h3></div>', unsafe_allow_html=True)
    
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    cap.set(cv2.CAP_PROP_FPS, 30)
    
    video_placeholder = st.empty()
    feedback_placeholder = st.empty()
    
    # ===== ADD THIS TO DISPLAY TIMER IN BROWSER =====
    timer_placeholder = st.empty()
    
    while st.session_state.webcam_active:
        ret, frame = cap.read()
        if not ret:
            st.error("Camera error")
            break
        
        image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = pose.process(image)
        image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
        
        feedback = ""
        if results.pose_landmarks:
            if yoga_pose == "Tree Pose":
                feedback = check_tree_pose(results.pose_landmarks, image)
            elif yoga_pose == "Warrior II":
                feedback = check_warrior_ii(results.pose_landmarks, image)
            elif yoga_pose == "Downward Dog":
                feedback = check_downward_dog(results.pose_landmarks, image)
            elif yoga_pose == "Cobra Pose":
                feedback = check_cobra_pose(results.pose_landmarks, image)
            elif yoga_pose == "Bridge Pose":
                feedback = check_bridge_pose(results.pose_landmarks, image)
            elif yoga_pose == "Child's Pose":
                feedback = check_childs_pose(results.pose_landmarks, image)
            
            mp_drawing.draw_landmarks(image, results.pose_landmarks, mp_pose.POSE_CONNECTIONS)
        
        # Display feedback
        if feedback:
            if "GOOD" in feedback:
                feedback_placeholder.markdown(f'<div class="pose-feedback" style="background-color:#e8f5e9;color:#4CAF50;">{feedback}</div>', unsafe_allow_html=True)
            else:
                feedback_placeholder.markdown(f'<div class="pose-feedback" style="background-color:#ffebee;color:#F44336;">{feedback}</div>', unsafe_allow_html=True)
        
        # ===== UPDATE TIMER DISPLAY IN BROWSER =====
        if yoga_pose == "Tree Pose":
            total_time = st.session_state.yoga_total_time
            if st.session_state.yoga_is_holding and st.session_state.yoga_start_time is not None:
                elapsed = time.time() - st.session_state.yoga_start_time
                display_time = total_time + elapsed
            else:
                display_time = total_time
            
            seconds = int(display_time)
            status = "🟢 Holding" if st.session_state.yoga_is_holding else "⏸️ Paused"
            timer_placeholder.markdown(f"""
            <div style="background: linear-gradient(135deg, #7c3aed, #06b6d4); 
                        padding: 15px; 
                        border-radius: 15px; 
                        text-align: center; 
                        color: white;
                        margin: 10px 0;">
                <h3>🧘 Tree Pose Timer</h3>
                <h1 style="font-size: 3rem; margin: 0;">{seconds} seconds</h1>
                <p style="margin: 5px 0;">{status}</p>
            </div>
            """, unsafe_allow_html=True)
        
        video_placeholder.image(image, channels="BGR")
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

# ===== EXERCISE PROCESSING FUNCTIONS =====

def process_squats(landmarks, image):
    """Process squats exercise"""
    try:
        left_hip = landmarks.landmark[mp_pose.PoseLandmark.LEFT_HIP.value]
        left_knee = landmarks.landmark[mp_pose.PoseLandmark.LEFT_KNEE.value]
        left_ankle = landmarks.landmark[mp_pose.PoseLandmark.LEFT_ANKLE.value]
        
        right_hip = landmarks.landmark[mp_pose.PoseLandmark.RIGHT_HIP.value]
        right_knee = landmarks.landmark[mp_pose.PoseLandmark.RIGHT_KNEE.value]
        right_ankle = landmarks.landmark[mp_pose.PoseLandmark.RIGHT_ANKLE.value]
        
        left_knee_angle = calculate_angle(left_hip, left_knee, left_ankle)
        right_knee_angle = calculate_angle(right_hip, right_knee, right_ankle)
        
        avg_knee_angle = (left_knee_angle + right_knee_angle) / 2
        
        if avg_knee_angle > 160:
            st.session_state.exercise_stage = "up"
            
        if avg_knee_angle < 90 and st.session_state.exercise_stage == "up":
            st.session_state.exercise_stage = "down"
            st.session_state.counter += 1
            cv2.putText(image, "REP COUNTED!", (image.shape[1]//2 - 100, 50), 
                       cv2.FONT_HERSHEY_TRIPLEX, 1, (0, 255, 0), 2)
        
        if st.session_state.exercise_stage == "up":
            cv2.putText(image, "BEND KNEES TO SQUAT", (image.shape[1]//2 - 150, image.shape[0] - 50), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 165, 255), 2)
        else:
            cv2.putText(image, "STAND UP", (image.shape[1]//2 - 70, image.shape[0] - 50), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)

    except Exception as e:
        st.error(f"Squats processing error: {e}")

def process_hand_raises(landmarks, image):
    """Process hand raises exercise with timer tracking and rep counting"""
    try:
        left_shoulder = landmarks.landmark[mp_pose.PoseLandmark.LEFT_SHOULDER.value]
        left_wrist = landmarks.landmark[mp_pose.PoseLandmark.LEFT_WRIST.value]
        
        right_shoulder = landmarks.landmark[mp_pose.PoseLandmark.RIGHT_SHOULDER.value]
        right_wrist = landmarks.landmark[mp_pose.PoseLandmark.RIGHT_WRIST.value]
        
        avg_wrist_height = (left_wrist.y + right_wrist.y) / 2
        avg_shoulder_height = (left_shoulder.y + right_shoulder.y) / 2
        
        # ===== REP COUNTING LOGIC (KEEP THIS) =====
        if avg_wrist_height > avg_shoulder_height + 0.05:
            st.session_state.exercise_stage = "down"
            
        if avg_wrist_height < avg_shoulder_height - 0.05 and st.session_state.exercise_stage == "down":
            st.session_state.exercise_stage = "up"
            st.session_state.counter += 1
            cv2.putText(image, "REP COUNTED!", (image.shape[1]//2 - 100, 50), 
                       cv2.FONT_HERSHEY_TRIPLEX, 1, (0, 255, 0), 2)
        
        # ===== TIMER LOGIC (ADD THIS) =====
        # Check if hands are raised (exercise position)
        hands_raised = avg_wrist_height < avg_shoulder_height - 0.05
        
        current_time = time.time()
        
        if hands_raised:
            # User is exercising
            if st.session_state.exercise_start_time is None:
                # Start timing
                st.session_state.exercise_start_time = current_time
                st.session_state.is_exercising = True
                cv2.putText(image, "EXERCISE STARTED!", (image.shape[1]//2 - 100, 30), 
                           cv2.FONT_HERSHEY_TRIPLEX, 0.8, (0, 255, 0), 2)
            else:
                # Update elapsed time
                elapsed = current_time - st.session_state.exercise_start_time
                st.session_state.total_exercise_time += elapsed
                st.session_state.exercise_start_time = current_time
                
                # Display timer on video
                total_min = int(st.session_state.total_exercise_time // 60)
                total_sec = int(st.session_state.total_exercise_time % 60)
                timer_text = f"⏱️ {total_min:02d}:{total_sec:02d}"
                cv2.putText(image, timer_text, (image.shape[1] - 200, 50), 
                           cv2.FONT_HERSHEY_TRIPLEX, 1, (0, 255, 255), 2)
                
                # Display "HOLD" message
                cv2.putText(image, "HOLD POSITION", (image.shape[1]//2 - 100, image.shape[0] - 50), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        else:
            # User stopped exercising
            if st.session_state.is_exercising:
                st.session_state.is_exercising = False
                st.session_state.exercise_start_time = None
                cv2.putText(image, "EXERCISE PAUSED", (image.shape[1]//2 - 100, 30), 
                           cv2.FONT_HERSHEY_TRIPLEX, 0.8, (0, 0, 255), 2)
            
            # Show instruction when not exercising
            if st.session_state.exercise_stage == "up":
                cv2.putText(image, "LOWER YOUR HANDS", (image.shape[1]//2 - 130, image.shape[0] - 50), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
            else:
                cv2.putText(image, "RAISE YOUR HANDS", (image.shape[1]//2 - 120, image.shape[0] - 50), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 165, 255), 2)
        
        # Display reps count
        cv2.putText(image, f"Reps: {st.session_state.counter}", (10, 30), 
                   cv2.FONT_HERSHEY_TRIPLEX, 1, (255, 0, 0), 2)

    except Exception as e:
        st.error(f"Hand raises processing error: {e}")

def process_pushups(landmarks, image):
    """Process push-ups exercise with improved detection"""
    try:
        left_shoulder = landmarks.landmark[mp_pose.PoseLandmark.LEFT_SHOULDER.value]
        left_elbow = landmarks.landmark[mp_pose.PoseLandmark.LEFT_ELBOW.value]
        left_wrist = landmarks.landmark[mp_pose.PoseLandmark.LEFT_WRIST.value]
        
        right_shoulder = landmarks.landmark[mp_pose.PoseLandmark.RIGHT_SHOULDER.value]
        right_elbow = landmarks.landmark[mp_pose.PoseLandmark.RIGHT_ELBOW.value]
        right_wrist = landmarks.landmark[mp_pose.PoseLandmark.RIGHT_WRIST.value]
        
        # Get hip landmarks (added these lines)
        left_hip = landmarks.landmark[mp_pose.PoseLandmark.LEFT_HIP.value]
        right_hip = landmarks.landmark[mp_pose.PoseLandmark.RIGHT_HIP.value]
        
        # Calculate elbow angles
        left_elbow_angle = calculate_angle(left_shoulder, left_elbow, left_wrist)
        right_elbow_angle = calculate_angle(right_shoulder, right_elbow, right_wrist)
        
        # Calculate shoulder angles (using hips as the third point)
        left_shoulder_angle = calculate_angle(left_elbow, left_shoulder, left_hip)
        right_shoulder_angle = calculate_angle(right_elbow, right_shoulder, right_hip)
        
        # Get average angles
        avg_elbow_angle = (left_elbow_angle + right_elbow_angle) / 2
        avg_shoulder_angle = (left_shoulder_angle + right_shoulder_angle) / 2
        
        # Push-up logic
        if avg_elbow_angle > 160 and avg_shoulder_angle > 160:
            st.session_state.exercise_stage = "up"
            
        if avg_elbow_angle < 70 and st.session_state.exercise_stage == "up":
            st.session_state.exercise_stage = "down"
            st.session_state.counter += 1
            cv2.putText(image, "REP COUNTED!", (image.shape[1]//2 - 100, 50), 
                       cv2.FONT_HERSHEY_TRIPLEX, 1, (0, 255, 0), 2)
        
        # Visual feedback
        if st.session_state.exercise_stage == "up":
            cv2.putText(image, "LOWER YOUR BODY", (image.shape[1]//2 - 120, image.shape[0] - 50), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 165, 255), 2)
            cv2.putText(image, f"Elbow Angle: {int(avg_elbow_angle)}°", (10, 60), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        else:
            cv2.putText(image, "PUSH UP", (image.shape[1]//2 - 70, image.shape[0] - 50), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
            cv2.putText(image, f"Elbow Angle: {int(avg_elbow_angle)}°", (10, 60), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        # Draw angles on frame for debugging
        cv2.putText(image, f"L Elbow: {int(left_elbow_angle)}°", 
                   (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
        cv2.putText(image, f"R Elbow: {int(right_elbow_angle)}°", 
                   (10, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)

    except Exception as e:
        st.error(f"Push-ups processing error: {e}")

def process_lunges(landmarks, image):
    """Process lunges exercise"""
    try:
        left_hip = landmarks.landmark[mp_pose.PoseLandmark.LEFT_HIP.value]
        left_knee = landmarks.landmark[mp_pose.PoseLandmark.LEFT_KNEE.value]
        left_ankle = landmarks.landmark[mp_pose.PoseLandmark.LEFT_ANKLE.value]
        
        right_hip = landmarks.landmark[mp_pose.PoseLandmark.RIGHT_HIP.value]
        right_knee = landmarks.landmark[mp_pose.PoseLandmark.RIGHT_KNEE.value]
        right_ankle = landmarks.landmark[mp_pose.PoseLandmark.RIGHT_ANKLE.value]
        
        left_knee_angle = calculate_angle(left_hip, left_knee, left_ankle)
        right_knee_angle = calculate_angle(right_hip, right_knee, right_ankle)
        
        if left_knee_angle > 160 and right_knee_angle > 160:
            st.session_state.exercise_stage = "up"
            
        if (left_knee_angle < 90 or right_knee_angle < 90) and st.session_state.exercise_stage == "up":
            st.session_state.exercise_stage = "down"
            st.session_state.counter += 1
            cv2.putText(image, "REP COUNTED!", (image.shape[1]//2 - 100, 50), 
                       cv2.FONT_HERSHEY_TRIPLEX, 1, (0, 255, 0), 2)
        
        if st.session_state.exercise_stage == "up":
            cv2.putText(image, "STEP FORWARD INTO LUNGE", (image.shape[1]//2 - 180, image.shape[0] - 50), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 165, 255), 2)
        else:
            cv2.putText(image, "RETURN TO START", (image.shape[1]//2 - 120, image.shape[0] - 50), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

    except Exception as e:
        st.error(f"Lunges processing error: {e}")

def process_bicep_curls(landmarks, image):
    """Process bicep curls exercise"""
    try:
        left_shoulder = landmarks.landmark[mp_pose.PoseLandmark.LEFT_SHOULDER.value]
        left_elbow = landmarks.landmark[mp_pose.PoseLandmark.LEFT_ELBOW.value]
        left_wrist = landmarks.landmark[mp_pose.PoseLandmark.LEFT_WRIST.value]
        
        right_shoulder = landmarks.landmark[mp_pose.PoseLandmark.RIGHT_SHOULDER.value]
        right_elbow = landmarks.landmark[mp_pose.PoseLandmark.RIGHT_ELBOW.value]
        right_wrist = landmarks.landmark[mp_pose.PoseLandmark.RIGHT_WRIST.value]
        
        left_elbow_angle = calculate_angle(left_shoulder, left_elbow, left_wrist)
        right_elbow_angle = calculate_angle(right_shoulder, right_elbow, right_wrist)
        
        if left_elbow_angle > 160 and right_elbow_angle > 160:
            st.session_state.exercise_stage = "down"
            
        if (left_elbow_angle < 50 or right_elbow_angle < 50) and st.session_state.exercise_stage == "down":
            st.session_state.exercise_stage = "up"
            st.session_state.counter += 1
            cv2.putText(image, "REP COUNTED!", (image.shape[1]//2 - 100, 50), 
                       cv2.FONT_HERSHEY_TRIPLEX, 1, (0, 255, 0), 2)
        
        if st.session_state.exercise_stage == "down":
            cv2.putText(image, "CURL YOUR ARMS UP", (image.shape[1]//2 - 140, image.shape[0] - 50), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 165, 255), 2)
        else:
            cv2.putText(image, "LOWER YOUR ARMS", (image.shape[1]//2 - 120, image.shape[0] - 50), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)

    except Exception as e:
        st.error(f"Bicep curls processing error: {e}")

def process_jumping_jacks(landmarks, image):
    """Process jumping jacks exercise"""
    try:
        left_shoulder = landmarks.landmark[mp_pose.PoseLandmark.LEFT_SHOULDER.value]
        left_hip = landmarks.landmark[mp_pose.PoseLandmark.LEFT_HIP.value]
        left_wrist = landmarks.landmark[mp_pose.PoseLandmark.LEFT_WRIST.value]
        
        right_shoulder = landmarks.landmark[mp_pose.PoseLandmark.RIGHT_SHOULDER.value]
        right_hip = landmarks.landmark[mp_pose.PoseLandmark.RIGHT_HIP.value]
        right_wrist = landmarks.landmark[mp_pose.PoseLandmark.RIGHT_WRIST.value]
        
        wrist_distance = calculate_distance(left_wrist, right_wrist)
        hip_distance = calculate_distance(left_hip, right_hip)
        
        if wrist_distance < 0.2 and hip_distance < 0.2:
            st.session_state.exercise_stage = "closed"
            
        if wrist_distance > 0.4 and hip_distance > 0.3 and st.session_state.exercise_stage == "closed":
            st.session_state.exercise_stage = "open"
            st.session_state.counter += 1
            cv2.putText(image, "REP COUNTED!", (image.shape[1]//2 - 100, 50), 
                       cv2.FONT_HERSHEY_TRIPLEX, 1, (0, 255, 0), 2)
        
        if st.session_state.exercise_stage == "closed":
            cv2.putText(image, "JUMP ARMS AND LEGS OUT", (image.shape[1]//2 - 180, image.shape[0] - 50), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 165, 255), 2)
        else:
            cv2.putText(image, "JUMP ARMS AND LEGS IN", (image.shape[1]//2 - 170, image.shape[0] - 50), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

    except Exception as e:
        st.error(f"Jumping jacks processing error: {e}")

# ===== YOGA POSE CHECKING FUNCTIONS =====

def check_tree_pose(landmarks, image):
    """Check Tree Pose form with timer tracking"""
    try:
        left_ankle = landmarks.landmark[mp_pose.PoseLandmark.LEFT_ANKLE.value]
        right_knee = landmarks.landmark[mp_pose.PoseLandmark.RIGHT_KNEE.value]
        left_hip = landmarks.landmark[mp_pose.PoseLandmark.LEFT_HIP.value]
        right_hip = landmarks.landmark[mp_pose.PoseLandmark.RIGHT_HIP.value]
        
        # Check if in correct Tree Pose position
        foot_near_knee = (abs(left_ankle.x - right_knee.x) < 0.05 and 
                         abs(left_ankle.y - right_knee.y) < 0.1)
        balanced = abs(left_hip.y - right_hip.y) < 0.05
        
        is_correct_pose = foot_near_knee and balanced
        
        # ===== TIMER LOGIC =====
        current_time = time.time()
        
        if is_correct_pose:
            # User is holding the pose correctly
            if st.session_state.yoga_start_time is None:
                # Start timing
                st.session_state.yoga_start_time = current_time
                st.session_state.yoga_is_holding = True
                cv2.putText(image, "✅ PERFECT FORM! TIMING STARTED!", (image.shape[1]//2 - 200, 30), 
                           cv2.FONT_HERSHEY_TRIPLEX, 0.7, (0, 255, 0), 2)
            else:
                # Update elapsed time
                elapsed = current_time - st.session_state.yoga_start_time
                st.session_state.yoga_total_time += elapsed
                st.session_state.yoga_start_time = current_time
                
                # Display timer on video
                total_seconds = int(st.session_state.yoga_total_time)
                cv2.putText(image, f"⏱️ {total_seconds}s", (image.shape[1] - 150, 50), 
                           cv2.FONT_HERSHEY_TRIPLEX, 1, (0, 255, 255), 2)
                
                cv2.putText(image, "GOOD TREE POSE - HOLD IT!", (image.shape[1]//2 - 150, image.shape[0] - 50), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        else:
            # User is not in correct pose
            if st.session_state.yoga_is_holding:
                st.session_state.yoga_is_holding = False
                st.session_state.yoga_start_time = None
                cv2.putText(image, "⏸️ TIMER PAUSED", (image.shape[1]//2 - 100, 30), 
                           cv2.FONT_HERSHEY_TRIPLEX, 0.8, (0, 0, 255), 2)
            
            # Give feedback on what to fix
            feedback = []
            if not foot_near_knee:
                cv2.putText(image, "PLACE FOOT NEAR KNEE", (image.shape[1]//2 - 150, image.shape[0] - 100), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
                feedback.append("Place foot near knee")
            if not balanced:
                cv2.putText(image, "KEEP HIPS LEVEL", (image.shape[1]//2 - 120, image.shape[0] - 70), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
                feedback.append("Keep hips level")
            
            # Show total time achieved
            if st.session_state.yoga_total_time > 0:
                total_seconds = int(st.session_state.yoga_total_time)
                cv2.putText(image, f"Total: {total_seconds}s", (10, 30), 
                           cv2.FONT_HERSHEY_TRIPLEX, 0.7, (255, 165, 0), 2)
            
            cv2.putText(image, "ADJUST YOUR POSE", (image.shape[1]//2 - 120, image.shape[0] - 40), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 165, 255), 2)
        
        # Display current timer on video always
        if st.session_state.yoga_total_time > 0:
            total_seconds = int(st.session_state.yoga_total_time)
            cv2.putText(image, f"Total Time: {total_seconds}s", (10, 60), 
                       cv2.FONT_HERSHEY_TRIPLEX, 0.7, (255, 165, 0), 2)
        
        return ""

    except Exception as e:
        st.error(f"Tree Pose check error: {e}")
        return ""

def check_warrior_ii(landmarks, image):
    """Check Warrior II pose form"""
    try:
        left_shoulder = landmarks.landmark[mp_pose.PoseLandmark.LEFT_SHOULDER.value]
        left_hip = landmarks.landmark[mp_pose.PoseLandmark.LEFT_HIP.value]
        left_knee = landmarks.landmark[mp_pose.PoseLandmark.LEFT_KNEE.value]
        left_ankle = landmarks.landmark[mp_pose.PoseLandmark.LEFT_ANKLE.value]
        
        right_shoulder = landmarks.landmark[mp_pose.PoseLandmark.RIGHT_SHOULDER.value]
        right_hip = landmarks.landmark[mp_pose.PoseLandmark.RIGHT_HIP.value]
        right_knee = landmarks.landmark[mp_pose.PoseLandmark.RIGHT_KNEE.value]
        right_ankle = landmarks.landmark[mp_pose.PoseLandmark.RIGHT_ANKLE.value]
        
        # Check front knee angle (should be ~90 degrees)
        front_knee_angle = calculate_angle(right_hip, right_knee, right_ankle)
        good_knee_angle = 80 < front_knee_angle < 100
        
        # Check arm alignment (should be straight line shoulder to wrist)
        arm_alignment = abs(left_shoulder.y - right_shoulder.y) < 0.05
        
        # Check hips facing sideways
        hips_alignment = abs(left_hip.x - right_hip.x) > 0.2
        
        if good_knee_angle and arm_alignment and hips_alignment:
            cv2.putText(image, "GOOD WARRIOR II", (image.shape[1]//2 - 120, 50), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            return "GOOD WARRIOR II FORM! 👍"
        else:
            feedback = []
            if not good_knee_angle:
                cv2.putText(image, f"BEND FRONT KNEE MORE ({int(front_knee_angle)}°)", 
                           (image.shape[1]//2 - 180, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
                feedback.append("Bend front knee to 90°")
            if not arm_alignment:
                cv2.putText(image, "STRETCH ARMS STRAIGHT", (image.shape[1]//2 - 150, 80), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
                feedback.append("Align arms straight")
            if not hips_alignment:
                cv2.putText(image, "FACE HIPS SIDEWAYS", (image.shape[1]//2 - 130, 110), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
                feedback.append("Turn hips sideways")
            return "ADJUST YOUR POSE: " + ", ".join(feedback)
    
    except Exception as e:
        st.error(f"Warrior II check error: {e}")
        return ""

def check_downward_dog(landmarks, image):
    """Check Downward Dog pose form"""
    try:
        left_shoulder = landmarks.landmark[mp_pose.PoseLandmark.LEFT_SHOULDER.value]
        left_hip = landmarks.landmark[mp_pose.PoseLandmark.LEFT_HIP.value]
        left_knee = landmarks.landmark[mp_pose.PoseLandmark.LEFT_KNEE.value]
        
        right_shoulder = landmarks.landmark[mp_pose.PoseLandmark.RIGHT_SHOULDER.value]
        right_hip = landmarks.landmark[mp_pose.PoseLandmark.RIGHT_HIP.value]
        right_knee = landmarks.landmark[mp_pose.PoseLandmark.RIGHT_KNEE.value]
        
        # Check if hips are higher than shoulders
        hips_higher = (left_hip.y + right_hip.y)/2 < (left_shoulder.y + right_shoulder.y)/2
        # Check if legs are straight
        left_leg_angle = calculate_angle(left_hip, left_knee, landmarks.landmark[mp_pose.PoseLandmark.LEFT_ANKLE.value])
        right_leg_angle = calculate_angle(right_hip, right_knee, landmarks.landmark[mp_pose.PoseLandmark.RIGHT_ANKLE.value])
        legs_straight = left_leg_angle > 160 and right_leg_angle > 160
        
        if hips_higher and legs_straight:
            cv2.putText(image, "GOOD DOWNWARD DOG", (image.shape[1]//2 - 150, 50), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            return "GOOD DOWNWARD DOG FORM! 👍"
        else:
            feedback = []
            if not hips_higher:
                cv2.putText(image, "LIFT HIPS HIGHER", (image.shape[1]//2 - 120, 50), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
                feedback.append("Lift hips higher")
            if not legs_straight:
                cv2.putText(image, "STRAIGHTEN LEGS", (image.shape[1]//2 - 130, 80), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
                feedback.append("Straighten legs")
            return "ADJUST YOUR POSE: " + ", ".join(feedback)
    
    except Exception as e:
        st.error(f"Downward Dog check error: {e}")
        return ""

def check_cobra_pose(landmarks, image):
    """Check Cobra Pose form"""
    try:
        left_shoulder = landmarks.landmark[mp_pose.PoseLandmark.LEFT_SHOULDER.value]
        left_elbow = landmarks.landmark[mp_pose.PoseLandmark.LEFT_ELBOW.value]
        
        right_shoulder = landmarks.landmark[mp_pose.PoseLandmark.RIGHT_SHOULDER.value]
        right_elbow = landmarks.landmark[mp_pose.PoseLandmark.RIGHT_ELBOW.value]
        
        # Check if shoulders are lifted
        shoulders_lifted = (left_shoulder.y + right_shoulder.y)/2 < 0.6
        # Check if elbows are slightly bent
        left_arm_angle = calculate_angle(
            landmarks.landmark[mp_pose.PoseLandmark.LEFT_WRIST.value],
            left_elbow,
            left_shoulder
        )
        right_arm_angle = calculate_angle(
            landmarks.landmark[mp_pose.PoseLandmark.RIGHT_WRIST.value],
            right_elbow,
            right_shoulder
        )
        arms_bent = 140 < left_arm_angle < 170 and 140 < right_arm_angle < 170
        
        if shoulders_lifted and arms_bent:
            cv2.putText(image, "GOOD COBRA POSE", (image.shape[1]//2 - 120, 50), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            return "GOOD COBRA POSE FORM! 👍"
        else:
            feedback = []
            if not shoulders_lifted:
                cv2.putText(image, "LIFT CHEST HIGHER", (image.shape[1]//2 - 140, 50), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
                feedback.append("Lift chest higher")
            if not arms_bent:
                cv2.putText(image, "BEND ARMS SLIGHTLY", (image.shape[1]//2 - 150, 80), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
                feedback.append("Bend arms slightly")
            return "ADJUST YOUR POSE: " + ", ".join(feedback)
    
    except Exception as e:
        st.error(f"Cobra Pose check error: {e}")
        return ""

def check_bridge_pose(landmarks, image):
    """Check Bridge Pose form"""
    try:
        left_shoulder = landmarks.landmark[mp_pose.PoseLandmark.LEFT_SHOULDER.value]
        left_hip = landmarks.landmark[mp_pose.PoseLandmark.LEFT_HIP.value]
        left_knee = landmarks.landmark[mp_pose.PoseLandmark.LEFT_KNEE.value]
        
        right_shoulder = landmarks.landmark[mp_pose.PoseLandmark.RIGHT_SHOULDER.value]
        right_hip = landmarks.landmark[mp_pose.PoseLandmark.RIGHT_HIP.value]
        right_knee = landmarks.landmark[mp_pose.PoseLandmark.RIGHT_KNEE.value]
        
        # Check if hips are lifted
        hips_lifted = (left_hip.y + right_hip.y)/2 < (left_shoulder.y + right_shoulder.y)/2
        # Check knee angles
        left_knee_angle = calculate_angle(left_hip, left_knee, landmarks.landmark[mp_pose.PoseLandmark.LEFT_ANKLE.value])
        right_knee_angle = calculate_angle(right_hip, right_knee, landmarks.landmark[mp_pose.PoseLandmark.RIGHT_ANKLE.value])
        knees_bent = 100 < left_knee_angle < 120 and 100 < right_knee_angle < 120
        
        if hips_lifted and knees_bent:
            cv2.putText(image, "GOOD BRIDGE POSE", (image.shape[1]//2 - 130, 50), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            return "GOOD BRIDGE POSE FORM! 👍"
        else:
            feedback = []
            if not hips_lifted:
                cv2.putText(image, "LIFT HIPS HIGHER", (image.shape[1]//2 - 120, 50), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
                feedback.append("Lift hips higher")
            if not knees_bent:
                cv2.putText(image, "ADJUST KNEE ANGLES", (image.shape[1]//2 - 150, 80), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
                feedback.append("Adjust knee angles")
            return "ADJUST YOUR POSE: " + ", ".join(feedback)
    
    except Exception as e:
        st.error(f"Bridge Pose check error: {e}")
        return ""

def check_childs_pose(landmarks, image):
    """Check Child's Pose form"""
    try:
        left_shoulder = landmarks.landmark[mp_pose.PoseLandmark.LEFT_SHOULDER.value]
        left_hip = landmarks.landmark[mp_pose.PoseLandmark.LEFT_HIP.value]
        
        right_shoulder = landmarks.landmark[mp_pose.PoseLandmark.RIGHT_SHOULDER.value]
        right_hip = landmarks.landmark[mp_pose.PoseLandmark.RIGHT_HIP.value]
        
        # Check if hips are close to heels (approximation)
        hips_low = (left_hip.y + right_hip.y)/2 > 0.8
        # Check if arms are extended forward
        left_arm_angle = calculate_angle(
            left_shoulder,
            landmarks.landmark[mp_pose.PoseLandmark.LEFT_ELBOW.value],
            landmarks.landmark[mp_pose.PoseLandmark.LEFT_WRIST.value]
        )
        right_arm_angle = calculate_angle(
            right_shoulder,
            landmarks.landmark[mp_pose.PoseLandmark.RIGHT_ELBOW.value],
            landmarks.landmark[mp_pose.PoseLandmark.RIGHT_WRIST.value]
        )
        arms_extended = left_arm_angle > 150 and right_arm_angle > 150
        
        if hips_low and arms_extended:
            cv2.putText(image, "GOOD CHILD'S POSE", (image.shape[1]//2 - 140, 50), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            return "GOOD CHILD'S POSE FORM! 👍"
        else:
            feedback = []
            if not hips_low:
                cv2.putText(image, "SINK HIPS LOWER", (image.shape[1]//2 - 120, 50), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
                feedback.append("Sink hips lower")
            if not arms_extended:
                cv2.putText(image, "EXTEND ARMS FORWARD", (image.shape[1]//2 - 160, 80), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
                feedback.append("Extend arms forward")
            return "ADJUST YOUR POSE: " + ", ".join(feedback)
    
    except Exception as e:
        st.error(f"Child's Pose check error: {e}")
        return ""

# ===== MAIN APPLICATION =====

def main():
    # Initialize the database
    initialize_database()
    
    # Set up page configuration
    set_page_config()
    
    # Initialize session state variables
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    if 'register_mode' not in st.session_state:
        st.session_state.register_mode = False
    if 'username' not in st.session_state:
        st.session_state.username = None
    if 'dark_mode' not in st.session_state:
        st.session_state.dark_mode = False
    
    # Check if any users exist (first run)
    if not users_exist() and not st.session_state.register_mode:
        st.session_state.register_mode = True
    
    # Show appropriate page based on state
    if not st.session_state.logged_in:
        if st.session_state.register_mode:
            register_page()
        else:
            login_page()
    else:
        # Render sidebar and get navigation
        nav = render_sidebar()

        if "Workout" in nav:
            pose_estimation_page()
        elif "Profile" in nav:
            profile_page()
        elif "Dashboard" in nav:
            dashboard_page()
        elif "Cost" in nav:
            cost_estimator_page()
        elif "Achievements" in nav:
            achievements_page()

if __name__ == "__main__":
    main()