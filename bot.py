import discord
from discord.ext import commands
import sqlite3
import json

# Load config
with open("config.json") as f:
    config = json.load(f)

BOT_TOKEN = config.get("bot_token")
ADMIN_ROLE = config.get("admin_role", "Admin")
TICKET_ROLE = config.get("ticket_role", "Customer")  # role allowed to open tickets
WEBHOOKS = config.get("webhooks", {})

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)

# --- SQLite setup ---
conn = sqlite3.connect("data.db")
c = conn.cursor()
c.execute("""
CREATE TABLE IF NOT EXISTS tickets (
    ticket_id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER,
    user_id INTEGER,
    channel_id INTEGER,
    status TEXT
)
""")
conn.commit()

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")

@bot.command(name="guide")
async def guide(ctx):
    guide_pages = [
        discord.Embed(title="Ticket Bot Setup Guide — Part 1", color=discord.Color.blue())
        .add_field(name="1️⃣ Create your Discord Bot",
                   value=(
                    "- Go to https://discord.com/developers/applications\n"
                    "- Click **New Application** → Name it → Create\n"
                    "- Under **Bot**, click **Add Bot** → Confirm\n"
                    "- Enable **Message Content Intent** and **Server Members Intent**\n"
                    "- Copy your bot token (keep it secret!)"
                   ), inline=False),

        discord.Embed(title="Ticket Bot Setup Guide — Part 2", color=discord.Color.blue())
        .add_field(name="2️⃣ Invite your Bot to your Server",
                   value=(
                    "- Go to **OAuth2** → **URL Generator**\n"
                    "- Select scope **bot**\n"
                    "- Under permissions, add:\n"
                    "  • Manage Channels\n  • Manage Roles\n  • Send Messages\n  • Read Message History\n  • Manage Messages\n"
                    "- Copy the generated URL, open it, invite bot to your server."
                   ), inline=False),

        discord.Embed(title="Ticket Bot Setup Guide — Part 3", color=discord.Color.blue())
        .add_field(name="3️⃣ Prepare your config.json",
                   value=(
                    "Create `config.json` in your bot folder:\n```json\n{\n"
                    '  "bot_token": "YOUR_BOT_TOKEN_HERE",\n'
                    '  "admin_role": "Admin",\n'
                    '  "ticket_role": "Member",\n'
                    '  "open_webhook": "YOUR_OPEN_WEBHOOK_URL",\n'
                    '  "close_webhook": "YOUR_CLOSE_WEBHOOK_URL"\n}\n```\n'
                    "- Replace tokens, roles, and webhook URLs with your own."
                   ), inline=False),

        discord.Embed(title="Ticket Bot Setup Guide — Part 4", color=discord.Color.blue())
        .add_field(name="4️⃣ Run & Setup",
                   value=(
                    "- Run your bot: `python bot.py`\n"
                    "- Run `!setup` command with Admin role to create categories & channels.\n"
                    "- Bot creates `data.db` automatically.\n"
                    "- Roles & permissions must be set properly."
                   ), inline=False),

        discord.Embed(title="Ticket Bot Setup Guide — Part 5", color=discord.Color.blue())
        .add_field(name="5️⃣ Using the Bot",
                   value=(
                    "- Users run `!open <reason>` to open tickets.\n"
                    "- Admins run `!close [#channel]` to close tickets.\n"
                    "- Logs go to channels `logs/open` and `logs/close` and via webhooks."
                   ), inline=False),

        discord.Embed(title="Support", color=discord.Color.blue())
        .add_field(name="Need help?",
                   value="If you encounter any issues, check console logs and permissions.\nFeel free to ask for help!",
                   inline=False),
    ]

    try:
        for embed in guide_pages:
            await ctx.author.send(embed=embed)
        await ctx.send(f"📬 {ctx.author.mention}, I sent you a detailed setup guide via DM.")
    except discord.Forbidden:
        # Fallback to channel (send all pages with delay)
        await ctx.send(f"📄 {ctx.author.mention}, I couldn't DM you. Here is the guide:")
        for embed in guide_pages:
            await ctx.send(embed=embed)
            
# --- Setup command ---
@bot.command(name="setup")
@commands.has_role(ADMIN_ROLE)
async def setup(ctx):
    guild = ctx.guild

    logs_cat = discord.utils.get(guild.categories, name="logs")
    if not logs_cat:
        logs_cat = await guild.create_category("logs")

    tickets_cat = discord.utils.get(guild.categories, name="tickets")
    if not tickets_cat:
        tickets_cat = await guild.create_category("tickets")

    open_ch = discord.utils.get(logs_cat.channels, name="open")
    if not open_ch:
        open_ch = await logs_cat.create_text_channel("open")

    close_ch = discord.utils.get(logs_cat.channels, name="close")
    if not close_ch:
        close_ch = await logs_cat.create_text_channel("close")

    embed = discord.Embed(
        title="✅ Setup Completed",
        description=(
            f"Created categories and channels:\n"
            f"- Category: {logs_cat.name}\n"
            f"- Category: {tickets_cat.name}\n"
            f"- Channel: {open_ch.mention}\n"
            f"- Channel: {close_ch.mention}\n\n"
            "**Important:** Please create webhooks manually in these channels and add their URLs to `config.json`."
        ),
        color=discord.Color.green()
    )
    await ctx.send(embed=embed)

