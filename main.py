import os
from threading import Thread
import discord
from discord.ext import commands
from flask import Flask

# --- PHẦN 1: TẠO WEB SERVER FLASK (GIỮ BOT ONLINE) ---
app = Flask('')


@app.route('/')
def home():
  return "Bot is running!"


def run_flask():
  # Chạy port 2024 theo cấu hình của VibeHost
  app.run(host='0.0.0.0', port=2024)


def keep_alive():
  t = Thread(target=run_flask)
  t.start()


# --- PHẦN 2: CẤU HÌNH BOT DISCORD ---
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
  print(f'Logged in as {bot.user} (ID: {bot.user.id})')
  print('------')


# Lệnh test welcome của bạn
@bot.tree.command(
    name="test_welcome", description="Test tính năng chào mừng"
)
async def test_welcome(interaction: discord.Interaction):
  await interaction.response.send_message(
      "Bot hoạt động bình thường!", ephemeral=True
  )


@bot.event
async def setup_hook():
  try:
    synced = await bot.tree.sync()
    print(f'Đã đồng bộ {len(synced)} lệnh slash.')
  except Exception as e:
    print(e)


# --- PHẦN 3: TOKEN VÀ KHỞI ĐỘNG ---
TOKEN = "MTU0MjE1NzYzNTY2MTQ3MTg4Ng.G5rSTI.KsQhAxODurEH2-9EqPC98U5EAGhVguN9XlQ_GQ"

if __name__ == "__main__":
  # Khởi động web Flask chạy ngầm
  keep_alive()
  # Khởi động bot Discord
  bot.run(TOKEN)
