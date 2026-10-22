import os
import logging
import sqlite3
from fastapi import FastAPI, Request, Response
import uvicorn
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = 8396752402
AD_CHANNEL_ID = "@Vasetearminazizi"

CHANNELS = [
    ("@Vasetearminazizi", "https://t.me/Vasetearminazizi"),
    ("@etemadearminazizi", "https://t.me/etemadearminazizi"),
]

conn = sqlite3.connect('bot.db', check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)''')
c.execute('''CREATE TABLE IF NOT EXISTS ads (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, message_ids TEXT, admin_msg_ids TEXT DEFAULT '', status TEXT DEFAULT 'pending', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
c.execute('''CREATE TABLE IF NOT EXISTS pricing_requests (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, message_ids TEXT, admin_msg_ids TEXT DEFAULT '', status TEXT DEFAULT 'pending', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
c.execute('''CREATE TABLE IF NOT EXISTS buy_requests (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, message_ids TEXT, admin_msg_ids TEXT DEFAULT '', link TEXT DEFAULT '', status TEXT DEFAULT 'pending', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
conn.commit()

def is_admin(user_id):
    return user_id == ADMIN_ID

async def check_membership(user_id, bot):
    not_joined = []
    for ch, link in CHANNELS:
        try:
            m = await bot.get_chat_member(ch, user_id)
            if m.status in ('left', 'kicked'):
                not_joined.append((ch, link))
        except Exception as e:
            logger.warning(f"check {ch}: {e}")
    return not_joined

def main_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📞 درخواست واسطه گری", callback_data="mediator")],
        [InlineKeyboardButton("📝 ثبت اگهی", callback_data="post_ad")],
        [InlineKeyboardButton("💰 قیمت گزاری روی اکانت", callback_data="pricing")],
        [InlineKeyboardButton("🛒 خرید اکانت", callback_data="buy_account")],
        [InlineKeyboardButton("⚠️ گزارش خرابی", callback_data="report")],
    ])

def admin_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📋 آگهی های ثبت شده", callback_data="admin_ads")],
        [InlineKeyboardButton("💰 درخواست قیمت گزاری", callback_data="admin_pricing")],
        [InlineKeyboardButton("🛒 خرید اکانت", callback_data="admin_buy")],
        [InlineKeyboardButton("📢 ارسال پیام همگانی", callback_data="admin_broadcast")],
    ])

WELCOME = "این تنها ربات پاسخگویی واسطه گری آرمین عزیزی است\nآیدی ادمین واسطه: @Vasete_armin_azizi"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    context.user_data.clear()
    c.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
    conn.commit()
    if is_admin(user_id):
        await show_admin_panel(update, context)
        return
    not_joined = await check_membership(user_id, context.bot)
    if not_joined:
        buttons = [[InlineKeyboardButton(f"🔗 عضویت در {ch}", url=link)] for ch, link in not_joined]
        buttons.append([InlineKeyboardButton("✅ عضو شدم", callback_data="check_join")])
        await update.message.reply_text("برای استفاده از ربات ابتدا در کانال‌های زیر عضو شوید:", reply_markup=InlineKeyboardMarkup(buttons))
        return
    await update.message.reply_text(WELCOME, reply_markup=main_menu_keyboard())

async def show_admin_panel(update, context):
    text = "🔧 پنل مدیریت\nیک گزینه را انتخاب کنید:"
    if update.callback_query: await update.callback_query.edit_message_text(text, reply_markup=admin_menu_keyboard())
    else: await update.message.reply_text(text, reply_markup=admin_menu_keyboard())

async def show_user_menu(update, context):
    if update.callback_query: await update.callback_query.edit_message_text(WELCOME, reply_markup=main_menu_keyboard())
    else: await update.message.reply_text(WELCOME, reply_markup=main_menu_keyboard())
