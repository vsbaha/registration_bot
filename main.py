"""
Основной файл бота
"""
import logging
import asyncio
import shutil
import tempfile
from pathlib import Path
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config.settings import BOT_TOKEN, CURATORS, GROUPS, DATA_PATH, ADMIN_ID
from config.messages import *
from handlers.registration import finalize_registration
from utils.file_manager import ensure_directories_exist

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Состояния для FSM (Finite State Machine)
class RegistrationStates(StatesGroup):
    choosing_curator = State()
    entering_fio = State()
    entering_pharmacy_name = State()
    entering_pharmacy_number = State()
    choosing_position = State()
    entering_inn = State()
    getting_phone = State()
    uploading_passport_front = State()
    uploading_passport_back = State()
    uploading_diploma = State()
    reviewing_data = State()
    editing_choice = State()
    waiting_for_back_navigation = State()  # После фото можно нажать кнопку "Назад"


# Создание клавиатуры с кураторами
def get_curators_keyboard():
    """Создает инлайн-клавиатуру с выбором кураторов"""
    buttons = [
        [KeyboardButton(text=curator) for curator in CURATORS[i:i+2]]
        for i in range(0, len(CURATORS), 2)
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True, one_time_keyboard=True)


# Обработчик команды /start
@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    """Обработка команды /start с приветствием и выбором куратора"""
    user_id = message.from_user.id
    username = message.from_user.username or "Пользователь"
    
    logger.info(f"Пользователь {user_id} (@{username}) начал регистрацию")
    
    # Сохраняем ID пользователя
    await state.update_data(user_id=user_id, username=username)
    
    welcome_text = START_WELCOME.format(username=username)
    
    await message.answer(welcome_text, reply_markup=get_curators_keyboard())
    await state.set_state(RegistrationStates.choosing_curator)

@dp.message(Command("cancel"))
async def cmd_cancel(message: types.Message, state: FSMContext):
    """Обработка команды /cancel для отмены регистрации"""
    await state.clear()
    await message.answer("Регистрация отменена. Вы можете начать заново с команды /start.")

# Обработчик выбора куратора
@dp.message(RegistrationStates.choosing_curator)
async def process_curator_choice(message: types.Message, state: FSMContext):
    """Обработка выбора куратора"""
    curator = message.text.strip()
    
    if curator not in CURATORS:
        curators_str = ', '.join(CURATORS)
        await message.answer(
            CURATOR_INVALID.format(curators=curators_str)
        )
        return
    
    await state.update_data(curator=curator)
    logger.info(f"Пользователь выбрал куратора: {curator}")
    
    # Проверяем, редактируем ли мы данные
    data = await state.get_data()
    if data.get('passport_front_file_id'):  # Если уже были загружены фото
        await show_review_screen(message, state)
    else:
        confirmation_text = CURATOR_CONFIRMED.format(curator=curator)
        await message.answer(confirmation_text)
        await state.set_state(RegistrationStates.entering_fio)


# Обработчик ввода ФИО
@dp.message(RegistrationStates.entering_fio)
async def process_fio(message: types.Message, state: FSMContext):
    """Обработка ввода ФИО"""
    fio = message.text.strip()
    
    if not fio or len(fio) < 3:
        await message.answer(FIO_INVALID)
        return
    
    await state.update_data(fio=fio)
    logger.info(f"ФИО сохранено: {fio}")
    
    # Проверяем, редактируем ли мы данные
    data = await state.get_data()
    if data.get('passport_front_file_id'):  # Если уже были загружены фото
        await show_review_screen(message, state)
    else:
        pharmacy_request_text = FIO_CONFIRMED.format(fio=fio)
        
        await message.answer(pharmacy_request_text)
        await state.set_state(RegistrationStates.entering_pharmacy_name)


# Обработчик ввода названия аптеки
@dp.message(RegistrationStates.entering_pharmacy_name)
async def process_pharmacy_name(message: types.Message, state: FSMContext):
    """Обработка ввода названия аптеки"""
    pharmacy_name = message.text.strip()
    
    if not pharmacy_name or len(pharmacy_name) < 2:
        await message.answer(PHARMACY_NAME_INVALID)
        return
    
    await state.update_data(pharmacy_name=pharmacy_name)
    logger.info(f"Название аптеки сохранено: {pharmacy_name}")
    
    # Проверяем, редактируем ли мы данные
    data = await state.get_data()
    if data.get('passport_front_file_id'):  # Если уже были загружены фото
        await show_review_screen(message, state)
    else:
        pharmacy_number_request_text = PHARMACY_NAME_CONFIRMED.format(pharmacy_name=pharmacy_name)
        
        await message.answer(pharmacy_number_request_text)
        await state.set_state(RegistrationStates.entering_pharmacy_number)


