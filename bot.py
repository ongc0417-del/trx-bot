from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, WebAppInfo, BotCommand
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import requests
import re
from datetime import datetime
import os
import json

TOKEN = os.environ.get("BOT_TOKEN", "9035180072:AAHdAj7AYA2U0UF_PfypTuRDkkWLFTNoMbg")
ADMIN_ID = 8382783315

WEBAPP_URL = "https://fantastic-gumption-f7dbd7.netlify.app"

# 数据存储
stats = {"users": set(), "views": 0, "start_count": 0}
ads = []

def get_main_keyboard():
    keyboard = [
        [KeyboardButton("⚡ 领取能量", web_app=WebAppInfo(url=WEBAPP_URL))],
        [KeyboardButton("💰 USDT换TRX", web_app=WebAppInfo(url=WEBAPP_URL + "/swap.html"))],
        [KeyboardButton("🔍 查地址", web_app=WebAppInfo(url=WEBAPP_URL + "/query.html"))],
        [KeyboardButton("📊 我的订单"), KeyboardButton("ℹ️ 帮助")],
        [KeyboardButton("📞 联系客服"), KeyboardButton("/start")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, is_persistent=True)

def get_trx_price():
    try:
        url = "https://api.coingecko.com/api/v3/simple/price?ids=tron&vs_currencies=usd&include_24hr_change=true"
        res = requests.get(url, timeout=5).json()
        price = res["tron"]["usd"]
        change_24h = res["tron"].get("usd_24h_change", 0)
        return round(price, 4), round(change_24h, 2)
    except:
        return None, None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    stats["users"].add(user_id)
    stats["start_count"] += 1
    stats["views"] += 1

    price, change_24h = get_trx_price()

    if price:
        usdt_to_trx = round(1 / price, 2)
        if change_24h >= 0:
            change_text = "📈 +" + str(change_24h) + "%"
        else:
            change_text = "📉 " + str(change_24h) + "%"
        price_text = "💰 实时价格\n1 TRX = $" + str(price) + "\n1 USDT = " + str(usdt_to_trx) + " TRX\n24h 涨跌：" + change_text
    else:
        price_text = "价格获取中..."

    caption = "⚡ TRX 能量助手\n\n🔥 每日免费领取 5 笔能量\n💰 全网高比例 USDT 换 TRX\n\n" + price_text

    # 显示广告
    if ads:
        caption += "\n\n📢 最新公告\n" + ads[-1]

    caption += "\n\n点击下方按钮开始使用"

    await update.message.reply_text(caption, reply_markup=get_main_keyboard())

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = "📖 使用说明\n\n⚡ 领取能量\n打开小程序，输入地址领取能量\n每日免费 5 笔\n\n💰 USDT换TRX\n查看实时价格，进行兑换\n\n🔍 查地址\n查询地址余额和交易记录\n\n📊 我的订单\n查看历史订单记录\n\n📞 联系客服\n有问题随时联系"
    await update.message.reply_text(text, reply_markup=get_main_keyboard())

async def contact_support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = "📞 联系客服\n\n如有问题请联系：\n@你的客服账号\n\n工作时间：24小时在线"
    await update.message.reply_text(text, reply_markup=get_main_keyboard())

# 管理员发布广告
async def post_ad(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("❌ 无权限")
        return

    if not context.args:
        await update.message.reply_text("用法：/ad 广告内容")
        return

    ad_text = " ".join(context.args)
    ads.append(ad_text)
    await update.message.reply_text("✅ 广告已发布\n\n" + ad_text)

# 查看统计
async def view_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("❌ 无权限")
        return

    text = f"📊 机器人统计\n\n"
    text += f"👥 用户数：{len(stats['users'])}\n"
    text += f"👁 浏览量：{stats['views']}\n"
    text += f"🚀 启动次数：{stats['start_count']}\n"
    text += f"📢 广告数：{len(ads)}"

    await update.message.reply_text(text)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    stats["views"] += 1
    text = update.message.text.strip()

    if text == "📊 我的订单":
        await update.message.reply_text("📊 我的订单\n\n你目前还没有订单。", reply_markup=get_main_keyboard())
    elif text == "ℹ️ 帮助":
        await help_command(update, context)
    elif text == "📞 联系客服":
        await contact_support(update, context)
    else:
        await update.message.reply_text("请点击下方菜单按钮。", reply_markup=get_main_keyboard())

async def post_init(application: Application):
    await application.bot.set_my_commands([
        BotCommand("start", "开始使用"),
        BotCommand("help", "帮助说明"),
        BotCommand("ad", "发布广告（管理员）"),
        BotCommand("stats", "查看统计（管理员）")
    ])

def main():
    app = Application.builder().token(TOKEN).post_init(post_init).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("ad", post_ad))
    app.add_handler(CommandHandler("stats", view_stats))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("机器人启动中...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()