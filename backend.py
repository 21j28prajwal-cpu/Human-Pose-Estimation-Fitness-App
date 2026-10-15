"""
Backend module for Human Pose Estimation App
Provides cost estimation, analytics, profile management, and workout tracking.
"""
import sqlite3
import os
from hashlib import sha256
from datetime import datetime, timedelta
import json

DB_PATH = os.path.join(os.path.dirname(__file__), "users.db")


def get_db():
    """Get a database connection with row factory."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ═══════════════════════════════════════════════════════
# AUTHENTICATION
# ═══════════════════════════════════════════════════════

def authenticate_user(username, password):
    """Authenticate a user by checking their hashed credentials."""
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
        user = cursor.fetchone()
        if user:
            input_hash = sha256((password + user['salt']).encode()).hexdigest()
            if input_hash == user['password_hash']:
                cursor.execute(
                    "UPDATE users SET last_login = ? WHERE id = ?",
                    (datetime.now().isoformat(), user['id'])
                )
                conn.commit()
                return True
        return False
    except sqlite3.Error:
        return False
    finally:
        conn.close()


def register_user(username, password):
    """Register a new user with hashed password."""
    conn = get_db()
    cursor = conn.cursor()
    try:
        existing = cursor.execute(
            'SELECT 1 FROM users WHERE username = ?', (username,)
        ).fetchone()
        if existing:
            return False

        salt = os.urandom(16).hex()
        hashed = sha256((password + salt).encode()).hexdigest()
        cursor.execute(
            'INSERT INTO users (username, password_hash, salt) VALUES (?, ?, ?)',
            (username, hashed, salt)
        )
        user_id = cursor.lastrowid

        # Create default profile for new user
        cursor.execute(
            '''INSERT INTO user_profiles (user_id, display_name)
               VALUES (?, ?)''',
            (user_id, username)
        )
        conn.commit()
        return True
    except sqlite3.Error:
        return False
    finally:
        conn.close()


def users_exist():
    """Check if any users exist in the database."""
    conn = get_db()
    try:
        return conn.execute('SELECT 1 FROM users').fetchone() is not None
    except sqlite3.Error:
        return False
    finally:
        conn.close()


def get_user_id(username):
    """Get user ID from username."""
    conn = get_db()
    try:
        row = conn.execute(
            'SELECT id FROM users WHERE username = ?', (username,)
        ).fetchone()
        return row['id'] if row else None
    except sqlite3.Error:
        return None
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════
# USER PROFILE
# ═══════════════════════════════════════════════════════

def get_user_profile(user_id):
    """Get user profile data."""
    conn = get_db()
    try:
        row = conn.execute(
            'SELECT * FROM user_profiles WHERE user_id = ?', (user_id,)
        ).fetchone()
        if row:
            return dict(row)
        # Create default profile if missing
        conn.execute(
            'INSERT OR IGNORE INTO user_profiles (user_id, display_name) VALUES (?, ?)',
            (user_id, f'User_{user_id}')
        )
        conn.commit()
        return get_user_profile(user_id)
    except sqlite3.Error:
        return None
    finally:
        conn.close()


def update_user_profile(user_id, display_name=None, bio=None,
                        avatar_emoji=None, fitness_goal=None, preferred_theme=None):
    """Update user profile fields."""
    conn = get_db()
    try:
        updates = []
        values = []
        if display_name is not None:
            updates.append("display_name = ?")
            values.append(display_name)
        if bio is not None:
            updates.append("bio = ?")
            values.append(bio)
        if avatar_emoji is not None:
            updates.append("avatar_emoji = ?")
            values.append(avatar_emoji)
        if fitness_goal is not None:
            updates.append("fitness_goal = ?")
            values.append(fitness_goal)
        if preferred_theme is not None:
            updates.append("preferred_theme = ?")
            values.append(preferred_theme)

        if updates:
            values.append(user_id)
            conn.execute(
                f"UPDATE user_profiles SET {', '.join(updates)} WHERE user_id = ?",
                values
            )
            conn.commit()
            return True
        return False
    except sqlite3.Error:
        return False
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════
# WORKOUT HISTORY
# ═══════════════════════════════════════════════════════

def save_workout(user_id, workout_type, workout_name, duration_seconds=0,
                 reps=0, calories_burned=0, pose_accuracy=0, notes=''):
    """Save a workout session to history."""
    conn = get_db()
    try:
        conn.execute('''
            INSERT INTO workout_history
            (user_id, workout_type, workout_name, duration_seconds, reps,
             calories_burned, pose_accuracy, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, workout_type, workout_name, duration_seconds,
              reps, calories_burned, pose_accuracy, notes))

        # Update profile stats
        conn.execute('''
            UPDATE user_profiles
            SET total_workouts = total_workouts + 1,
                total_minutes = total_minutes + ?,
                last_workout_date = ?
            WHERE user_id = ?
        ''', (duration_seconds / 60.0, datetime.now().strftime('%Y-%m-%d'), user_id))

        conn.commit()

        # Check and award achievements
        _check_achievements(conn, user_id)
        return True
    except sqlite3.Error:
        return False
    finally:
        conn.close()


def get_workout_history(user_id, limit=50):
    """Get recent workout history for a user."""
    conn = get_db()
    try:
        rows = conn.execute('''
            SELECT * FROM workout_history
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT ?
        ''', (user_id, limit)).fetchall()
        return [dict(r) for r in rows]
    except sqlite3.Error:
        return []
    finally:
        conn.close()


def get_workout_stats(user_id):
    """Get aggregated workout statistics for a user."""
    conn = get_db()
    try:
        stats = {}

        # Total workouts
        row = conn.execute(
            'SELECT COUNT(*) as cnt FROM workout_history WHERE user_id = ?',
            (user_id,)
        ).fetchone()
        stats['total_workouts'] = row['cnt'] if row else 0

        # Total duration
        row = conn.execute(
            'SELECT COALESCE(SUM(duration_seconds), 0) as total FROM workout_history WHERE user_id = ?',
            (user_id,)
        ).fetchone()
        stats['total_seconds'] = row['total'] if row else 0
        stats['total_minutes'] = round(stats['total_seconds'] / 60, 1)

        # Total reps
        row = conn.execute(
            'SELECT COALESCE(SUM(reps), 0) as total FROM workout_history WHERE user_id = ?',
            (user_id,)
        ).fetchone()
        stats['total_reps'] = row['total'] if row else 0

        # Total calories
        row = conn.execute(
            'SELECT COALESCE(SUM(calories_burned), 0) as total FROM workout_history WHERE user_id = ?',
            (user_id,)
        ).fetchone()
        stats['total_calories'] = round(row['total'] if row else 0, 1)

        # Avg pose accuracy
        row = conn.execute(
            'SELECT COALESCE(AVG(pose_accuracy), 0) as avg_acc FROM workout_history WHERE user_id = ?',
            (user_id,)
        ).fetchone()
        stats['avg_accuracy'] = round(row['avg_acc'] if row else 0, 1)

        # Workouts per type
        rows = conn.execute('''
            SELECT workout_type, COUNT(*) as cnt
            FROM workout_history WHERE user_id = ?
            GROUP BY workout_type
        ''', (user_id,)).fetchall()
        stats['by_type'] = {r['workout_type']: r['cnt'] for r in rows}

        # Workouts per name
        rows = conn.execute('''
            SELECT workout_name, COUNT(*) as cnt, COALESCE(SUM(reps), 0) as total_reps
            FROM workout_history WHERE user_id = ?
            GROUP BY workout_name
            ORDER BY cnt DESC
        ''', (user_id,)).fetchall()
        stats['by_name'] = [dict(r) for r in rows]

        # Last 7 days activity
        week_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        rows = conn.execute('''
            SELECT DATE(created_at) as day, COUNT(*) as cnt,
                   COALESCE(SUM(duration_seconds), 0) as dur
            FROM workout_history
            WHERE user_id = ? AND DATE(created_at) >= ?
            GROUP BY DATE(created_at)
            ORDER BY day
        ''', (user_id, week_ago)).fetchall()
        stats['weekly'] = [dict(r) for r in rows]

        return stats
    except sqlite3.Error:
        return {}
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════
# COST ESTIMATION
# ═══════════════════════════════════════════════════════

# Pricing rates (per minute) for different session types
YOGA_RATES = {
    "Tree Pose": 2.50,
    "Warrior II": 3.00,
    "Downward Dog": 2.00,
    "Cobra Pose": 2.50,
    "Bridge Pose": 3.50,
    "Child's Pose": 1.50,
}

EXERCISE_RATES = {
    "Squats": 2.00,
    "Hand Raises": 1.50,
    "Push-ups": 2.50,
    "Lunges": 2.00,
    "Bicep Curls": 2.50,
    "Jumping Jacks": 1.50,
}

INSTRUCTOR_MULTIPLIERS = {
    "Self-Guided": 1.0,
    "AI-Assisted": 1.5,
    "Personal Trainer": 3.0,
    "Group Class": 0.7,
}

DIFFICULTY_MULTIPLIERS = {
    "Beginner": 0.8,
    "Intermediate": 1.0,
    "Advanced": 1.3,
    "Expert": 1.6,
}


def estimate_cost(session_type, session_name, duration_minutes,
                  instructor_type="Self-Guided", difficulty="Intermediate",
                  include_equipment=False):
    """
    Estimate the cost of a yoga/exercise session.

    Returns a dict with breakdown:
      - base_cost
      - instructor_fee
      - difficulty_adjustment
      - equipment_fee
      - subtotal
      - tax
      - total
      - per_minute_rate
      - estimated_calories
    """
    rates = YOGA_RATES if session_type == "Yoga" else EXERCISE_RATES
    per_minute = rates.get(session_name, 2.00)

    base_cost = per_minute * duration_minutes
    instructor_mult = INSTRUCTOR_MULTIPLIERS.get(instructor_type, 1.0)
    difficulty_mult = DIFFICULTY_MULTIPLIERS.get(difficulty, 1.0)

    instructor_fee = base_cost * (instructor_mult - 1.0)
    difficulty_adj = base_cost * (difficulty_mult - 1.0)
    equipment_fee = 5.00 * (duration_minutes / 30) if include_equipment else 0

    subtotal = base_cost + instructor_fee + difficulty_adj + equipment_fee
    tax = subtotal * 0.08  # 8% tax
    total = subtotal + tax

    # Estimate calories (rough approximation)
    cal_per_minute = {
        "Tree Pose": 3.5, "Warrior II": 5.0, "Downward Dog": 4.0,
        "Cobra Pose": 3.0, "Bridge Pose": 4.5, "Child's Pose": 2.0,
        "Squats": 8.0, "Hand Raises": 4.0, "Push-ups": 7.0,
        "Lunges": 6.5, "Bicep Curls": 5.0, "Jumping Jacks": 9.0,
    }
    estimated_calories = cal_per_minute.get(session_name, 4.0) * duration_minutes

    return {
        "session_type": session_type,
        "session_name": session_name,
        "duration_minutes": duration_minutes,
        "per_minute_rate": per_minute,
        "base_cost": round(base_cost, 2),
        "instructor_type": instructor_type,
        "instructor_fee": round(instructor_fee, 2),
        "difficulty": difficulty,
        "difficulty_adjustment": round(difficulty_adj, 2),
        "equipment_fee": round(equipment_fee, 2),
        "subtotal": round(subtotal, 2),
        "tax": round(tax, 2),
        "total": round(total, 2),
        "estimated_calories": round(estimated_calories, 1),
    }


# ═══════════════════════════════════════════════════════
# ANALYTICS & METRICS
# ═══════════════════════════════════════════════════════

def record_metric(metric_name, metric_value, metric_unit='', category='general'):
    """Record a performance/analytics metric."""
    conn = get_db()
    try:
        conn.execute('''
            INSERT INTO analytics (metric_name, metric_value, metric_unit, category)
            VALUES (?, ?, ?, ?)
        ''', (metric_name, metric_value, metric_unit, category))
        conn.commit()
    except sqlite3.Error:
        pass
    finally:
        conn.close()


def get_metrics(category=None, limit=100):
    """Get recorded metrics, optionally filtered by category."""
    conn = get_db()
    try:
        if category:
            rows = conn.execute('''
                SELECT * FROM analytics
                WHERE category = ?
                ORDER BY recorded_at DESC LIMIT ?
            ''', (category, limit)).fetchall()
        else:
            rows = conn.execute('''
                SELECT * FROM analytics
                ORDER BY recorded_at DESC LIMIT ?
            ''', (limit,)).fetchall()
        return [dict(r) for r in rows]
    except sqlite3.Error:
        return []
    finally:
        conn.close()


def get_app_stats():
    """Get overall application statistics."""
    conn = get_db()
    try:
        stats = {}
        row = conn.execute('SELECT COUNT(*) as cnt FROM users').fetchone()
        stats['total_users'] = row['cnt'] if row else 0

        row = conn.execute('SELECT COUNT(*) as cnt FROM workout_history').fetchone()
        stats['total_workouts'] = row['cnt'] if row else 0

        row = conn.execute(
            'SELECT COALESCE(SUM(duration_seconds), 0) as total FROM workout_history'
        ).fetchone()
        stats['total_minutes'] = round((row['total'] if row else 0) / 60, 1)

        row = conn.execute(
            'SELECT COALESCE(SUM(calories_burned), 0) as total FROM workout_history'
        ).fetchone()
        stats['total_calories'] = round(row['total'] if row else 0, 1)

        return stats
    except sqlite3.Error:
        return {}
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════
# ACHIEVEMENTS
# ═══════════════════════════════════════════════════════

BADGE_DEFINITIONS = [
    {"name": "First Steps", "icon": "🌟", "desc": "Complete your first workout", "threshold": 1},
    {"name": "Getting Started", "icon": "🔥", "desc": "Complete 5 workouts", "threshold": 5},
    {"name": "Committed", "icon": "💪", "desc": "Complete 10 workouts", "threshold": 10},
    {"name": "Dedicated", "icon": "🏆", "desc": "Complete 25 workouts", "threshold": 25},
    {"name": "Iron Will", "icon": "⚡", "desc": "Complete 50 workouts", "threshold": 50},
    {"name": "Legend", "icon": "👑", "desc": "Complete 100 workouts", "threshold": 100},
]


def _check_achievements(conn, user_id):
    """Check and award new achievements based on workout count."""
    try:
        row = conn.execute(
            'SELECT COUNT(*) as cnt FROM workout_history WHERE user_id = ?',
            (user_id,)
        ).fetchone()
        count = row['cnt'] if row else 0

        for badge in BADGE_DEFINITIONS:
            if count >= badge['threshold']:
                existing = conn.execute(
                    'SELECT 1 FROM achievements WHERE user_id = ? AND badge_name = ?',
                    (user_id, badge['name'])
                ).fetchone()
                if not existing:
                    conn.execute(
                        '''INSERT INTO achievements (user_id, badge_name, badge_icon, description)
                           VALUES (?, ?, ?, ?)''',
                        (user_id, badge['name'], badge['icon'], badge['desc'])
                    )
        conn.commit()
    except sqlite3.Error:
        pass


def get_user_achievements(user_id):
    """Get all achievements earned by a user."""
    conn = get_db()
    try:
        rows = conn.execute(
            'SELECT * FROM achievements WHERE user_id = ? ORDER BY earned_at DESC',
            (user_id,)
        ).fetchall()
        return [dict(r) for r in rows]
    except sqlite3.Error:
        return []
    finally:
        conn.close()