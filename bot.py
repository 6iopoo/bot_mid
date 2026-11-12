import os
import ssl
import random
import asyncio
import discord
from discord.ext import commands, tasks
from discord.ui import Button, View, Select
from threading import Thread
from flask import Flask

app = Flask('')

@app.route('/')
def home():
    return "Midnight Bot is Running!"

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_web_server)
    t.start()

if not os.environ.get("PYTHONHTTPSVERIFY", "") and getattr(ssl, "_create_unverified_context", None):
    ssl._create_default_https_context = ssl._create_unverified_context

intents = discord.Intents.all()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

WINNING_IMAGE_URL = "https://imgur.com"
TICKET_CHANNEL_ID = 1570094397771489311
protection_status = True
is_bot_paused = False

@bot.check
async def check_bot_active(ctx):
    if is_bot_paused:
        await ctx.send("⏳ البوت في فترة راحة وصيانة تلقائية لمدة 5 دقائق، سيعود للعمل قريباً.", delete_after=10)
        return False
    return True

@tasks.loop(hours=24)
async def auto_rest_cycle():
    global is_bot_paused
    is_bot_paused = True
    await bot.change_presence(status=discord.Status.invisible)
    print("⏸️ تم إيقاف نشاط البوت مؤقتاً لمدة 5 دقائق...")
    await asyncio.sleep(300)
    is_bot_paused = False
    await bot.change_presence(status=discord.Status.online, activity=discord.Game(name="Midnight Bot | #cmd"))
    print("▶️ عاد البوت للعمل ونشاطه الطبيعي الآن!")

@auto_rest_cycle.before_loop
async def before_auto_rest():
    await bot.wait_until_ready()
    await asyncio.sleep(86400)
class CloseTicketView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="إغلاق التيكيت 🔒", style=discord.ButtonStyle.red, custom_id="close_ticket_btn")
    async def close_ticket(self, interaction: discord.Interaction, button: Button):
        is_admin = interaction.user.guild_permissions.manage_channels or interaction.user == interaction.guild.owner
        if not is_admin:
            await interaction.response.send_message("❌ هذا الإجراء مخصص للإدارة فقط.", ephemeral=True)
            return
        await interaction.response.send_message("🔒 سيتم إغلاق هذه التيكيت وحذف الغرفة خلال 5 ثوانٍ...")
        await asyncio.sleep(5)
        await interaction.channel.delete()

class TicketTypeSelect(Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="دعم فني", description="للمساعدة والمشاكل التقنية بالسيرفر", emoji="🛠️"),
            discord.SelectOption(label="شكوى", description="لرفع شكوى ضد عضو أو مشكلة معينة", emoji="⚠️"),
            discord.SelectOption(label="تقديم طلب", description="لتقديم طلبات الانضمام أو رتب معينة", emoji="📝"),
            discord.SelectOption(label="إدارة", description="للتحدث مع الإدارة العليا مباشرة", emoji="👑"),
        ]
        super().__init__(placeholder="👉 اختر نوع الخدمة المطلوبة هنا...", min_values=1, max_values=1, options=options, custom_id="ticket_type_select")

    async def callback(self, interaction: discord.Interaction):
        if is_bot_paused:
            await interaction.response.send_message("⏳ البوت في فترة راحة لمدة 5 دقائق، يرجى المحاولة بعد قليل.", ephemeral=True)
            return
        selected_service = self.values[0]
        guild = interaction.guild
        user = interaction.user
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True, embed_links=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        ticket_channel = await guild.create_text_channel(
            name=f"ticket-{selected_service}-{user.name}",
            overwrites=overwrites,
            reason=f"فتح تيكيت بواسطة {user.name}"
        )
        await interaction.response.send_message(f"✅ تم إنشاء التيكيت الخاصة بك بنجاح: {ticket_channel.mention}", ephemeral=True)
        embed = discord.Embed(
            title=f"🎫 تيكيت جديدة | قسم {selected_service}",
            description=f"مرحباً بك {user.mention} في قسم الخدمة والدعم المباشر.\nيرجى كتابة مشكلتك أو استفسارك هنا وسيقوم فريق العمل بالرد عليك في أقرب وقت ممكن.",
            color=discord.Color.green()
        )
        await ticket_channel.send(content=f"{user.mention} | الإدارة", embed=embed, view=CloseTicketView())

