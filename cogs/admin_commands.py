import discord
from discord import app_commands
from discord.ext import commands
import config

# Custom Check Function
def is_authorized():
    def predicate(interaction: discord.Interaction) -> bool:
        # Allow if user is Administrator OR has the specific Role
        if interaction.user.guild_permissions.administrator:
            return True
        if interaction.user.get_role(config.ALLOWED_ROLE_ID):
            return True
        return False
    return app_commands.check(predicate)

class AdminCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ════════════════════════════════════════════════════════════════════
    #                       RESTRICTED COMMANDS
    #           (Usable by Admin OR Users with ALLOWED_ROLE_ID)
    # ════════════════════════════════════════════════════════════════════

    @app_commands.command(name="setglobalcut", description="Set global staff cut percentage")
    @is_authorized()  # <--- USES THE NEW CHECK
    async def setglobalcut(self, interaction: discord.Interaction, percent: int):
        if not 0 <= percent <= 100: 
            return await interaction.response.send_message("❌ Percent must be 0-100.", ephemeral=True)
        
        await self.bot.db.execute("INSERT OR REPLACE INTO config (key, value) VALUES ('global_percent', ?)", (percent,))
        await self.bot.db.commit()
        
        interval = int(100/percent) if percent > 0 else 0
        await interaction.response.send_message(f"✅ **Global Staff Cut** updated to **{percent}%**.\nThis results in a cut every **{interval}th** claim.", ephemeral=True)

    @app_commands.command(name="setusercut", description="Set specific user percentage")
    @is_authorized()  # <--- USES THE NEW CHECK
    async def setusercut(self, interaction: discord.Interaction, user: discord.User, percent: int):
        if not 0 <= percent <= 100: 
            return await interaction.response.send_message("❌ Percent must be 0-100.", ephemeral=True)
        
        await self.bot.db.execute("INSERT OR REPLACE INTO user_overrides (user_id, cut_percentage) VALUES (?, ?)", (user.id, percent))
        await self.bot.db.commit()
        await interaction.response.send_message(f"✅ **{user.name}** is now set to **{percent}%** staff cut chance (Overrides global).", ephemeral=True)

    @app_commands.command(name="resetusercut", description="Reset a user to global settings")
    @is_authorized()  # <--- USES THE NEW CHECK
    async def resetusercut(self, interaction: discord.Interaction, user: discord.User):
        await self.bot.db.execute("DELETE FROM user_overrides WHERE user_id = ?", (user.id,))
        await self.bot.db.commit()
        await interaction.response.send_message(f"✅ **{user.name}** reset to global settings.", ephemeral=True)

    # ════════════════════════════════════════════════════════════════════
    #                       PUBLIC COMMANDS
    # ════════════════════════════════════════════════════════════════════

    @app_commands.command(name="claimstats", description="View stats for the server or any user")
    async def claimstats(self, interaction: discord.Interaction, user: discord.User = None):
        await interaction.response.defer(ephemeral=True)

        async with self.bot.db.execute("SELECT value FROM config WHERE key='global_percent'") as cur:
            row = await cur.fetchone()
            g_percent = row[0] if row else config.DEFAULT_GLOBAL_PERCENT

        if user:
            async with self.bot.db.execute("SELECT cut_percentage FROM user_overrides WHERE user_id=?", (user.id,)) as cur: ovr = await cur.fetchone()
            async with self.bot.db.execute("SELECT COUNT(*) FROM claims WHERE claimed_by=? AND is_claimed=1", (user.id,)) as cur: total = (await cur.fetchone())[0]
            async with self.bot.db.execute("SELECT COUNT(*) FROM claims WHERE claimed_by=? AND is_staff_cut=1", (user.id,)) as cur: cuts = (await cur.fetchone())[0]
            
            embed = discord.Embed(title=f"📊 Stats: {user.display_name}", color=config.COLOR_INFO)
            embed.set_thumbnail(url=user.display_avatar.url)
            embed.add_field(name="Total Claims", value=str(total))
            embed.add_field(name="Staff Cuts", value=str(cuts))
            rate = f"**{ovr[0]}%** (Override)" if ovr else f"**{g_percent}%** (Global)"
            embed.add_field(name="Cut Rate", value=rate, inline=False)
            await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            async with self.bot.db.execute("SELECT COUNT(*) FROM claims WHERE is_claimed=1") as cur: total = (await cur.fetchone())[0]
            async with self.bot.db.execute("SELECT COUNT(*) FROM claims WHERE is_claimed=1 AND is_staff_cut=1") as cur: cuts = (await cur.fetchone())[0]
            embed = discord.Embed(title="📊 Server Stats", color=config.COLOR_INFO)
            embed.add_field(name="Total Claims", value=str(total))
            embed.add_field(name="Staff Cuts", value=str(cuts))
            embed.add_field(name="Global Rate", value=f"{g_percent}%")
            await interaction.followup.send(embed=embed, ephemeral=True)

    # ════════════════════════════════════════════════════════════════════
    #                       ERROR HANDLING
    # ════════════════════════════════════════════════════════════════════

    @setglobalcut.error
    @setusercut.error
    @resetusercut.error
    async def admin_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.CheckFailure):
            await interaction.response.send_message("❌ **Access Denied:** You need the restricted Staff Role to use this.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ An unknown error occurred.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(AdminCommands(bot))
