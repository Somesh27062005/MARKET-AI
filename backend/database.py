import json
import os
from datetime import datetime

# ── Database Configuration ────────────────────────────────────────────────────
# Set DATABASE_URL in .env for PostgreSQL: postgresql://user:password@host:5432/dbname
# Falls back to SQLite for local development
DATABASE_URL = os.getenv("DATABASE_URL", "")
USE_POSTGRES = bool(DATABASE_URL and DATABASE_URL.startswith("postgresql"))

if USE_POSTGRES:
    import psycopg2
    import psycopg2.extras
else:
    import sqlite3

current_dir = os.path.dirname(os.path.abspath(__file__))
if os.path.basename(current_dir) == 'backend':
    DB_PATH = os.path.join(os.path.dirname(current_dir), "marketmind.db")
else:
    DB_PATH = os.path.join(current_dir, "marketmind.db")

# ── Placeholder helpers ───────────────────────────────────────────────────────
PH = "%s" if USE_POSTGRES else "?"   # SQL placeholder
AI = "SERIAL" if USE_POSTGRES else "INTEGER"  # auto-increment type


def get_db():
    """Return a DB connection. PostgreSQL if DATABASE_URL is set, else SQLite."""
    if USE_POSTGRES:
        conn = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)
        conn.autocommit = False
        return conn
    else:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn


def _exec(conn, sql, params=()):
    """Execute with either psycopg2 or sqlite3 cursor."""
    cur = conn.cursor()
    cur.execute(sql, params)
    return cur


def _fetchone(cur):
    row = cur.fetchone()
    if row is None:
        return None
    return dict(row)


def _fetchall(cur):
    return [dict(r) for r in cur.fetchall()]


