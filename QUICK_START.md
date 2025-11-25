# QUICK_START.md - Быстрый старт развертывания

## За 5 минут на Linux сервере

### 1. SSH и базовая подготовка (1 мин)
```bash
ssh root@your_server_ip

apt update && apt upgrade -y
apt install -y python3.9 python3.9-venv python3-pip git
mkdir -p /opt/mama_reg_bots && cd /opt/mama_reg_bots
```

### 2. Клонировать и настроить (1 мин)
```bash
git clone https://github.com/username/mama_reg_bots.git .
python3.9 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Подготовить данные (1 мин)
```bash
cp .env.example .env
nano .env  # Вставить BOT_TOKEN и ID групп

mkdir -p data/Айгерим data/Бермет data/Майрам data/Жайна data/Чолпон
```

### 4. Создать systemd сервис (1 мин)
```bash
sudo tee /etc/systemd/system/mama-bot.service > /dev/null <<EOF
[Unit]
Description=MAMA Registration Bot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/mama_reg_bots
ExecStart=/opt/mama_reg_bots/venv/bin/python /opt/mama_reg_bots/main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable mama-bot
sudo systemctl start mama-bot
```

### 5. Проверить статус (1 мин)
```bash
sudo systemctl status mama-bot
sudo journalctl -u mama-bot -f  # Ctrl+C для выхода
```

## Готово! 🎉

Бот теперь запущен и будет автоматически перезагружаться при падении или перезагрузке сервера.

---

## Команды для управления

```bash
# Остановить
sudo systemctl stop mama-bot

# Перезагрузить
sudo systemctl restart mama-bot

# Обновить код
git pull origin main
sudo systemctl restart mama-bot

# Просмотреть логи
sudo journalctl -u mama-bot -n 100 -f

# Создать резервную копию
tar -czf backup_$(date +%Y%m%d).tar.gz data/ config/counters.json
```

---

## Если что-то не работает

```bash
# 1. Проверить логи
sudo journalctl -u mama-bot -n 50

# 2. Проверить .env
cat .env

# 3. Проверить токен (тестовый запуск)
cd /opt/mama_reg_bots
source venv/bin/activate
python main.py

# 4. Если ошибка - исправить и перезагрузить
sudo systemctl restart mama-bot
```

Подробнее в `DEPLOYMENT.md` 📖
