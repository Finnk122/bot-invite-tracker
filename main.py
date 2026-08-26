import os
import json
import discord
from discord.ext import commands
from flask import Flask
import threading

# --- PHẦN GIẢ LẬP WEB SERVER ĐỂ QUA MẶT RENDER ---
app = Flask('')

@app.route('/')
def home():
    return "Bot is running 24/7!"

def run_web():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = threading.Thread(target=run_web)
    t.start()


# --- PHẦN CHÍNH CỦA BOT DISCORD ---
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

# Cache lưu trữ invite: {guild_id: {code: uses}} và thống kê: {guild_id: {user_id: count}}
invite_cache = {}
user_invites_count = {}

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    print("------")
    for guild in bot.guilds:
        try:
            invites = await guild.invites()
            invite_cache[guild.id] = {invite.code: invite.uses for invite in invites}
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
    if invite.guild.id in invite_cache and invite.code in invite_cache[invite.guild.id]:
        del invite_cache[invite.guild.id][invite.code]

@bot.event
async def on_member_join(member):
    guild = member.guild
    data = load_config()
    guild_id_str = str(guild.id)
    
    conf = data.get(guild_id_str, {})
    channel_id = conf.get("channel_id")
    welcome_msg = conf.get("message", "Welcome in {user} hello con vợ")
    gif_url = conf.get("gif_url", "https://media.giphy.com/media/3o7TKSjRrfIPjeiOkM/giphy.gif")
    rewards = conf.get("rewards", {}) # Lưu dạng {"5": role_id_1, "10": role_id_2}

    # Tìm người mời
    inviter = None
    try:
        old_invites = invite_cache.get(guild.id, {})
        new_invites = await guild.invites()
        invite_cache[guild.id] = {inv.code: inv.uses for inv in new_invites}
        
        for new_inv in new_invites:
            if new_inv.code in old_invites:
                if new_inv.uses > old_invites[new_inv.code]:
                    inviter = new_inv.inviter
                    break
    except Exception as e:
        print(f"Lỗi khi track invite: {e}")

    # Cập nhật số lượng người mà inviter đã mời được
    total_invited = 0
    if inviter and not member.bot:
        if guild_id_str not in user_invites_count:
            user_invites_count[guild_id_str] = {}
        
        inviter_id_str = str(inviter.id)
        user_invites_count[guild_id_str][inviter_id_str] = user_invites_count[guild_id_str].get(inviter_id_str, 0) + 1
        total_invited = user_invites_count[guild_id_str][inviter_id_str]

        # Kiểm tra trao role tự động theo mốc số lượng
        for count_str, role_id in rewards.items():
            if total_invited >= int(count_str):
                role = guild.get_role(int(role_id))
                if role:
                    try:
                        await inviter.add_roles(role)
                    except Exception as ex:
                        print(f"Không thể cấp role cho user: {ex}")

    # Gửi tin nhắn chào mừng nếu có cài đặt kênh
    if channel_id:
        channel = guild.get_channel(int(channel_id))
        if channel:
            formatted_msg = welcome_msg.replace("{user}", member.mention)
            if inviter:
                formatted_msg += f" (Được mời bởi {inviter.mention} - Đã mời được {total_invited} người)"

            embed = discord.Embed(description=formatted_msg, color=discord.Color.pink())
            if gif_url:
                embed.set_image(url=gif_url)
            await channel.send(embed=embed)


# --- CÁC LỆNH SLASH ---

@bot.tree.command(name="set_channel", description="Cài đặt kênh gửi tin nhắn chào mừng")
@commands.has_permissions(administrator=True)
async def set_channel(interaction: discord.Interaction, channel: discord.TextChannel):
    data = load_config()
    guild_id = str(interaction.guild_id)
    if guild_id not in data: data[guild_id] = {}
    data[guild_id]["channel_id"] = channel.id
    save_config(data)
    await interaction.response.send_message(f"✅ Đã cài đặt kênh chào mừng thành: {channel.mention}", ephemeral=True)

@bot.tree.command(name="set_welcome", description="Cài đặt câu chào mừng (Dùng {user})")
@commands.has_permissions(administrator=True)
async def set_welcome(interaction: discord.Interaction, *, message: str):
    data = load_config()
    guild_id = str(interaction.guild_id)
    if guild_id not in data: data[guild_id] = {}
    data[guild_id]["message"] = message
    save_config(data)
    await interaction.response.send_message(f"✅ Đã cập nhật câu chào:\n> {message}", ephemeral=True)

@bot.tree.command(name="set_gif", description="Cài đặt link ảnh GIF chào mừng")
@commands.has_permissions(administrator=True)
async def set_gif(interaction: discord.Interaction, url: str):
    data = load_config()
    guild_id = str(interaction.guild_id)
    if guild_id not in data: data[guild_id] = {}
    data[guild_id]["gif_url"] = url
    save_config(data)
    embed = discord.Embed(description="✅ Đã cập nhật ảnh GIF!", color=discord.Color.green())
    embed.set_image(url=url)
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="set_reward", description="Cài đặt tự động thưởng role khi đạt mốc số lượng mời")
@commands.has_permissions(administrator=True)
async def set_reward(interaction: discord.Interaction, invites_count: int, role: discord.Role):
    data = load_config()
    guild_id = str(interaction.guild_id)
    if guild_id not in data: data[guild_id] = {}
    if "rewards" not in data[guild_id]: data[guild_id]["rewards"] = {}
    
    data[guild_id]["rewards"][str(invites_count)] = role.id
    save_config(data)
    await interaction.response.send_message(f"✅ Đã thiết lập: Mời đủ **{invites_count}** người sẽ tự động nhận role **{role.name}**!", ephemeral=True)

@bot.tree.command(name="invites", description="Kiểm tra bạn (hoặc người khác) đã mời được bao nhiêu người")
async def check_invites(interaction: discord.Interaction, member: discord.Member = None):
    target = member or interaction.user
    guild_id_str = str(interaction.guild_id)
    
    count = 0
    if guild_id_str in user_invites_count:
        count = user_invites_count[guild_id_str].get(str(target.id), 0)
        
    await interaction.response.send_message(f"📊 Thành viên **{target.display_name}** đã mời được tổng cộng **{count}** người vào server.", ephemeral=True)

# --- KHỞI CHẠY CHƯƠNG TRÌNH ---
if __name__ == "__main__":
    keep_alive()  # Chạy server ẩn để qua mặt Render
    TOKEN = os.getenv("DISCORD_TOKEN")
    if TOKEN:
        bot.run(TOKEN)
    else:
        print("LỖI: Chưa cấu hình DISCORD_TOKEN trong Environment Variables!")