def _commit(conn):
    if not (USE_POSTGRES and conn.autocommit):
        conn.commit()

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
    # Users Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        email TEXT PRIMARY KEY,
        password TEXT NOT NULL,
        name TEXT NOT NULL,
        firstName TEXT,
        lastName TEXT,
        avatar TEXT,
        joinedAt TEXT
    )
    """)
    
    # Pre-populate demo user
    cursor.execute("SELECT 1 FROM users WHERE email = 'demo@marketmind.ai'")
    if not cursor.fetchone():
        cursor.execute("""
        INSERT INTO users (email, password, name, firstName, lastName, avatar, joinedAt)
        VALUES ('demo@marketmind.ai', 'password123', 'Demo User', 'Demo', 'User', 'D', '2026-06-06T00:00:00.000Z')
        """)
        
    # Saved History Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_email TEXT NOT NULL,
        type TEXT NOT NULL, -- 'campaign', 'pitch', 'lead-scoring', 'market-analysis', 'business-insights'
        title TEXT NOT NULL,
        input_data TEXT NOT NULL, -- JSON string
        result TEXT NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY (user_email) REFERENCES users (email) ON DELETE CASCADE
    )
    """)
    
    # CRM Qualified Leads Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS crm_leads (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_email TEXT NOT NULL,
        name TEXT NOT NULL,
        company TEXT,
        score INTEGER,
        grade TEXT,
        status TEXT NOT NULL, -- 'New', 'Contacted', 'Proposal', 'Closed Won'
        details TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY (user_email) REFERENCES users (email) ON DELETE CASCADE
    )
    """)
    
    # Stock Prices Table
    _exec(conn, f"""
    CREATE TABLE IF NOT EXISTS stock_prices (
        ticker TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        price REAL NOT NULL,
        change_pct REAL NOT NULL,
        history TEXT NOT NULL,
        last_updated TEXT NOT NULL
    )
    """)

    # ── NEW v2 Tables ──────────────────────────────────────────────────────
    _exec(conn, f"""
    CREATE TABLE IF NOT EXISTS analysis_reports (
        id {AI} PRIMARY KEY,
        user_email TEXT NOT NULL,
        module TEXT NOT NULL,
        title TEXT NOT NULL,
        input_data TEXT NOT NULL,
        result_json TEXT NOT NULL,
        confidence_score INTEGER DEFAULT 0,
        created_at TEXT NOT NULL
    )
    """)

    _exec(conn, f"""
    CREATE TABLE IF NOT EXISTS exported_reports (
        id {AI} PRIMARY KEY,
        user_email TEXT NOT NULL,
        report_id INTEGER NOT NULL,
        format TEXT NOT NULL,
        file_path TEXT NOT NULL,
        file_size INTEGER,
        created_at TEXT NOT NULL
    )
    """)

    _exec(conn, f"""
    CREATE TABLE IF NOT EXISTS watchlists (
        id {AI} PRIMARY KEY,
        user_email TEXT NOT NULL,
        industry TEXT NOT NULL,
        keywords TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
    """)

    _exec(conn, f"""
    CREATE TABLE IF NOT EXISTS user_profiles (
        user_email TEXT PRIMARY KEY,
        company_name TEXT NOT NULL,
        industry TEXT,
        company_size TEXT,
        website TEXT,
        description TEXT,
        sub_industry TEXT DEFAULT '',
        hq_country TEXT DEFAULT '',
        geo_market TEXT DEFAULT '',
        business_model TEXT DEFAULT '',
        target_customer TEXT DEFAULT '',
        objectives TEXT DEFAULT '[]',
        founded_year TEXT DEFAULT '',
        created_at TEXT NOT NULL
    )
    """)

    # Migrate user_profiles to add new columns if they don't exist
    for col, default in [
        ("sub_industry", "''"),
        ("hq_country", "''"),
        ("geo_market", "''"),
        ("business_model", "''"),
        ("target_customer", "''"),
        ("objectives", "'[]'"),
        ("founded_year", "''")
    ]:
        try:
            _exec(conn, f"ALTER TABLE user_profiles ADD COLUMN {col} TEXT DEFAULT {default}")
        except Exception:
            pass

    _exec(conn, f"""
    CREATE TABLE IF NOT EXISTS knowledge_base (
        id {AI} PRIMARY KEY,
        user_email TEXT NOT NULL,
        filename TEXT NOT NULL,
        content TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
    """)

    _exec(conn, f"""
    CREATE TABLE IF NOT EXISTS icp_profiles (
        user_email TEXT PRIMARY KEY,
        icp_industry TEXT DEFAULT '',
        icp_company_size TEXT DEFAULT '',
        icp_revenue_range TEXT DEFAULT '',
        icp_job_titles TEXT DEFAULT '[]',
        icp_decision_makers TEXT DEFAULT '[]',
        icp_pain_points TEXT DEFAULT '[]',
        icp_notes TEXT DEFAULT '',
        updated_at TEXT NOT NULL
    )
    """)

    _exec(conn, f"""
    CREATE TABLE IF NOT EXISTS activity_log (
        id {AI} PRIMARY KEY,
        user_email TEXT NOT NULL,
        activity_type TEXT NOT NULL,
        title TEXT NOT NULL,
        metadata TEXT DEFAULT '{{}}',
        created_at TEXT NOT NULL
    )
    """)

    try:
        _exec(conn, "ALTER TABLE analysis_reports ADD COLUMN is_public INTEGER DEFAULT 0")
    except Exception:
        pass
    try:
        _exec(conn, "ALTER TABLE analysis_reports ADD COLUMN share_token TEXT")
    except Exception:
        pass

    # Company business metrics table — stores real user-provided KPI snapshots
    _exec(conn, f"""
    CREATE TABLE IF NOT EXISTS company_metrics (
        id {AI} PRIMARY KEY,
        user_email TEXT NOT NULL UNIQUE,
        monthly_revenue REAL DEFAULT 0,
        revenue_target REAL DEFAULT 0,
        monthly_leads INTEGER DEFAULT 0,
        lead_target INTEGER DEFAULT 0,
        active_campaigns INTEGER DEFAULT 0,
        conversion_rate REAL DEFAULT 0,
        avg_deal_size REAL DEFAULT 0,
        sales_cycle_days INTEGER DEFAULT 0,
        top_channel TEXT DEFAULT '',
        revenue_trend TEXT DEFAULT '[]',
        campaign_clicks TEXT DEFAULT '[]',
        lead_distribution TEXT DEFAULT '[]',
        currency TEXT DEFAULT 'USD',
        notes TEXT DEFAULT '',
        sales_team_size INTEGER DEFAULT 0,
        win_rate REAL DEFAULT 0.0,
        lost_deal_rate REAL DEFAULT 0.0,
        monthly_opportunities INTEGER DEFAULT 0,
        monthly_marketing_budget REAL DEFAULT 0.0,
        cac REAL DEFAULT 0.0,
        ltv REAL DEFAULT 0.0,
        lead_to_customer_rate REAL DEFAULT 0.0,
        secondary_channel TEXT DEFAULT '',
        ai_summary TEXT DEFAULT '',
        ai_highlights TEXT DEFAULT '[]',
        updated_at TEXT NOT NULL
    )
    """)
    # Migrate existing rows — add new columns if they don't exist yet
    for col, default in [("campaign_clicks", "'[]'"), ("lead_distribution", "'[]'")]:
        try:
            _exec(conn, f"ALTER TABLE company_metrics ADD COLUMN {col} TEXT DEFAULT {default}")
        except Exception:
            pass

    # Migrate company_metrics for the new sales & marketing columns
    for col, col_type, default in [
        ("sales_team_size", "INTEGER", "0"),
        ("win_rate", "REAL", "0.0"),
        ("lost_deal_rate", "REAL", "0.0"),
        ("monthly_opportunities", "INTEGER", "0"),
        ("monthly_marketing_budget", "REAL", "0.0"),
        ("cac", "REAL", "0.0"),
        ("ltv", "REAL", "0.0"),
        ("lead_to_customer_rate", "REAL", "0.0"),
        ("secondary_channel", "TEXT", "''"),
        ("ai_summary", "TEXT", "''"),
        ("ai_highlights", "TEXT", "'[]'")
    ]:
        try:
            _exec(conn, f"ALTER TABLE company_metrics ADD COLUMN {col} {col_type} DEFAULT {default}")
        except Exception:
            pass


    demo_stocks = [
        # SPY — steady bull trend, gradual climb Jan→Dec
        ('SPY', 'S&P 500 ETF', 737.55, 0.45, json.dumps([680, 688, 697, 703, 710, 716, 718, 722, 726, 730, 735, 737.55]), datetime.utcnow().isoformat() + "Z"),
        # QQQ — strong Jan-Feb spike, Mar-Apr pullback, then recovery
        ('QQQ', 'Nasdaq 100 ETF', 705.06, 1.20, json.dumps([640, 660, 678, 659, 648, 656, 668, 679, 688, 696, 700, 705.06]), datetime.utcnow().isoformat() + "Z"),
        # DIA — very flat / range-bound between 490-520, minimal volatility
        ('DIA', 'Dow Jones ETF', 516.70, -0.15, json.dumps([502, 508, 514, 511, 509, 513, 516, 512, 510, 514, 518, 516.70]), datetime.utcnow().isoformat() + "Z"),
        # AAPL — dip in Mar-Apr, strong recovery from May onwards
        ('AAPL', 'Apple Inc.', 311.64, 0.25, json.dumps([290, 295, 282, 270, 265, 278, 290, 298, 303, 308, 310, 311.64]), datetime.utcnow().isoformat() + "Z"),
        # GOOGL — sharp V-shaped recovery after Feb-Mar correction
        ('GOOGL', 'Alphabet Inc.', 368.53, 0.85, json.dumps([340, 345, 320, 308, 316, 330, 342, 350, 356, 362, 366, 368.53]), datetime.utcnow().isoformat() + "Z"),
        # MSFT — mostly flat Jan-Sep then sharp Q4 acceleration
        ('MSFT', 'Microsoft Corp.', 416.67, -0.10, json.dumps([390, 392, 391, 393, 394, 392, 395, 394, 396, 402, 411, 416.67]), datetime.utcnow().isoformat() + "Z"),
        # NVDA — hockey-stick parabolic from May onwards (AI boom)
        ('NVDA', 'NVIDIA Corp.', 205.10, 4.20, json.dumps([118, 122, 125, 124, 130, 148, 162, 172, 184, 196, 201, 205.10]), datetime.utcnow().isoformat() + "Z"),
        # TSLA — high volatility, big Apr-Jun drawdown then bounce
        ('TSLA', 'Tesla Inc.', 391.00, -2.30, json.dumps([420, 410, 395, 360, 340, 348, 360, 375, 382, 390, 395, 391.00]), datetime.utcnow().isoformat() + "Z"),
        # NIFTY50 — gradual uptrend with mid-year consolidation
        ('NIFTY50', 'NIFTY 50 Index', 23366.70, 0.65, json.dumps([21500, 21800, 22100, 22050, 22300, 22600, 22700, 22600, 22850, 23100, 23200, 23366.70]), datetime.utcnow().isoformat() + "Z"),
        # SENSEX — strong Jan-Mar rally, Apr consolidation, then new highs
        ('SENSEX', 'SENSEX Index', 74243.00, 0.55, json.dumps([67000, 69500, 72000, 71200, 71800, 72500, 72800, 72400, 73000, 73600, 73900, 74243.00]), datetime.utcnow().isoformat() + "Z"),
        # RELIANCE — flat Jan-Jun, breakout Jul-Dec
        ('RELIANCE', 'Reliance Industries', 1291.00, 1.15, json.dumps([1220, 1215, 1218, 1222, 1220, 1225, 1240, 1255, 1265, 1278, 1285, 1291.00]), datetime.utcnow().isoformat() + "Z"),
        # TCS — results-driven: Q1 dip, Q2 strong, Q3 flat, Q4 surge
        ('TCS', 'Tata Consultancy Services', 2198.90, -0.45, json.dumps([2100, 2080, 2060, 2090, 2130, 2160, 2155, 2150, 2160, 2175, 2185, 2198.90]), datetime.utcnow().isoformat() + "Z"),
        # HDFCBANK — post-merger recovery trajectory, steady climb
        ('HDFCBANK', 'HDFC Bank', 747.05, 0.25, json.dumps([680, 688, 698, 703, 710, 718, 724, 728, 734, 740, 744, 747.05]), datetime.utcnow().isoformat() + "Z"),
        # INFY  — sharp Feb drop (guidance cut), gradual Q3-Q4 recovery
        ('INFY', 'Infosys', 1197.50, -0.85, json.dumps([1180, 1140, 1100, 1085, 1095, 1108, 1120, 1138, 1155, 1172, 1185, 1197.50]), datetime.utcnow().isoformat() + "Z"),
        # TATAMOTORS — strong cyclical uptrend with minor volatility bumps
        ('TATAMOTORS', 'Tata Motors', 369.15, 2.30, json.dumps([300, 312, 325, 320, 330, 338, 345, 352, 358, 364, 366, 369.15]), datetime.utcnow().isoformat() + "Z"),
        # SBIN — budget-driven rally Feb, Mar correction, steady Q2-Q4
        ('SBIN', 'State Bank of India', 977.70, 1.45, json.dumps([860, 905, 930, 895, 905, 918, 930, 940, 952, 962, 970, 977.70]), datetime.utcnow().isoformat() + "Z"),
        # ICICIBANK — consistent outperformer, smooth upward trajectory
        ('ICICIBANK', 'ICICI Bank', 1262.10, 0.85, json.dumps([1090, 1108, 1125, 1135, 1148, 1162, 1175, 1188, 1202, 1220, 1240, 1262.10]), datetime.utcnow().isoformat() + "Z")
    ]
    for ticker, name, price, change_pct, history_str, last_updated in demo_stocks:
        cursor.execute("""
        INSERT OR REPLACE INTO stock_prices (ticker, name, price, change_pct, history, last_updated)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (ticker, name, price, change_pct, history_str, last_updated))

    # ── NEW v3 Enterprise Redesign Tables ───────────────────────────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_workspaces (
        id TEXT PRIMARY KEY,
        owner_email TEXT NOT NULL,
        company_name TEXT NOT NULL,
        industry TEXT NOT NULL,
        sub_industry TEXT DEFAULT '',
        hq_country TEXT DEFAULT '',
        geo_market TEXT DEFAULT '',
        business_model TEXT DEFAULT '',
        target_customer TEXT DEFAULT '',
        founded_year INTEGER,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY (owner_email) REFERENCES users(email) ON DELETE CASCADE
    )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_workspaces_owner ON user_workspaces(owner_email)")

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS market_sizes (
        id TEXT PRIMARY KEY,
        workspace_id TEXT NOT NULL,
        currency TEXT DEFAULT 'USD',
        tam_value REAL NOT NULL,
        sam_value REAL NOT NULL,
        som_value REAL NOT NULL,
        growth_rate_cagr REAL,
        source_documentation TEXT DEFAULT '',
        updated_at TEXT NOT NULL,
        FOREIGN KEY (workspace_id) REFERENCES user_workspaces(id) ON DELETE CASCADE
    )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_market_sizes_ws ON market_sizes(workspace_id)")

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS competitor_profiles (
        id TEXT PRIMARY KEY,
        workspace_id TEXT NOT NULL,
        name TEXT NOT NULL,
        market_share_pct REAL CHECK (market_share_pct >= 0 AND market_share_pct <= 100),
        strengths TEXT DEFAULT '[]', -- JSON array
        weaknesses TEXT DEFAULT '[]', -- JSON array
        threat_level TEXT CHECK (threat_level IN ('Critical', 'High', 'Medium', 'Low')),
        innovation_score INTEGER CHECK (innovation_score >= 0 AND innovation_score <= 100),
        pricing_score INTEGER CHECK (pricing_score >= 0 AND pricing_score <= 100),
        reach_score INTEGER CHECK (reach_score >= 0 AND reach_score <= 100),
        support_score INTEGER CHECK (support_score >= 0 AND support_score <= 100),
        quality_score INTEGER CHECK (quality_score >= 0 AND quality_score <= 100),
        created_at TEXT NOT NULL,
        FOREIGN KEY (workspace_id) REFERENCES user_workspaces(id) ON DELETE CASCADE
    )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_competitors_ws ON competitor_profiles(workspace_id)")

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS market_opportunities (
        id TEXT PRIMARY KEY,
        workspace_id TEXT NOT NULL,
        title TEXT NOT NULL,
        description TEXT NOT NULL,
        impact_score INTEGER CHECK (impact_score >= 1 AND impact_score <= 10),
        effort_score INTEGER CHECK (effort_score >= 1 AND effort_score <= 10),
        estimated_revenue REAL,
        target_audience TEXT DEFAULT '',
        required_capabilities TEXT DEFAULT '[]', -- JSON array
        status TEXT DEFAULT 'discovered' CHECK (status IN ('discovered', 'analyzing', 'accepted', 'rejected', 'archived')),
        created_at TEXT NOT NULL,
        FOREIGN KEY (workspace_id) REFERENCES user_workspaces(id) ON DELETE CASCADE
    )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_opps_ws ON market_opportunities(workspace_id)")

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS strategic_recommendations (
        id TEXT PRIMARY KEY,
        workspace_id TEXT NOT NULL,
        title TEXT NOT NULL,
        description TEXT NOT NULL,
        priority TEXT CHECK (priority IN ('High', 'Medium', 'Low')),
        timeframe_weeks INTEGER,
        owner TEXT DEFAULT '',
        kpi_metric TEXT DEFAULT '',
        kpi_target REAL,
        action_type TEXT DEFAULT '',
        associated_tools TEXT DEFAULT '[]', -- JSON array
        created_at TEXT NOT NULL,
        FOREIGN KEY (workspace_id) REFERENCES user_workspaces(id) ON DELETE CASCADE
    )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_recs_ws ON strategic_recommendations(workspace_id)")

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS growth_simulations (
        id TEXT PRIMARY KEY,
        workspace_id TEXT NOT NULL,
        simulation_name TEXT NOT NULL,
        input_parameters TEXT NOT NULL, -- JSON config
        simulation_output TEXT NOT NULL, -- JSON config
        created_at TEXT NOT NULL,
        FOREIGN KEY (workspace_id) REFERENCES user_workspaces(id) ON DELETE CASCADE
    )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_sims_ws ON growth_simulations(workspace_id)")

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS social_integrations (
        user_email TEXT NOT NULL,
        platform TEXT NOT NULL,
        connected INTEGER DEFAULT 0,
        username TEXT DEFAULT '',
        PRIMARY KEY (user_email, platform),
        FOREIGN KEY (user_email) REFERENCES users (email) ON DELETE CASCADE
    )
    """)

    conn.commit()
    conn.close()
    print("✅ SQLite database initialized successfully with demo data, stock tickers, and new enterprise analyzer tables.")


# User Operations


# User Operations
def get_user(email):
    conn = get_db()
    row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    conn.close()
    return dict(row) if row else None

def create_user(email, password, name, first_name="", last_name="", avatar="", joined_at=None):
    if not joined_at:
        joined_at = datetime.utcnow().isoformat() + "Z"
    conn = get_db()
    try:
        conn.execute("""
        INSERT INTO users (email, password, name, firstName, lastName, avatar, joinedAt)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (email, password, name, first_name, last_name, avatar, joined_at))
        conn.commit()
        success = True
    except sqlite3.IntegrityError:
        success = False
    conn.close()
    return success

