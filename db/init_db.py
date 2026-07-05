"""
Database initialization script.
Creates all database tables in SQLite or PostgreSQL.
"""

from db.database import engine, cache_engine, Base
# Import models to register them
from db.models import QueryLog, Recommendation, Collaboration, ProjectSuggestion, Feedback, FacultyWorkload, PaperEnrichment, SemanticCache, ChatMessage, PaperChat, FacultyChat, Announcement
from core.logger import logger

def init_database():
    """Create all relational database tables."""
    logger.info("Initializing database schema...")
    try:
        # Define tables for student history (main DB - e.g. Supabase)
        history_tables = [
            QueryLog.__table__,
            Recommendation.__table__,
            Collaboration.__table__,
            ProjectSuggestion.__table__,
            Feedback.__table__,
            ChatMessage.__table__,   # Chat turns for both student and faculty
            PaperChat.__table__,     # Student-Teacher paper discussions
            FacultyChat.__table__,   # Direct student-to-faculty DM messages
            Announcement.__table__,  # Faculty announcements
        ]
        # Define tables for local cache and workloads (local SQLite)
        cache_tables = [
            FacultyWorkload.__table__,
            PaperEnrichment.__table__,
            SemanticCache.__table__
        ]

        # Create tables on respective engines
        Base.metadata.create_all(bind=engine, tables=history_tables)
        Base.metadata.create_all(bind=cache_engine, tables=cache_tables)
        logger.info("Database tables created successfully on main and local cache engines.")
        
        # Backwards-compatible column migrations using ALTER TABLE (silently ignored if already present)
        from sqlalchemy import text
        from db.database import SessionLocal
        db = SessionLocal()
        migrations = [
            ("ALTER TABLE query_logs ADD COLUMN role VARCHAR(50) DEFAULT 'student'",
             "role column added to query_logs"),
            ("ALTER TABLE query_logs ADD COLUMN session_id VARCHAR(100)",
             "session_id column added to query_logs"),
            ("ALTER TABLE query_logs ADD COLUMN sources_used TEXT",
             "sources_used column added to query_logs"),
            ("ALTER TABLE announcements ADD COLUMN category VARCHAR(100)",
             "category column added to announcements"),
            ("ALTER TABLE announcements ADD COLUMN priority VARCHAR(50) DEFAULT 'Low'",
             "priority column added to announcements"),
            ("ALTER TABLE announcements ADD COLUMN attachment VARCHAR(500)",
             "attachment column added to announcements"),
            ("ALTER TABLE announcements ADD COLUMN target_audience VARCHAR(100) DEFAULT 'All'",
             "target_audience column added to announcements"),
            ("ALTER TABLE announcements ADD COLUMN target_dept VARCHAR(100)",
             "target_dept column added to announcements"),
            ("ALTER TABLE announcements ADD COLUMN target_year VARCHAR(100)",
             "target_year column added to announcements"),
            ("ALTER TABLE announcements ADD COLUMN target_sec VARCHAR(100)",
             "target_sec column added to announcements"),
            ("ALTER TABLE announcements ADD COLUMN expiry_date VARCHAR(100)",
             "expiry_date column added to announcements"),
            ("ALTER TABLE announcements ADD COLUMN status VARCHAR(50) DEFAULT 'published'",
             "status column added to announcements"),
        ]
        for sql, label in migrations:
            try:
                db.execute(text(sql))
                db.commit()
                logger.info(f"Migrated database: {label}.")
            except Exception:
                # Column already exists or unsupported by the target engine – safe to ignore
                db.rollback()
        db.close()
        
        # Seed workloads into the local cache database if empty
        from db.database import CacheSessionLocal
        db = CacheSessionLocal()
        try:
            if db.query(FacultyWorkload).count() == 0:
                logger.info("Seeding initial faculty workloads in local SQLite cache...")
                workloads = [
                    FacultyWorkload(
                        faculty_name="shirina samreen",
                        active_projects=3,
                        project_titles=["Trust Management in MANETs", "Refinement of Recommendation Trust", "Attack Patterns in Ad Hoc Networks"]
                    ),
                    FacultyWorkload(
                        faculty_name="akhil jabbar meerja",
                        active_projects=2,
                        project_titles=["Refinement of Recommendation Trust", "Security in MANETs"]
                    ),
                    FacultyWorkload(
                        faculty_name="jaishree agrawal",
                        active_projects=1,
                        project_titles=["Software Engineering Practices"]
                    ),
                    FacultyWorkload(
                        faculty_name="nimesh raj",
                        active_projects=1,
                        project_titles=["Network Security"]
                    ),
                    FacultyWorkload(
                        faculty_name="gagandeep",
                        active_projects=2,
                        project_titles=["IoT based Health Monitoring", "Blockchain Security"]
                    )
                ]
                db.add_all(workloads)
                db.commit()
                logger.info("Faculty workloads seeded successfully in local SQLite cache.")
        except Exception as e:
            logger.error(f"Error seeding workloads: {e}")
            db.rollback()
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        raise

if __name__ == "__main__":
    init_database()
