from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, WebAppInfo, BotCommand, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
import requests
import re
from datetime import datetime

TOKEN = "9035180072:AAHdAj7AYA2U0UF_PfypTuRDkkWLFTNoMbg"

WEBAPP_URL = "https://fantastic-gumption-f7dbd7.netlify.app"

monitored_addresses = {}

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

def is_tron_address(text):
    return bool(re.match(r'^T[A-Za-z1-9]{33}$', text.strip()))

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
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

    caption = "⚡ TRX 能量助手\n\n🔥 每日免费领取 5 笔能量\n💰 全网高比例 USDT 换 TRX\n\n" + price_text + "\n\n点击下方按钮开始使用"

    await update.message.reply_text(caption, reply_markup=get_main_keyboard())

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = "📖 使用说明\n\n⚡ 领取能量\n打开小程序，输入地址领取能量\n每日免费 5 笔\n\n💰 USDT换TRX\n查看实时价格，进行兑换\n\n🔍 查地址\n查询地址余额和交易记录\n查询后可点击按钮开启监控\n\n📊 我的订单\n查看历史订单记录\n\n📞 联系客服\n有问题随时联系"
    await update.message.reply_text(text, reply_markup=get_main_keyboard())

async def contact_support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = "📞 联系客服\n\n如有问题请联系：\n@你的客服账号\n\n工作时间：24小时在线"
    await update.message.reply_text(text, reply_markup=get_main_keyboard())

def get_recent_transactions(address):
    try:
        url = "https://api.trongrid.io/v1/accounts/" + address + "/transactions?limit=5"
        res = requests.get(url, timeout=10).json()
        
        if "data" not in res or len(res["data"]) == 0:
            return "暂无交易记录"
        
        lines = []
        for tx in res["data"][:5]:
            timestamp = tx.get("block_timestamp", 0)
            if timestamp:
                time_str = datetime.fromtimestamp(timestamp / 1000).strftime("%m-%d %H:%M")
            else:
                time_str = "未知"
            
            contract = tx.get("raw_data", {}).get("contract", [{}])[0]
            contract_type = contract.get("type", "")
            value = contract.get("parameter", {}).get("value", {})
            
            if contract_type == "TransferContract":
                amount = value.get("amount", 0) / 1000000
                from_addr = value.get("owner_address", "")
                to_addr = value.get("to_address", "")
                
                if to_addr and to_addr.endswith(address[-6:]):
                    short_from = from_addr[:6] + "..." + from_addr[-4:] if from_addr else "未知"
                    lines.append("• " + time_str + "\n  转入 " + str(round(amount, 2)) + " TRX\n  来自 " + short_from)
                else:
                    short_to = to_addr[:6] + "..." + to_addr[-4:] if to_addr else "未知"
                    lines.append("• " + time_str + "\n  转出 " + str(round(amount, 2)) + " TRX\n  到 " + short_to)
            elif contract_type == "TriggerSmartContract":
                lines.append("• " + time_str + " 合约调用")
            else:
                lines.append("• " + time_str + " " + contract_type)
        
        if lines:
            return "\n".join(lines)
        else:
            return "暂无交易记录"
    except:
        return "获取交易记录失败"

async def query_address(update: Update, context: ContextTypes.DEFAULT_TYPE, address=None):
    if not address:
        await update.message.reply_text(
            "🔍 请发送 TRC20 地址进行查询\n\n示例：Txxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
            reply_markup=get_main_keyboard()
        )
        context.user_data["waiting_address"] = True
        return

    await update.message.reply_text("🔍 正在查询，请稍候...")

    try:
        url = "https://api.trongrid.io/v1/accounts/" + address
        res = requests.get(url, timeout=10).json()

        if "data" in res and len(res["data"]) > 0:
            data = res["data"][0]
            trx_balance = data.get("balance", 0) / 1000000

            usdt_balance = 0
            trc20 = data.get("trc20", [])
            for token in trc20:
                if "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t" in token:
                    usdt_balance = int(token["TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"]) / 1000000

            tx_records = get_recent_transactions(address)
            context.user_data["last_address"] = address

            text = "🔍 地址查询结果\n\n"
            text += "地址：" + address[:8] + "..." + address[-6:] + "\n\n"
            text += "💎 TRX 余额：" + str(round(trx_balance, 2)) + "\n"
            text += "💵 USDT 余额：" + str(round(usdt_balance, 2)) + "\n\n"
            text += "📋 最近 5 笔交易：\n"
            text += tx_records

            # 监控按钮（内联按钮，不在主菜单）
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔔 开启监控", callback_data="monitor_" + address)],
                [InlineKeyboardButton("🔕 取消监控", callback_data="unmonitor_" + address)]
            ])

            await update.message.reply_text(text, reply_markup=keyboard)
        else:
            await update.message.reply_text("❌ 未查询到该地址信息，请检查地址是否正确", reply_markup=get_main_keyboard())

    except:
        await update.message.reply_text("❌ 查询失败，请稍后重试", reply_markup=get_main_keyboard())

    context.user_data["waiting_address"] = False

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_id = update.effective_user.id
    
    if data.startswith("monitor_"):
        address = data.replace("monitor_", "")
        if user_id not in monitored_addresses:
            monitored_addresses[user_id] = []
        if address not in monitored_addresses[user_id]:
            monitored_addresses[user_id].append(address)
            await query.edit_message_text(
                query.message.text + "\n\n✅ 已开启监控，有资金变动时会通知你"
            )
        else:
            await query.answer("该地址已在监控中", show_alert=True)
    
    elif data.startswith("unmonitor_"):
        address = data.replace("unmonitor_", "")
        if user_id in monitored_addresses and address in monitored_addresses[user_id]:
            monitored_addresses[user_id].remove(address)
            await query.edit_message_text(
                query.message.text + "\n\n🔕 已取消监控"
            )
        else:
            await query.answer("该地址未在监控中", show_alert=True)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    if context.user_data.get("waiting_address") and is_tron_address(text):
        await query_address(update, context, text)
        return

    if is_tron_address(text):
        await query_address(update, context, text)
        return

    if text == "📊 我的订单":
        await update.message.reply_text("📊 我的订单\n\n你目前还没有订单。", reply_markup=get_main_keyboard())
    elif text == "ℹ️ 帮助":
        await help_command(update, context)
    elif text == "📞 联系客服":
        await contact_support(update, context)
    elif text == "🔍 查地址":
        await query_address(update, context)
    else:
        await update.message.reply_text("请点击下方菜单按钮，或发送 TRC20 地址进行查询。", reply_markup=get_main_keyboard())

async def post_init(application: Application):
    await application.bot.set_my_commands([
        BotCommand("start", "开始使用"),
        BotCommand("help", "帮助说明")
    ])

def main():
    app = Application.builder().token(TOKEN).post_init(post_init).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("机器人启动中...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()