# Обработчик ввода номера аптеки
@dp.message(RegistrationStates.entering_pharmacy_number)
async def process_pharmacy_number(message: types.Message, state: FSMContext):
    """Обработка ввода номера аптеки"""
    pharmacy_number = message.text.strip()
    
    if not pharmacy_number:
        await message.answer(PHARMACY_NUMBER_INVALID)
        return
    
    await state.update_data(pharmacy_number=pharmacy_number)
    logger.info(f"Номер аптеки сохранен: {pharmacy_number}")
    
    # Проверяем, редактируем ли мы данные
    data = await state.get_data()
    if data.get('passport_front_file_id'):  # Если уже были загружены фото
        await show_review_screen(message, state)
    else:
        position_request_text = PHARMACY_NUMBER_CONFIRMED.format(pharmacy_number=pharmacy_number)
        
        # Создание клавиатуры с выбором должности
        position_keyboard = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text=BUTTON_POSITION_MANAGER)],
                [KeyboardButton(text=BUTTON_POSITION_PHARMACIST)],
                [KeyboardButton(text=BUTTON_POSITION_MANUAL)]
            ],
            resize_keyboard=True,
            one_time_keyboard=True
        )
        
        await message.answer(position_request_text, reply_markup=position_keyboard)
        await state.set_state(RegistrationStates.choosing_position)


# Обработчик выбора должности
@dp.message(RegistrationStates.choosing_position)
async def process_position(message: types.Message, state: FSMContext):
    """Обработка выбора должности"""
    position_input = message.text.strip()
    
    # Проверяем, нажал ли кнопку ручного ввода
    if position_input == BUTTON_POSITION_MANUAL:
        await message.answer(
            "✍️ Введите вашу должность:",
            reply_markup=types.ReplyKeyboardRemove()
        )
        await state.update_data(manual_position_input=True)
        return
    
    # Убираем эмодзи из должности перед сохранением
    if position_input == BUTTON_POSITION_MANAGER:
        position = "Заведующий"
    elif position_input == BUTTON_POSITION_PHARMACIST:
        position = "Фармацевт"
    else:
        # Ручной ввод
        data = await state.get_data()
        if data.get('manual_position_input'):
            position = position_input
            if len(position) < 2:
                await message.answer(POSITION_INVALID)
                return
            # Удаляем флаг ручного ввода
            await state.update_data(manual_position_input=False)
        else:
            await message.answer(POSITION_INVALID)
            return
    
    await state.update_data(position=position)
    logger.info(f"Должность сохранена: {position}")
    
    # Проверяем, редактируем ли мы данные
    data = await state.get_data()
    if data.get('passport_front_file_id'):  # Если уже были загружены фото
        await show_review_screen(message, state)
    else:
        # Используем разные сообщения для кнопки и ручного ввода
        if data.get('manual_position_input') is False or position_input in [BUTTON_POSITION_MANAGER, BUTTON_POSITION_PHARMACIST]:
            inn_request_text = POSITION_MANUAL_CONFIRMED.format(position=position) if data.get('manual_position_input') is False else POSITION_CONFIRMED.format(position=position)
        else:
            inn_request_text = POSITION_CONFIRMED.format(position=position)
        
        await message.answer(inn_request_text, reply_markup=types.ReplyKeyboardRemove())
        await state.set_state(RegistrationStates.entering_inn)


# Обработчик ввода ИНН
@dp.message(RegistrationStates.entering_inn)
async def process_inn(message: types.Message, state: FSMContext):
    """Обработка ввода ИНН"""
    inn = message.text.strip()
    
    # Валидация ИНН
    if not inn.isdigit() or len(inn) != 14:
        await message.answer(INN_INVALID)
        return
    
    await state.update_data(inn=inn)
    logger.info(f"ИНН сохранен: {inn}")
    
    # Проверяем, редактируем ли мы данные
    data = await state.get_data()
    if data.get('passport_front_file_id'):  # Если уже были загружены фото
        await show_review_screen(message, state)
    else:
        phone_request_text = INN_CONFIRMED.format(inn=inn)
        
        # Клавиатура с кнопкой отправки контакта
        phone_keyboard = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text=BUTTON_SEND_CONTACT, request_contact=True)],
                [KeyboardButton(text=BUTTON_ENTER_MANUAL)]
            ],
            resize_keyboard=True,
            one_time_keyboard=True
        )
        
        await message.answer(phone_request_text, reply_markup=phone_keyboard)
        await state.set_state(RegistrationStates.getting_phone)


