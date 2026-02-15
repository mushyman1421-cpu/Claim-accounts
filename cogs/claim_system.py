# cogs/claim_system.py
import discord
from discord.ext import commands
import datetime
import json
import random
import config
import utils

class RedeemModal(discord.ui.Modal, title="🔐  Verify & Redeem"):
    answer = discord.ui.TextInput(label="Account Username", placeholder="Type the exact username...", required=True, max_length=150)

    def __init__(self, bot, claim_id: int, real_username: str, source_msg_id: int | None):
        super().__init__()
        self.bot = bot
        self.claim_id = claim_id
        self.real_username = real_username
        self.source_msg_id = source_msg_id

    async def on_submit(self, interaction: discord.Interaction):
        if self.answer.value.strip().lower() != self.real_username.lower():
            return await interaction.response.send_message("❌ **Incorrect Username.**", ephemeral=True)

        await interaction.response.defer(ephemeral=True)

        async with self.bot.db.execute("SELECT is_claimed, embed_data FROM claims WHERE id = ?", (self.claim_id,)) as cur:
            row = await cur.fetchone()
        if not row or row[0]: return await interaction.followup.send("❌ **Already Claimed.**", ephemeral=True)

        embed_data = json.loads(row[1])
        now = datetime.datetime.utcnow()

        # Logic
        is_staff_cut = False
        override_active = False

        async with self.bot.db.execute("SELECT cut_percentage FROM user_overrides WHERE user_id = ?", (interaction.user.id,)) as cur:
            user_ovr = await cur.fetchone()

        if user_ovr:
            override_active = True
            if random.randint(1, 100) <= user_ovr[0]: is_staff_cut = True
        else:
            async with self.bot.db.execute("SELECT value FROM config WHERE key = 'global_percent'") as cur:
                g_percent = (await cur.fetchone())[0]
            async with self.bot.db.execute("SELECT value FROM config WHERE key = 'claim_counter'") as cur:
                next_count = (await cur.fetchone())[0] + 1

            if g_percent > 0:
                if next_count % int(100 / g_percent) == 0: is_staff_cut = True

        full_embed = utils.rebuild_full_embed(embed_data)
        full_embed.timestamp = now
        full_embed.set_footer(text=f"Claim ID: #{self.claim_id}")

        if is_staff_cut:
            staff_ch = self.bot.get_channel(config.STAFF_CUT_CHANNEL_ID)
            if staff_ch:
                full_embed.title = "👮 Staff Cut Allocated"
                trigger = "User Override (RNG)" if override_active else "Global Interval"
                full_embed.description = f"**Trigger:** {interaction.user.mention}\n**Type:** {trigger}\n\n" + (full_embed.description or "")
                full_embed.color = config.COLOR_STAFF
                await staff_ch.send(embed=full_embed)
            await interaction.followup.send(embed=discord.Embed(title="📋 Staff Cut", description="Allocated to staff pool.", color=config.COLOR_STAFF), ephemeral=True)
        else:
            full_embed.title = "🎉 Account Details"
            try:
                await interaction.user.send(embed=full_embed)
                await interaction.followup.send(embed=discord.Embed(title="✅ Success", description="Check DMs!", color=config.COLOR_SUCCESS), ephemeral=True)
            except:
                return await interaction.followup.send(embed=discord.Embed(title="⚠️ DMs Disabled", description="Enable DMs.", color=config.COLOR_WARNING), ephemeral=True)

        await self.bot.db.execute("UPDATE config SET value = value + 1 WHERE key = 'claim_counter'")
        is_cut_int = 1 if is_staff_cut else 0
        await self.bot.db.execute("UPDATE claims SET is_claimed=1, claimed_by=?, claimed_by_name=?, claimed_at=?, is_staff_cut=? WHERE id=?", 
                             (interaction.user.id, str(interaction.user), now.isoformat(), is_cut_int, self.claim_id))
        
        action = "STAFF_CUT" if is_staff_cut else "CLAIMED"
        await self.bot.db.execute("INSERT INTO claim_logs (claim_id, account_username, claimed_by, claimed_by_name, action, is_staff_cut) VALUES (?, ?, ?, ?, ?, ?)",
                             (self.claim_id, self.real_username, interaction.user.id, str(interaction.user), action, is_cut_int))
        await self.bot.db.commit()

        await self._disable_button(interaction, now)

    async def _disable_button(self, interaction, now):
        try:
            ch = self.bot.get_channel(config.CLAIM_CHANNEL_ID)
            if self.source_msg_id and ch:
                msg = await ch.fetch_message(self.source_msg_id)
                view = discord.ui.View()
                view.add_item(discord.ui.Button(label="Claimed", style=discord.ButtonStyle.grey, disabled=True, emoji="✅"))
                embed = msg.embeds[0]
                embed.color = discord.Color.dark_grey()
                updated = False
                for idx, f in enumerate(embed.fields):
                    if "status" in f.name.lower():
                        embed.set_field_at(idx, name=f.name, value=f"🔴 Claimed by {interaction.user.name}", inline=f.inline)
                        updated = True
                if not updated: embed.add_field(name="📌 Status", value=f"🔴 Claimed by {interaction.user.name}")
                await msg.edit(embed=embed, view=view)
        except: pass

