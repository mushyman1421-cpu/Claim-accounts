# utils.py
import discord
import json
import datetime
import config

def mask_username(username: str) -> str:
    """Dynamic masking based on length."""
    length = len(username)
    if length <= 3: visible = 1
    elif length <= 7: visible = 2
    else: visible = 4
    
    if visible >= length: visible = length - 1
    if visible < 1: visible = 1

    return username[:visible] + "*" * (length - visible)

def serialize_embed(embed: discord.Embed) -> str:
    return json.dumps({
        "title": embed.title, "description": embed.description, "color": embed.color.value if embed.color else None,
        "url": embed.url, "fields": [{"name": f.name, "value": f.value, "inline": f.inline} for f in embed.fields],
        "footer_text": embed.footer.text if embed.footer else None, "footer_icon": str(embed.footer.icon_url) if embed.footer else None,
        "thumbnail": str(embed.thumbnail.url) if embed.thumbnail else None, "image": str(embed.image.url) if embed.image else None,
        "author_name": embed.author.name if embed.author else None, "timestamp": embed.timestamp.isoformat() if embed.timestamp else None,
    })

def rebuild_full_embed(data: dict) -> discord.Embed:
    embed = discord.Embed(title=data.get("title") or "Account Details", description=data.get("description"), color=data.get("color") or config.COLOR_SUCCESS, url=data.get("url"))
    for f in data.get("fields", []): embed.add_field(name=f["name"], value=f["value"], inline=f.get("inline", False))
    if data.get("thumbnail"): embed.set_thumbnail(url=data["thumbnail"])
    if data.get("image"): embed.set_image(url=data["image"])
    if data.get("footer_text"): embed.set_footer(text=data["footer_text"], icon_url=data.get("footer_icon"))
    if data.get("author_name"): embed.set_author(name=data["author_name"])
    if data.get("timestamp"):
        try: embed.timestamp = datetime.datetime.fromisoformat(data["timestamp"])
        except: pass
    return embed

def format_timestamp(dt: datetime.datetime) -> str:
    return dt.strftime("%m/%d/%Y %I:%M %p UTC")