# Обработчик получения телефона через contact
@dp.message(RegistrationStates.getting_phone, lambda msg: msg.contact is not None)
async def process_phone_contact(message: types.Message, state: FSMContext):
    """Обработка отправленного контакта"""
    phone = message.contact.phone_number
    
    # Форматирование номера телефона
    if not phone.startswith("+"):
        phone = "+" + phone
    
    await state.update_data(phone=phone)
    logger.info(f"Телефон получен через контакт: {phone}")
    
    # Проверяем, редактируем ли мы данные
    data = await state.get_data()
    if data.get('passport_front_file_id'):  # Если уже были загружены фото
        await show_review_screen(message, state)
    else:
        await ask_passport_photos(message, state)


# Обработчик ручного ввода телефона
@dp.message(RegistrationStates.getting_phone)
async def process_phone_manual(message: types.Message, state: FSMContext):
    """Обработка ручного ввода телефона"""
    phone = message.text.strip()
    
    if message.text == BUTTON_ENTER_MANUAL:
        await message.answer("Введи номер телефона в формате +996XXXXXXXXX или 0XXXXXXXXXX (Кыргызстан):")
        return
    
    # Простая валидация телефона для Кыргызстана
    # Допустимые форматы: +996XXXXXXXXX или 0XXXXXXXXXX
    phone_digits = phone.replace("+", "").replace("-", "").replace(" ", "")
    
    is_valid = False
    if phone.startswith("+996") and len(phone_digits) == 12:
        is_valid = True
        phone = phone  # Уже в правильном формате
    elif phone.startswith("0") and len(phone_digits) == 10:
        is_valid = True
        phone = "+996" + phone[1:]  # Конвертируем 0XXXXXXXXX в +996XXXXXXXXX
    
    if not is_valid:
        await message.answer(
            "❌ Пожалуйста, введи номер в формате:\n"
            "• +996XXXXXXXXX (например: +996701234567)\n"
            "• 0XXXXXXXXXX (например: 0701234567)"
        )
        return
    
    await state.update_data(phone=phone)
    logger.info(f"Телефон получен вручную: {phone}")
    
    # Проверяем, редактируем ли мы данные
    data = await state.get_data()
    if data.get('passport_front_file_id'):  # Если уже были загружены фото
        await show_review_screen(message, state)
    else:
        await ask_passport_photos(message, state)


# Функция для запроса фото паспорта
async def ask_passport_photos(message: types.Message, state: FSMContext):
    """Запрашивает фото паспорта"""
    passport_text = PASSPORT_FRONT_REQUEST
    
    back_keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=BUTTON_BACK)]],
        resize_keyboard=True
    )
    
    await message.answer(passport_text, reply_markup=back_keyboard)
    await state.set_state(RegistrationStates.uploading_passport_front)


# Обработчик загрузки фото лицевой стороны паспорта
@dp.message(RegistrationStates.uploading_passport_front, lambda msg: msg.photo is not None)
async def process_passport_front(message: types.Message, state: FSMContext):
    """Обработка загрузки фото лицевой стороны паспорта"""
    # Проверяем что отправлено одно фото
    if message.caption or message.media_group_id:
        await message.answer(PASSPORT_FRONT_INVALID)
        return
    
    photo = message.photo[-1]  # Берем самое качественное фото
    
    await state.update_data(passport_front_file_id=photo.file_id)
    logger.info(f"Фото лицевой стороны паспорта получено: {photo.file_id}")
    
    data = await state.get_data()
    is_editing = data.get('editing_mode', False)
    
    if is_editing:
        # Если редактируем - возвращаемся к просмотру данных
        await state.update_data(editing_mode=False)
        await show_review_screen(message, state)
    else:
        # Если первичная загрузка - переходим к следующему фото
        back_keyboard = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text=BUTTON_BACK)]],
            resize_keyboard=True
        )
        
        await message.answer(
            PASSPORT_FRONT_CONFIRMED,
            reply_markup=back_keyboard
        )
        await state.set_state(RegistrationStates.uploading_passport_back)