# --- open ticket command ---
@bot.command(name="open")
@commands.has_role(TICKET_ROLE)
async def open_ticket(ctx, *, reason: str = None):
    if reason is None:
        await ctx.send("❌ Please provide a reason. Example: `!open I need help with billing`")
        return

    guild = ctx.guild

    # Get or validate ticket category
    tickets_cat = discord.utils.get(guild.categories, name="tickets")
    if not tickets_cat:
        await ctx.send("❌ Tickets category doesn't exist. Please run `!setup` first.")
        return

    # Prevent duplicate tickets
    for channel in tickets_cat.channels:
        if channel.topic == f"user_id:{ctx.author.id}":
            await ctx.send(f"❌ You already have an open ticket: {channel.mention}")
            return

    # Permissions
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        ctx.author: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        discord.utils.get(guild.roles, name=ADMIN_ROLE): discord.PermissionOverwrite(read_messages=True, send_messages=True)
    }

    # Create ticket channel
    ticket_channel = await tickets_cat.create_text_channel(
        f"ticket-{ctx.author.name}", overwrites=overwrites, topic=f"user_id:{ctx.author.id}"
    )

    # Save to database
    c.execute("INSERT INTO tickets (guild_id, user_id, channel_id, status) VALUES (?, ?, ?, ?)",
              (guild.id, ctx.author.id, ticket_channel.id, "open"))
    conn.commit()

    created_at = ticket_channel.created_at.strftime("%Y-%m-%d %H:%M:%S UTC")

    # Embed for ticket channel (user)
    embed_user = discord.Embed(
        title="🎫 Ticket Opened!",
        color=discord.Color.green(),
        timestamp=discord.utils.utcnow()
    )
    embed_user.add_field(name="User ID", value=f"`{ctx.author.id}`", inline=False)
    embed_user.add_field(name="Channel ID", value=f"`{ticket_channel.id}`", inline=False)
    embed_user.add_field(name="Reason", value=reason, inline=False)
    embed_user.add_field(name="Created At", value=created_at, inline=False)

    await ticket_channel.send(embed=embed_user)

    # Embed for logs channel
    logs_cat = discord.utils.get(guild.categories, name="logs")
    open_log_ch = discord.utils.get(logs_cat.channels, name="open") if logs_cat else None

    if open_log_ch:
        embed_log = discord.Embed(
            title="📥 Ticket Opened (Log)",
            color=discord.Color.blue(),
            timestamp=discord.utils.utcnow()
        )
        embed_log.add_field(name="User ID", value=f"`{ctx.author.id}`", inline=True)
        embed_log.add_field(name="Channel ID", value=f"`{ticket_channel.id}`", inline=True)
        embed_log.add_field(name="Reason", value=reason, inline=False)
        embed_log.add_field(name="Created At", value=created_at, inline=False)

        await open_log_ch.send(embed=embed_log)



# --- close ticket command ---
@bot.command(name="close")
@commands.has_role(ADMIN_ROLE)
async def close_ticket(ctx, channel: discord.TextChannel = None):
    channel = channel or ctx.channel
    guild = ctx.guild

    c.execute("SELECT user_id FROM tickets WHERE channel_id = ? AND status = 'open'", (channel.id,))
    row = c.fetchone()
    if not row:
        await ctx.send("❌ This channel is not an open ticket.")
        return

    user_id = row[0]
    c.execute("UPDATE tickets SET status = ? WHERE channel_id = ?", ("closed", channel.id))
    conn.commit()

    logs_cat = discord.utils.get(guild.categories, name="logs")
    close_ch = discord.utils.get(logs_cat.channels, name="close") if logs_cat else None

    ticket_user = await bot.fetch_user(user_id)
    channel_obj = guild.get_channel(channel.id)

    msg_count = 0
    async for _ in channel_obj.history(limit=None):
        msg_count += 1

    created_at = channel.created_at
    closed_at = discord.utils.utcnow()

    embed = discord.Embed(
        title="📁 Ticket Closed",
        color=discord.Color.red(),
        timestamp=closed_at
    )
    embed.add_field(name="User ID", value=f"`{user_id}`", inline=False)
    embed.add_field(name="Channel ID", value=f"`{channel.id}`", inline=False)
    embed.add_field(name="Created At", value=created_at.strftime("%Y-%m-%d %H:%M:%S UTC"), inline=False)
    embed.add_field(name="Closed At", value=closed_at.strftime("%Y-%m-%d %H:%M:%S UTC"), inline=False)
    embed.add_field(name="Number of Messages", value=str(msg_count), inline=False)

    await ctx.send(embed=embed)
    if close_ch:
        await close_ch.send(embed=embed)

    await channel.delete()


# --- Error handling ---
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingRole):
        await ctx.send(f"❌ You do not have the required role to use this command.")
    elif isinstance(error, commands.CommandNotFound):
        await ctx.send("❌ Unknown command.")
    else:
        raise error

# Run bot with token from config
bot.run(BOT_TOKEN)
