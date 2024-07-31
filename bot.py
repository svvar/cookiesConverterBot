import io
import os
import uuid

from aiosqlite import DatabaseError
from aiogram import Bot, Dispatcher, types, F, filters
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from aiogram.fsm.context import FSMContext

from cookies_convertor import extract_cookies_from_db, convert_to_json
from user_storage import UserStorage
from states import AddingPermission, RemovingPermission, Mailing


class CookiesConvertorBot:
    def __init__(self, token: str, temp_cookies_dir: str, user_storage: UserStorage):
        self.bot = Bot(token=token)
        self.dp = Dispatcher()

        self.temp_cookies_dir = temp_cookies_dir
        self.user_storage = user_storage

        self.register_handlers()

    def register_handlers(self):
        self.dp.message(filters.command.Command('reset'))(self.reset_state)  # this should be first
        self.dp.message(filters.command.CommandStart())(self.start_msg)
        self.dp.message(F.content_type == types.ContentType.DOCUMENT)(self.on_document)
        self.dp.message(filters.command.Command('add_myself_as_an_admin'))(self.add_admin)
        self.dp.message(F.text.lower() == 'додати користувача')(self.give_user_permission)
        self.dp.message(AddingPermission.entering_name)(self.entering_name_state)
        self.dp.message(AddingPermission.entering_id)(self.entering_id_state)
        self.dp.message(F.text.lower() == 'видалити користувача')(self.delete_user)
        self.dp.message(RemovingPermission.entering_name)(self.entering_name_removing_state)
        self.dp.message(F.text.lower() == 'запустити розсилку')(self.start_mailing)
        self.dp.message(Mailing.entering_message)(self.processing_mailing)


    async def start_msg(self, message: types.Message):
        if not await self.user_storage.check_user(message.from_user.id):
            await self.user_storage.save_user(message.from_user.id)

        await message.answer('Привіт, відправте sqlite файл з facebook cookies для конвертації у json формат\n'
                             '*Ви зможете користуватися ботом коли вам дозволить адміністратор*', parse_mode='markdown')

    async def on_document(self, message: types.Message):
        if not await self.user_storage.can_use(message.from_user.id):
            await message.answer('У вас немає доступу до бота.')
            return

        doc_name = message.document.file_name
        file_id = message.document.file_id
        incoming_file_name = str(uuid.uuid4())

        await message.bot.download(file_id, f'{self.temp_cookies_dir}/{incoming_file_name}')
        try:
            extracted_cookies = await extract_cookies_from_db(f'{self.temp_cookies_dir}/{incoming_file_name}')
        except DatabaseError as e:
            if 'file is not a database' in str(e):
                await message.answer('Файл не є базою даних що містить cookies!')
            elif 'no such column' in str(e):
                await message.answer(f'Файл не містить усіх необхідних колонок!\n{str(e).split(": ")[1]}')
            else:
                await message.answer(f'Помилка бази даних: {str(e)}')
        else:
            fixed_cookies = convert_to_json(extracted_cookies)
            with io.BytesIO() as outcoming_file:
                outcoming_file.write(str(fixed_cookies).encode())
                output_file = types.BufferedInputFile(outcoming_file.getvalue(), filename=f'{doc_name.split(".")[0]}.json')
                await message.answer_document(output_file)
        finally:
            os.remove(f'{self.temp_cookies_dir}/{incoming_file_name}')

    async def add_admin(self, message: types.Message):
        await self.user_storage.make_admin(message.from_user.id)
        reply_markup = ReplyKeyboardBuilder()
        reply_markup.add(types.KeyboardButton(text='Додати користувача'))
        reply_markup.add(types.KeyboardButton(text='Видалити користувача'))
        reply_markup.add(types.KeyboardButton(text='Запустити розсилку'))

        await message.answer('*Ви успішно додані до адміністраторів!*\n'
                             'Додатковий функціонал доступний за допомогою клавіатури\n'
                             '/reset - очистити стан, скасувати почату дію', reply_markup=reply_markup.as_markup(),
                             parse_mode='markdown')

    async def give_user_permission(self, message: types.Message, state: FSMContext):
        if not await self.user_storage.is_admin(message.from_user.id):
            await message.answer('У вас немає доступу до цієї команди.')
            return

        await message.answer('Введіть ім\'я користувача (унікальне, тільки для адміна):')
        await state.set_state(AddingPermission.entering_name)

    async def entering_name_state(self, message: types.Message, state: FSMContext):
        name = message.text
        if await self.user_storage.check_nick_unique(name):
            await message.answer('Ім\'я користувача не є унікальним, введіть інше')
            return

        await state.update_data(name=name)

        await message.answer('Введіть ID користувача:')
        await state.set_state(AddingPermission.entering_id)

    async def entering_id_state(self, message: types.Message, state: FSMContext):
        name = (await state.get_data())['name']

        try:
            user_id = int(message.text)
        except ValueError:
            await message.answer('Помилка! ID користувача має бути числом\nПочніть спочатку')
            await state.clear()
            return

        if not await self.user_storage.check_user(user_id):
            await message.answer('Користувач з таким ID не існує, або ще не запустив бота\nПочніть спочатку')
            await state.clear()
            return

        await self.user_storage.add_nick_for_admin(user_id, name)
        await self.user_storage.give_permission_to_use(user_id)

        await self.bot.send_message(user_id, 'Вам надано дозвіл на використання бота!')

        await message.answer(f'Користувач {name} успішно доданий!')
        await state.clear()

    async def delete_user(self, message: types.Message, state: FSMContext):
        if not await self.user_storage.is_admin(message.from_user.id):
            await message.answer('У вас немає доступу до цієї команди.')
            return

        all_nicks = await self.user_storage.get_all_nicks()
        if not all_nicks:
            await message.answer('Немає користувачів для видалення')
            return

        await message.answer(f'Користувачі з дозволом: \n{", ".join(all_nicks)}')
        await message.answer('Введіть ім\'я користувача для видалення:')

        await state.set_state(RemovingPermission.entering_name)

    async def entering_name_removing_state(self, message: types.Message, state: FSMContext):
        name = message.text
        if name not in await self.user_storage.get_all_nicks():
            await message.answer('Неправильний ввід, повторіть')
            return

        await self.user_storage.remove_permission_by_nick(name)
        await message.answer(f'Користувач {name} позбалений доступу!')
        await state.clear()

    async def start_mailing(self, message: types.Message, state: FSMContext):
        if not await self.user_storage.is_admin(message.from_user.id):
            await message.answer('У вас немає доступу до цієї команди.')
            return

        await message.answer('Введіть текст розсилки або перешліть готове повідомлення:')

        await state.set_state(Mailing.entering_message)

    async def processing_mailing(self, message: types.Message, state: FSMContext):
        all_users = await self.user_storage.get_all_user_ids()
        all_users.remove(message.from_user.id)
        for user in all_users:
            try:
                await self.bot.copy_message(chat_id=user, from_chat_id=message.chat.id, message_id=message.message_id)
            except Exception as e:
                print(f'Error while sending message to {user}: {e}')
        await message.answer('Здійснюю розсилку...')
        await state.clear()

    async def reset_state(self, message: types.Message, state: FSMContext):
        await state.clear()
        await message.answer('Стан очищено!')

    async def start_polling(self):
        await self.dp.start_polling(self.bot)