class RedeemView(discord.ui.View):
    def __init__(self, bot, claim_id: int):
        super().__init__(timeout=None)
        self.bot = bot
        self.claim_id = claim_id
        btn = discord.ui.Button(label="Redeem", style=discord.ButtonStyle.green, emoji="🎁", custom_id=f"redeem_{claim_id}")
        btn.callback = self._on_click
        self.add_item(btn)

    async def _on_click(self, interaction: discord.Interaction):
        async with self.bot.db.execute("SELECT is_claimed, account_username FROM claims WHERE id = ?", (self.claim_id,)) as cur:
            row = await cur.fetchone()
        if not row: return await interaction.response.send_message("❌ Missing.", ephemeral=True)
        if row[0]: return await interaction.response.send_message("❌ Claimed.", ephemeral=True)
        await interaction.response.send_modal(RedeemModal(self.bot, self.claim_id, row[1], interaction.message.id))

class ClaimSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        # Restore buttons
        async with self.bot.db.execute("SELECT id FROM claims WHERE is_claimed = 0 AND message_id IS NOT NULL") as cur:
            rows = await cur.fetchall()
        for row in rows:
            self.bot.add_view(RedeemView(self.bot, row[0]))
        print(f"Restored {len(rows)} buttons.")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.channel.id != config.SOURCE_CHANNEL_ID or message.author.id != config.SOURCE_BOT_ID: return
        if not message.embeds or not message.embeds[0].title.startswith("Account secured"): return

        embed = message.embeds[0]
        username = next((f.value.strip() for f in embed.fields if "username" in f.name.lower()), None)
        if not username: return
        
        masked = utils.mask_username(username)
        data = utils.serialize_embed(embed)

        async with self.bot.db.execute("INSERT INTO claims (account_username, masked_username, embed_data) VALUES (?, ?, ?)", (username, masked, data)) as cur:
            claim_id = cur.lastrowid
        await self.bot.db.commit()

        claim_embed = discord.Embed(title="🔒 New Account Available", description="Click Redeem to claim.", color=config.COLOR_DEFAULT)
        claim_embed.add_field(name="👤 Username", value=f"`{masked}`", inline=True)
        claim_embed.add_field(name="🆔 Claim ID", value=f"`#{claim_id}`", inline=True)
        claim_embed.add_field(name="📌 Status", value="🟢 Available", inline=True)
        
        for f in embed.fields:
            if "username" not in f.name.lower(): claim_embed.add_field(name=f.name, value=f"||{f.value[:50]}||", inline=f.inline)

        ch = self.bot.get_channel(config.CLAIM_CHANNEL_ID)
        if ch:
            msg = await ch.send(embed=claim_embed, view=RedeemView(self.bot, claim_id))
            await self.bot.db.execute("UPDATE claims SET message_id = ? WHERE id = ?", (msg.id, claim_id))
            await self.bot.db.commit()

async def setup(bot):
    await bot.add_cog(ClaimSystem(bot))

