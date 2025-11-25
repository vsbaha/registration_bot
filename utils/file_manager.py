"""
Утилиты для работы с файлами и данными
"""
import os
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

from config.settings import DATA_PATH, CURATORS, COUNTERS_FILE


def ensure_directories_exist():
    """Создает необходимые директории"""
    Path(DATA_PATH).mkdir(exist_ok=True)
    
    for curator in CURATORS:
        curator_path = Path(DATA_PATH) / curator
        curator_path.mkdir(exist_ok=True)


def load_counters() -> Dict[str, int]:
    """Загружает счетчики участников"""
    ensure_directories_exist()
    
    if os.path.exists(COUNTERS_FILE):
        try:
            with open(COUNTERS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    
    # Инициализируем счетчики
    counters = {
        "total": 0,
    }
    for curator in CURATORS:
        counters[curator] = 0
    
    save_counters(counters)
    return counters


def save_counters(counters: Dict[str, int]):
    """Сохраняет счетчики участников"""
    os.makedirs(os.path.dirname(COUNTERS_FILE), exist_ok=True)
    
    with open(COUNTERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(counters, f, ensure_ascii=False, indent=2)


def increment_counters(curator: str) -> tuple[int, int]:
    """
    Увеличивает счетчики
    Возвращает: (общий номер, номер куратора)
    """
    counters = load_counters()
    
    counters["total"] += 1
    counters[curator] += 1
    
    save_counters(counters)
    
    return counters["total"], counters[curator]


def create_user_folder(curator: str, fio: str) -> Path:
    """Создает папку для пользователя"""
    curator_path = Path(DATA_PATH) / curator
    
    # Замена недопустимых символов в имени папки
    safe_fio = "".join(c if c.isalnum() or c in "-_ кириллица" else "_" 
                       for c in fio).replace(" ", "_")
    
    user_path = curator_path / safe_fio
    user_path.mkdir(parents=True, exist_ok=True)
    
    return user_path


def save_user_info(
    user_path: Path, 
    data: Dict[str, Any],
    total_number: int,
    curator_number: int
):
    """Сохраняет информацию пользователя в info.txt"""
    info_file = user_path / "info.txt"
    
    content = f"""ИНФОРМАЦИЯ О УЧАСТНИКЕ
======================
ФИО: {data.get('fio', 'N/A')}
ИНН: {data.get('inn', 'N/A')}
Телефон: {data.get('phone', 'N/A')}
Куратор: {data.get('curator', 'N/A')}
Общий номер: {total_number}
Номер у куратора: {curator_number}
Дата регистрации: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}
"""
    
    with open(info_file, 'w', encoding='utf-8') as f:
        f.write(content)


def get_user_number(curator: str) -> int:
    """Получает текущий номер пользователя для куратора"""
    counters = load_counters()
    return counters.get(curator, 0)
