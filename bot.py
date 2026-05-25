import os
import asyncio
import pyrebase
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, 
    MessageHandler, filters, ConversationHandler, ContextTypes
)

# --- ফায়ারবেস কনফিগারেশন (আপনার দেওয়া নতুন URL সহ আপডেট করা হয়েছে) ---
firebase_config = {
    "apiKey": "AIzaSyBvE82yFAhJbGTuj_l-wGvI8aBh-2B7O_0",
    "authDomain": "aesthetics-academy.firebaseapp.com",
    "databaseURL": "https://aesthetics-academy-default-rtdb.asia-southeast1.firebasedatabase.app/", 
    "projectId": "aesthetics-academy",
    "storageBucket": "aesthetics-academy.firebasestorage.app",
    "messagingSenderId": "229742131602",
    "appId": "1:229742131602:web:89ebc8ad85442e7d83294b",
    "measurementId": "G-NZTP202VJM"
}

# ফায়ারবেস ইনিশিয়ালাইজেশন
firebase = pyrebase.initialize_app(firebase_config)
db = firebase.database()

# --- আপনার আসল টেলিগ্রাম বোট টোকেন (বাড়তি লেখা ছাড়া) ---
BOT_TOKEN = "8678814164:AAFYnrBuocg0O_IbmwK9EHoi_APuOhhIhPo"

# States
CHOOSING_CATEGORY, TYPING_TIME, TYPING_NOTE, CHOOSING_SOUND, UPLOADING_SOUND = range(5)

