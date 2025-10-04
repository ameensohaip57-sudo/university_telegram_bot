import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
import sqlite3
from datetime import datetime

# إعدادات البوت
TOKEN = "8226186187:AAHIOUzLo1jAhTcv4LuKwpyw6rFcXaUx7io"
SUPER_ADMIN_ID = 7642188270  # آيدي @eng_Soh_57

# إعداد التسجيل
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(_name_)

# إعداد قاعدة البيانات
def init_db():
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            is_admin INTEGER DEFAULT 0
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_id TEXT NOT NULL,
            file_name TEXT NOT NULL,
            file_type TEXT NOT NULL,
            uploaded_by INTEGER,
            upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # إضافة المدير العام
    cursor.execute('''
        INSERT OR REPLACE INTO users (user_id, username, first_name, is_admin) 
        VALUES (?, ?, ?, 1)
    ''', (SUPER_ADMIN_ID, 'eng_Soh_57', 'المدير العام'))
    
    conn.commit()
    conn.close()

def is_admin(user_id):
    return user_id == SUPER_ADMIN_ID

def add_user(user_id, username, first_name):
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO users (user_id, username, first_name) VALUES (?, ?, ?)", 
                   (user_id, username, first_name))
    conn.commit()
    conn.close()

def save_file(file_id, file_name, file_type, uploaded_by):
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO files (file_id, file_name, file_type, uploaded_by) VALUES (?, ?, ?, ?)",
                   (file_id, file_name, file_type, uploaded_by))
    conn.commit()
    conn.close()

def get_all_files():
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM files")
    files = cursor.fetchall()
    conn.close()
    return files

def get_all_users():
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users")
    users = cursor.fetchall()
    conn.close()
    return users

def delete_file(file_id):
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM files WHERE id = ?", (file_id,))
    conn.commit()
    conn.close()

def delete_user(user_id):
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE user_id = ? AND user_id != ?", (user_id, SUPER_ADMIN_ID))
    conn.commit()
    conn.close()

# وظائف البوت
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username
    first_name = update.effective_user.first_name
    
    add_user(user_id, username, first_name)
    
    if is_admin(user_id):
        keyboard = [
            [InlineKeyboardButton("📊 عرض جميع المستخدمين", callback_data="view_users")],
            [InlineKeyboardButton("📁 عرض جميع الملفات", callback_data="view_files")],
            [InlineKeyboardButton("🗑 حذف جميع الملفات", callback_data="delete_all_files")],
            [InlineKeyboardButton("🔧 إعدادات متقدمة", callback_data="advanced_settings")]
        ]
        welcome_text = f"👑 أهلاً وسهلاً بك {first_name}!\nأنت المدير العام لهذا البوت"
    else:
        keyboard = [
            [InlineKeyboardButton("📤 رفع ملف", callback_data="upload_file")],
            [InlineKeyboardButton("ℹ معلومات", callback_data="info")]
        ]
        welcome_text = f"مرحباً {first_name}!"
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(welcome_text, reply_markup=reply_markup)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data
    
    if data == "upload_file":
        context.user_data['waiting_for_file'] = True
        await query.edit_message_text("📤 أرسل الملف الذي تريد رفعه الآن")
    
    elif data == "view_files" and is_admin(user_id):
        files = get_all_files()
        if not files:
            await query.edit_message_text("📭 لا توجد ملفات في النظام")
            return
        
        text = "📁 *جميع الملفات في النظام:*\n\n"
        keyboard = []
        
        for file in files:
            text += f"📄 {file[2]} (بواسطة: {file[4]})\n"
            keyboard.append([InlineKeyboardButton(f"🗑 حذف {file[2]}", callback_data=f"delete_file_{file[0]}")])
        
        keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data="back_to_start")])
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif data == "view_users" and is_admin(user_id):
        users = get_all_users()
        text = "👥 *جميع المستخدمين:*\n\n"
        keyboard = []
        
        for user in users:
            status = "👑 مدير" if user[3] == 1 else "👤 مستخدم"
            text += f"{status}: {user[2]} (ID: {user[0]})\n"
            if user[0] != SUPER_ADMIN_ID:
                keyboard.append([InlineKeyboardButton(f"🗑 حذف {user[2]}", callback_data=f"delete_user_{user[0]}")])
        
        keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data="back_to_start")])
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif data == "delete_all_files" and is_admin(user_id):
        conn = sqlite3.connect('bot.db')
        cursor = conn.cursor()
        cursor.execute("DELETE FROM files")
        conn.commit()
        conn.close()
        await query.edit_message_text("✅ تم حذف جميع الملفات")
    
    elif data.startswith("delete_file_") and is_admin(user_id):
        file_id = int(data.split("_")[2])
        delete_file(file_id)
        await query.edit_message_text("✅ تم حذف الملف")
    
    elif data.startswith("delete_user_") and is_admin(user_id):
        user_id_to_delete = int(data.split("_")[2])
        delete_user(user_id_to_delete)
        await query.edit_message_text("✅ تم حذف المستخدم")
    
    elif data == "advanced_settings" and is_admin(user_id):
        keyboard = [
            [InlineKeyboardButton("📈 إحصائيات النظام", callback_data="stats")],
            [InlineKeyboardButton("🔄 إعادة تشغيل البوت", callback_data="restart")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="back_to_start")]
        ]
        await query.edit_message_text("⚙ *الإعدادات المتقدمة:*", reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif data == "stats" and is_admin(user_id):
        users = get_all_users()
        files = get_all_files()
        text = f"📊 *إحصائيات النظام:*\n\n"
        text += f"👥 عدد المستخدمين: {len(users)}\n"
        text += f"📁 عدد الملفات: {len(files)}\n"
        text += f"🆔 آيدي المدير: {SUPER_ADMIN_ID}\n"
        text += f"👤 يوزر المدير: @eng_Soh_57"
        await query.edit_message_text(text)
    
    elif data == "info":
        await query.edit_message_text("🤖 هذا بوت لرفع ومشاركة الملفات\n\n👨‍💼 المطور: @eng_Soh_57")
    
    elif data == "back_to_start":
        await start(update, context)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if context.user_data.get('waiting_for_file'):
        if update.message.document or update.message.photo:
            if update.message.document:
                file = update.message.document
                file_type = "document"
            else:
                file = update.message.photo[-1]
                file_type = "photo"
            
            file_id = file.file_id
            file_name = file.file_name if hasattr(file, 'file_name') else f"صورة_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            save_file(file_id, file_name, file_type, user_id)
            await update.message.reply_text("✅ تم رفع الملف بنجاح!")
            context.user_data['waiting_for_file'] = False
        else:
            await update.message.reply_text("❌ يرجى إرسال ملف أو صورة")
    else:
        if is_admin(user_id):
            await update.message.reply_text("👑 يمكنك استخدام الأزرار للتحكم في البوت")
        else:
            await update.message.reply_text("🔧 استخدم /start لرؤية الخيارات المتاحة")

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await handle_message(update, context)

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await handle_message(update, context)

def main():
    init_db()
    
    application = Application.builder().token(TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    logger.info("🚀 البوت يعمل الآن...")
    logger.info(f"👑 المدير العام: {SUPER_ADMIN_ID} (@eng_Soh_57)")
    
    application.run_polling()
