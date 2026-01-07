"""Connectivity test script for Clothify bot startup validation."""

import asyncio
import os
import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    import asyncpg
    import discord
    import aiohttp
    from bot.config import Config
except ImportError as e:
    print(f"❌ Missing dependency: {e}")
    sys.exit(1)


class ConnectivityTester:
    """Test connectivity to required services on bot startup."""
    
    def __init__(self):
        self.results = []
        self.all_passed = True
        
    def log(self, emoji: str, service: str, status: str, details: str = ""):
        """Log test result."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        msg = f"[{timestamp}] {emoji} {service:<15} {status}"
        if details:
            msg += f" - {details}"
        print(msg)
        self.results.append((service, status, details))
        
    async def test_postgres(self) -> bool:
        """Test PostgreSQL connection."""
        try:
            db_url = os.getenv("DATABASE_URL")
            if not db_url:
                self.log("⚠️", "PostgreSQL", "SKIP", "DATABASE_URL not set")
                return False
                
            # Parse connection string
            conn = await asyncio.wait_for(
                asyncpg.connect(db_url),
                timeout=5.0
            )
            
            # Test query (non-intrusive)
            version = await conn.fetchval("SELECT version()")
            pg_version = version.split()[1] if version else "unknown"
            
            await conn.close()
            self.log("✅", "PostgreSQL", "OK", f"v{pg_version}")
            return True
            
        except asyncio.TimeoutError:
            self.log("❌", "PostgreSQL", "TIMEOUT", "Connection timeout (5s)")
            self.all_passed = False
            return False
        except Exception as e:
            self.log("❌", "PostgreSQL", "ERROR", str(e)[:50])
            self.all_passed = False
            return False
    
    async def test_discord(self) -> bool:
        """Test Discord API connectivity (without logging in)."""
        try:
            token = os.getenv("DISCORD_TOKEN")
            if not token:
                self.log("⚠️", "Discord API", "SKIP", "DISCORD_TOKEN not set")
                return False
            
            # Test Discord API endpoint (lightweight, no actual login)
            async with aiohttp.ClientSession() as session:
                headers = {"Authorization": f"Bot {token}"}
                async with session.get(
                    "https://discord.com/api/v10/users/@me",
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        bot_name = data.get("username", "Unknown")
                        self.log("✅", "Discord API", "OK", f"Bot: {bot_name}")
                        return True
                    else:
                        self.log("❌", "Discord API", "ERROR", f"HTTP {resp.status}")
                        self.all_passed = False
                        return False
                        
        except asyncio.TimeoutError:
            self.log("❌", "Discord API", "TIMEOUT", "Connection timeout (5s)")
            self.all_passed = False
            return False
        except Exception as e:
            self.log("❌", "Discord API", "ERROR", str(e)[:50])
            self.all_passed = False
            return False
    
    async def test_n8n(self) -> bool:
        """Test n8n API connectivity (optional)."""
        try:
            n8n_port = os.getenv("N8N_PORT", "5678")
            n8n_url = f"http://n8n:{n8n_port}/healthz"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    n8n_url,
                    timeout=aiohttp.ClientTimeout(total=3)
                ) as resp:
                    if resp.status == 200:
                        self.log("✅", "n8n", "OK", f"port {n8n_port}")
                        return True
                    else:
                        self.log("⚠️", "n8n", "WARN", f"HTTP {resp.status}")
                        return False
                        
        except asyncio.TimeoutError:
            self.log("⚠️", "n8n", "TIMEOUT", "Not critical")
            return False
        except Exception as e:
            self.log("⚠️", "n8n", "UNREACHABLE", "Not critical")
            return False
    
    async def test_volume_access(self) -> bool:
        """Test shared volume read/write access."""
        try:
            # Use Config constants (derived from SHARED_VOLUME_PATH)
            input_dir = Config.INPUT_DIR
            output_dir = Config.OUTPUT_DIR
            
            # Test read access
            if not os.path.exists(input_dir):
                self.log("❌", "Volume (input)", "ERROR", f"{input_dir} not found")
                self.all_passed = False
                return False
            
            if not os.path.exists(output_dir):
                self.log("❌", "Volume (output)", "ERROR", f"{output_dir} not found")
                self.all_passed = False
                return False
            
            # Test write access (create temporary file, then delete)
            test_file = os.path.join(input_dir, ".connectivity_test")
            try:
                with open(test_file, 'w') as f:
                    f.write("test")
                os.remove(test_file)
                self.log("✅", "Volume Access", "OK", "Read/Write verified")
                return True
            except PermissionError:
                self.log("❌", "Volume Access", "ERROR", "No write permission")
                self.all_passed = False
                return False
                
        except Exception as e:
            self.log("❌", "Volume Access", "ERROR", str(e)[:50])
            self.all_passed = False
            return False
    
    async def run_all_tests(self) -> bool:
        """Run all connectivity tests."""
        print("\n" + "="*60)
        print("🔍 Clothify Bot - Connectivity Tests")
        print("="*60 + "\n")
        
        # Critical tests (must pass)
        await self.test_postgres()
        await self.test_discord()
        await self.test_volume_access()
        
        # Optional tests (warnings only)
        await self.test_n8n()
        
        print("\n" + "="*60)
        if self.all_passed:
            print("✅ All critical tests passed - Bot starting...")
        else:
            print("❌ Some critical tests failed - Check configuration")
        print("="*60 + "\n")
        
        return self.all_passed


async def main():
    """Run connectivity tests."""
    tester = ConnectivityTester()
    success = await tester.run_all_tests()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
