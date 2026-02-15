# bot.py
import discord
from discord.ext import commands
import aiosqlite
import logging
import sys
import config
from database import init_database

# Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s │ %(levelname)-8s │ %(message)s", datefmt="%Y-%m-%d %H:%M:%S", handlers=[logging.StreamHandler(sys.stdout)])
logger = logging.getLogger("ClaimBot")

class ClaimBot(commands.Bot):
    def __init__(self) -> None:
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        super().__init__(command_prefix="!", intents=intents, activity=discord.Activity(type=discord.ActivityType.watching, name="accounts"))
        self.db: aiosqlite.Connection = None

    async def setup_hook(self) -> None:
        # DB Setup
        self.db = await aiosqlite.connect(config.DATABASE_FILE)
        self.db.row_factory = aiosqlite.Row
        await init_database(self.db)
        
        # Load Cogs
        await self.load_extension("cogs.claim_system")
        await self.load_extension("cogs.admin_commands")
        
        await self.tree.sync()
        logger.info("Bot Ready & Cogs Loaded")

    async def close(self) -> None:
        if self.db: await self.db.close()
        await super().close()

bot = ClaimBot()

if __name__ == "__main__":
    bot.run(config.BOT_TOKEN)

