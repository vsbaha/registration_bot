"""
Обработчики для сохранения файлов и отправки сообщений
"""
import logging
from pathlib import Path
from typing import Dict, Any

from aiogram import Bot
from aiogram.types import Message

from config.settings import GROUPS, DATA_PATH
from config.messages import (
    GENERAL_GROUP_MESSAGE, 
    CURATOR_GROUP_MESSAGE,
    REGISTRATION_SUCCESS,
    REGISTRATION_ERROR,
    WARNING_PHOTO_SAVE
)
from utils.file_manager import (
    create_user_folder, 
    save_user_info, 
    increment_counters
)
from utils.excel_manager import create_or_update_curator_excel, create_or_update_general_excel

logger = logging.getLogger(__name__)


async def save_photos(
    bot: Bot,
    user_data: Dict[str, Any],
    user_path: Path
) -> bool:
    """
    Скачивает и сохраняет фото
    """
    try:
        # Скачивание фото лицевой стороны паспорта
        passport_front_file = await bot.get_file(user_data.get('passport_front_file_id'))
        passport_front_path = user_path / "passport_front.jpg"
        await bot.download_file(passport_front_file.file_path, passport_front_path)
        logger.info(f"Фото паспорта (лицевая) сохранено: {passport_front_path}")
        
        # Скачивание фото обратной стороны паспорта
        passport_back_file = await bot.get_file(user_data.get('passport_back_file_id'))
        passport_back_path = user_path / "passport_back.jpg"
        await bot.download_file(passport_back_file.file_path, passport_back_path)
        logger.info(f"Фото паспорта (обратная) сохранено: {passport_back_path}")
        
        # Скачивание фото диплома
        diploma_file = await bot.get_file(user_data.get('diploma_file_id'))
        diploma_path = user_path / "diploma.jpg"
        await bot.download_file(diploma_file.file_path, diploma_path)
        logger.info(f"Фото диплома сохранено: {diploma_path}")
        
        return True
    except Exception as e:
        logger.error(f"Ошибка при сохранении фото: {e}")
        return False


async def send_to_groups(
    bot: Bot,
    user_data: Dict[str, Any],
    total_number: int,
    curator_number: int
) -> bool:
    """
    Отправляет сообщения в группы с фото альбомом
    """
    from aiogram.types import InputMediaPhoto
    
    try:
        curator = user_data.get('curator')
        
        # Сообщение в общую группу
        general_msg = GENERAL_GROUP_MESSAGE.format(
            total_number=total_number,
            curator_number=curator_number,
            fio=user_data.get('fio'),
            pharmacy_name=user_data.get('pharmacy_name', ''),
            pharmacy_number=user_data.get('pharmacy_number', ''),
            position=user_data.get('position', ''),
            inn=user_data.get('inn'),
            phone=user_data.get('phone'),
            curator=curator
        )
        
        await bot.send_message(
            GROUPS['general'],
            general_msg,
            parse_mode="HTML"
        )
        logger.info(f"Сообщение отправлено в общую группу")
        
        # Собираем фото для альбома
        media_group = []
        
        try:
            passport_front = user_data.get('passport_front_file_id')
            if passport_front:
                media_group.append(
                    InputMediaPhoto(
                        media=passport_front,
                        caption="📸 <b>Лицевая сторона паспорта</b>",
                        parse_mode="HTML"
                    )
                )
        except Exception as e:
            logger.error(f"Ошибка при подготовке фото паспорта (лицевая): {e}")
        
        try:
            passport_back = user_data.get('passport_back_file_id')
            if passport_back:
                media_group.append(
                    InputMediaPhoto(
                        media=passport_back,
                        caption="📸 <b>Обратная сторона паспорта</b>",
                        parse_mode="HTML"
                    )
                )
        except Exception as e:
            logger.error(f"Ошибка при подготовке фото паспорта (обратная): {e}")
        
        try:
            diploma = user_data.get('diploma_file_id')
            if diploma:
                media_group.append(
                    InputMediaPhoto(
                        media=diploma,
                        caption="🎓 <b>Диплом</b>",
                        parse_mode="HTML"
                    )
                )
        except Exception as e:
            logger.error(f"Ошибка при подготовке фото диплома: {e}")
        
        # Отправляем альбом в общую группу
        if media_group:
            try:
                await bot.send_media_group(GROUPS['general'], media=media_group)
                logger.info("Альбом фото отправлен в общую группу")
            except Exception as e:
                logger.error(f"Ошибка при отправке альбома в общую группу: {e}")
        
        # Сообщение в группу куратора
        curator_msg = CURATOR_GROUP_MESSAGE.format(
            curator_number=curator_number,
            fio=user_data.get('fio'),
            pharmacy_name=user_data.get('pharmacy_name', ''),
            pharmacy_number=user_data.get('pharmacy_number', ''),
            position=user_data.get('position', ''),
            inn=user_data.get('inn'),
            phone=user_data.get('phone')
        )
        
        curator_group_id = GROUPS.get(curator)
        if curator_group_id:
            await bot.send_message(
                curator_group_id,
                curator_msg,
                parse_mode="HTML"
            )
            logger.info(f"Сообщение отправлено в группу {curator}")
            
            # Отправляем альбом в группу куратора
            if media_group:
                try:
                    await bot.send_media_group(curator_group_id, media=media_group)
                    logger.info("Альбом фото отправлен в группу куратора")
                except Exception as e:
                    logger.error(f"Ошибка при отправке альбома в группу куратора: {e}")
        
        return True
    except Exception as e:
        logger.error(f"Ошибка при отправке сообщений в группы: {e}")
        return False