async def mediator_handler(update, context):
    text = "قیمت های واسطه گری به این صورت است:\n\nمعامله زیر 50 هزار : رایگان\n━━━━━━━━━━━━━━━━━\nمعامله 50 هزار تا 100 هزار: رایگان\n━━━━━━━━━━━━━━━━━\nمعامله 100 تا 300 : نفری ۱۰ هزار\n━━━━━━━━━━━━━━━━━\nمعامله 400 تا 900 هزار: نفری ۵۰ هزار\n━━━━━━━━━━━━━━━━━\nمعامله 1500 تا 3 میل : نفری 100 هزار\n━━━━━━━━━━━━━━━━━\nمعامله ۴ میل تا ۱۰ میل : نفری 350 هزار\n━━━━━━━━━━━━━━━━━\nمعامله های بالای 10 میل: نفری ۵۰۰ هزار\n\nاگر با قیمت ها اوکی بودید گزینه تایید رو بزنید."
    await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ تایید", callback_data="mediator_confirm")], [InlineKeyboardButton("🔙 برگشت", callback_data="restart")]]))

async def mediator_confirm(update, context):
    text = "لطفاً اطلاعات زیر را به ایدی زیر ارسال نمایید:\n\n@Vasete_armin_azizi\n\n1_ آیدی شما و طرف مقابل\n2_ فرم اگهی اکانت یا عکس ها\n3_ ارزش اکانت شما\n\n⚠️ توجه داشته باشید تایید دو مرحله اکانت کالاف دیوتی الزامی است.\n\n⚠️ معامله فقط توسط همین آیدی بالا انجام میشود و ربات واسطه گری نمیکند."
    await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 برگشت", callback_data="restart")]]))

async def post_ad_handler(update, context):
    text = "📋 فرم ثبت اگهی:\n\nنوع بازی🎮:\nـــــــــــــــــــــــــــــــــــ\n\nسیو ها📥:\nـــــــــــــــــــــــــــــــــ\n\nآیا قابل چنج هست:\nتعداد سیپی🪙:\nتعداد گان متیک 🟥:\nتعداد گان لجند 🟨:\nتعداد بتل پس:\nتوضیحات فروشنده:\nUid:\nقیمت:\nآیدی فروشنده:\n\nجهت خرید و واسطه گری و آگهی اکانت:\n@Vasete_armin_azizi\n\nچنلمون: https://t.me/Vasetearminazizi\n\nاعتماد: https://t.me/etemadearminazizi\n\nاطلاعات اکانتتونو در فرم بالا پر کنید و سپس ارسال کنید\n\n❗️ اگر اکانت شما گزینه های زیر رو نداشته باشه آگهی نمیشه:\n1_ آیدی فروشنده الزامیس\n2_ عکس حد اقل 2 و حد اکثر 9 تا\n\nفرم را همراه عکس ها ارسال کنید و پیام اضافه نفرستید.\nممنون از شما❤️"
    context.user_data.clear()
    context.user_data['state'] = 'ad_waiting'
    context.user_data['ad_messages'] = []
    await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 برگشت", callback_data="restart")]]))

async def pricing_handler(update, context):
    text = "برای قیمت گزاری اکانت اطلاعات زیر را ارسال نمایید:\n\n• عکس های اکانت\n• ایتم ها\n• وضعیت سیو ها\n• سیپی منفی دارد / ندارد\n\nلطفا از ارسال پیام های دیگر خودداری نمایید.\nپس از ارسال اطلاعات نهایتا تا یک الی دو ساعت قیمت تقریبی اکانت برای شما ارسال میشود."
    context.user_data.clear()
    context.user_data['state'] = 'pricing_waiting'
    context.user_data['pricing_messages'] = []
    await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 برگشت", callback_data="restart")]]))

async def buy_handler(update, context):
    text = "اکانتی که قصد خرید ان را دارید لینک پیام آن را در چنل آگهی و دارید و بفرستید.\nدقت کنید اگهی فقط باید در چنل خرید فروش ما آگهی شده باشد.\n\nاز ارسال پیام های دیگر خودداری کنید.\nپس از ارسال آگهی ان اکانت استعلام گرفته میشود و سپس به شما اطلاع داده میشود.\n\nبا تشکر از همراهی شما."
    context.user_data.clear()
    context.user_data['state'] = 'buy_waiting'
    context.user_data['buy_messages'] = []
    await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 برگشت", callback_data="restart")]]))