# Обработчик кнопки Назад при загрузке паспорта (лицевая сторона)
@dp.message(RegistrationStates.uploading_passport_front, lambda msg: msg.text == BUTTON_BACK or msg.text == "⬅️ Назад")
async def back_from_passport_front(message: types.Message, state: FSMContext):
    """Возврат из загрузки лицевой стороны паспорта"""
    phone_keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BUTTON_SEND_CONTACT, request_contact=True)],
            [KeyboardButton(text=BUTTON_ENTER_MANUAL)]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    await message.answer(
        BACK_FROM_PASSPORT_FRONT,
        reply_markup=phone_keyboard
    )
    await state.set_state(RegistrationStates.getting_phone)


@dp.message(RegistrationStates.uploading_passport_front)
async def invalid_passport_front(message: types.Message):
    """Ошибка: отправлено не фото"""
    await message.answer(PASSPORT_FRONT_INVALID)


# Обработчик загрузки фото обратной стороны паспорта
@dp.message(RegistrationStates.uploading_passport_back, lambda msg: msg.photo is not None)
async def process_passport_back(message: types.Message, state: FSMContext):
    """Обработка загрузки фото обратной стороны паспорта"""
    # Проверяем что отправлено одно фото
    if message.caption or message.media_group_id:
        await message.answer(PASSPORT_BACK_INVALID)
        return
    
    photo = message.photo[-1]
    
    await state.update_data(passport_back_file_id=photo.file_id)
    logger.info(f"Фото обратной стороны паспорта получено: {photo.file_id}")
    
    data = await state.get_data()
    is_editing = data.get('editing_mode', False)
    
    if is_editing:
        # Если редактируем - возвращаемся к просмотру данных
        await state.update_data(editing_mode=False)
        await show_review_screen(message, state)
    else:
        # Если первичная загрузка - переходим к следующему фото
        back_keyboard = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text=BUTTON_BACK)]],
            resize_keyboard=True
        )
        
        await message.answer(
            PASSPORT_BACK_CONFIRMED,
            reply_markup=back_keyboard
        )
        await state.set_state(RegistrationStates.uploading_diploma)


# Обработчик кнопки Назад при загрузке паспорта (обратная сторона)
@dp.message(RegistrationStates.uploading_passport_back, lambda msg: msg.text == BUTTON_BACK or msg.text == "⬅️ Назад")
async def back_from_passport_back(message: types.Message, state: FSMContext):
    """Возврат из загрузки обратной стороны паспорта"""
    back_keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=BUTTON_BACK)]],
        resize_keyboard=True
    )
    
    await message.answer(
        BACK_FROM_PASSPORT_BACK,
        reply_markup=back_keyboard
    )
    await state.set_state(RegistrationStates.uploading_passport_front)


@dp.message(RegistrationStates.uploading_passport_back)
async def invalid_passport_back(message: types.Message):
    """Ошибка: отправлено не фото"""
    await message.answer(PASSPORT_BACK_INVALID)


# Обработчик загрузки фото диплома
@dp.message(RegistrationStates.uploading_diploma, lambda msg: msg.photo is not None)
async def process_diploma(message: types.Message, state: FSMContext):
    """Обработка загрузки фото диплома"""
    # Проверяем что отправлено одно фото
    if message.caption or message.media_group_id:
        await message.answer(DIPLOMA_INVALID)
        return
    
    photo = message.photo[-1]
    
    await state.update_data(diploma_file_id=photo.file_id)
    logger.info(f"Фото диплома получено: {photo.file_id}")
    
    data = await state.get_data()
    is_editing = data.get('editing_mode', False)
    
    if is_editing:
        # Если редактируем - возвращаемся к просмотру данных
        await state.update_data(editing_mode=False)
        await show_review_screen(message, state)
    else:
        # Если первичная загрузка - переходим к просмотру данных
        await show_review_screen(message, state)


# Обработчик кнопки Назад при загрузке диплома
@dp.message(RegistrationStates.uploading_diploma, lambda msg: msg.text == BUTTON_BACK or msg.text == "⬅️ Назад")
async def back_from_diploma(message: types.Message, state: FSMContext):
    """Возврат из загрузки диплома"""
    back_keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=BUTTON_BACK)]],
        resize_keyboard=True
    )
    
    await message.answer(
        BACK_FROM_DIPLOMA,
        reply_markup=back_keyboard
    )
    await state.set_state(RegistrationStates.uploading_passport_back)


@dp.message(RegistrationStates.uploading_diploma)
async def invalid_diploma(message: types.Message):
    """Ошибка: отправлено не фото"""
    await message.answer(DIPLOMA_INVALID)


