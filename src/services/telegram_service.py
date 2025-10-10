import asyncio
from telethon import TelegramClient
from src.config.settings import SESSION_FILE_PREFIX

class TelegramService:
    def __init__(self, loop):
        self.client = None
        self.sent_code_hash = None
        self.stop_requested = False
        self.loop = loop

    async def connect(self, api_id, api_hash, phone_number):
        session_file = f"{SESSION_FILE_PREFIX}{phone_number}"
        self.client = TelegramClient(session_file, api_id, api_hash, loop=self.loop)
        await self.client.connect()

    async def disconnect(self):
        if self.client and self.client.is_connected():
            await self.client.disconnect()

    async def logout(self):
        if self.client and self.client.is_connected():
            await self.client.log_out()

    async def is_user_authorized(self):
        return await self.client.is_user_authorized()

    async def send_code_request(self, phone_number):
        result = await self.client.send_code_request(phone_number)
        self.sent_code_hash = result.phone_code_hash

    async def sign_in(self, phone_number, code):
        await self.client.sign_in(phone=phone_number, code=code, phone_code_hash=self.sent_code_hash)

    async def get_groups(self):
        groups = []
        async for dialog in self.client.iter_dialogs():
            if dialog.is_group:
                groups.append((dialog.entity, dialog.title))
        return groups

    async def send_message_to_groups(self, message_text, delay_seconds, groups_list, log_callback, progress_callback):
        self.stop_requested = False
        total_groups = len(groups_list)
        for i, (entity, title) in enumerate(groups_list):
            if self.stop_requested:
                log_callback("\n--- Process stopped by user! ---")
                break

            try:
                await self.client.send_message(entity, message_text)
                log_callback(f"✅ Sent to: {title}")
                progress_callback()

                if delay_seconds > 0:
                    await asyncio.sleep(delay_seconds)

            except Exception as e:
                log_callback(f"❌ Error sending to {title}: {e}")
                await asyncio.sleep(5)
        else:
            log_callback("\n--- All messages sent successfully! ---")

    def request_stop(self):
        self.stop_requested = True
