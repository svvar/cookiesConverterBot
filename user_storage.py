import os.path
import aiosqlite

class UserStorage:
    def __init__(self, db_file: str):
        self.db = db_file
        self.conn = None

    async def start_db(self):
        if not os.path.exists(self.db):
            conn = await aiosqlite.connect(self.db)
            await self._create_schema(conn)
            self.conn = conn
        else:
            self.conn = await aiosqlite.connect(self.db)

    async def _create_schema(self, conn):
        await conn.execute('''
            create table bot_users(
                user_id        int not null primary key,
                can_use        int not null,
                is_admin       int not null,
                nick_for_admin varchar(50) default null );
            ''')
        await conn.commit()

    async def close(self):
        await self.conn.close()

    async def get_user(self, user_id: int):
        async with self.conn.execute('''
            SELECT * FROM bot_users WHERE user_id = ?
            ''', (user_id,)) as cursor:
            return await cursor.fetchone()

    async def check_user(self, user_id: int):
        user = await self.get_user(user_id)
        if user:
            return True
        return False

    async def save_user(self, user_id: int):
        await self.conn.execute('''
            INSERT INTO bot_users (user_id, can_use, is_admin) 
            VALUES (?, 0, 0)
            ''', (user_id,))
        await self.conn.commit()

    async def get_all_user_ids(self):
        async with self.conn.execute('''
            SELECT user_id FROM bot_users
            ''') as cursor:
            res = await cursor.fetchall()

            return [x[0] for x in res]

    async def give_permission_to_use(self, user_id: int):
        await self.conn.execute('''
            UPDATE bot_users SET can_use = 1 WHERE user_id = ?
            ''', (user_id,))
        await self.conn.commit()

    async def remove_permission_to_use(self, user_id: int):
        await self.conn.execute('''
            UPDATE bot_users SET can_use = 0 WHERE user_id = ?
            ''', (user_id,))
        await self.conn.commit()

    async def remove_permission_by_nick(self, nick: str):
        await self.conn.execute('''
            UPDATE bot_users SET can_use = 0, nick_for_admin = null WHERE nick_for_admin = ?
            ''', (nick,))
        await self.conn.commit()

    async def make_admin(self, user_id: int):
        await self.conn.execute('''
            UPDATE bot_users SET is_admin = 1, can_use = 1 WHERE user_id = ?
            ''', (user_id,))
        await self.conn.commit()

    async def is_admin(self, user_id: int):
        async with self.conn.execute('''
            SELECT is_admin FROM bot_users WHERE user_id = ?
            ''', (user_id,)) as cursor:
            res = await cursor.fetchone()
            return res[0]

    async def can_use(self, user_id: int):
        async with self.conn.execute('''
            SELECT can_use FROM bot_users WHERE user_id = ?
            ''', (user_id,)) as cursor:
            res = await cursor.fetchone()
            return res[0]

    async def add_nick_for_admin(self, user_id: int, nick: str):
        await self.conn.execute('''
            UPDATE bot_users SET nick_for_admin = ? WHERE user_id = ?
            ''', (nick, user_id))
        await self.conn.commit()

    async def check_nick_unique(self, nick: str):
        async with self.conn.execute('''
            SELECT user_id FROM bot_users WHERE nick_for_admin = ?
            ''', (nick,)) as cursor:
            return await cursor.fetchone()

    async def get_all_nicks(self):
        async with self.conn.execute('''
            SELECT nick_for_admin FROM bot_users WHERE nick_for_admin IS NOT NULL
            ''') as cursor:
            res = await cursor.fetchall()

            return [x[0] for x in res]