# Функция для отображения экрана просмотра данных
async def show_review_screen(message: types.Message, state: FSMContext):
    """Показывает экран просмотра данных перед подтверждением"""
    from aiogram.types import InputMediaPhoto
    
    data = await state.get_data()
    
    review_text = (
        REVIEW_HEADER +
        REVIEW_FIO.format(fio=data.get('fio', 'N/A')) +
        REVIEW_PHARMACY_NAME.format(pharmacy_name=data.get('pharmacy_name', 'N/A')) +
        REVIEW_PHARMACY_NUMBER.format(pharmacy_number=data.get('pharmacy_number', 'N/A')) +
        REVIEW_POSITION.format(position=data.get('position', 'N/A')) +
        REVIEW_INN.format(inn=data.get('inn', 'N/A')) +
        REVIEW_PHONE.format(phone=data.get('phone', 'N/A')) +
        REVIEW_CURATOR.format(curator=data.get('curator', 'N/A')) +
        REVIEW_PASSPORT_FRONT +
        REVIEW_PASSPORT_BACK +
        REVIEW_DIPLOMA +
        REVIEW_QUESTION
    )
    
    review_keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BUTTON_EDIT), KeyboardButton(text=BUTTON_CONFIRM)]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    
    # Отправляем карточку с данными
    await message.answer(review_text, reply_markup=review_keyboard, parse_mode="HTML")
    
    # Собираем фото для альбома
    media_group = []
    
    try:
        passport_front_file_id = data.get('passport_front_file_id')
        if passport_front_file_id:
            media_group.append(
                InputMediaPhoto(
                    media=passport_front_file_id,
                    caption="📸 <b>Лицевая сторона паспорта</b>",
                    parse_mode="HTML"
                )
            )
    except Exception as e:
        logger.error(f"Ошибка при подготовке фото паспорта (лицевая): {e}")
    
    try:
        passport_back_file_id = data.get('passport_back_file_id')
        if passport_back_file_id:
            media_group.append(
                InputMediaPhoto(
                    media=passport_back_file_id,
                    caption="📸 <b>Обратная сторона паспорта</b>",
                    parse_mode="HTML"
                )
            )
    except Exception as e:
        logger.error(f"Ошибка при подготовке фото паспорта (обратная): {e}")
    
    try:
        diploma_file_id = data.get('diploma_file_id')
        if diploma_file_id:
            media_group.append(
                InputMediaPhoto(
                    media=diploma_file_id,
                    caption="🎓 <b>Диплом</b>",
                    parse_mode="HTML"
                )
            )
    except Exception as e:
        logger.error(f"Ошибка при подготовке фото диплома: {e}")
    
    # Отправляем альбом фотографий
    if media_group:
        try:
            await message.answer_media_group(media=media_group)
        except Exception as e:
            logger.error(f"Ошибка при отправке альбома фото: {e}")
    
    await state.set_state(RegistrationStates.reviewing_data)


# Обработчик кнопок на экране просмотра
@dp.message(RegistrationStates.reviewing_data)
async def process_review_action(message: types.Message, state: FSMContext):
    """Обработка действий на экране просмотра"""
    action = message.text.strip()
    
    if action == BUTTON_CONFIRM:
        data = await state.get_data()
        success = await finalize_registration(bot, message, data)
        if success:
            await state.clear()
        else:
            await message.answer(REGISTRATION_ERROR)
    elif action == BUTTON_EDIT:
        edit_keyboard = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text=BUTTON_FIO), KeyboardButton(text=BUTTON_INN)],
                [KeyboardButton(text=BUTTON_PHARMACY_NAME), KeyboardButton(text=BUTTON_PHARMACY_NUMBER)],
                [KeyboardButton(text=BUTTON_POSITION), KeyboardButton(text=BUTTON_PHONE)],
                [KeyboardButton(text=BUTTON_CURATOR)],
                [KeyboardButton(text="📸 Паспорт (лицевая)"), KeyboardButton(text="📸 Паспорт (обратная)")],
                [KeyboardButton(text="🎓 Диплом")],
                [KeyboardButton(text=BUTTON_BACK)]
            ],
            resize_keyboard=True,
            one_time_keyboard=True
        )
        
        await message.answer(
            EDIT_CHOICE_PROMPT,
            reply_markup=edit_keyboard
        )
        await state.set_state(RegistrationStates.editing_choice)
    else:
        await message.answer(REGISTRATION_INVALID_ACTION)