async def finalize_registration(
    bot: Bot,
    message: Message,
    user_data: Dict[str, Any]
) -> bool:
    """
    Завершает регистрацию:
    1. Создает папку пользователя
    2. Сохраняет фото
    3. Сохраняет инфо
    4. Обновляет Excel куратора
    5. Отправляет сообщения в группы
    """
    try:
        curator = user_data.get('curator')
        fio = user_data.get('fio')
        
        # Создание папки
        user_path = create_user_folder(curator, fio)
        logger.info(f"Создана папка пользователя: {user_path}")
        
        # Увеличение счетчиков
        total_number, curator_number = increment_counters(curator)
        logger.info(f"Счетчики обновлены: Общий={total_number}, Куратор={curator_number}")
        
        # Сохранение фото
        photos_saved = await save_photos(bot, user_data, user_path)
        if not photos_saved:
            await message.answer(WARNING_PHOTO_SAVE)
            return False
        
        # Сохранение информации
        save_user_info(user_path, user_data, total_number, curator_number)
        logger.info("Информация пользователя сохранена")
        
        # Обновление Excel
        excel_ok = create_or_update_curator_excel(
            curator=curator,
            fio=fio,
            inn=user_data.get('inn'),
            phone=user_data.get('phone'),
            curator_number=curator_number,
            total_number=total_number,
            user_folder_path=str(user_path),
            pharmacy_name=user_data.get('pharmacy_name', ''),
            pharmacy_number=user_data.get('pharmacy_number', ''),
            position=user_data.get('position', '')
        )
        if excel_ok:
            logger.info(f"Excel файл куратора {curator} обновлен")
        else:
            logger.warning(f"Ошибка при обновлении Excel для куратора {curator}")
        
        # Обновление общего Excel
        general_excel_ok = create_or_update_general_excel(
            fio=fio,
            inn=user_data.get('inn'),
            phone=user_data.get('phone'),
            curator=curator,
            total_number=total_number,
            curator_number=curator_number,
            pharmacy_name=user_data.get('pharmacy_name', ''),
            pharmacy_number=user_data.get('pharmacy_number', ''),
            position=user_data.get('position', '')
        )
        if general_excel_ok:
            logger.info("Общий Excel файл обновлен")
        else:
            logger.warning("Ошибка при обновлении общего Excel файла")
        
        # Отправка в группы
        groups_ok = await send_to_groups(bot, user_data, total_number, curator_number)
        
        await message.answer(
            REGISTRATION_SUCCESS.format(
                total_number=total_number,
                curator_number=curator_number
            ),
            parse_mode="HTML"
        )
        
        return True
    except Exception as e:
        logger.error(f"Ошибка при завершении регистрации: {e}")
        await message.answer(REGISTRATION_ERROR)
        return False
