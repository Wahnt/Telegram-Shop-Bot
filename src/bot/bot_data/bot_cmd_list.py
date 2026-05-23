from aiogram.types import BotCommand

"""Модуль содержит список команд для пользователей и администраторов в приватных чатах"""

private = [
    BotCommand(
        command="start", description="Подтверждение на обработку персональных данных"
    ),
    BotCommand(
        command="info", description="Политика конфиденциальности, договор оферты"
    ),
    BotCommand(command="support", description="Сервис технической поддержки"),
    BotCommand(
        command="revoke_consent", description="Отозвать согласие и удалить данные"
    ),
]

admin_commands = [
    BotCommand(
        command="start", description="Подтверждение на обработку персональных данных"
    ),
    BotCommand(
        command="info", description="Политика конфиденциальности, договор оферты"
    ),
    BotCommand(command="admin", description="Октрыть панель администратора"),
    BotCommand(command="connect", description="Связаться с пользователем"),
]
