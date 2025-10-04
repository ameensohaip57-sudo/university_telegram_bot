import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
import sqlite3
from datetime import datetime

# إعدادات البوت
TOKEN = "8404978127:AAHTmTMaF20x86NMzcjiqUIQNvKwpvOO8RQ"
ADMIN_IDS = [7642188270]  # أي دي المدير الرئيسي
DELEGATE_IDS = [7642188270]  # أيدي المندوبين الإضافيين

# إعداد قاعدة البيانات
def init_db():
    conn = sqlite3.connect('university_bot.db')
    cursor = conn.cursor()
    
    # جدول الكليات
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS faculties (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        )
    ''')
    
    # جدول المواد
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS courses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            faculty_id INTEGER,
            FOREIGN KEY (faculty_id) REFERENCES faculties (id)
        )
    ''')
    
    # جدول المستخدمين والصلاحيات
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            faculty_id INTEGER,
            is_delegate INTEGER DEFAULT 0,
            FOREIGN KEY (faculty_id) REFERENCES faculties (id)
        )
    ''')
    
    # جدول الملفات
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_id TEXT NOT NULL,
            file_name TEXT NOT NULL,
            file_type TEXT NOT NULL,
            course_id INTEGER,
            faculty_id INTEGER,
            uploaded_by INTEGER,
            upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (course_id) REFERENCES courses (id),
            FOREIGN KEY (faculty_id) REFERENCES faculties (id),
            FOREIGN KEY (uploaded_by) REFERENCES users (user_id)
        )
    ''')
    
    # إضافة بيانات أولية
    cursor.execute("SELECT COUNT(*) FROM faculties")
    if cursor.fetchone()[0] == 0:
        faculties = [
            ('كلية الهندسة',),
            ('كلية الطب',),
            ('كلية العلوم',),
            ('كلية الآداب',),
            ('كلية إدارة الأعمال',)
        ]
        cursor.executemany("INSERT INTO faculties (name) VALUES (?)", faculties)
        
        # إضافة مواد لكل كلية
        for faculty_id in range(1, 6):
            if faculty_id == 1:  # كلية الهندسة
                courses = [('هندسة الحاسوب',), ('هندسة الكهرباء',), ('هندسة الميكانيكا',)]
            elif faculty_id == 2:  # كلية الطب
                courses = [('طب عام',), ('جراحة',), ('باطنية',)]
            elif faculty_id == 3:  # كلية العلوم
                courses = [('رياضيات',), ('فيزياء',), ('كيمياء',)]
            elif faculty_id == 4:  # كلية الآداب
                courses = [('لغة عربية',), ('تاريخ',), ('فلسفة',)]
            else:  # كلية إدارة الأعمال
                courses = [('محاسبة',), ('إدارة',), ('اقتصاد',)]
            
            for course in courses:
                cursor.execute("INSERT INTO courses (name, faculty_id) VALUES (?, ?)", (course[0], faculty_id))
    
    conn.commit()
    conn.close()

# وظائف مساعدة للقاعدة البيانات
def get_user(user_id):
    conn = sqlite3.connect('university_bot.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()
    conn.close()
    return user

def add_user(user_id, username, first_name):
    conn = sqlite3.connect('university_bot.db')
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO users (user_id, username, first_name) VALUES (?, ?, ?)", 
                   (user_id, username, first_name))
    conn.commit()
    conn.close()

