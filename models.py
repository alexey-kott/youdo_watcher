from aiogram.types import User as AiogramUser
from peewee import Model, SqliteDatabase, IntegerField, TextField, BooleanField


class BaseModel(Model):
    class Meta:
        database = SqliteDatabase('db.sqlite3')


class User(BaseModel):
    id = IntegerField(primary_key=True)
    username = TextField(unique=True)
    first_name = TextField()
    last_name = TextField(null=True)
    is_bot = BooleanField()
    language_code = TextField()

