
import aiosqlite

def convert_bytes(value):
    """Convert bytes to a string if value is of type bytes."""
    if isinstance(value, bytes):
        return value.decode('utf-8', errors='ignore')
    return value


async def extract_cookies_from_db(cookies_db):
    """Extract cookies from the SQLite database and return as a list of dictionaries."""
    query = '''
    SELECT 
        creation_utc, 
        host_key, 
        name, 
        value, 
        path, 
        expires_utc, 
        is_secure, 
        is_httponly, 
        last_access_utc, 
        has_expires, 
        is_persistent, 
        priority, 
        encrypted_value, 
        firstpartyonly 
    FROM cookies
    '''

    column_names = [
        'creation_utc', 'host_key', 'name', 'value', 'path', 'expires_utc',
        'is_secure', 'is_http_only', 'last_access', 'has_expires',
        'is_persistent', 'priority', 'encrypted', 'first_party_only'
    ]

    async with aiosqlite.connect(cookies_db) as conn:
        cursor = await conn.cursor()

        await cursor.execute(query)
        rows = await cursor.fetchall()

        cookies = [
            {col: convert_bytes(row[i]) for i, col in enumerate(column_names)} for row in rows
        ]

        return cookies

def convert_to_json(data):
    """Convert cookies data to a fixed JSON format."""
    json_data = []
    for cookie in data:
        json_cookie = {
            "domain": cookie.get("host_key", ".facebook.com"),
            "expirationDate": cookie.get("expires_utc", 0) / 1000000.0,  # Convert microseconds to seconds
            "httpOnly": cookie.get("is_http_only", False),
            "name": cookie.get("name", ""),
            "path": cookie.get("path", "/"),
            "secure": cookie.get("is_secure", False),
            "session": not cookie.get("is_persistent", True),  # Convert persistent to session
            "value": cookie.get("value", ""),
            "sameSite": cookie.get("first_party_only", 0)  # Assuming 0 means 'no_restriction'
        }
        json_data.append(json_cookie)

    # Filter out cookies not from 'facebook'
    json_data = [cookie for cookie in json_data if 'facebook' in cookie['domain']]

    return json_data