def update_user_faculty(user_id, faculty_id):
    conn = sqlite3.connect('university_bot.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET faculty_id = ? WHERE user_id = ?", (faculty_id, user_id))
    conn.commit()
    conn.close()

def set_user_delegate(user_id, faculty_id):
    conn = sqlite3.connect('university_bot.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET faculty_id = ?, is_delegate = 1 WHERE user_id = ?", (faculty_id, user_id))
    conn.commit()
    conn.close()

def get_faculties():
    conn = sqlite3.connect('university_bot.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM faculties")
    faculties = cursor.fetchall()
    conn.close()
    return faculties

def get_courses_by_faculty(faculty_id):
    conn = sqlite3.connect('university_bot.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM courses WHERE faculty_id = ?", (faculty_id,))
    courses = cursor.fetchall()
    conn.close()
    return courses

def save_file(file_id, file_name, file_type, course_id, faculty_id, uploaded_by):
    conn = sqlite3.connect('university_bot.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO files (file_id, file_name, file_type, course_id, faculty_id, uploaded_by) VALUES (?, ?, ?, ?, ?, ?)",
                   (file_id, file_name, file_type, course_id, faculty_id, uploaded_by))
    conn.commit()
    conn.close()

def get_files_by_course(course_id):
    conn = sqlite3.connect('university_bot.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM files WHERE course_id = ?", (course_id,))
    files = cursor.fetchall()
    conn.close()
    return files

# وظائف البوت
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username
    first_name = update.effective_user.first_name
    
    add_user(user_id, username, first_name)
    
    keyboard = [
        [InlineKeyboardButton("اختيار الكلية", callback_data="select_faculty")],
        [InlineKeyboardButton("عرض المواد والملفات", callback_data="view_courses")],
        [InlineKeyboardButton("رفع ملف", callback_data="upload_file")]
    ]
    
    if user_id in ADMIN_IDS:
        keyboard.append([InlineKeyboardButton("إدارة النظام", callback_data="admin_panel")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"مرحباً {first_name} في بوت تنظيم المحاضرات!\n"
        "اختر من الخيارات أدناه:",
        reply_markup=reply_markup
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_id = query.from_user.id
    
    if data == "select_faculty":
        await select_faculty(query, context)
    elif data.startswith("faculty_"):
        faculty_id = int(data.split("_")[1])
        update_user_faculty(user_id, faculty_id)
        await query.edit_message_text(f"تم اختيار الكلية بنجاح!")
    elif data == "view_courses":
        await view_courses_menu(query, context)
    elif data.startswith("course_files_"):
        course_id = int(data.split("_")[2])
        await show_course_files(query, context, course_id)
    elif data == "upload_file":
        await upload_file_menu(query, context)
    elif data.startswith("upload_course_"):
        course_id = int(data.split("_")[2])
        context.user_data['upload_course'] = course_id
        await query.edit_message_text("الآن أرسل الملف الذي تريد رفعه")
    elif data == "admin_panel":
        await admin_panel(query, context)
    elif data.startswith("set_delegate_"):
        faculty_id = int(data.split("_")[2])
        context.user_data['set_delegate_faculty'] = faculty_id
        await query.edit_message_text("أرسل معرف المستخدم (User ID) الذي تريد تعيينه مندوباً لهذه الكلية:")

async def select_faculty(query, context):
    faculties = get_faculties()
    keyboard = []
    
    for faculty in faculties:
        keyboard.append([InlineKeyboardButton(faculty[1], callback_data=f"faculty_{faculty[0]}")])
    
    keyboard.append([InlineKeyboardButton("رجوع", callback_data="start")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text("اختر كليتك:", reply_markup=reply_markup)

async def view_courses_menu(query, context):
    user = get_user(query.from_user.id)
    if not user or not user[3]:  # إذا لم يختر الكلية
        await query.edit_message_text("يجب عليك اختيار الكلية أولاً!")
        return
    
    faculty_id = user[3]
    courses = get_courses_by_faculty(faculty_id)
    
    keyboard = []
    for course in courses:
        keyboard.append([InlineKeyboardButton(course[1], callback_data=f"course_files_{course[0]}")])
    
    keyboard.append([InlineKeyboardButton("رجوع", callback_data="start")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text("اختر المادة لعرض ملفاتها:", reply_markup=reply_markup)

async def show_course_files(query, context, course_id):
    files = get_files_by_course(course_id)
    
    if not files:
        await query.edit_message_text("لا توجد ملفات لهذه المادة بعد.")
        return
    
    message_text = "ملفات المادة:\n\n"
    for file in files:
        message_text += f"📄 {file[2]} (تم الرفع في: {file[7]})\n"
    
    await query.edit_message_text(message_text)

async def upload_file_menu(query, context):
    user = get_user(query.from_user.id)
    if not user or not user[3]:
        await query.edit_message_text("يجب عليك اختيار الكلية أولاً!")
        return
    
    # التحقق من الصلاحيات - تحديث الشرط
    if not user[4] and query.from_user.id not in ADMIN_IDS and query.from_user.id not in DELEGATE_IDS:
        await query.edit_message_text("ليس لديك صلاحية رفع الملفات. فقط المندوبون يمكنهم رفع الملفات.")
        return
    
    faculty_id = user[3]
    courses = get_courses_by_faculty(faculty_id)
    
    keyboard = []
    for course in courses:
        keyboard.append([InlineKeyboardButton(course[1], callback_data=f"upload_course_{course[0]}")])
    
    keyboard.append([InlineKeyboardButton("رجوع", callback_data="start")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text("اختر المادة لرفع ملف لها:", reply_markup=reply_markup)

async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)
    
    # التحقق من الصلاحيات - تحديث الشرط
    if not user or (not user[4] and user_id not in ADMIN_IDS and user_id not in DELEGATE_IDS):
        await update.message.reply_text("ليس لديك صلاحية رفع الملفات.")
        return
    
    if 'upload_course' not in context.user_data:
        await update.message.reply_text("يرجى اختيار المادة أولاً من القائمة.")
        return
    
    course_id = context.user_data['upload_course']
    faculty_id = user[3]
    
    # تحديد نوع الملف
    if update.message.document:
        file = update.message.document
        file_type = "document"
    elif update.message.photo:
        file = update.message.photo[-1]  # أعلى دقة
        file_type = "photo"
    else:
        await update.message.reply_text("يرجى إرسال ملف أو صورة صالحة.")
        return
    
    file_id = file.file_id
    file_name = file.file_name if hasattr(file, 'file_name') else f"صورة_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # حفظ المعلومات في قاعدة البيانات
    save_file(file_id, file_name, file_type, course_id, faculty_id, user_id)
    
    await update.message.reply_text("تم رفع الملف بنجاح!")
    del context.user_data['upload_course']

async def admin_panel(query, context):
    if query.from_user.id not in ADMIN_IDS:
        await query.edit_message_text("ليس لديك صلاحية الدخول لهذه الصفحة.")
        return
    
    faculties = get_faculties()
    keyboard = []
    
    for faculty in faculties:
        keyboard.append([InlineKeyboardButton(f"تعيين مندوب لـ {faculty[1]}", callback_data=f"set_delegate_{faculty[0]}")])
    
    keyboard.append([InlineKeyboardButton("رجوع", callback_data="start")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text("لوحة إدارة النظام:", reply_markup=reply_markup)

async def handle_admin_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return
    
    if 'set_delegate_faculty' in context.user_data:
        try:
            delegate_id = int(update.message.text)
            faculty_id = context.user_data['set_delegate_faculty']
            
            set_user_delegate(delegate_id, faculty_id)
            
            await update.message.reply_text(f"تم تعيين المستخدم {delegate_id} كمندوب للكلية بنجاح!")
            del context.user_data['set_delegate_faculty']
        except ValueError:
            await update.message.reply_text("يرجى إرسال معرف مستخدم صحيح (أرقام فقط).")

def main():
    # إعداد قاعدة البيانات
    init_db()
    
    # إعداد البوت
    application = Application.builder().token(TOKEN).build()
    
    # إضافة handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.Document.ALL | filters.PHOTO, handle_file))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_admin_message))
    
    # بدء البوت
    print("البوت يعمل الآن...")
    application.run_polling()

if _name_ == '_main_':
    main()import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
import sqlite3
from datetime import datetime

# إعدادات البوت
TOKEN = "8404978127:AAHTmTMaF20x86NMzcjiqUIQNvKwpvOO8RQ"
ADMIN_IDS = [7642188270]  # أي دي المدير الرئيسي
DELEGATE_IDS = [7642188270]  # أيدي المندوبين الإضافيين

# إعداد قاعدة البيانات
def init_db():
    conn = sqlite3.connect('university_bot.db')
    cursor = conn.cursor()
    
    # جدول الكليات
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS faculties (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        )
    ''')
    
    # جدول المواد
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS courses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            faculty_id INTEGER,
            FOREIGN KEY (faculty_id) REFERENCES faculties (id)
        )
    ''')
    
    # جدول المستخدمين والصلاحيات
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            faculty_id INTEGER,
            is_delegate INTEGER DEFAULT 0,
            FOREIGN KEY (faculty_id) REFERENCES faculties (id)
        )
    ''')
    
    # جدول الملفات
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_id TEXT NOT NULL,
            file_name TEXT NOT NULL,
            file_type TEXT NOT NULL,
            course_id INTEGER,
            faculty_id INTEGER,
            uploaded_by INTEGER,
            upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (course_id) REFERENCES courses (id),
            FOREIGN KEY (faculty_id) REFERENCES faculties (id),
            FOREIGN KEY (uploaded_by) REFERENCES users (user_id)
        )
    ''')
    
    # إضافة بيانات أولية
    cursor.execute("SELECT COUNT(*) FROM faculties")
    if cursor.fetchone()[0] == 0:
        faculties = [
            ('كلية الهندسة',),
            ('كلية الطب',),
            ('كلية العلوم',),
            ('كلية الآداب',),
            ('كلية إدارة الأعمال',)
        ]
        cursor.executemany("INSERT INTO faculties (name) VALUES (?)", faculties)
        
        # إضافة مواد لكل كلية
        for faculty_id in range(1, 6):
            if faculty_id == 1:  # كلية الهندسة
                courses = [('هندسة الحاسوب',), ('هندسة الكهرباء',), ('هندسة الميكانيكا',)]
            elif faculty_id == 2:  # كلية الطب
                courses = [('طب عام',), ('جراحة',), ('باطنية',)]
            elif faculty_id == 3:  # كلية العلوم
                courses = [('رياضيات',), ('فيزياء',), ('كيمياء',)]
            elif faculty_id == 4:  # كلية الآداب
                courses = [('لغة عربية',), ('تاريخ',), ('فلسفة',)]
            else:  # كلية إدارة الأعمال
                courses = [('محاسبة',), ('إدارة',), ('اقتصاد',)]
            
            for course in courses:
                cursor.execute("INSERT INTO courses (name, faculty_id) VALUES (?, ?)", (course[0], faculty_id))
    
    conn.commit()
    conn.close()

# وظائف مساعدة للقاعدة البيانات
def get_user(user_id):
    conn = sqlite3.connect('university_bot.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()
    conn.close()
    return user

def add_user(user_id, username, first_name):
    conn = sqlite3.connect('university_bot.db')
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO users (user_id, username, first_name) VALUES (?, ?, ?)", 
                   (user_id, username, first_name))
    conn.commit()
    conn.close()

def update_user_faculty(user_id, faculty_id):
    conn = sqlite3.connect('university_bot.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET faculty_id = ? WHERE user_id = ?", (faculty_id, user_id))
    conn.commit()
    conn.close()

def set_user_delegate(user_id, faculty_id):
    conn = sqlite3.connect('university_bot.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET faculty_id = ?, is_delegate = 1 WHERE user_id = ?", (faculty_id, user_id))
    conn.commit()
    conn.close()

def get_faculties():
    conn = sqlite3.connect('university_bot.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM faculties")
    faculties = cursor.fetchall()
    conn.close()
    return faculties

def get_courses_by_faculty(faculty_id):
    conn = sqlite3.connect('university_bot.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM courses WHERE faculty_id = ?", (faculty_id,))
    courses = cursor.fetchall()
    conn.close()
    return courses

def save_file(file_id, file_name, file_type, course_id, faculty_id, uploaded_by):
    conn = sqlite3.connect('university_bot.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO files (file_id, file_name, file_type, course_id, faculty_id, uploaded_by) VALUES (?, ?, ?, ?, ?, ?)",
                   (file_id, file_name, file_type, course_id, faculty_id, uploaded_by))
    conn.commit()
    conn.close()

def get_files_by_course(course_id):
    conn = sqlite3.connect('university_bot.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM files WHERE course_id = ?", (course_id,))
    files = cursor.fetchall()
    conn.close()
    return files

# وظائف البوت
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username
    first_name = update.effective_user.first_name
    
    add_user(user_id, username, first_name)
    
    keyboard = [
        [InlineKeyboardButton("اختيار الكلية", callback_data="select_faculty")],
        [InlineKeyboardButton("عرض المواد والملفات", callback_data="view_courses")],
        [InlineKeyboardButton("رفع ملف", callback_data="upload_file")]
    ]
    
    if user_id in ADMIN_IDS:
        keyboard.append([InlineKeyboardButton("إدارة النظام", callback_data="admin_panel")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"مرحباً {first_name} في بوت تنظيم المحاضرات!\n"
        "اختر من الخيارات أدناه:",
        reply_markup=reply_markup
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_id = query.from_user.id
    
    if data == "select_faculty":
        await select_faculty(query, context)
    elif data.startswith("faculty_"):
        faculty_id = int(data.split("_")[1])
        update_user_faculty(user_id, faculty_id)
        await query.edit_message_text(f"تم اختيار الكلية بنجاح!")
    elif data == "view_courses":
        await view_courses_menu(query, context)
    elif data.startswith("course_files_"):
        course_id = int(data.split("_")[2])
        await show_course_files(query, context, course_id)
    elif data == "upload_file":
        await upload_file_menu(query, context)
    elif data.startswith("upload_course_"):
        course_id = int(data.split("_")[2])
        context.user_data['upload_course'] = course_id
        await query.edit_message_text("الآن أرسل الملف الذي تريد رفعه")
    elif data == "admin_panel":
        await admin_panel(query, context)
    elif data.startswith("set_delegate_"):
        faculty_id = int(data.split("_")[2])
        context.user_data['set_delegate_faculty'] = faculty_id
        await query.edit_message_text("أرسل معرف المستخدم (User ID) الذي تريد تعيينه مندوباً لهذه الكلية:")

async def select_faculty(query, context):
    faculties = get_faculties()
    keyboard = []
    
    for faculty in faculties:
        keyboard.append([InlineKeyboardButton(faculty[1], callback_data=f"faculty_{faculty[0]}")])
    
    keyboard.append([InlineKeyboardButton("رجوع", callback_data="start")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text("اختر كليتك:", reply_markup=reply_markup)

async def view_courses_menu(query, context):
    user = get_user(query.from_user.id)
    if not user or not user[3]:  # إذا لم يختر الكلية
        await query.edit_message_text("يجب عليك اختيار الكلية أولاً!")
        return
    
    faculty_id = user[3]
    courses = get_courses_by_faculty(faculty_id)
    
    keyboard = []
    for course in courses:
        keyboard.append([InlineKeyboardButton(course[1], callback_data=f"course_files_{course[0]}")])
    
    keyboard.append([InlineKeyboardButton("رجوع", callback_data="start")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text("اختر المادة لعرض ملفاتها:", reply_markup=reply_markup)

async def show_course_files(query, context, course_id):
    files = get_files_by_course(course_id)
    
    if not files:
        await query.edit_message_text("لا توجد ملفات لهذه المادة بعد.")
        return
    
    message_text = "ملفات المادة:\n\n"
    for file in files:
        message_text += f"📄 {file[2]} (تم الرفع في: {file[7]})\n"
    
    await query.edit_message_text(message_text)

async def upload_file_menu(query, context):
    user = get_user(query.from_user.id)
    if not user or not user[3]:
        await query.edit_message_text("يجب عليك اختيار الكلية أولاً!")
        return
    
    # التحقق من الصلاحيات - تحديث الشرط
    if not user[4] and query.from_user.id not in ADMIN_IDS and query.from_user.id not in DELEGATE_IDS:
        await query.edit_message_text("ليس لديك صلاحية رفع الملفات. فقط المندوبون يمكنهم رفع الملفات.")
        return
    
    faculty_id = user[3]
    courses = get_courses_by_faculty(faculty_id)
    
    keyboard = []
    for course in courses:
        keyboard.append([InlineKeyboardButton(course[1], callback_data=f"upload_course_{course[0]}")])
    
    keyboard.append([InlineKeyboardButton("رجوع", callback_data="start")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text("اختر المادة لرفع ملف لها:", reply_markup=reply_markup)

async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)
    
    # التحقق من الصلاحيات - تحديث الشرط
    if not user or (not user[4] and user_id not in ADMIN_IDS and user_id not in DELEGATE_IDS):
        await update.message.reply_text("ليس لديك صلاحية رفع الملفات.")
        return
    
    if 'upload_course' not in context.user_data:
        await update.message.reply_text("يرجى اختيار المادة أولاً من القائمة.")
        return
    
    course_id = context.user_data['upload_course']
    faculty_id = user[3]
    
    # تحديد نوع الملف
    if update.message.document:
        file = update.message.document
        file_type = "document"
    elif update.message.photo:
        file = update.message.photo[-1]  # أعلى دقة
        file_type = "photo"
    else:
        await update.message.reply_text("يرجى إرسال ملف أو صورة صالحة.")
        return
    
    file_id = file.file_id
    file_name = file.file_name if hasattr(file, 'file_name') else f"صورة_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # حفظ المعلومات في قاعدة البيانات
    save_file(file_id, file_name, file_type, course_id, faculty_id, user_id)
    
    await update.message.reply_text("تم رفع الملف بنجاح!")
    del context.user_data['upload_course']

async def admin_panel(query, context):
    if query.from_user.id not in ADMIN_IDS:
        await query.edit_message_text("ليس لديك صلاحية الدخول لهذه الصفحة.")
        return
    
    faculties = get_faculties()
    keyboard = []
    
    for faculty in faculties:
        keyboard.append([InlineKeyboardButton(f"تعيين مندوب لـ {faculty[1]}", callback_data=f"set_delegate_{faculty[0]}")])
    
    keyboard.append([InlineKeyboardButton("رجوع", callback_data="start")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text("لوحة إدارة النظام:", reply_markup=reply_markup)

async def handle_admin_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return
    
    if 'set_delegate_faculty' in context.user_data:
        try:
            delegate_id = int(update.message.text)
            faculty_id = context.user_data['set_delegate_faculty']
            
            set_user_delegate(delegate_id, faculty_id)
            
            await update.message.reply_text(f"تم تعيين المستخدم {delegate_id} كمندوب للكلية بنجاح!")
            del context.user_data['set_delegate_faculty']
        except ValueError:
            await update.message.reply_text("يرجى إرسال معرف مستخدم صحيح (أرقام فقط).")

def main():
    # إعداد قاعدة البيانات
    init_db()
    
    # إعداد البوت
    application = Application.builder().token(TOKEN).build()
    
    # إضافة handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.Document.ALL | filters.PHOTO, handle_file))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_admin_message))
    
    # بدء البوت
    print("البوت يعمل الآن...")
    application.run_polling()

if _name_ == '_main_':
    main()import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
import sqlite3
from datetime import datetime

# إعدادات البوت - استخدم متغيرات البيئة للحماية
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '8404978127:AAHTmTMaF20x86NMzcjiqUIQNvKwpvOO8RQ')
ADMIN_IDS = [int(x) for x in os.getenv('ADMIN_IDS', '7642188270').split(',')]
DELEGATE_IDS = [int(x) for x in os.getenv('DELEGATE_IDS', '7642188270').split(',')]

# إعداد التسجيل
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(_name_)

# إعداد قاعدة البيانات
def init_db():
    conn = sqlite3.connect('university_bot.db')
    cursor = conn.cursor()
    
    # جدول الكليات
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS faculties (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        )
    ''')
    
    # جدول المواد
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS courses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            faculty_id INTEGER,
            FOREIGN KEY (faculty_id) REFERENCES faculties (id)
        )
    ''')
    
    # جدول المستخدمين والصلاحيات
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            faculty_id INTEGER,
            is_delegate INTEGER DEFAULT 0,
            FOREIGN KEY (faculty_id) REFERENCES faculties (id)
        )
    ''')
    
    # جدول الملفات
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_id TEXT NOT NULL,
            file_name TEXT NOT NULL,
            file_type TEXT NOT NULL,
            course_id INTEGER,
            faculty_id INTEGER,
            uploaded_by INTEGER,
            upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (course_id) REFERENCES courses (id),
            FOREIGN KEY (faculty_id) REFERENCES faculties (id),
            FOREIGN KEY (uploaded_by) REFERENCES users (user_id)
        )
    ''')
    
    # إضافة بيانات أولية
    cursor.execute("SELECT COUNT(*) FROM faculties")
    if cursor.fetchone()[0] == 0:
        faculties = [
            ('كلية الهندسة',),
            ('كلية الطب',),
            ('كلية العلوم',),
            ('كلية الآداب',),
            ('كلية إدارة الأعمال',)
        ]
        cursor.executemany("INSERT INTO faculties (name) VALUES (?)", faculties)
        
        # إضافة مواد لكل كلية
        for faculty_id in range(1, 6):
            if faculty_id == 1:  # كلية الهندسة
                courses = [('هندسة الحاسوب',), ('هندسة الكهرباء',), ('هندسة الميكانيكا',)]
            elif faculty_id == 2:  # كلية الطب
                courses = [('طب عام',), ('جراحة',), ('باطنية',)]
            elif faculty_id == 3:  # كلية العلوم
                courses = [('رياضيات',), ('فيزياء',), ('كيمياء',)]
            elif faculty_id == 4:  # كلية الآداب
                courses = [('لغة عربية',), ('تاريخ',), ('فلسفة',)]
            else:  # كلية إدارة الأعمال
                courses = [('محاسبة',), ('إدارة',), ('اقتصاد',)]
            
            for course in courses:
                cursor.execute("INSERT INTO courses (name, faculty_id) VALUES (?, ?)", (course[0], faculty_id))
    
    conn.commit()
    conn.close()

# وظائف مساعدة للقاعدة البيانات
def get_user(user_id):
    conn = sqlite3.connect('university_bot.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()
    conn.close()
    return user

def add_user(user_id, username, first_name):
    conn = sqlite3.connect('university_bot.db')
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO users (user_id, username, first_name) VALUES (?, ?, ?)", 
                   (user_id, username, first_name))
    conn.commit()
    conn.close()

def update_user_faculty(user_id, faculty_id):
    conn = sqlite3.connect('university_bot.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET faculty_id = ? WHERE user_id = ?", (faculty_id, user_id))
    conn.commit()
    conn.close()

def set_user_delegate(user_id, faculty_id):
    conn = sqlite3.connect('university_bot.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET faculty_id = ?, is_delegate = 1 WHERE user_id = ?", (faculty_id, user_id))
    conn.commit()
    conn.close()

def get_faculties():
    conn = sqlite3.connect('university_bot.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM faculties")
    faculties = cursor.fetchall()
    conn.close()
    return faculties

def get_courses_by_faculty(faculty_id):
    conn = sqlite3.connect('university_bot.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM courses WHERE faculty_id = ?", (faculty_id,))
    courses = cursor.fetchall()
    conn.close()
    return courses

def save_file(file_id, file_name, file_type, course_id, faculty_id, uploaded_by):
    conn = sqlite3.connect('university_bot.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO files (file_id, file_name, file_type, course_id, faculty_id, uploaded_by) VALUES (?, ?, ?, ?, ?, ?)",
                   (file_id, file_name, file_type, course_id, faculty_id, uploaded_by))
    conn.commit()
    conn.close()

def get_files_by_course(course_id):
    conn = sqlite3.connect('university_bot.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM files WHERE course_id = ?", (course_id,))
    files = cursor.fetchall()
    conn.close()
    return files

# وظائف البوت
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username
    first_name = update.effective_user.first_name
    
    add_user(user_id, username, first_name)
    
    keyboard = [
        [InlineKeyboardButton("اختيار الكلية", callback_data="select_faculty")],
        [InlineKeyboardButton("عرض المواد والملفات", callback_data="view_courses")],
        [InlineKeyboardButton("رفع ملف", callback_data="upload_file")]
    ]
    
    if user_id in ADMIN_IDS:
        keyboard.append([InlineKeyboardButton("إدارة النظام", callback_data="admin_panel")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"مرحباً {first_name} في بوت تنظيم المحاضرات!\n"
        "اختر من الخيارات أدناه:",
        reply_markup=reply_markup
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_id = query.from_user.id
    
    if data == "select_faculty":
        await select_faculty(query, context)
    elif data.startswith("faculty_"):
        faculty_id = int(data.split("_")[1])
        update_user_faculty(user_id, faculty_id)
        await query.edit_message_text(f"تم اختيار الكلية بنجاح!")
    elif data == "view_courses":
        await view_courses_menu(query, context)
    elif data.startswith("course_files_"):
        course_id = int(data.split("_")[2])
        await show_course_files(query, context, course_id)
    elif data == "upload_file":
        await upload_file_menu(query, context)
    elif data.startswith("upload_course_"):
        course_id = int(data.split("_")[2])
        context.user_data['upload_course'] = course_id
        await query.edit_message_text("الآن أرسل الملف الذي تريد رفعه")
    elif data == "admin_panel":
        await admin_panel(query, context)
    elif data.startswith("set_delegate_"):
        faculty_id = int(data.split("_")[2])
        context.user_data['set_delegate_faculty'] = faculty_id
        await query.edit_message_text("أرسل معرف المستخدم (User ID) الذي تريد تعيينه مندوباً لهذه الكلية:")

async def select_faculty(query, context):
    faculties = get_faculties()
    keyboard = []
    
    for faculty in faculties:
        keyboard.append([InlineKeyboardButton(faculty[1], callback_data=f"faculty_{faculty[0]}")])
    
    keyboard.append([InlineKeyboardButton("رجوع", callback_data="start")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text("اختر كليتك:", reply_markup=reply_markup)

async def view_courses_menu(query, context):
    user = get_user(query.from_user.id)
    if not user or not user[3]:  # إذا لم يختر الكلية
        await query.edit_message_text("يجب عليك اختيار الكلية أولاً!")
        return
    
    faculty_id = user[3]
    courses = get_courses_by_faculty(faculty_id)
    
    keyboard = []
    for course in courses:
        keyboard.append([InlineKeyboardButton(course[1], callback_data=f"course_files_{course[0]}")])
    
    keyboard.append([InlineKeyboardButton("رجوع", callback_data="start")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text("اختر المادة لعرض ملفاتها:", reply_markup=reply_markup)

async def show_course_files(query, context, course_id):
    files = get_files_by_course(course_id)
    
    if not files:
        await query.edit_message_text("لا توجد ملفات لهذه المادة بعد.")
        return
    
    message_text = "ملفات المادة:\n\n"
    for file in files:
        message_text += f"📄 {file[2]} (تم الرفع في: {file[7]})\n"
    
    await query.edit_message_text(message_text)

async def upload_file_menu(query, context):
    user = get_user(query.from_user.id)
    if not user or not user[3]:
        await query.edit_message_text("يجب عليك اختيار الكلية أولاً!")
        return
    
    # التحقق من الصلاحيات
    if not user[4] and query.from_user.id not in ADMIN_IDS and query.from_user.id not in DELEGATE_IDS:
        await query.edit_message_text("ليس لديك صلاحية رفع الملفات. فقط المندوبون يمكنهم رفع الملفات.")
        return
    
    faculty_id = user[3]
    courses = get_courses_by_faculty(faculty_id)
    
    keyboard = []
    for course in courses:
        keyboard.append([InlineKeyboardButton(course[1], callback_data=f"upload_course_{course[0]}")])
    
    keyboard.append([InlineKeyboardButton("رجوع", callback_data="start")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text("اختر المادة لرفع ملف لها:", reply_markup=reply_markup)

async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)
    
    # التحقق من الصلاحيات
    if not user or (not user[4] and user_id not in ADMIN_IDS and user_id not in DELEGATE_IDS):
        await update.message.reply_text("ليس لديك صلاحية رفع الملفات.")
        return
    
    if 'upload_course' not in context.user_data:
        await update.message.reply_text("يرجى اختيار المادة أولاً من القائمة.")
        return
    
    course_id = context.user_data['upload_course']
    faculty_id = user[3]
    
    # تحديد نوع الملف
    if update.message.document:
        file = update.message.document
        file_type = "document"
    elif update.message.photo:
        file = update.message.photo[-1]  # أعلى دقة
        file_type = "photo"
    else:
        await update.message.reply_text("يرجى إرسال ملف أو صورة صالحة.")
        return
    
    file_id = file.file_id
    file_name = file.file_name if hasattr(file, 'file_name') else f"صورة_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # حفظ المعلومات في قاعدة البيانات
    save_file(file_id, file_name, file_type, course_id, faculty_id, user_id)
    
    await update.message.reply_text("تم رفع الملف بنجاح!")
    del context.user_data['upload_course']

async def admin_panel(query, context):
    if query.from_user.id not in ADMIN_IDS:
        await query.edit_message_text("ليس لديك صلاحية الدخول لهذه الصفحة.")
        return
    
    faculties = get_faculties()
    keyboard = []
    
    for faculty in faculties:
        keyboard.append([InlineKeyboardButton(f"تعيين مندوب لـ {faculty[1]}", callback_data=f"set_delegate_{faculty[0]}")])
    
    keyboard.append([InlineKeyboardButton("رجوع", callback_data="start")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text("لوحة إدارة النظام:", reply_markup=reply_markup)

async def handle_admin_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return
    
    if 'set_delegate_faculty' in context.user_data:
        try:
            delegate_id = int(update.message.text)
            faculty_id = context.user_data['set_delegate_faculty']
            
            set_user_delegate(delegate_id, faculty_id)
            
            await update.message.reply_text(f"تم تعيين المستخدم {delegate_id} كمندوب للكلية بنجاح!")
            del context.user_data['set_delegate_faculty']
        except ValueError:
            await update.message.reply_text("يرجى إرسال معرف مستخدم صحيح (أرقام فقط).")

def main():
    # إعداد قاعدة البيانات
    init_db()
    
    # إعداد البوت
    application = Application.builder().token(TOKEN).build()
    
    # إضافة handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.Document.ALL | filters.PHOTO, handle_file))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_admin_message))
    
    # بدء البوت
    logger.info("البوت يعمل الآن...")
    application.run_polling()