class TicketMainView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="فتح تيكيت 🎫", style=discord.ButtonStyle.blurple, custom_id="open_ticket_btn")
    async def open_ticket(self, interaction: discord.Interaction, button: Button):
        if is_bot_paused:
            await interaction.response.send_message("⏳ البوت في فترة راحة لمدة 5 دقائق، يرجى المحاولة بعد قليل.", ephemeral=True)
            return
        view = View()
        view.add_item(TicketTypeSelect())
        await interaction.response.send_message("الرجاء اختيار القسم الذي تود التواصل معه من القائمة أدناه:", view=view, ephemeral=True)

@bot.event
async def on_ready():
    if not discord.opus.is_loaded():
        try:
            discord.opus.load_opus()
        except:
            pass
    print(f"✅ تم تشغيل البوت بنجاح باسم: {bot.user}")
    await bot.change_presence(status=discord.Status.online, activity=discord.Game(name="Midnight Bot | #cmd"))
    if not auto_rest_cycle.is_running():
        auto_rest_cycle.start()
    channel = bot.get_channel(TICKET_CHANNEL_ID)
    if channel:
        try:
            await channel.purge(limit=10)
            embed = discord.Embed(
                title="⚡ نظام الدعم الفني والتذاكر ⚡",
                description="**موجـود في خدمتك**\n\nاضغط على الزر بالأسفل لفتح تذكرة وتحديد القسم المطلوب للتواصل مع الإدارة مباشرة.",
                color=discord.Color.from_rgb(10, 10, 10)
            )
            embed.set_image(url="https://adobe.com")
            await channel.send(embed=embed, view=TicketMainView())
            print("✅ تم إرسال لوحة التيكيت بنجاح.")
        except Exception as e:
            print(f"❌ فشل إرسال لوحة التيكيت: {e}")

@bot.event
async def on_member_join(member):
    global protection_status
    if is_bot_paused:
        return
    if member.bot and protection_status:
        try:
            await member.kick(reason="الحماية التلقائية: غير مسموح بدخول البوتات التطبيقية المزعجة.")
        except:
            pass

@bot.command()
async def join(ctx):
    channel = bot.get_channel(1568728547214884916)
    if channel:
        try:
            if ctx.voice_client is None:
                await channel.connect(timeout=60.0, reconnect=True)
            else:
                await ctx.voice_client.move_to(channel)
            await ctx.message.add_reaction("✅")
        except Exception as e:
            await ctx.message.add_reaction("❌")
            try:
                await ctx.author.send(f"❌ **فشل تنفيذ أمر الانضمام للروم الصوتية:**\nالسبب: {str(e)}")
            except discord.Forbidden:
                await ctx.send(f"⚠️ {ctx.author.mention}، لم أتمكن من إرسال تفاصيل الخطأ لك في الخاص بسبب إعدادات الخصوصية لديك.", delete_after=10)
    else:
        await ctx.message.add_reaction("❌")
        try:
            await ctx.author.send("❌ **فشل تنفيذ أمر الانضمام:** لا يمكن العثور على الروم الصوتية المحددة بالأيدي المكتوب بالكود.")
        except:
            pass

@bot.command()
async def leave(ctx):
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        await ctx.message.add_reaction("✅")
    else:
        await ctx.message.add_reaction("❌")
        await ctx.send("⚠️ البوت غير متواجد في أي روم صوتي حالياً.", delete_after=5)
