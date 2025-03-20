import logging
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)


engine = create_engine('sqlite:///time_capsules.db', echo=False)
Base = declarative_base()



class TimeCapsule(Base):
    __tablename__ = 'capsules'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    message = Column(String, nullable=False)
    send_date = Column(DateTime, nullable=False)



Base.metadata.create_all(engine)


Session = sessionmaker(bind=engine)



def save_capsule(user_id, message, send_date):
    session = Session()
    capsule = TimeCapsule(user_id=user_id, message=message, send_date=send_date)
    session.add(capsule)
    session.commit()
    session.close()


async def check_and_send_capsules(context: ContextTypes.DEFAULT_TYPE):
    session = Session()
    current_time = datetime.now()
    capsules = session.query(TimeCapsule).filter(TimeCapsule.send_date <= current_time).all()

    for capsule in capsules:
        await context.bot.send_message(chat_id=capsule.user_id,
                                       text=f"Ваша капсула времени от {capsule.send_date.strftime('%Y-%m-%d %H:%M:%S')}: {capsule.message}")
        session.delete(capsule)

    session.commit()
    session.close()



async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Привет! Напиши сообщение для капсулы времени и укажи, через сколько дней его отправить (например, 'Привет через 365')).")



async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.chat_id
    text = update.message.text.strip()

    # Разделяем сообщение и время
    try:
        parts = text.split(" через ")
        if len(parts) != 2:
            raise ValueError
        message = parts[0].strip()
        days = int(parts[1].strip())
    except (ValueError, IndexError):
        await update.message.reply_text(
            "Напиши сообщение в формате: 'Сообщение через <число дней>' (например, 'Привет через 365').")
        return


    send_date = datetime.now() + timedelta(days=days)


    save_capsule(user_id, message, send_date)


    send_date_str = send_date.strftime('%Y-%m-%d %H:%M:%S')
    await update.message.reply_text(f"Ваше сообщение '{message}' сохранено. Оно будет отправлено вам {send_date_str}.")



def main() -> None:
    TOKEN = os.getenv('TOKEN')
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    application.job_queue.run_repeating(check_and_send_capsules, interval=60)

    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
