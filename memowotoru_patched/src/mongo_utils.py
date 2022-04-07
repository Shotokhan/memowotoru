import pymongo
from pymongo.database import Database
from pymongo.collection import Collection
import time


class AlreadyExistentUser(Exception):
    pass


class NotExistentUser(Exception):
    pass


def get_db_manager(mongo_config, mongo_client=None):
    if mongo_client is None:
        mongo_client = open_client(mongo_config['hostname'], mongo_config['port'], mongo_config['user'], mongo_config['password'])
    db = get_db(mongo_client, mongo_config['db_name'])
    col = get_collection(db, 'humans')
    return col, mongo_client


def open_client(hostname, port, user, password) -> pymongo.MongoClient:
    mongo_url = f"mongodb://{user}:{password}@{hostname}"
    mongo_client = pymongo.MongoClient(mongo_url, port)
    return mongo_client


def get_db(mongo_client: pymongo.MongoClient, db_name: str) -> Database:
    return mongo_client.get_database(db_name)


def get_collection(db: Database, collection_name: str) -> Collection:
    return db.get_collection(collection_name)


def get_user(col: Collection, user: str):
    user_dict = col.find_one({"username": user})
    return user_dict


def get_and_check_user(col: Collection, user: str):
    user = get_user(col, user)
    if user is None:
        raise NotExistentUser
    return user


def register_user(col: Collection, username: str, hashed_pw: str):
    user = get_user(col, username)
    if user is not None:
        raise AlreadyExistentUser
    else:
        col.insert_one({"username": username, "password": hashed_pw, "notes": []})


def push_note(col: Collection, username: str, title: str, content: str, public: bool):
    user = get_and_check_user(col, username)
    note_id = len(user['notes'])
    col.update_one({"username": username}, {"$push": {"notes": {"title": title, "content": content, "public": public, "timestamp": time.time(), "id": note_id}}})


def get_user_notes(col: Collection, username: str):
    user = get_and_check_user(col, username)
    notes = user["notes"]
    return sorted(notes, key=lambda note: note["timestamp"], reverse=True)


def get_all_public_notes(col: Collection):
    users = col.find()
    notes = []
    for user in users:
        user_notes = user["notes"]
        for user_note in user_notes:
            if user_note["public"]:
                user_note["author"] = user["username"]
                notes.append(user_note)
    return sorted(notes, key=lambda note: note["timestamp"], reverse=True)