class LobbyView(View):
    def __init__(self, ctx):
        super().__init__(timeout=60.0)
        self.ctx = ctx
        self.players = set()

    def make_embed(self):
        embed = discord.Embed(title="🎮 غرفة الانتظار للبطولة الكبرى!", description="ستبدأ **5 جولات حماسية** بعد قليل، الفوز بـ **5 نقاط**!", color=discord.Color.blue())
        p_list = "\n".join([f"• {p.mention}" for p in self.players]) if self.players else "*لا يوجد أحد حالياً*"
        embed.add_field(name=f"👥 المشاركون ({len(self.players)}):", value=p_list, inline=False)
        return embed

    @discord.ui.button(label="📥 دخول", style=discord.ButtonStyle.green)
    async def join_button(self, interaction: discord.Interaction, button: Button):
        self.players.add(interaction.user)
        await interaction.response.edit_message(embed=self.make_embed(), view=self)

    @discord.ui.button(label="📤 خروج", style=discord.ButtonStyle.red)
    async def leave_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user in self.players:
            self.players.remove(interaction.user)
        await interaction.response.edit_message(embed=self.make_embed(), view=self)

@bot.command(name="game")
async def start_tournament(ctx):
    view = LobbyView(ctx)
    initial_msg = await ctx.send(embed=view.make_embed(), view=view)
    countdown = 50
    timer_msg = await ctx.send(f"⏳ المتبقي على بدء اللعبة: **{countdown}** ثانية...")
    while countdown > 0:
        await asyncio.sleep(10)
        countdown -= 10
        if countdown > 0:
            await timer_msg.edit(content=f"⏳ المتبقي: **{countdown}** ثانية...")
    await timer_msg.delete()
    for item in view.children:
        item.disabled = True
    await initial_msg.edit(view=view)
    if len(view.players) < 1:
        await ctx.send("❌ تم إلغاء الجولة لعدم دخول أي لاعبين.")
        return
    await ctx.send("🚀 **بدأت البطولة الآن!**")
    scores = {player: 0 for player in view.players}
    cats = ["إنسان", "حيوان", "بلد", "نبات", "جماد"]
    letters = ['أ', 'ب', 'ت', 'ج', 'ح', 'خ', 'د', 'ر', 'س', 'ش', 'ع', 'غ', 'ف', 'ق', 'ك', 'م', 'ن', 'هـ', 'و', 'ي']
    for r in range(1, 6):
        await ctx.send(f"🏆 **--- الجولة [{r} / 5] ---**")
        await asyncio.sleep(1)
        c, l = random.choice(cats), random.choice(letters)
        await ctx.send(f"⚡ أسرع شخص يكتب اسم **({c})** يبدأ بحرف **({l})**!")
        def chk(m):
            return m.channel == ctx.channel and m.author in view.players and m.content.strip().startswith(l) and len(m.content.strip()) > 1
        try:
            msg = await bot.wait_for('message', check=chk, timeout=20.0)
            scores[msg.author] += 5
            win = discord.Embed(title=f"🎉 فائز في الجولة {r}!", description=f"كفو {msg.author.mention}! إجابتك صحيحة (**{msg.content}**).\nحصلت على **+5 نقاط** 🌟", color=discord.Color.gold())
            win.set_image(url=WINNING_IMAGE_URL)
            await ctx.send(embed=win)
        except asyncio.TimeoutError:
            await ctx.send(f"⏰ انتهى الوقت! لم يجب أحد.")
        await asyncio.sleep(3)
    sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    lb = discord.Embed(title="🏆 لوحة صدارة البطولة 🏆", color=discord.Color.purple())
    txt = ""
    for i, (p, s) in enumerate(sorted_scores):
        m = "🥇 المركز الأول" if i == 0 else "🥈 المركز الثاني" if i == 1 else "🥉 المركز الثالث" if i == 2 else f"🎖️ المرتبة {i+1}"
        if i == 0:
            lb.set_thumbnail(url=p.display_avatar.url)
        txt += f"{m}: {p.mention} ➜ **{s} نقطة**\n"
    lb.description = txt
    await ctx.send(embed=lb)

