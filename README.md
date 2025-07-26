# Ticket Bot Setup Guide

- **Current version: 1.0**

## Change Log

### Version 1.0
- Initial release with ticket open/close system
- Webhook logging for ticket open and close events
- SQLite database tracking user tickets with details (reason, timestamps, roles)
- Commands: `!setup`, `!open <reason>`, `!close [channel]`, `!guide`
- Role-based permission control for admins and ticket users

---

## 1. Create Your Discord Bot and Get Token
- Go to [Discord Developer Portal](https://discord.com/developers/applications)
- Click **New Application**, name it, and create
- Go to **Bot** tab → **Add Bot**
- Copy the **Token** — you'll need it for your config file

## 2. Invite the Bot to Your Server
- Go to **OAuth2** → **URL Generator**
- Select **bot** scope
- Under **Bot Permissions**, check:
  - Manage Channels
  - Send Messages
  - Read Message History
  - Manage Messages
  - Mention Everyone
- Copy the generated URL, open it, and invite the bot to your server

## 3. Prepare `config.json`
Create a file called `config.json` in your bot folder, with this structure:

```json
{
  "bot_token": "YOUR_BOT_TOKEN_HERE",
  "admin_role": "Admin",
  "ticket_role": "Member",
  "open_webhook": "YOUR_OPEN_WEBHOOK_URL",
  "close_webhook": "YOUR_CLOSE_WEBHOOK_URL"
}
```
## 4. Requirements

- **DB Browser (SQLLite)** (download from [sqlitebrowser.org](https://sqlitebrowser.org/dl/))
- **Python 3.8+** (download from [python.org](https://www.python.org/downloads/))
- **discord.py** library  
  Install with:
  ```bash
  pip install discord.py
  ```
