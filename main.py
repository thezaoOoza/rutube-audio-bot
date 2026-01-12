import os
import asyncio
import logging
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
import yt_dlp
import httpx

# --- НАСТРОЙКИ ---
API_TOKEN = os.getenv("TELEGRAM_TOKEN")
# На Render URL будет иметь вид https://имя-сервиса.onrender.com
BASE_URL = os.getenv("RENDER_EXTERNAL_URL") 

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# --- ЛОГИКА ЗАГРУЗКИ ---
def download_audio(url):
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': 'downloads/%(id)s.%(ext)s',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'quiet': True,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        return f"downloads/{info['id']}.mp3", info.get('title', 'Аудио')

# --- ХЕНДЛЕРЫ ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("🚀 Бот на Render запущен! Присылай ссылку на Rutube.")

@dp.message(F.text.contains("rutube.ru"))
async def handle_rutube(message: types.Message):
    status_msg = await message.answer("Запрос обрабатывается ⏳")
    try:
        loop = asyncio.get_event_loop()
        file_path, title = await loop.run_in_executor(None, download_audio, message.text)
        
        await message.answer_audio(
            types.FSInputFile(file_path), 
            caption=f"🎬 {title}\n(Скорость меняется в плеере Telegram)"
        )
        await status_msg.delete()
        if os.path.exists(file_path): os.remove(file_path)
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        await status_msg.edit_text(f"❌ Ошибка: {str(e)}")

# --- АНТИ-СОН (Keep Alive) ---
async def keep_alive():
    """Пингует сам себя каждые 10 минут, чтобы Render не заснул"""
    if not BASE_URL:
        logger.warning("RENDER_EXTERNAL_URL не найден. Бот может уснуть.")
        return
    
    async with httpx.AsyncClient() as client:
        while True:
            await asyncio.sleep(600) # 10 минут
            try:
                resp = await client.get(BASE_URL)
                logger.info(f"Self-ping: {resp.status_code}")
            except Exception as e:
                logger.error(f"Ping error: {e}")

# --- LIFESPAN ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Запуск бота
    polling_task = asyncio.create_task(dp.start_polling(bot))
    # Запуск анти-сна
    ping_task = asyncio.create_task(keep_alive())
    logger.info("Бот и система анти-сна запущены!")
    
    yield
    
    polling_task.cancel()
    ping_task.cancel()

app = FastAPI(lifespan=lifespan)

@app.get("/")
async def root():
    return {"status": "online"}

if __name__ == "__main__":
    # Render передает порт в переменную PORT
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