@bot.event
async def on_message(message):
    global protection_status
    if message.author == bot.user:
        return
    if is_bot_paused:
        return

    # أمر عرض جميع الأوامر (#cmd)
    if message.content == "#cmd":
        embed = discord.Embed(
            title="📜 قائمة أوامر بوت Midnight",
            description="إليك جميع الأوامر المتاحة في البوت وطريقة استخدامها:",
            color=discord.Color.from_rgb(20, 20, 30)
        )
        embed.add_field(
            name="🎮 أوامر الألعاب والصوتيات (`!`)",
            value="• **`!game`** : بدء بطولة إنسان حيوان نبات جماد (5 جولات).\n"
                  "• **`!join`** : إدخال البوت إلى الروم الصوتي المحدد.\n"
                  "• **`!leave`** : إخراج البوت من الروم الصوتي.",
            inline=False
        )
        embed.add_field(
            name="🛡️ أوامر الحماية والإدارة (`#`)",
            value="• **`#EY`** : تفعيل الحماية التلقائية ضد دخول البوتات المزعجة.\n"
                  "• **`#EYY`** : إيقاف نظام الحماية التلقائية.\n"
                  "• **`#KI @العضو`** : طرد عضو من السيرفر (تتطلب صلاحية الطرد).\n"
                  "• **`#cmd`** : عرض قائمة الأوامر هذه.",
            inline=False
        )
        embed.add_field(
            name="🎫 نظام التذاكر (Tickets)",
            value="• يعمل تلقائياً عبر الأزرار في الروم المخصص لفتح تذاكر الدعم الفني، الشكاوى، التقديم، والإدارة.",
            inline=False
        )
        embed.set_footer(text=f"تم الطلب بواسطة: {message.author.name}", icon_url=message.author.display_avatar.url)
        await message.channel.send(embed=embed)
        return

    is_admin = message.author.guild_permissions.manage_guild or message.author == message.guild.owner
    if message.content == "#EY":
        if not is_admin:
            await message.add_reaction("❌")
            return
        protection_status = True
        await message.add_reaction("✅")
        await message.channel.send("🛡️ **تم تفعيل نظام الحماية من بوتات الـ App بنجاح!**")
        return
    elif message.content == "#EYY":
        if not is_admin:
            await message.add_reaction("❌")
            return
        protection_status = False
        await message.add_reaction("✅")
        await message.channel.send("⚠️ **تم إيقاف نظام الحماية! يمكن للبوتات الدخول الآن.**")
        return
    elif message.content.startswith("#KI"):
        if not message.author.guild_permissions.kick_members:
            await message.add_reaction("❌")
            try:
                await message.author.send("❌ **فشل تنفيذ الأمر:** أنت لا تملك صلاحية `طرد الأعضاء`.")
            except:
                pass
            return
        args = message.content.split()
        if len(args) < 2:
            await message.add_reaction("❌")
            try:
                await message.author.send("❌ **صيغة الأمر خاطئة:** يجب منشنة العضو أو وضع الـ ID الخاص به. مثال: `#KI @اسم_العضو`")
            except:
                pass
            return
        member = None
        if message.mentions:
            member = message.mentions[0]
        else:
            try:
                raw_id = "".join(character for character in args[1] if character.isdigit())
                if raw_id:
                    member = message.guild.get_member(int(raw_id))
            except:
                pass
        if member is None:
            await message.add_reaction("❌")
            try:
                await message.author.send("❌ **فشل تنفيذ الأمر:** لم أتمكن من العثور على هذا العضو في السيرفر.")
            except:
                pass
            return
        reason = " ".join(args[2:]) if len(args) > 2 else "لم يتم ذكر سبب."
        try:
            await member.kick(reason=reason)
            await message.add_reaction("✅")
            await message.channel.send(f"👢 **تم طرد العضو {member.mention} بنجاح من السيرفر.**")
        except Exception as e:
            await message.add_reaction("❌")
            try:
                await message.author.send(f"❌ **فشل تنفيذ أمر الطرد للعضو {member.name}:**\nالسبب: {str(e)}")
            except:
                pass
    await bot.process_commands(message)

keep_alive()
bot.run("MTU2ODcwNDMwNDMxNzk4ODk0NA.GO7wHE.zqqdPPpWAy5iEtcPVb0wv8Gr-IOXNzAY45CxXM")
