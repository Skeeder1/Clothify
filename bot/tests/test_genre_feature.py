#!/usr/bin/env python3
"""Test de validation statique de la fonctionnalité genre."""

import sys
import re
from pathlib import Path

def test_views_file():
    """Valider que views.py contient les changements nécessaires."""
    views_path = Path(__file__).parent.parent / "handlers" / "views.py"
    content = views_path.read_text()
    
    checks = [
        ("PendingUpload has genre field", r"genre:\s*Optional\[str\]\s*=\s*None"),
        ("GenreSelectView class exists", r"class\s+GenreSelectView\(discord\.ui\.View\)"),
        ("genre_homme button exists", r"async\s+def\s+genre_homme"),
        ("genre_femme button exists", r"async\s+def\s+genre_femme"),
        ("handle_genre_selection method exists", r"async\s+def\s+handle_genre_selection"),
        ("GarmentSelect sends GenreSelectView", r"GenreSelectView\(user_id\)"),
    ]
    
    results = []
    for description, pattern in checks:
        if re.search(pattern, content):
            print(f"✅ {description}")
            results.append(True)
        else:
            print(f"❌ {description}")
            results.append(False)
    
    return all(results)

def test_database_file():
    """Valider que database.py contient les changements nécessaires."""
    db_path = Path(__file__).parent.parent / "database.py"
    content = db_path.read_text()
    
    checks = [
        ("create_job has genre parameter", r"genre:\s*Optional\[str\]\s*=\s*None"),
        ("INSERT includes genre column", r"INSERT\s+INTO\s+jobs\s*\([^)]*genre[^)]*\)"),
        ("VALUES includes genre value", r"VALUES\s*\([^)]*\$6[^)]*\)"),
    ]
    
    results = []
    for description, pattern in checks:
        if re.search(pattern, content, re.DOTALL | re.IGNORECASE):
            print(f"✅ {description}")
            results.append(True)
        else:
            print(f"❌ {description}")
            results.append(False)
    
    return all(results)

def test_migration_file():
    """Valider que le fichier de migration existe."""
    migration_path = Path(__file__).parent.parent.parent / "Database" / "scripts" / "migrations" / "005_add_gender_column.sql"
    
    if migration_path.exists():
        content = migration_path.read_text()
        if "ALTER TABLE jobs ADD COLUMN" in content and "genre" in content:
            print("✅ Migration file exists and contains ALTER TABLE")
            return True
    
    print("❌ Migration file missing or incomplete")
    return False

if __name__ == "__main__":
    print("🔍 Testing genre selection feature implementation...\n")
    
    print("📄 Testing bot/handlers/views.py:")
    views_ok = test_views_file()
    
    print("\n📄 Testing bot/database.py:")
    db_ok = test_database_file()
    
    print("\n📄 Testing Database/scripts/migrations/005_add_gender_column.sql:")
    migration_ok = test_migration_file()
    
    print("\n" + "="*60)
    if views_ok and db_ok and migration_ok:
        print("🎉 All validations passed! Genre feature is properly implemented.")
        sys.exit(0)
    else:
        print("❌ Some validations failed. Please review the implementation.")
        sys.exit(1)
