"""
Database initialization script.
Creates all database tables in SQLite or PostgreSQL.
"""

from db.database import engine, Base
# Import models to register them
from db.models import QueryLog, Recommendation, Collaboration, ProjectSuggestion, Feedback, FacultyWorkload
from core.logger import logger

def init_database():
    """Create all relational database tables."""
    logger.info("Initializing database schema...")
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully.")
        
        # Check/add role column to query_logs for backwards compatibility
        from sqlalchemy import text
        from db.database import SessionLocal
        db = SessionLocal()
        try:
            db.execute(text("ALTER TABLE query_logs ADD COLUMN role VARCHAR(50) DEFAULT 'student'"))
            db.commit()
            logger.info("Migrated database: role column added to query_logs.")
        except Exception:
            # Column already exists or other database engines where it's handled differently
            db.rollback()
        finally:
            db.close()
        
        # Seed workloads if table is empty
        from db.database import SessionLocal
        db = SessionLocal()
        try:
            if db.query(FacultyWorkload).count() == 0:
                logger.info("Seeding initial faculty workloads...")
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
                logger.info("Faculty workloads seeded successfully.")
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
