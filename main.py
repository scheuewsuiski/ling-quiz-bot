#!/usr/bin/env python

import logging
import json
from random import shuffle
from secret import TOKEN

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Poll,
    PollAnswer,
    Update,
)
from telegram.constants import ParseMode, ChatType
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    PollAnswerHandler,
    PollHandler,
    CallbackQueryHandler,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data.clear()
    context.user_data['state'] = 'idle'
    await update.message.reply_text("Привет! 👋 Это бот-викторина, чтобы проверить твои знания в  лингвистике!\n\nНапиши /quiz чтобы начать викторину\n\nУдачи!")

quizzes = []

quiz_list = {"фонетика": "quizzes/phonetics.json", "старослав": "quizzes/ocs.json"}

async def pitch_question(chat_id: int, context: ContextTypes.DEFAULT_TYPE, q, user_id):
    message = await context.bot.send_poll(
                chat_id=chat_id,
                question=q["message"],
                options=q["options"],
                type=Poll.QUIZ,
                correct_option_id=q["corr"],
                is_anonymous=False
        )
    payload = {
        message.poll.id: {
            "chat_id": chat_id,
            "message_id": message.message_id,
            "correct_option": q["corr"],
            "user_answers": {},
            "user_id": user_id,
            }
    }
    context.bot_data.update(payload)

async def start_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    shuffle(quizzes)
    context.user_data['state']  = 'quiz'
    context.user_data['score']  = 0
    context.user_data['curr_q'] = 0
    context.user_data['user_id'] = update.effective_chat.id
    if update.effective_chat.type == ChatType.GROUP or update.effective_chat.type == ChatType.SUPERGROUP:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Этим ботом можно пользоваться только в лс.")
        return

    await pitch_question(update.effective_chat.id, context, quizzes[context.user_data['curr_q']], user_id=update.effective_chat.id)
    context.user_data['curr_q'] += 1

async def quiz(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data['state'] = 'selecting_quiz'
    keyboard = []
    for i in list(quiz_list.keys()):
        keyboard.append([InlineKeyboardButton(i, callback_data=quiz_list[i])])

    await update.message.reply_text("На какую тему ты хочешь викторину?", reply_markup=InlineKeyboardMarkup(keyboard))

async def end_quiz(chat_id: int, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data['state'] = 'idle'
    await context.bot.send_message(chat_id=chat_id, text=f"У тебя: {context.user_data['score']} правильных ответов")

async def quiz_answer_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    answer = update.poll_answer

    quiz_data = context.bot_data[answer.poll_id]
    chat_id = quiz_data["chat_id"]

    if answer.user.id != quiz_data["user_id"]:
        await context.bot.send_message(chat_id=chat_id, text="На опрос ответил не ты. Может быть ты переслал кому-то сообщение? Думать надо собственной головой.")
        return

    if not answer.option_ids:
        return

    if answer.option_ids[0] == quiz_data["correct_option"]:
        context.user_data["score"] += 1
    
    if context.user_data["curr_q"] == len(quizzes):
        await end_quiz(chat_id, context)
        return
    else:
        await pitch_question(chat_id, context, quizzes[context.user_data['curr_q']], user_id=answer.user.id)
        context.user_data["curr_q"] += 1

async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("/start - показать приветственное сообщение\n/quiz - начать викторину\n/help - вывести это сообщение")

async def button_feedback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if context.user_data['state'] != 'selecting_quiz':
        print('s')
        return
    global quizzes
    query = update.callback_query
    await query.answer()

    with open(query.data) as f:
        quizzes = json.load(f)
    quizzes = quizzes["questions"]
    await start_quiz(update, context)

def main() -> None:
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("quiz", quiz))
    application.add_handler(CommandHandler("help", help_handler))
    application.add_handler(PollAnswerHandler(quiz_answer_handler))
    application.add_handler(CallbackQueryHandler(button_feedback))

    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
