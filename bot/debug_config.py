"""Debug script to verify configuration and paths."""

import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from bot.config import Config

print("="*60)
print("🔍 Clothify Configuration Debug")
print("="*60)
print()

print("📂 PATH CONFIGURATION:")
print(f"  SHARED_VOLUME_PATH: {Config.SHARED_VOLUME_PATH}")
print(f"  INPUT_DIR:          {Config.INPUT_DIR}")
print(f"  OUTPUT_DIR:         {Config.OUTPUT_DIR}")
print()

print("📁 DIRECTORY EXISTENCE:")
input_path = Path(Config.INPUT_DIR)
output_path = Path(Config.OUTPUT_DIR)

print(f"  {Config.INPUT_DIR}")
if input_path.exists():
    print(f"    ✅ Exists")
    print(f"    📊 Permissions: {oct(input_path.stat().st_mode)[-3:]}")
    print(f"    👤 Owner UID:   {input_path.stat().st_uid}")
    print(f"    👥 Group GID:   {input_path.stat().st_gid}")
else:
    print(f"    ❌ Does NOT exist")
print()

print(f"  {Config.OUTPUT_DIR}")
if output_path.exists():
    print(f"    ✅ Exists")
    print(f"    📊 Permissions: {oct(output_path.stat().st_mode)[-3:]}")
    print(f"    👤 Owner UID:   {output_path.stat().st_uid}")
    print(f"    👥 Group GID:   {output_path.stat().st_gid}")
else:
    print(f"    ❌ Does NOT exist")
print()

print("🔐 WRITE TEST:")
test_file = input_path / ".write_test"
try:
    test_file.write_text("test")
    test_file.unlink()
    print(f"  ✅ Can write to {Config.INPUT_DIR}")
except Exception as e:
    print(f"  ❌ Cannot write to {Config.INPUT_DIR}")
    print(f"     Error: {e}")
print()

print("🐍 PYTHON PROCESS:")
import os
print(f"  Current UID: {os.getuid()}")
print(f"  Current GID: {os.getgid()}")
print(f"  Current User: {os.getenv('USER', 'unknown')}")
print()

print("="*60)
