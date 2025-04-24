import logging
import asyncio
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.enums import ParseMode
from aiogram.types import FSInputFile
from oauth2client.service_account import ServiceAccountCredentials
import gspread
from PIL import Image, ImageDraw, ImageFont

# Получаем токен из переменных окружения
TOKEN = os.getenv("BOT_TOKEN")

# Настройки путей
CREDENTIALS_FILE = "creds.json"
TEMPLATE_PATH = "card_template.png"
OUTPUT_PATH = "output/generated_card.png"

# Создание бота и диспетчера
bot = Bot(token=TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher()

# Функция подключения к таблице
def get_sheet(link: str):
    sheet_id = link.split("/d/")[1].split("/")[0]
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, scope)
    client = gspread.authorize(creds)
    return client.open_by_key(sheet_id).sheet1

# Команда /start
@dp.message(Command("start"))
async def start_handler(message: types.Message):
    await message.answer(
        "👋 Привет! Я бот для генерации турнирных таблиц по Google Таблице.\n\n"
        "Используй команду:\n"
        "<code>/reg_table Турнир Организация Стадия ССЫЛКА</code>\n\n"
        "Пример:\n"
        "/reg_table WinterCup MEOW Group https://docs.google.com/spreadsheets/d/abc123"
    )

# Команда /reg_table
@dp.message(Command("reg_table"))
async def reg_table_handler(message: types.Message):
    try:
        parts = message.text.split(maxsplit=4)
        if len(parts) != 5:
            await message.answer("❗ Формат: /reg_table Турнир Организация Стадия ССЫЛКА")
            return

        tournament, org, stage, url = parts[1:]
        sheet = get_sheet(url)
        records = sheet.get_all_records()

        # Фильтрация по организации
        team_data = [row for row in records if org.lower() in row.get("Team", "").lower()]
        if not team_data:
            await message.answer("❌ Команды этой организации не найдены.")
            return

        # Загрузка шаблона и шрифтов
        image = Image.open(TEMPLATE_PATH).convert("RGB")
        draw = ImageDraw.Draw(image)
        font = ImageFont.truetype("arial.ttf", 22)
        header_font = ImageFont.truetype("arial.ttf", 36)

        # Название и стадия турнира
        draw.text((500, 100), tournament, font=header_font, fill="white")
        draw.text((500, 150), stage, font=header_font, fill="white")

        # Координаты таблицы
        base_y = 240
        step_y = 40

        left_x = {
            "team": 105, "wwcd": 410, "pp": 460, "fp": 515, "tp": 575
        }
        right_x = {
            "team": 765, "wwcd": 1070, "pp": 1120, "fp": 1170, "tp": 1230
        }

        for i, row in enumerate(team_data[:20]):
            y = base_y + step_y * (i % 10)
            x_set = left_x if i < 10 else right_x
            draw.text((x_set["team"], y), row.get("Team", ""), font=font, fill="white")
            draw.text((x_set["wwcd"], y), str(row.get("WWCD", "0")), font=font, fill="white")
            draw.text((x_set["pp"], y), str(row.get("PP", "0")), font=font, fill="white")
            draw.text((x_set["fp"], y), str(row.get("FP", "0")), font=font, fill="white")
            draw.text((x_set["tp"], y), str(row.get("TP", "0")), font=font, fill="white")

        os.makedirs("output", exist_ok=True)
        image.save(OUTPUT_PATH)

        await message.answer_photo(FSInputFile(OUTPUT_PATH), caption=f"<b>{tournament}</b> — <i>{stage}</i>")

    except Exception as e:
        logging.exception(e)
        await message.answer("⚠️ Ошибка при обработке таблицы. Проверь ссылку и формат.")

# Запуск бота
async def main():
    logging.basicConfig(level=logging.INFO)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