async def report_handler(update, context):
    context.user_data.clear()
    context.user_data['state'] = 'report_waiting'
    await update.callback_query.edit_message_text("⚠️ لطفاً مشکل یا باگ پیش آمده را توضیح دهید و ارسال کنید:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 برگشت", callback_data="restart")]]))
async def submit_ad(update, context):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    msg_ids = context.user_data.get('ad_messages', [])
    if not msg_ids: return await query.edit_message_text("هیچ محتوایی دریافت نشد.")
    c.execute("INSERT INTO ads (user_id, message_ids) VALUES (?, ?)", (user_id, ','.join(map(str, msg_ids))))
    ad_id = c.lastrowid
    conn.commit()
    admin_msg_ids = []
    for mid in msg_ids:
        try:
            fwd = await context.bot.forward_message(chat_id=ADMIN_ID, from_chat_id=user_id, message_id=mid)
            admin_msg_ids.append(fwd.message_id)
        except: pass
    c.execute("UPDATE ads SET admin_msg_ids=? WHERE id=?", (','.join(map(str, admin_msg_ids)), ad_id))
    conn.commit()
    try:
        await context.bot.send_message(ADMIN_ID, f"📝 آگهی جدید #{ad_id}\nاز کاربر: {user_id}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ تایید و ارسال به چنل", callback_data=f"approve_ad_{ad_id}"), InlineKeyboardButton("❌ رد", callback_data=f"reject_ad_{ad_id}")]]))
    except: pass
    await query.edit_message_text("فرم شما ارسال شد ✅🌹\n\nزمان تقریبی اگهی: بین بیست دقیقه تا یک ساعت⏰\nپس از بررسی نتیجه به شما اطلاع داده میشود.")
    context.user_data.clear()