# অলটাইম কিবোর্ড মেনু
def get_main_keyboard():
    keyboard = [
        [KeyboardButton("➕ নতুন রিমাইন্ডার সেট করুন"), KeyboardButton("📋 আমার রিমাইন্ডার তালিকা")],
        [KeyboardButton("ℹ️ বোট ইনফো"), KeyboardButton("❌ সব রিমাইন্ডার মুছুন")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "🧠 **Welcome to Advanced Reminder Pro** 🧠\n\n"
        "এই বোটটি আপনার রিমাইন্ডার ক্লাউডে সেভ রাখবে এবং নির্দিষ্ট সময়ে কাস্টম অ্যালার্ম "
        "সাউন্ডসহ আপনাকে অ্যালার্ট করবে। কাজ শেষ হওয়া মাত্রই ডেটাবেস থেকে ডাটা অটো ডিলিট হয়ে যাবে।"
    )
    await update.message.reply_text(welcome_text, reply_markup=get_main_keyboard(), parse_mode='Markdown')

async def handle_menu_options(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    chat_id = str(update.message.chat_id)

    if text == "➕ নতুন রিমাইন্ডার সেট করুন":
        keyboard = [
            [InlineKeyboardButton("⏰ সাধারণ অ্যালার্ম", callback_data='Alarm'),
             InlineKeyboardButton("💊 ওষুধের রিমাইন্ডার", callback_data='Medicine')],
            [InlineKeyboardButton("💪 জিম/ওয়ার্কআউট", callback_data='Gym'),
             InlineKeyboardButton("⚙️ কাস্টম রিমাইন্ডার", callback_data='Custom')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("🎯 **একটি ক্যাটাগরি নির্বাচন করুন:**", reply_markup=reply_markup, parse_mode='Markdown')
        return CHOOSING_CATEGORY

    elif text == "📋 আমার রিমাইন্ডার তালিকা":
        try:
            loop = asyncio.get_event_loop()
            reminders = await loop.run_in_executor(None, lambda: db.child("reminders").child(chat_id).get().val())
            if not reminders:
                await update.message.reply_text("📭 আপনার কোনো একটিভ রিমাইন্ডার সেট করা নেই।")
                return
            
            msg = "📋 **আপনার একটিভ রিমাইন্ডারসমূহ:**\n━━━━━━━━━━━━━━━━━━━━━\n"
            for k, v in reminders.items():
                msg += f"📌 **{v['category']}** - {v['minutes']} মিনিট পর\n📝 `{v['note']}`\n━━━━━━━━━━━━━━━━━━━━━\n"
            await update.message.reply_text(msg, parse_mode='Markdown')
        except Exception as e:
            await update.message.reply_text("⚠️ ডাটাবেস থেকে তথ্য আনতে সমস্যা হয়েছে।")
        
    elif text == "❌ সব রিমাইন্ডার মুছুন":
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, lambda: db.child("reminders").child(chat_id).remove())
        await update.message.reply_text("🗑️ আপনার সব রিমাইন্ডার ডাটাবেস থেকে ডিলিট করা হয়েছে!")
        
    elif text == "ℹ️ বোট ইনফো":
        await update.message.reply_text("🤖 **Reminder Bot v2.5**\n⚡ Powered by Python & Firebase Realtime Database (Asia-Southeast1).")

async def category_picked(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data['category'] = query.data
    await query.edit_message_text(text=f"⏳ **{query.data}** মোড সিলেক্ট হয়েছে। কত মিনিট পর অ্যালার্ম চান? (শুধু সংখ্যা দিন):")
    return TYPING_TIME

async def time_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text
    if not user_input.isdigit():
        await update.message.reply_text("⚠️ অনুগ্রহ করে শুধু সংখ্যা লিখুন:")
        return TYPING_TIME
    context.user_data['time_mins'] = int(user_input)
    await update.message.reply_text("📝 রিমাইন্ডারের জন্য একটি নজরকাড়া নোট বা মেসেজ লিখুন:")
    return TYPING_NOTE

async def note_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['note'] = update.message.text
    
    keyboard = [
        [InlineKeyboardButton("🎵 ডিফল্ট টোন ১", callback_data='default1')],
        [InlineKeyboardButton("🎙️ কাস্টম ভয়েস/অডিও আপলোড করুন", callback_data='custom_upload')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("🔊 **অ্যালার্ম সাউন্ড অপশন:**\n\nডিফল্ট সাউন্ড ব্যবহার করতে পারেন অথবা আপনার নিজের ভয়েস রেকর্ড বা অডিও ফাইল পাঠাতে পারেন।", reply_markup=reply_markup, parse_mode='Markdown')
    return CHOOSING_SOUND

async def sound_decision(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == 'default1':
        context.user_data['sound_type'] = 'default'
        context.user_data['sound_file_id'] = 'sound1.mp3'
        return await save_and_schedule_reminder(query.message, context)
    else:
        context.user_data['sound_type'] = 'custom'
        await query.edit_message_text("🎙️ **অনুগ্রহ করে এখন আপনার ফোন থেকে একটি ভয়েস নোট বা ছোট অডিও (.mp3) ফাইল সেন্ড করুন:**")
        return UPLOADING_SOUND

async def custom_sound_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.voice:
        context.user_data['sound_file_id'] = update.message.voice.file_id
    elif update.message.audio:
        context.user_data['sound_file_id'] = update.message.audio.file_id
    else:
        await update.message.reply_text("⚠️ এটি সঠিক অডিও ফাইল নয়। অনুগ্রহ করে একটি ভয়েস রেকর্ড বা অডিও ফাইল পাঠান:")
        return UPLOADING_SOUND

    return await save_and_schedule_reminder(update.message, context)

async def save_and_schedule_reminder(message, context):
    chat_id = str(message.chat_id)
    category = context.user_data['category']
    time_mins = context.user_data['time_mins']
    note = context.user_data['note']
    sound_file_id = context.user_data['sound_file_id']
    sound_type = context.user_data['sound_type']
    
    reminder_data = {
        "category": category, 
        "minutes": time_mins, 
        "note": note, 
        "sound_id": sound_file_id,
        "sound_type": sound_type
    }
    
    # ফায়ারবেসে ডাটা সেভ এবং ইউনিক কী (Key) জেনারেট করা
    try:
        loop = asyncio.get_event_loop()
        # push() করার পর জেনারেট হওয়া ইউনিক আইডিটি (Key) আমরা লুফে নেব, পরে ডিলিট করার জন্য
        push_result = await loop.run_in_executor(None, lambda: db.child("reminders").child(chat_id).push(reminder_data))
        reminder_key = push_result['name'] 
        reminder_data['db_key'] = reminder_key # ডেটাবেস কী-টি ডাটার সাথে যুক্ত করা হলো
        print(f"✅ Data saved with key: {reminder_key}")
    except Exception as e:
        print(f"Firebase Error: {e}")
        reminder_data['db_key'] = None

    # JobQueue শিডিউল
    context.job_queue.run_once(trigger_reminder, time_mins * 60, chat_id=chat_id, data=reminder_data)
    
    await message.reply_text("🚀 **রিমাইন্ডারটি ক্লাউডে সেভ করা হয়েছে এবং টাইমার চালু হয়েছে!**", reply_markup=get_main_keyboard(), parse_mode='Markdown')
    return ConversationHandler.END

async def trigger_reminder(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    chat_id = job.chat_id
    note_text = job.data['note']
    category = job.data['category']
    sound_id = job.data['sound_id']
    sound_type = job.data['sound_type']
    db_key = job.data['db_key'] # সেভ করে রাখা ডেটাবেস কী

    # আল্ট্রা-মডার্ন নজরকাড়া নোটিফিকেশন ইন্টারফেস
    stylish_message = (
        f"🚨 ⚠️ **CRITICAL REMINDER ALERT** ⚠️ 🚨\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📌 **Category:** `# {category.upper()}`\n"
        f"📝 **Message:** `{note_text}`\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"⏰ *অনুগ্রহ করে কাজটি এখনই সম্পন্ন করুন!*"
    )

    await context.bot.send_message(chat_id=chat_id, text=stylish_message, parse_mode='Markdown')
    
    # সাউন্ড প্লে করা
    try:
        if sound_type == 'custom':
            await context.bot.send_voice(chat_id=chat_id, voice=sound_id, disable_notification=False)
        else:
            if os.path.exists(sound_id):
                with open(sound_id, 'rb') as voice:
                    await context.bot.send_voice(chat_id=chat_id, voice=voice, disable_notification=False)
    except Exception as e:
        print(f"Sound Trigger Error: {e}")

    # 🔥 [শর্ত পূরণ] কাজ শেষ! এবার ফায়ারবেস ডেটাবেস থেকে এই রিমাইন্ডারটি অটো-মুছে ফেলা হবে
    if db_key:
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, lambda: db.child("reminders").child(chat_id).child(db_key).remove())
            print(f"🗑️ Work finished. Automatically deleted reminder key {db_key} from Firebase!")
        except Exception as e:
            print(f"Error while auto-deleting from Firebase: {e}")

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ বাতিল করা হয়েছে।", reply_markup=get_main_keyboard())
    return ConversationHandler.END

def main():
    from telegram.request import HTTPXRequest
    custom_request = HTTPXRequest(connect_timeout=30.0, read_timeout=30.0)

    app = Application.builder().token(BOT_TOKEN).request(custom_request).build()

    conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex('^➕ নতুন রিমাইন্ডার সেট করুন$'), handle_menu_options)],
        states={
            CHOOSING_CATEGORY: [CallbackQueryHandler(category_picked)],
            TYPING_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, time_received)],
            TYPING_NOTE: [MessageHandler(filters.TEXT & ~filters.COMMAND, note_received)],
            CHOOSING_SOUND: [CallbackQueryHandler(sound_decision)],
            UPLOADING_SOUND: [MessageHandler(filters.VOICE | filters.AUDIO, custom_sound_received)]
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        per_message=False
    )

    app.add_handler(CommandHandler('start', start))
    app.add_handler(conv_handler)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_menu_options))
    
    print("🚀 Advanced Multi-Feature Bot with Auto-Clean DB is running...")
    app.run_polling()

if __name__ == '__main__':
    main()