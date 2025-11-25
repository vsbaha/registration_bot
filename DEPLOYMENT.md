# DEPLOYMENT.md - Развертывание MAMA Bot на сервере

## Оглавление
1. [Подготовка на локальной машине](#подготовка-на-локальной-машине)
2. [Выбор сервера](#выбор-сервера)
3. [Настройка сервера](#настройка-сервера)
4. [Развертывание через Git](#развертывание-через-git)
5. [Альтернативные способы развертывания](#альтернативные-способы-развертывания)
6. [Монитиринг и обслуживание](#монитиринг-и-обслуживание)

---

## Подготовка на локальной машине

### 1. Инициализация Git репозитория

```bash
cd mama_reg_bots

# Инициализировать git
git init

# Добавить все файлы
git add .

# Первый коммит
git commit -m "Initial commit: MAMA Bot setup"
```

### 2. Создание учетной записи на GitHub/GitLab

1. Создайте репозиторий на [GitHub](https://github.com) или [GitLab](https://gitlab.com)
2. Скопируйте URL репозитория (HTTPS или SSH)

### 3. Загрузить в облако

```bash
# Добавить удаленный репозиторий
git remote add origin https://github.com/username/mama_reg_bots.git

# Загрузить
git branch -M main
git push -u origin main
```

### 4. Проверить файлы перед публикацией

Убедитесь что `.env` находится в `.gitignore`:

```bash
cat .gitignore | grep ".env"
# Должно быть:
# .env
```

⚠️ **ВАЖНО:** Никогда не публикуйте .env файл в git!

---

## Выбор сервера

### Рекомендуемые варианты:

1. **VPS (Virtual Private Server)**
   - Hetzner ($3-5/месяц)
   - DigitalOcean ($5/месяц)
   - Linode ($5/месяц)
   - Vultr ($2.50/месяц)

2. **Облачные сервисы**
   - AWS EC2 (free tier 12 месяцев)
   - Google Cloud (free tier)
   - Azure (free tier)

3. **Выделенный сервер**
   - Для большой нагрузки

### Минимальные требования:
- CPU: 1 ядро
- RAM: 512 MB - 1 GB
- Storage: 10-20 GB
- OS: Ubuntu 20.04 LTS или Debian 11+

---

## Настройка сервера

### Шаг 1: SSH подключение

```bash
# Из терминала на локальной машине
ssh root@your_server_ip

# Или если у вас есть SSH ключ
ssh -i ~/.ssh/id_rsa root@your_server_ip
```

### Шаг 2: Обновить систему

```bash
sudo apt update
sudo apt upgrade -y
sudo apt install -y build-essential
```

### Шаг 3: Установить Python 3.9 и Git

```bash
sudo apt install -y python3.9 python3.9-venv python3-pip git curl wget
```

### Шаг 4: Создать рабочую папку

```bash
sudo mkdir -p /opt/mama_reg_bots
cd /opt/mama_reg_bots

# Если нужны права
sudo chown -R $USER:$USER /opt/mama_reg_bots
```

### Шаг 5: Клонировать репозиторий

```bash
git clone https://github.com/username/mama_reg_bots.git .

# Если используете SSH ключи
git clone git@github.com:username/mama_reg_bots.git .
```

### Шаг 6: Подготовить окружение

```bash
# Создать виртуальное окружение
python3.9 -m venv venv

# Активировать
source venv/bin/activate

# Установить зависимости
pip install -r requirements.txt

# Создать файл .env
cp .env.example .env

# Отредактировать .env (добавить токен и ID групп)
nano .env
```

### Шаг 7: Создать структуру папок данных

```bash
mkdir -p data/Айгерим data/Бермет data/Майрам data/Жайна data/Чолпон
```

---

## Развертывание через Git

### Способ 1: Systemd (РЕКОМЕНДУЕТСЯ)

#### Создать service файл

```bash
sudo nano /etc/systemd/system/mama-bot.service
```

Содержимое:

```ini
[Unit]
Description=MAMA Registration Bot
After=network.target

[Service]
Type=simple
User=<your_username>
WorkingDirectory=/opt/mama_reg_bots
Environment="PATH=/opt/mama_reg_bots/venv/bin"
ExecStart=/opt/mama_reg_bots/venv/bin/python /opt/mama_reg_bots/main.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

#### Активировать сервис

```bash
sudo systemctl daemon-reload
sudo systemctl enable mama-bot
sudo systemctl start mama-bot

# Проверить статус
sudo systemctl status mama-bot

# Просмотреть логи
sudo journalctl -u mama-bot -f
```

### Способ 2: PM2 (для Node.js пользователей)

```bash
# Установить Node.js
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs

# Установить PM2
sudo npm install -g pm2

# Запустить бота через PM2
pm2 start "venv/bin/python main.py" --name "mama-bot" --interpreter bash

# Сохранить конфиг
pm2 save
pm2 startup
pm2 monit
```

### Способ 3: Screen (простейший способ)

```bash
# Установить screen
sudo apt install -y screen

# Создать новую сессию
screen -S mama-bot

# В новой сессии
cd /opt/mama_reg_bots
source venv/bin/activate
python main.py

# Отключиться (Ctrl+A, потом D)
# Ctrl+A, D

# Вернуться к сессии
screen -r mama-bot
```

### Способ 4: Nohup (самый простой)

```bash
cd /opt/mama_reg_bots
source venv/bin/activate
nohup python main.py > bot.log 2>&1 &

# Просмотреть логи
tail -f bot.log
```

---

## Альтернативные способы развертывания

### Docker (контейнеризация)

1. **Создать Dockerfile:**

```dockerfile
FROM python:3.9-slim

WORKDIR /app

# Установить зависимости
RUN apt-get update && apt-get install -y git

# Копировать файлы
COPY . .

# Установить Python пакеты
RUN pip install --no-cache-dir -r requirements.txt

# Запустить бота
CMD ["python", "main.py"]
```

2. **Создать docker-compose.yml:**

```yaml
version: '3.8'

services:
  mama-bot:
    build: .
    container_name: mama-bot
    restart: always
    environment:
      - BOT_TOKEN=${BOT_TOKEN}
      - ADMIN_ID=${ADMIN_ID}
    volumes:
      - ./data:/app/data
      - ./config:/app/config
    env_file: .env
```

3. **Запустить:**

```bash
docker-compose up -d
```

### Heroku (облачный хостинг)

1. Создать Procfile:
```
worker: python main.py
```

2. Создать runtime.txt:
```
python-3.9.0
```

3. Развернуть через Heroku CLI

---

## Монитиринг и обслуживание

### Проверка статуса

```bash
# Systemd
sudo systemctl status mama-bot

# PM2
pm2 status

# Screen
screen -ls
```

### Просмотр логов

```bash
# Systemd
sudo journalctl -u mama-bot -f           # Real-time
sudo journalctl -u mama-bot -n 50        # Последние 50 строк
sudo journalctl -u mama-bot --since today  # За сегодня

# PM2
pm2 logs mama-bot

# Nohup/Screen
tail -f bot.log
```

### Обновление кода

```bash
cd /opt/mama_reg_bots

# Получить обновления
git pull origin main

# Перезагрузить бота
sudo systemctl restart mama-bot

# Проверить логи
sudo journalctl -u mama-bot -f
```

### Резервные копии

```bash
# Создать архив
tar -czf mama_backup_$(date +%Y%m%d_%H%M%S).tar.gz data/ config/

# Загрузить на другой сервер/облако
scp mama_backup_*.tar.gz user@backup_server:/backups/

# Восстановить
tar -xzf mama_backup_*.tar.gz
```

### Создать скрипт автоматических резервных копий

```bash
# /opt/mama_reg_bots/backup.sh
#!/bin/bash

BACKUP_DIR="/opt/mama_reg_bots/backups"
mkdir -p $BACKUP_DIR

DATE=$(date +%Y%m%d_%H%M%S)
ARCHIVE="$BACKUP_DIR/mama_backup_$DATE.tar.gz"

tar -czf $ARCHIVE /opt/mama_reg_bots/data /opt/mama_reg_bots/config/counters.json

# Удалить старые резервные копии (старше 30 дней)
find $BACKUP_DIR -name "*.tar.gz" -mtime +30 -delete

echo "Резервная копия создана: $ARCHIVE"
```

Добавить в crontab:
```bash
crontab -e
# Добавить строку для ежедневного запуска в 3:00 AM
0 3 * * * /opt/mama_reg_bots/backup.sh >> /var/log/mama_backup.log 2>&1
```

### Мониторинг уровня диска

```bash
# Проверить свободное место
df -h

# Размер папки data
du -sh /opt/mama_reg_bots/data/

# Если мало места, удалить старые резервные копии
rm /opt/mama_reg_bots/backups/mama_backup_*.tar.gz --oldest
```

---

## Решение проблем

### Бот не запускается

```bash
# Проверить логи
sudo journalctl -u mama-bot -n 50

# Попробовать запустить вручную
cd /opt/mama_reg_bots
source venv/bin/activate
python main.py
```

### Ошибка "Permission denied"

```bash
# Проверить права
ls -la /opt/mama_reg_bots/

# Изменить права
sudo chown -R $USER:$USER /opt/mama_reg_bots/
chmod +x /opt/mama_reg_bots/main.py
```

### Ошибка "Token invalid"

```bash
# Проверить .env
cat .env | grep BOT_TOKEN

# Убедиться что токен скопирован правильно
# Получить новый токен у @BotFather
```

### Фото не загружаются

```bash
# Проверить права на папку data
ls -la /opt/mama_reg_bots/data/

# Проверить свободное место
df -h

# Проверить логи
sudo journalctl -u mama-bot -f | grep -i "photo\|ошибка"
```

---

## Финальный чеклист

- ✅ Git репозиторий создан и загружен
- ✅ .env файл на сервере настроен (не в git!)
- ✅ .gitignore правильно исключает данные
- ✅ Сервис создан и запущен
- ✅ Логи видны и нет ошибок
- ✅ Бот отвечает на команды
- ✅ Фото загружаются в группы
- ✅ Данные сохраняются локально
- ✅ Резервные копии настроены
- ✅ Мониторинг настроен

---

## Поддержка

При возникновении проблем:
1. Проверьте логи: `sudo journalctl -u mama-bot -f`
2. Убедитесь что .env правильный
3. Проверьте интернет соединение
4. Перезагрузите сервис: `sudo systemctl restart mama-bot`

**Успехов с развертыванием!** 🚀