async def submit_pricing(update, context):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    msg_ids = context.user_data.get('pricing_messages', [])
    if not msg_ids: return await query.edit_message_text("هیچ محتوایی دریافت نشد.")
    c.execute("INSERT INTO pricing_requests (user_id, message_ids) VALUES (?, ?)", (user_id, ','.join(map(str, msg_ids))))
    req_id = c.lastrowid
    conn.commit()
    admin_msg_ids = []
    for mid in msg_ids:
        try:
            fwd = await context.bot.forward_message(chat_id=ADMIN_ID, from_chat_id=user_id, message_id=mid)
            admin_msg_ids.append(fwd.message_id)
        except: pass
    c.execute("UPDATE pricing_requests SET admin_msg_ids=? WHERE id=?", (','.join(map(str, admin_msg_ids)), req_id))
    conn.commit()
    try:
        await context.bot.send_message(ADMIN_ID, f"💰 درخواست قیمت گزاری #{req_id}\nاز کاربر: {user_id}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("💵 ارسال قیمت", callback_data=f"send_price_{req_id}"), InlineKeyboardButton("❌ رد", callback_data=f"reject_pricing_{req_id}")]]))
    except: pass
    await query.edit_message_text("اطلاعات شما دریافت شد ✅\nنهایتا تا یک الی دو ساعت قیمت تقریبی اکانت برای شما ارسال میشود.")
    context.user_data.clear()

async def submit_buy(update, context):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    msg_ids = context.user_data.get('buy_messages', [])
    link_text = context.user_data.get('buy_link', '')
    if not msg_ids: return await query.edit_message_text("هیچ محتوایی دریافت نشد.")
    c.execute("INSERT INTO buy_requests (user_id, message_ids, link) VALUES (?, ?, ?)", (user_id, ','.join(map(str, msg_ids)), link_text))
    req_id = c.lastrowid
    conn.commit()
    admin_msg_ids = []
    for mid in msg_ids:
        try:
            fwd = await context.bot.forward_message(chat_id=ADMIN_ID, from_chat_id=user_id, message_id=mid)
            admin_msg_ids.append(fwd.message_id)
        except: pass
    c.execute("UPDATE buy_requests SET admin_msg_ids=? WHERE id=?", (','.join(map(str, admin_msg_ids)), req_id))
    conn.commit()
    try:
        await context.bot.send_message(ADMIN_ID, f"🛒 درخواست خرید #{req_id}\nاز کاربر: {user_id}\n\nلینک: {link_text}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("💬 ارسال پاسخ", callback_data=f"reply_buy_{req_id}")]]))
    except: pass
    await query.edit_message_text("لینک شما دریافت شد ✅\nپس از استعلام به شما اطلاع داده میشود.")
    context.user_data.clear()

async def approve_ad(update, context, ad_id):
    query = update.callback_query
    c.execute("SELECT user_id, admin_msg_ids, status FROM ads WHERE id=?", (ad_id,))
    row = c.fetchone()
    if not row or row[2] != 'pending': return
    user_id, admin_msg_ids_str, status = row
    admin_msg_ids = [int(x) for x in admin_msg_ids_str.split(',') if x]
    for amid in admin_msg_ids:
        try: await context.bot.copy_message(chat_id=AD_CHANNEL_ID, from_chat_id=ADMIN_ID, message_id=amid)
        except: pass
    c.execute("UPDATE ads SET status='approved' WHERE id=?", (ad_id,))
    conn.commit()
    try: await context.bot.send_message(user_id, f"✅ آگهی شما (#{ad_id}) تایید و در چنل منتشر شد.")
    except: pass
    await query.edit_message_text(f"✅ آگهی #{ad_id} تایید شد.")

async def reject_ad(update, context, ad_id):
    query = update.callback_query
    c.execute("SELECT user_id, status FROM ads WHERE id=?", (ad_id,))
    row = c.fetchone()
    if not row or row[1] != 'pending': return
    user_id, status = row
    c.execute("UPDATE ads SET status='rejected' WHERE id=?", (ad_id,))
    conn.commit()
    try: await context.bot.send_message(user_id, f"❌ آگهی شما (#{ad_id}) رد شد.")
    except: pass
    await query.edit_message_text(f"❌ آگهی #{ad_id} رد شد.")

async def start_send_price(update, context, req_id):
    query = update.callback_query
    c.execute("SELECT user_id, status FROM pricing_requests WHERE id=?", (req_id,))
    row = c.fetchone()
    if not row or row[1] != 'pending': return
    context.user_data['admin_send_price_for'] = {'user_id': row[0], 'request_id': req_id}
    context.user_data['state'] = 'admin_send_price'
    await query.edit_message_text(f"قیمت اکانت را برای کاربر {row[0]} تایپ و ارسال کنید.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 لغو", callback_data="admin_back")]]))

async def reject_pricing(update, context, req_id):
    query = update.callback_query
    c.execute("SELECT user_id FROM pricing_requests WHERE id=?", (req_id,))
    row = c.fetchone()
    if not row: return
    c.execute("UPDATE pricing_requests SET status='rejected' WHERE id=?", (req_id,))
    conn.commit()
    try: await context.bot.send_message(row[0], f"❌ درخواست قیمت گزاری شما (#{req_id}) رد شد.")
    except: pass
    await query.edit_message_text(f"❌ درخواست #{req_id} رد شد.")

async def start_reply_buy(update, context, req_id):
    query = update.callback_query
    c.execute("SELECT user_id FROM buy_requests WHERE id=?", (req_id,))
    row = c.fetchone()
    if not row: return
    context.user_data['admin_reply_buy_for'] = {'user_id': row[0], 'request_id': req_id}
    context.user_data['state'] = 'admin_reply_buy'
    await query.edit_message_text(f"پاسخ خود را برای کاربر {row[0]} تایپ کنید.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 لغو", callback_data="admin_back")]]))

