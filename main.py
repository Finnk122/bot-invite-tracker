import os
from threading import Thread
import discord
from discord.ext import commands
from flask import Flask

# --- PHẦN 1: TẠO WEB SERVER FLASK (GIỮ BOT ONLINE 24/7) ---
app = Flask('')


@app.route('/')
def home():
  Template = "Bot is running!"
  return Template


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


# Ví dụ lệnh test của bạn
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


# --- PHẦN 3: CHẠY BOT ---
# ĐIỀN TOKEN THẬT CỦA BẠN VÀO TRONG DẤU NHÁY KÉP BÊN DƯỚI:
TOKEN = "DÁN_TOKEN_BOT_CỦA_BẠN_VÀO_ĐÂY"

if __name__ == "__main__":
  # Khởi động web Flask chạy ngầm trước
  keep_alive()
  # Sau đó chạy bot Discord
  bot.run(TOKEN)
