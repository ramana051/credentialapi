"""
Database migration utilities for the Digital Credentials Platform.
"""

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from alembic.environment import EnvironmentContext
from sqlalchemy import create_engine, text
import os
import logging

from .config import settings
from .database import Base, engine
from .models import *  # Import all models to ensure they're registered

logger = logging.getLogger(__name__)


def create_migration(message: str, autogenerate: bool = True):
    """Create a new migration file."""
    alembic_cfg = Config("alembic.ini")
    command.revision(alembic_cfg, message=message, autogenerate=autogenerate)


def upgrade_database(revision: str = "head"):
    """Upgrade database to a specific revision."""
    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, revision)


def downgrade_database(revision: str):
    """Downgrade database to a specific revision."""
    alembic_cfg = Config("alembic.ini")
    command.downgrade(alembic_cfg, revision)


def get_current_revision():
    """Get current database revision."""
    alembic_cfg = Config("alembic.ini")
    script = ScriptDirectory.from_config(alembic_cfg)
    
    with engine.connect() as connection:
        context = EnvironmentContext(alembic_cfg, script)
        context.configure(connection=connection)
        return context.get_current_revision()


def init_database():
    """Initialize database with all tables."""
    try:
        # Create all tables
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
        
        # Create initial data if needed
        create_initial_data()
        
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        raise


def create_initial_data():
    """Create initial data for the application."""
    from sqlalchemy.orm import sessionmaker
    from .models import User, Organization, UserRole
    from .utils import hash_password
    
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # Check if super admin already exists
        super_admin = session.query(User).filter(
            User.role == UserRole.SUPER_ADMIN
        ).first()
        
        if not super_admin:
            # Create default super admin
            admin_user = User(
                email="admin@digitalcredentials.com",
                username="admin",
                first_name="Super",
                last_name="Admin",
                password_hash=hash_password("admin123"),  # Change this in production
                role=UserRole.SUPER_ADMIN,
                is_active=True,
                is_verified=True
            )
            session.add(admin_user)
            
            # Create default organization
            default_org = Organization(
                name="Digital Credentials Platform",
                slug="dcp-default",
                description="Default organization for the Digital Credentials Platform",
                is_verified=True
            )
            session.add(default_org)
            
            session.commit()
            logger.info("Initial data created successfully")
        else:
            logger.info("Initial data already exists")
            
    except Exception as e:
        session.rollback()
        logger.error(f"Error creating initial data: {e}")
        raise
    finally:
        session.close()


def backup_database(backup_path: str):
    """Create a database backup."""
    import subprocess
    
    try:
        # Extract database connection details
        db_url = settings.database_url
        # Parse the URL to extract components
        # This is a simplified version - you might want to use urllib.parse
        
        cmd = [
            "pg_dump",
            db_url,
            "-f", backup_path,
            "--verbose"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            logger.info(f"Database backup created successfully: {backup_path}")
        else:
            logger.error(f"Database backup failed: {result.stderr}")
            raise Exception(f"Backup failed: {result.stderr}")
            
    except Exception as e:
        logger.error(f"Error creating database backup: {e}")
        raise


def restore_database(backup_path: str):
    """Restore database from backup."""
    import subprocess
    
    try:
        if not os.path.exists(backup_path):
            raise FileNotFoundError(f"Backup file not found: {backup_path}")
        
        # Extract database connection details
        db_url = settings.database_url
        
        cmd = [
            "psql",
            db_url,
            "-f", backup_path,
            "--verbose"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            logger.info(f"Database restored successfully from: {backup_path}")
        else:
            logger.error(f"Database restore failed: {result.stderr}")
            raise Exception(f"Restore failed: {result.stderr}")
            
    except Exception as e:
        logger.error(f"Error restoring database: {e}")
        raise


def check_database_health():
    """Check database connectivity and health."""
    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            if result.fetchone()[0] == 1:
                logger.info("Database health check passed")
                return True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False


if __name__ == "__main__":
    # Command line interface for database operations
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python migrations.py <command>")
        print("Commands: init, upgrade, downgrade, backup, restore, health")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "init":
        init_database()
    elif command == "upgrade":
        revision = sys.argv[2] if len(sys.argv) > 2 else "head"
        upgrade_database(revision)
    elif command == "downgrade":
        if len(sys.argv) < 3:
            print("Downgrade requires a revision")
            sys.exit(1)
        downgrade_database(sys.argv[2])
    elif command == "backup":
        if len(sys.argv) < 3:
            print("Backup requires a file path")
            sys.exit(1)
        backup_database(sys.argv[2])
    elif command == "restore":
        if len(sys.argv) < 3:
            print("Restore requires a file path")
            sys.exit(1)
        restore_database(sys.argv[2])
    elif command == "health":
        if check_database_health():
            print("Database is healthy")
        else:
            print("Database health check failed")
            sys.exit(1)
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)