# History Operations
def save_history(email, type_name, title, input_dict, result):
    conn = get_db()
    created_at = datetime.utcnow().isoformat() + "Z"
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO history (user_email, type, title, input_data, result, created_at)
    VALUES (?, ?, ?, ?, ?, ?)
    """, (email, type_name, title, json.dumps(input_dict), result, created_at))
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    return new_id

def get_user_history(email):
    conn = get_db()
    rows = conn.execute("SELECT * FROM history WHERE user_email = ? ORDER BY created_at DESC", (email,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def delete_history(email, record_id):
    conn = get_db()
    conn.execute("DELETE FROM history WHERE user_email = ? AND id = ?", (email, record_id))
    conn.commit()
    conn.close()
    return True

# CRM Operations
def add_crm_lead(email, name, company, score, grade, details=""):
    conn = get_db()
    created_at = datetime.utcnow().isoformat() + "Z"
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO crm_leads (user_email, name, company, score, grade, status, details, created_at)
    VALUES (?, ?, ?, ?, ?, 'New', ?, ?)
    """, (email, name, company, score, grade, details, created_at))
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    return new_id

def get_crm_leads(email):
    conn = get_db()
    rows = conn.execute("SELECT * FROM crm_leads WHERE user_email = ? ORDER BY created_at DESC", (email,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def update_crm_lead_status(email, lead_id, new_status):
    conn = get_db()
    conn.execute("UPDATE crm_leads SET status = ? WHERE user_email = ? AND id = ?", (new_status, email, lead_id))
    conn.commit()
    conn.close()
    return True

def delete_crm_lead(email, lead_id):
    conn = get_db()
    conn.execute("DELETE FROM crm_leads WHERE user_email = ? AND id = ?", (email, lead_id))
    conn.commit()
    conn.close()
    return True

# ── v2 Analysis Reports ──────────────────────────────────────────────────────

def save_analysis_report(email, module, title, input_dict, result_dict, confidence_score=0):
    """Save a v2 structured analysis report."""
    conn = get_db()
    created_at = datetime.utcnow().isoformat() + "Z"
    cur = conn.cursor()
    cur.execute("""
    INSERT INTO analysis_reports (user_email, module, title, input_data, result_json, confidence_score, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (email, module, title, json.dumps(input_dict), json.dumps(result_dict), confidence_score, created_at))
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return new_id


def get_analysis_reports(email, module=None, limit=50):
    """Get all v2 analysis reports for a user, optionally filtered by module."""
    conn = get_db()
    if module:
        rows = conn.execute(
            "SELECT id, user_email, module, title, confidence_score, created_at FROM analysis_reports "
            "WHERE user_email = ? AND module = ? ORDER BY created_at DESC LIMIT ?",
            (email, module, limit)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT id, user_email, module, title, confidence_score, created_at FROM analysis_reports "
            "WHERE user_email = ? ORDER BY created_at DESC LIMIT ?",
            (email, limit)
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_analysis_report_by_id(email, report_id):
    """Get a single full analysis report with result_json."""
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM analysis_reports WHERE user_email = ? AND id = ?",
        (email, report_id)
    ).fetchone()
    conn.close()
    if not row:
        return None
    d = dict(row)
    try:
        d["result_json"] = json.loads(d["result_json"])
        d["input_data"] = json.loads(d["input_data"])
    except Exception:
        pass
    return d


def delete_analysis_report(email, report_id):
    conn = get_db()
    conn.execute("DELETE FROM analysis_reports WHERE user_email = ? AND id = ?", (email, report_id))
    conn.commit()
    conn.close()
    return True


# ── v2 Watchlists ─────────────────────────────────────────────────────────────

def add_watchlist(email, industry, keywords: list):
    conn = get_db()
    created_at = datetime.utcnow().isoformat() + "Z"
    cur = conn.cursor()
    cur.execute("""
    INSERT INTO watchlists (user_email, industry, keywords, created_at)
    VALUES (?, ?, ?, ?)
    """, (email, industry, json.dumps(keywords), created_at))
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return new_id


def get_watchlists(email):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM watchlists WHERE user_email = ? ORDER BY created_at DESC",
        (email,)
    ).fetchall()
    conn.close()
    result = []
    for r in rows:
        d = dict(r)
        try:
            d["keywords"] = json.loads(d["keywords"])
        except Exception:
            pass
        result.append(d)
    return result


def delete_watchlist(email, watchlist_id):
    conn = get_db()
    conn.execute("DELETE FROM watchlists WHERE user_email = ? AND id = ?", (email, watchlist_id))
    conn.commit()
    conn.close()
    return True


# ── v2 Analytics Summary ──────────────────────────────────────────────────────

def get_analytics_summary(email):
    """Return aggregated usage analytics for the Analytics dashboard."""
    conn = get_db()
    
    # Reports by module
    module_counts = conn.execute("""
    SELECT module, COUNT(*) as count FROM analysis_reports
    WHERE user_email = ? GROUP BY module
    """, (email,)).fetchall()

    # Total reports
    total_reports = conn.execute(
        "SELECT COUNT(*) as c FROM analysis_reports WHERE user_email = ?", (email,)
    ).fetchone()["c"]

    # Average confidence
    avg_conf = conn.execute(
        "SELECT AVG(confidence_score) as avg FROM analysis_reports WHERE user_email = ?", (email,)
    ).fetchone()["avg"] or 0

    # Total v1 history runs
    total_runs = conn.execute(
        "SELECT COUNT(*) as c FROM history WHERE user_email = ?", (email,)
    ).fetchone()["c"]

    # Top 5 recent reports
    recent = conn.execute(
        "SELECT id, module, title, confidence_score, created_at FROM analysis_reports "
        "WHERE user_email = ? ORDER BY created_at DESC LIMIT 5",
        (email,)
    ).fetchall()

    # CRM leads count by status
    crm_stats = conn.execute("""
    SELECT status, COUNT(*) as count FROM crm_leads
    WHERE user_email = ? GROUP BY status
    """, (email,)).fetchall()

    conn.close()
    return {
        "total_reports": total_reports,
        "total_runs": total_runs,
        "avg_confidence": round(float(avg_conf), 1),
        "module_counts": [dict(r) for r in module_counts],
        "recent_reports": [dict(r) for r in recent],
        "crm_stats": [dict(r) for r in crm_stats],
    }


# User Profile Operations

def get_user_profile(email):
    conn = get_db()
    try:
        cur = _exec(conn, f"SELECT * FROM user_profiles WHERE user_email = {PH}", (email,))
        row = _fetchone(cur)
        if row and row.get("objectives"):
            try:
                row["objectives"] = json.loads(row["objectives"])
            except Exception:
                row["objectives"] = []
        elif row:
            row["objectives"] = []
        return row
    finally:
        conn.close()

def save_user_profile(email, company_name, industry, company_size, website, description,
                      sub_industry="", hq_country="", geo_market="", business_model="",
                      target_customer="", objectives=None, founded_year=""):
    conn = get_db()
    # Validate/coerce business model to satisfy database check constraints
    if not business_model or business_model not in ('B2B', 'B2C', 'B2B2C', 'D2C', 'Marketplace'):
        business_model = "B2B"
        
    try:
        cur = _exec(conn, f"SELECT 1 FROM user_profiles WHERE user_email = {PH}", (email,))
        row = _fetchone(cur)
        now_str = datetime.utcnow().isoformat() + "Z"
        obj_str = json.dumps(objectives if isinstance(objectives, list) else [])
        if row:
            _exec(conn, f"""
                UPDATE user_profiles 
                SET company_name = {PH}, industry = {PH}, company_size = {PH}, website = {PH}, description = {PH},
                    sub_industry = {PH}, hq_country = {PH}, geo_market = {PH}, business_model = {PH},
                    target_customer = {PH}, objectives = {PH}, founded_year = {PH}, created_at = {PH}
                WHERE user_email = {PH}
            """, (company_name, industry, company_size, website, description,
                  sub_industry, hq_country, geo_market, business_model,
                  target_customer, obj_str, founded_year, now_str, email))
        else:
            _exec(conn, f"""
                INSERT INTO user_profiles (user_email, company_name, industry, company_size, website, description,
                                           sub_industry, hq_country, geo_market, business_model,
                                           target_customer, objectives, founded_year, created_at)
                VALUES ({PH}, {PH}, {PH}, {PH}, {PH}, {PH}, {PH}, {PH}, {PH}, {PH}, {PH}, {PH}, {PH}, {PH})
            """, (email, company_name, industry, company_size, website, description,
                  sub_industry, hq_country, geo_market, business_model,
                  target_customer, obj_str, founded_year, now_str))
        
        # Sync workspace parameters to match the updated profile details
        try:
            founded_int = int(founded_year) if founded_year else None
        except ValueError:
            founded_int = None
            
        cur_ws = _exec(conn, f"SELECT id FROM user_workspaces WHERE owner_email = {PH}", (email,))
        row_ws = _fetchone(cur_ws)
        if row_ws:
            _exec(conn, f"""
                UPDATE user_workspaces
                SET company_name = {PH}, industry = {PH}, sub_industry = {PH}, hq_country = {PH}, geo_market = {PH},
                    business_model = {PH}, target_customer = {PH}, founded_year = {PH}, updated_at = {PH}
                WHERE owner_email = {PH}
            """, (company_name, industry, sub_industry, hq_country, geo_market, business_model,
                  target_customer, founded_int, now_str, email))
                  
        _commit(conn)
    finally:
        conn.close()



# Knowledge Base Operations

def add_knowledge_doc(email, filename, content):
    conn = get_db()
    created_at = datetime.utcnow().isoformat() + "Z"
    try:
        cur = _exec(conn, f"""
            INSERT INTO knowledge_base (user_email, filename, content, created_at)
            VALUES ({PH}, {PH}, {PH}, {PH})
        """, (email, filename, content, created_at))
        _commit(conn)
        return cur.lastrowid
    finally:
        conn.close()

def get_knowledge_docs(email):
    conn = get_db()
    try:
        cur = _exec(conn, f"SELECT id, filename, created_at FROM knowledge_base WHERE user_email = {PH} ORDER BY created_at DESC", (email,))
        return _fetchall(cur)
    finally:
        conn.close()

def get_knowledge_docs_content(email):
    conn = get_db()
    try:
        cur = _exec(conn, f"SELECT content FROM knowledge_base WHERE user_email = {PH}", (email,))
        rows = _fetchall(cur)
        return "\n\n".join([r["content"] for r in rows if r.get("content")])
    finally:
        conn.close()

def delete_knowledge_doc(email, doc_id):
    conn = get_db()
    try:
        _exec(conn, f"DELETE FROM knowledge_base WHERE user_email = {PH} AND id = {PH}", (email, doc_id))
        _commit(conn)
        return True
    finally:
        conn.close()


# Shareable Reports Operations

def toggle_report_share(email, report_id, is_public):
    import uuid
    conn = get_db()
    try:
        # Check current status and token
        cur = _exec(conn, f"SELECT share_token FROM analysis_reports WHERE user_email = {PH} AND id = {PH}", (email, report_id))
        row = _fetchone(cur)
        if not row:
            return None
        
        token = row.get("share_token")
        if not token:
            token = str(uuid.uuid4())
            
        _exec(conn, f"""
            UPDATE analysis_reports 
            SET is_public = {PH}, share_token = {PH}
            WHERE user_email = {PH} AND id = {PH}
        """, (1 if is_public else 0, token, email, report_id))
        _commit(conn)
        return token
    finally:
        conn.close()

def get_shared_report(token):
    conn = get_db()
    try:
        cur = _exec(conn, f"SELECT * FROM analysis_reports WHERE share_token = {PH} AND is_public = 1", (token,))
        row = _fetchone(cur)
        if not row:
            return None
        d = dict(row)
        try:
            d["result_json"] = json.loads(d["result_json"])
            d["input_data"] = json.loads(d["input_data"])
        except Exception:
            pass
        return d
    finally:
        conn.close()


# ── Company Business Metrics ─────────────────────────────────────────────────

def get_company_metrics(email):
    """Return the user's real company KPI metrics row, or None."""
    conn = get_db()
    try:
        cur = _exec(conn, f"SELECT * FROM company_metrics WHERE user_email = {PH}", (email,))
        row = _fetchone(cur)
        if row:
            for field in ("revenue_trend", "campaign_clicks", "lead_distribution"):
                val = row.get(field)
                if val:
                    try:
                        row[field] = json.loads(val)
                    except Exception:
                        row[field] = []
                else:
                    row[field] = []
            
            # Parse ai_highlights
            ai_h = row.get("ai_highlights")
            if ai_h:
                try:
                    row["ai_highlights"] = json.loads(ai_h)
                except Exception:
                    row["ai_highlights"] = []
            else:
                row["ai_highlights"] = []
        return row
    finally:
        conn.close()


def save_company_metrics(email, monthly_revenue, revenue_target, monthly_leads,
                         lead_target, active_campaigns, conversion_rate,
                         avg_deal_size, sales_cycle_days, top_channel,
                         revenue_trend, campaign_clicks=None, lead_distribution=None,
                         currency="USD", notes="", sales_team_size=0, win_rate=0.0,
                         lost_deal_rate=0.0, monthly_opportunities=0,
                         monthly_marketing_budget=0.0, cac=0.0, ltv=0.0,
                         lead_to_customer_rate=0.0, secondary_channel=""):
    """Insert or update the company_metrics row for the given user."""
    conn = get_db()
    now = datetime.utcnow().isoformat() + "Z"
    trend_str = json.dumps(revenue_trend if isinstance(revenue_trend, list) else [])
    clicks_str = json.dumps(campaign_clicks if isinstance(campaign_clicks, list) else [])
    dist_str   = json.dumps(lead_distribution if isinstance(lead_distribution, list) else [])
    try:
        existing = _fetchone(_exec(conn, f"SELECT 1 FROM company_metrics WHERE user_email = {PH}", (email,)))
        if existing:
            _exec(conn, f"""
                UPDATE company_metrics SET
                    monthly_revenue = {PH}, revenue_target = {PH},
                    monthly_leads = {PH}, lead_target = {PH},
                    active_campaigns = {PH}, conversion_rate = {PH},
                    avg_deal_size = {PH}, sales_cycle_days = {PH},
                    top_channel = {PH}, revenue_trend = {PH},
                    campaign_clicks = {PH}, lead_distribution = {PH},
                    currency = {PH}, notes = {PH},
                    sales_team_size = {PH}, win_rate = {PH}, lost_deal_rate = {PH},
                    monthly_opportunities = {PH}, monthly_marketing_budget = {PH},
                    cac = {PH}, ltv = {PH}, lead_to_customer_rate = {PH},
                    secondary_channel = {PH}, updated_at = {PH}
                WHERE user_email = {PH}
            """, (monthly_revenue, revenue_target, monthly_leads, lead_target,
                  active_campaigns, conversion_rate, avg_deal_size, sales_cycle_days,
                  top_channel, trend_str, clicks_str, dist_str,
                  currency, notes, sales_team_size, win_rate, lost_deal_rate,
                  monthly_opportunities, monthly_marketing_budget, cac, ltv,
                  lead_to_customer_rate, secondary_channel, now, email))
        else:
            _exec(conn, f"""
                INSERT INTO company_metrics
                (user_email, monthly_revenue, revenue_target, monthly_leads, lead_target,
                 active_campaigns, conversion_rate, avg_deal_size, sales_cycle_days,
                 top_channel, revenue_trend, campaign_clicks, lead_distribution,
                 currency, notes, sales_team_size, win_rate, lost_deal_rate,
                 monthly_opportunities, monthly_marketing_budget, cac, ltv,
                 lead_to_customer_rate, secondary_channel, updated_at)
                VALUES ({PH},{PH},{PH},{PH},{PH},{PH},{PH},{PH},{PH},{PH},{PH},{PH},{PH},{PH},{PH},{PH},{PH},{PH},{PH},{PH},{PH},{PH},{PH},{PH},{PH})
            """, (email, monthly_revenue, revenue_target, monthly_leads, lead_target,
                  active_campaigns, conversion_rate, avg_deal_size, sales_cycle_days,
                  top_channel, trend_str, clicks_str, dist_str,
                  currency, notes, sales_team_size, win_rate, lost_deal_rate,
                  monthly_opportunities, monthly_marketing_budget, cac, ltv,
                  lead_to_customer_rate, secondary_channel, now))
        _commit(conn)
    finally:
        conn.close()


# ── Ideal Customer Profile (ICP) Operations ──────────────────────────────────

def get_icp_profile(email):
    conn = get_db()
    try:
        cur = _exec(conn, f"SELECT * FROM icp_profiles WHERE user_email = {PH}", (email,))
        row = _fetchone(cur)
        if row:
            for field in ("icp_job_titles", "icp_decision_makers", "icp_pain_points"):
                val = row.get(field)
                if val:
                    try:
                        row[field] = json.loads(val)
                    except Exception:
                        row[field] = []
                else:
                    row[field] = []
        return row
    finally:
        conn.close()

def save_icp_profile(email, icp_industry, icp_company_size, icp_revenue_range,
                     icp_job_titles, icp_decision_makers, icp_pain_points, icp_notes=""):
    conn = get_db()
    now = datetime.utcnow().isoformat() + "Z"
    titles_str = json.dumps(icp_job_titles if isinstance(icp_job_titles, list) else [])
    dm_str = json.dumps(icp_decision_makers if isinstance(icp_decision_makers, list) else [])
    pain_str = json.dumps(icp_pain_points if isinstance(icp_pain_points, list) else [])
    try:
        existing = _fetchone(_exec(conn, f"SELECT 1 FROM icp_profiles WHERE user_email = {PH}", (email,)))
        if existing:
            _exec(conn, f"""
                UPDATE icp_profiles SET
                    icp_industry = {PH}, icp_company_size = {PH}, icp_revenue_range = {PH},
                    icp_job_titles = {PH}, icp_decision_makers = {PH}, icp_pain_points = {PH},
                    icp_notes = {PH}, updated_at = {PH}
                WHERE user_email = {PH}
            """, (icp_industry, icp_company_size, icp_revenue_range,
                  titles_str, dm_str, pain_str, icp_notes, now, email))
        else:
            _exec(conn, f"""
                INSERT INTO icp_profiles
                (user_email, icp_industry, icp_company_size, icp_revenue_range,
                 icp_job_titles, icp_decision_makers, icp_pain_points, icp_notes, updated_at)
                VALUES ({PH}, {PH}, {PH}, {PH}, {PH}, {PH}, {PH}, {PH}, {PH})
            """, (email, icp_industry, icp_company_size, icp_revenue_range,
                  titles_str, dm_str, pain_str, icp_notes, now))
        _commit(conn)
    finally:
        conn.close()


# ── Activity Log Operations ──────────────────────────────────────────────────

def log_activity(email, activity_type, title, metadata=None):
    conn = get_db()
    now = datetime.utcnow().isoformat() + "Z"
    meta_str = json.dumps(metadata if isinstance(metadata, dict) else {})
    try:
        _exec(conn, f"""
            INSERT INTO activity_log (user_email, activity_type, title, metadata, created_at)
            VALUES ({PH}, {PH}, {PH}, {PH}, {PH})
        """, (email, activity_type, title, meta_str, now))
        _commit(conn)
    finally:
        conn.close()

def get_recent_activity(email, limit=20):
    conn = get_db()
    try:
        cur = _exec(conn, f"""
            SELECT * FROM activity_log 
            WHERE user_email = {PH} 
            ORDER BY created_at DESC 
            LIMIT {PH}
        """, (email, limit))
        rows = _fetchall(cur)
        for row in rows:
            val = row.get("metadata")
            if val:
                try:
                    row["metadata"] = json.loads(val)
                except Exception:
                    row["metadata"] = {}
            else:
                row["metadata"] = {}
        return rows
    finally:
        conn.close()


def update_cached_summary(email, summary, highlights):
    """Save the successfully generated AI summary and highlights to the cache."""
    conn = get_db()
    try:
        highlights_str = json.dumps(highlights if isinstance(highlights, list) else [])
        _exec(conn, f"""
            UPDATE company_metrics 
            SET ai_summary = {PH}, ai_highlights = {PH}
            WHERE user_email = {PH}
        """, (summary, highlights_str, email))
        _commit(conn)
    finally:
        conn.close()


# ── NEW v3 Enterprise Redesign Helpers ──────────────────────────────────
def get_or_create_workspace(email):
    import uuid
    conn = get_db()
    try:
        cur = _exec(conn, f"SELECT * FROM user_workspaces WHERE owner_email = {PH}", (email,))
        row = _fetchone(cur)
        if row:
            return row
        
        # Workspace does not exist, look up company profile info for sensible defaults
        cur_prof = _exec(conn, f"SELECT * FROM user_profiles WHERE user_email = {PH}", (email,))
        prof = _fetchone(cur_prof)
        
        company_name = prof.get("company_name", "My Company") if prof else "My Company"
        industry = prof.get("industry", "Technology") if prof else "Technology"
        sub_industry = prof.get("sub_industry", "") if prof else ""
        hq_country = prof.get("hq_country", "") if prof else ""
        geo_market = prof.get("geo_market", "") if prof else ""
        business_model = prof.get("business_model", "B2B") if prof else "B2B"
        if not business_model or business_model not in ('B2B', 'B2C', 'B2B2C', 'D2C', 'Marketplace'):
            business_model = "B2B"
        target_customer = prof.get("target_customer", "") if prof else ""
        founded_year = prof.get("founded_year", "") if prof else ""
        try:
            founded_year = int(founded_year) if founded_year else None
        except ValueError:
            founded_year = None
            
        ws_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat() + "Z"
        _exec(conn, f"""
            INSERT INTO user_workspaces (id, owner_email, company_name, industry, sub_industry, hq_country, geo_market, business_model, target_customer, founded_year, created_at, updated_at)
            VALUES ({PH}, {PH}, {PH}, {PH}, {PH}, {PH}, {PH}, {PH}, {PH}, {PH}, {PH}, {PH})
        """, (ws_id, email, company_name, industry, sub_industry, hq_country, geo_market, business_model, target_customer, founded_year, now, now))
        _commit(conn)
        
        cur = _exec(conn, f"SELECT * FROM user_workspaces WHERE id = {PH}", (ws_id,))
        return _fetchone(cur)
    finally:
        conn.close()

def get_market_size(workspace_id):
    conn = get_db()
    try:
        cur = _exec(conn, f"SELECT * FROM market_sizes WHERE workspace_id = {PH} ORDER BY updated_at DESC LIMIT 1", (workspace_id,))
        return _fetchone(cur)
    finally:
        conn.close()

def save_market_size(workspace_id, tam_value, sam_value, som_value, growth_rate_cagr=None, source_documentation="", currency="USD"):
    import uuid
    conn = get_db()
    try:
        # Check if one exists
        cur = _exec(conn, f"SELECT id FROM market_sizes WHERE workspace_id = {PH}", (workspace_id,))
        row = _fetchone(cur)
        now = datetime.utcnow().isoformat() + "Z"
        if row:
            # Update
            _exec(conn, f"""
                UPDATE market_sizes
                SET currency = {PH}, tam_value = {PH}, sam_value = {PH}, som_value = {PH}, growth_rate_cagr = {PH}, source_documentation = {PH}, updated_at = {PH}
                WHERE id = {PH}
            """, (currency, tam_value, sam_value, som_value, growth_rate_cagr, source_documentation, now, row["id"]))
            ms_id = row["id"]
        else:
            # Insert
            ms_id = str(uuid.uuid4())
            _exec(conn, f"""
                INSERT INTO market_sizes (id, workspace_id, currency, tam_value, sam_value, som_value, growth_rate_cagr, source_documentation, updated_at)
                VALUES ({PH}, {PH}, {PH}, {PH}, {PH}, {PH}, {PH}, {PH}, {PH})
            """, (ms_id, workspace_id, currency, tam_value, sam_value, som_value, growth_rate_cagr, source_documentation, now))
        _commit(conn)
        return ms_id
    finally:
        conn.close()

def get_competitor_profiles(workspace_id):
    conn = get_db()
    try:
        cur = _exec(conn, f"SELECT * FROM competitor_profiles WHERE workspace_id = {PH} ORDER BY market_share_pct DESC", (workspace_id,))
        rows = _fetchall(cur)
        for r in rows:
            # Deserialize JSON fields
            for field in ["strengths", "weaknesses"]:
                if r.get(field):
                    try:
                        r[field] = json.loads(r[field])
                    except Exception:
                        r[field] = []
                else:
                    r[field] = []
        return rows
    finally:
        conn.close()

def save_competitor_profile(workspace_id, name, market_share_pct=0.0, strengths=None, weaknesses=None, threat_level="Medium", innovation_score=50, pricing_score=50, reach_score=50, support_score=50, quality_score=50):
    import uuid
    conn = get_db()
    try:
        strengths_str = json.dumps(strengths if strengths else [])
        weaknesses_str = json.dumps(weaknesses if weaknesses else [])
        now = datetime.utcnow().isoformat() + "Z"
        
        # Check if competitor by this name already exists in this workspace
        cur = _exec(conn, f"SELECT id FROM competitor_profiles WHERE workspace_id = {PH} AND name = {PH}", (workspace_id, name))
        row = _fetchone(cur)
        
        if row:
            _exec(conn, f"""
                UPDATE competitor_profiles
                SET market_share_pct = {PH}, strengths = {PH}, weaknesses = {PH}, threat_level = {PH},
                    innovation_score = {PH}, pricing_score = {PH}, reach_score = {PH}, support_score = {PH}, quality_score = {PH}
                WHERE id = {PH}
            """, (market_share_pct, strengths_str, weaknesses_str, threat_level, innovation_score, pricing_score, reach_score, support_score, quality_score, row["id"]))
            comp_id = row["id"]
        else:
            comp_id = str(uuid.uuid4())
            _exec(conn, f"""
                INSERT INTO competitor_profiles (id, workspace_id, name, market_share_pct, strengths, weaknesses, threat_level, innovation_score, pricing_score, reach_score, support_score, quality_score, created_at)
                VALUES ({PH}, {PH}, {PH}, {PH}, {PH}, {PH}, {PH}, {PH}, {PH}, {PH}, {PH}, {PH}, {PH})
            """, (comp_id, workspace_id, name, market_share_pct, strengths_str, weaknesses_str, threat_level, innovation_score, pricing_score, reach_score, support_score, quality_score, now))
        _commit(conn)
        return comp_id
    finally:
        conn.close()

def get_market_opportunities(workspace_id):
    conn = get_db()
    try:
        cur = _exec(conn, f"SELECT * FROM market_opportunities WHERE workspace_id = {PH} ORDER BY impact_score DESC, estimated_revenue DESC", (workspace_id,))
        rows = _fetchall(cur)
        for r in rows:
            if r.get("required_capabilities"):
                try:
                    r["required_capabilities"] = json.loads(r["required_capabilities"])
                except Exception:
                    r["required_capabilities"] = []
            else:
                r["required_capabilities"] = []
        return rows
    finally:
        conn.close()

def save_market_opportunity(workspace_id, title, description, impact_score=5, effort_score=5, estimated_revenue=0.0, target_audience="", required_capabilities=None, status="discovered"):
    import uuid
    conn = get_db()
    try:
        cap_str = json.dumps(required_capabilities if required_capabilities else [])
        now = datetime.utcnow().isoformat() + "Z"
        
        # Check if opportunity by this title already exists in this workspace
        cur = _exec(conn, f"SELECT id FROM market_opportunities WHERE workspace_id = {PH} AND title = {PH}", (workspace_id, title))
        row = _fetchone(cur)
        
        if row:
            _exec(conn, f"""
                UPDATE market_opportunities
                SET description = {PH}, impact_score = {PH}, effort_score = {PH}, estimated_revenue = {PH},
                    target_audience = {PH}, required_capabilities = {PH}, status = {PH}
                WHERE id = {PH}
            """, (description, impact_score, effort_score, estimated_revenue, target_audience, cap_str, status, row["id"]))
            opp_id = row["id"]
        else:
            opp_id = str(uuid.uuid4())
            _exec(conn, f"""
                INSERT INTO market_opportunities (id, workspace_id, title, description, impact_score, effort_score, estimated_revenue, target_audience, required_capabilities, status, created_at)
                VALUES ({PH}, {PH}, {PH}, {PH}, {PH}, {PH}, {PH}, {PH}, {PH}, {PH}, {PH})
            """, (opp_id, workspace_id, title, description, impact_score, effort_score, estimated_revenue, target_audience, cap_str, status, now))
        _commit(conn)
        return opp_id
    finally:
        conn.close()

def get_strategic_recommendations(workspace_id):
    conn = get_db()
    try:
        cur = _exec(conn, f"SELECT * FROM strategic_recommendations WHERE workspace_id = {PH} ORDER BY priority DESC", (workspace_id,))
        rows = _fetchall(cur)
        for r in rows:
            if r.get("associated_tools"):
                try:
                    r["associated_tools"] = json.loads(r["associated_tools"])
                except Exception:
                    r["associated_tools"] = []
            else:
                r["associated_tools"] = []
        return rows
    finally:
        conn.close()

def save_strategic_recommendation(workspace_id, title, description, priority="Medium", timeframe_weeks=4, owner="", kpi_metric="", kpi_target=0.0, action_type="", associated_tools=None):
    import uuid
    conn = get_db()
    try:
        tools_str = json.dumps(associated_tools if associated_tools else [])
        now = datetime.utcnow().isoformat() + "Z"
        
        # Check if recommendation by this title already exists in this workspace
        cur = _exec(conn, f"SELECT id FROM strategic_recommendations WHERE workspace_id = {PH} AND title = {PH}", (workspace_id, title))
        row = _fetchone(cur)
        
        if row:
            _exec(conn, f"""
                UPDATE strategic_recommendations
                SET description = {PH}, priority = {PH}, timeframe_weeks = {PH}, owner = {PH},
                    kpi_metric = {PH}, kpi_target = {PH}, action_type = {PH}, associated_tools = {PH}
                WHERE id = {PH}
            """, (description, priority, timeframe_weeks, owner, kpi_metric, kpi_target, action_type, tools_str, row["id"]))
            rec_id = row["id"]
        else:
            rec_id = str(uuid.uuid4())
            _exec(conn, f"""
                INSERT INTO strategic_recommendations (id, workspace_id, title, description, priority, timeframe_weeks, owner, kpi_metric, kpi_target, action_type, associated_tools, created_at)
                VALUES ({PH}, {PH}, {PH}, {PH}, {PH}, {PH}, {PH}, {PH}, {PH}, {PH}, {PH}, {PH})
            """, (rec_id, workspace_id, title, description, priority, timeframe_weeks, owner, kpi_metric, kpi_target, action_type, tools_str, now))
        _commit(conn)
        return rec_id
    finally:
        conn.close()

def get_growth_simulations(workspace_id):
    conn = get_db()
    try:
        cur = _exec(conn, f"SELECT * FROM growth_simulations WHERE workspace_id = {PH} ORDER BY created_at DESC", (workspace_id,))
        rows = _fetchall(cur)
        for r in rows:
            for field in ["input_parameters", "simulation_output"]:
                if r.get(field):
                    try:
                        r[field] = json.loads(r[field])
                    except Exception:
                        r[field] = {}
                else:
                    r[field] = {}
        return rows
    finally:
        conn.close()

def save_growth_simulation(workspace_id, simulation_name, input_parameters, simulation_output):
    import uuid
    conn = get_db()
    try:
        params_str = json.dumps(input_parameters if input_parameters else {})
        out_str = json.dumps(simulation_output if simulation_output else {})
        now = datetime.utcnow().isoformat() + "Z"
        
        sim_id = str(uuid.uuid4())
        _exec(conn, f"""
            INSERT INTO growth_simulations (id, workspace_id, simulation_name, input_parameters, simulation_output, created_at)
            VALUES ({PH}, {PH}, {PH}, {PH}, {PH}, {PH})
        """, (sim_id, workspace_id, simulation_name, params_str, out_str, now))
        _commit(conn)
        return sim_id
    finally:
        conn.close()


def get_social_integrations(email):
    conn = get_db()
    try:
        cur = _exec(conn, f"SELECT platform, connected, username FROM social_integrations WHERE user_email = {PH}", (email,))
        rows = cur.fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def save_social_integration(email, platform, connected, username):
    conn = get_db()
    try:
        cur = _exec(conn, f"SELECT 1 FROM social_integrations WHERE user_email = {PH} AND platform = {PH}", (email, platform))
        exists = cur.fetchone()
        if exists:
            _exec(conn, f"""
                UPDATE social_integrations 
                SET connected = {PH}, username = {PH} 
                WHERE user_email = {PH} AND platform = {PH}
            """, (1 if connected else 0, username, email, platform))
        else:
            _exec(conn, f"""
                INSERT INTO social_integrations (user_email, platform, connected, username)
                VALUES ({PH}, {PH}, {PH}, {PH})
            """, (email, platform, 1 if connected else 0, username))
        _commit(conn)
        return True
    finally:
        conn.close()