# Обработчик выбора при редактировании
@dp.message(RegistrationStates.editing_choice)
async def process_edit_choice(message: types.Message, state: FSMContext):
    """Обработка выбора поля для редактирования"""
    choice = message.text.strip()
    
    if choice == BUTTON_FIO:
        await message.answer(FIO_REQUEST)
        await state.set_state(RegistrationStates.entering_fio)
    elif choice == BUTTON_PHARMACY_NAME:
        await message.answer(PHARMACY_NAME_REQUEST)
        await state.set_state(RegistrationStates.entering_pharmacy_name)
    elif choice == BUTTON_PHARMACY_NUMBER:
        await message.answer(PHARMACY_NUMBER_REQUEST)
        await state.set_state(RegistrationStates.entering_pharmacy_number)
    elif choice == BUTTON_POSITION:
        position_keyboard = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text=BUTTON_POSITION_MANAGER)],
                [KeyboardButton(text=BUTTON_POSITION_PHARMACIST)],
                [KeyboardButton(text=BUTTON_POSITION_MANUAL)]
            ],
            resize_keyboard=True,
            one_time_keyboard=True
        )
        await message.answer(POSITION_REQUEST, reply_markup=position_keyboard)
        await state.set_state(RegistrationStates.choosing_position)
    elif choice == BUTTON_INN:
        await message.answer(INN_REQUEST)
        await state.set_state(RegistrationStates.entering_inn)
    elif choice == BUTTON_PHONE:
        phone_keyboard = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text=BUTTON_SEND_CONTACT, request_contact=True)],
                [KeyboardButton(text=BUTTON_ENTER_MANUAL)]
            ],
            resize_keyboard=True,
            one_time_keyboard=True
        )
        await message.answer(
            PHONE_REQUEST,
            reply_markup=phone_keyboard
        )
        await state.set_state(RegistrationStates.getting_phone)
    elif choice == BUTTON_CURATOR:
        await message.answer(
            "Выбери нового куратора:",
            reply_markup=get_curators_keyboard()
        )
        await state.set_state(RegistrationStates.choosing_curator)
    elif choice == "📸 Паспорт (лицевая)":
        await message.answer(PASSPORT_FRONT_REQUEST)
        await state.update_data(editing_mode=True)
        await state.set_state(RegistrationStates.uploading_passport_front)
    elif choice == "📸 Паспорт (обратная)":
        await message.answer(PASSPORT_BACK_REQUEST)
        await state.update_data(editing_mode=True)
        await state.set_state(RegistrationStates.uploading_passport_back)
    elif choice == "🎓 Диплом":
        await message.answer(DIPLOMA_REQUEST)
        await state.update_data(editing_mode=True)
        await state.set_state(RegistrationStates.uploading_diploma)
    elif BUTTON_BACK in choice or "Назад" in choice:
        await show_review_screen(message, state)
    else:
        await message.answer(EDIT_FIELD_CHOICES)


# Обработчик команды /getfile
@dp.message(Command("getfile"))
async def cmd_getfile(message: types.Message):
    """Создает и отправляет ZIP архив всей папки /data администратору"""
    # Проверка прав (заменить на реальный ID администратора)
    # ADMIN_ID переменная должна быть установлена
    
    try:
        user_id = message.from_user.id
        logger.info(f"Команда /getfile выполнена пользователем {user_id}")
        
        # Создаем временную папку для архива
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            zip_path = temp_path / "data"
            
            # Копируем папку data в архив
            if Path(DATA_PATH).exists():
                shutil.copytree(DATA_PATH, zip_path)
                logger.info(f"Папка {DATA_PATH} скопирована в архив")
            
            # Создаем ZIP архив
            archive_path = temp_path / "registrations"
            shutil.make_archive(
                str(archive_path),
                'zip',
                root_dir=str(temp_path),
                base_dir='data'
            )
            
            zip_file_path = Path(str(archive_path) + '.zip')
            
            if zip_file_path.exists():
                # Отправляем файл
                file = FSInputFile(zip_file_path, filename="registrations.zip")
                await message.answer_document(
                    file,
                    caption=GETFILE_SUCCESS
                )
                logger.info(f"ZIP архив отправлен: {zip_file_path}")
            else:
                await message.answer(GETFILE_ERROR)
                logger.error("ZIP архив не создан")
    except Exception as e:
        logger.error(f"Ошибка при выполнении /getfile: {e}")
        await message.answer(f"❌ Ошибка: {str(e)}")


async def main():
    """Запуск бота"""
    try:
        ensure_directories_exist()
        logger.info("🤖 Бот запущен...")
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
