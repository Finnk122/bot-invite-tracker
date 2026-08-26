import os
import discord

intents = discord.Intents.default()
intents.members = True          # Bật quyền đọc thành viên
intents.guilds = True           # Bật quyền quản lý server
intents.invites = True          # Bật quyền đọc link mời

client = discord.Client(intents=intents)

# Biến lưu trữ số lượng lượt dùng của các link mời trước đó
invites_cache = {}

@client.event
async def on_ready():
    print(f'Bot đã đăng nhập thành công dưới tên: {client.user}')
    # Khi bot khởi động, lưu lại toàn bộ invite hiện tại của các server
    for guild in client.guilds:
        try:
            invites_cache[guild.id] = await guild.invites()
        except discord.Forbidden:
            print(f'Không có quyền đọc invite ở server: {guild.name}')

@client.event
async def on_invite_create(invite):
    # Cập nhật lại cache khi có link mời mới được tạo
    try:
        invites_cache[invite.guild.id] = await invite.guild.invites()
    except:
        pass

@client.event
async def on_invite_delete(invite):
    # Cập nhật lại cache khi có link mời bị xóa
    try:
        invites_cache[invite.guild.id] = await invite.guild.invites()
    except:
        pass

@client.event
async def on_member_join(member):
    guild = member.guild
    
    # Lấy danh sách invite cũ đã lưu
    old_invites = invites_cache.get(guild.id, [])
    
    try:
        # Lấy danh sách invite mới nhất ở thời điểm hiện tại
        new_invites = await guild.invites()
    except discord.Forbidden:
        return

    # Cập nhật lại cache mới
    invites_cache[guild.id] = new_invites

    # Tìm xem link nào đã bị tăng số lượt sử dụng (uses) lên 1
    used_invite = None
    for old_inv in old_invites:
        for new_inv in new_invites:
            if old_inv.code == new_inv.code:
                if new_inv.uses > old_inv.uses:
                    used_invite = new_inv
                    break
        if used_invite:
            break

    # Tìm kênh chat chung đầu tiên trong server để gửi thông báo
    target_channel = None
    for channel in guild.text_channels:
        if channel.permissions_for(guild.me).send_messages:
            target_channel = channel
            break

    # Gửi tin nhắn thông báo kết quả
    if target_channel:
        if used_invite:
            inviter = used_invite.inviter
            await target_channel.send(
                f"👋 Chào mừng **{member.mention}** đã tham gia server!\n"
                f"🔗 Người mời: **{inviter.name}** (Link mời: `{used_invite.code}`, số lần dùng: `{used_invite.uses}`)"
            )
        else:
            await target_channel.send(
                f"👋 Chào mừng **{member.mention}** đã tham gia server!\n"
                f"🔗 (Không xác định được rõ người mời hoặc dùng link tùy chỉnh/vanity URL)."
            )

# Lấy token an toàn từ cấu hình môi trường của hệ thống đám mây
TOKEN = os.getenv('DISCORD_TOKEN')
client.run(TOKEN)