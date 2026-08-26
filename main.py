import json
import os
import threading
import discord
from discord.ext import commands
from flask import Flask

# --- WEB SERVER GIẢ LẬP ĐỂ CHẠY TRÊN VIBEHOST (PORT 2024) ---
app = Flask('')
bot_ready = False


@app.route('/')
def home():
  if bot_ready:
    return "Bot is running and online!", 200
  else:
    return "Bot is starting...", 200


def run_web():
  port = 2024  # Cố định port 2024 cho VibeHost
  app.run(host='0.0.0.0', port=port)


def keep_alive():
  t = threading.Thread(target=run_web)
  t.start()


# --- CẤU HÌNH BOT DISCORD ---
CONFIG_FILE = "config.json"


def load_config():
  if os.path.exists(CONFIG_FILE):
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
      try:
        return json.load(f)
      except:
        return {}
  return {}


def save_config(config_data):
  with open(CONFIG_FILE, "w", encoding="utf-8") as f:
    json.dump(config_data, f, ensure_ascii=False, indent=4)


intents = discord.Intents.default()
intents.members = True
intents.invites = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

invite_cache = {}
user_invites_count = {}


@bot.event
async def on_ready():
  global bot_ready
  bot_ready = True
  print(f"Logged in as {bot.user} (ID: {bot.user.id})")
  print("------")
  for guild in bot.guilds:
    try:
      invites = await guild.invites()
      invite_cache[guild.id] = {invite.code: invite.uses for invite in invites}
      print(f"Đã lưu cache invites cho server: {guild.name}")
    except discord.Forbidden:
      print(f"Không có quyền đọc invites ở server: {guild.name}")

  try:
    synced = await bot.tree.sync()
    print(f"Đã đồng bộ thành công {len(synced)} lệnh slash.")
  except Exception as e:
    print(e)


@bot.event
async def on_guild_invite_create(invite):
  if invite.guild.id not in invite_cache:
    invite_cache[invite.guild.id] = {}
  invite_cache[invite.guild.id][invite.code] = invite.uses


@bot.event
async def on_guild_invite_delete(invite):
  if (
      invite.guild.id in invite_cache
      and invite.code in invite_cache[invite.guild.id]
  ):
    del invite_cache[invite.guild.id][invite.code]


@bot.event
async def on_member_join(member):
  guild = member.guild
  data = load_config()
  guild_id_str = str(guild.id)

  conf = data.get(guild_id_str, {})
  channel_id = conf.get("channel_id")
  welcome_msg = conf.get("message", "Welcome {user}")
  gif_url = conf.get("gif_url", "")
  rewards = conf.get("rewards", {})

  inviter = None
  total_invited = 0

  try:
    old_invites = invite_cache.get(guild.id, {})
    new_invites = await guild.invites()

    # Cập nhật lại cache ngay lập tức
    invite_cache[guild.id] = {inv.code: inv.uses for inv in new_invites}

    # So sánh tìm ra mã invite bị tăng số lần sử dụng
    for new_inv in new_invites:
      old_uses = old_invites.get(new_inv.code, 0)
      if new_inv.uses > old_uses:
        inviter = new_inv.inviter
        print(
            f"👉 Phát hiện invite tăng: Code {new_inv.code} được dùng bởi"
            f" {inviter} (Tăng từ {old_uses} lên {new_inv.uses})"
        )
        break
  except Exception as e:
    print(f"❌ Lỗi khi track invite trong on_member_join: {e}")

  if inviter and not member.bot:
    if guild_id_str not in user_invites_count:
      user_invites_count[guild_id_str] = {}

    inviter_id_str = str(inviter.id)
    user_invites_count[guild_id_str][inviter_id_str] = (
        user_invites_count[guild_id_str].get(inviter_id_str, 0) + 1
    )
    total_invited = user_invites_count[guild_id_str][inviter_id_str]

    for count_str, role_id in rewards.items():
      if total_invited >= int(count_str):
        role = guild.get_role(int(role_id))
        if role:
          try:
            await inviter.add_roles(role)
          except Exception as ex:
            print(f"Không thể cấp role cho user: {ex}")

  # Gửi tin nhắn chào mừng độc lập
  if channel_id:
    channel = guild.get_channel(int(channel_id))
    if channel:
      formatted_msg = welcome_msg.replace("{user}", member.mention)
      if inviter:
        formatted_msg += (
            f" (Được mời bởi {inviter.mention} - Đã mời được {total_invited}"
            " người)"
        )

      embed = discord.Embed(
          description=formatted_msg, color=discord.Color.pink()
      )
      if gif_url:
        embed.set_image(url=gif_url)
      try:
        await channel.send(embed=embed)
      except Exception as ex:
        print(f"Không thể gửi tin nhắn chào mừng: {ex}")
  else:
    print("⚠️ Cảnh báo: Chưa cài đặt channel_id cho server này!")


# --- CÁC LỆNH SLASH ---


@bot.tree.command(
    name="set_channel", description="Cài đặt kênh gửi tin nhắn chào mừng"
)
@commands.has_permissions(administrator=True)
async def set_channel(
    interaction: discord.Interaction, channel: discord.TextChannel
):
  data = load_config()
  guild_id = str(interaction.guild_id)
  if guild_id not in data:
    data[guild_id] = {}
  data[guild_id]["channel_id"] = channel.id
  save_config(data)
  await interaction.response.send_message(
      f"✅ Đã cài đặt kênh chào mừng thành: {channel.mention}", ephemeral=True
  )


@bot.tree.command(
    name="set_welcome", description="Cài đặt câu chào mừng (Dùng {user})"
)
@commands.has_permissions(administrator=True)
async def set_welcome(interaction: discord.Interaction, *, message: str):
  data = load_config()
  guild_id = str(interaction.guild_id)
  if guild_id not in data:
    data[guild_id] = {}
  data[guild_id]["message"] = message
  save_config(data)
  await interaction.response.send_message(
      f"✅ Đã cập nhật câu chào:\n> {message}", ephemeral=True
  )


@bot.tree.command(name="set_gif", description="Cài đặt link ảnh GIF chào mừng")
@commands.has_permissions(administrator=True)
async def set_gif(interaction: discord.Interaction, url: str):
  data = load_config()
  guild_id = str(interaction.guild_id)
  if guild_id not in data:
    data[guild_id] = {}
  data[guild_id]["gif_url"] = url
  save_config(data)
  embed = discord.Embed(
      description="✅ Đã cập nhật ảnh GIF!", color=discord.Color.green()
  )
  embed.set_image(url=url)
  await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(
    name="set_reward",
    description="Cài đặt tự động thưởng role khi đạt mốc số lượng mời",
)
@commands.has_permissions(administrator=True)
async def set_reward(
    interaction: discord.Interaction, invites_count: int, role: discord.Role
):
  data = load_config()
  guild_id = str(interaction.guild_id)
  if guild_id not in data:
    data[guild_id] = {}
  if "rewards" not in data[guild_id]:
    data[guild_id]["rewards"] = {}

  data[guild_id]["rewards"][str(invites_count)] = role.id
  save_config(data)
  await interaction.response.send_message(
      f"✅ Đã thiết lập: Mời đủ **{invites_count}** người sẽ tự động nhận role"
      f" **{role.name}**!",
      ephemeral=True,
  )


@bot.tree.command(
    name="invites", description="Kiểm tra bạn đã mời được bao nhiêu người"
)
async def check_invites(
    interaction: discord.Interaction, member: discord.Member = None
):
  target = member or interaction.user
  guild_id_str = str(interaction.guild_id)

  count = 0
  if guild_id_str in user_invites_count:
    count = user_invites_count[guild_id_str].get(str(target.id), 0)

  await interaction.response.send_message(
      f"📊 Thành viên **{target.display_name}** đã mời được tổng cộng"
      f" **{count}** người vào server.",
      ephemeral=True,
  )


@bot.tree.command(
    name="test_welcome",
    description="Gửi tin nhắn chào mừng thử nghiệm để kiểm tra giao diện",
)
@commands.has_permissions(administrator=True)
async def test_welcome(interaction: discord.Interaction):
  data = load_config()
  guild_id_str = str(interaction.guild_id)
  conf = data.get(guild_id_str, {})

  channel_id = conf.get("channel_id")
  welcome_msg = conf.get("message", "Welcome {user}")
  gif_url = conf.get("gif_url", "")

  if not channel_id:
    await interaction.response.send_message(
        "❌ Bạn chưa cài đặt kênh chào mừng! Hãy dùng lệnh `/set_channel`"
        " trước.",
        ephemeral=True,
    )
    return

  channel = interaction.guild.get_channel(int(channel_id))
  if not channel:
    await interaction.response.send_message(
        "❌ Không tìm thấy kênh chào mừng đã cài đặt!", ephemeral=True
    )
    return

  formatted_msg = welcome_msg.replace("{user}", interaction.user.mention)
  formatted_msg += " (Được mời bởi @TestInviter - Đã mời được 1 người)"

  embed = discord.Embed(description=formatted_msg, color=discord.Color.pink())
  if gif_url:
    embed.set_image(url=gif_url)

  await channel.send(embed=embed)
  await interaction.response.send_message(
      "✅ Đã gửi tin nhắn test chào mừng vào kênh!", ephemeral=True
  )


# --- KHỞI CHẠY ---
if __name__ == "__main__":
  keep_alive()
  # Đã gán sẵn token chuẩn của bạn vào đây
  TOKEN = "MTU0MjE1NzYzNTY2MTQ3MTg4Ng.G5rSTI.KsQhAxODurEH2-9EqPC98U5EAGhVguN9XlQ_GQ"
  if TOKEN:
    bot.run(TOKEN)
  else:
    print("LỖI: Chưa cấu hình DISCORD_TOKEN!")
