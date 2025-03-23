import re
import uuid
import logging
import gradio as gr
from datetime import datetime
from typing import Any, List
from tinydb import TinyDB, Query

logger = logging.getLogger(__name__)


_CONVERSATION_DB_FILE = 'dialog_db.json'
DEFAULT_CONVERSATION_NAME = "New chat (1)"
CONVERSATION_NAME_MAX_LENGTH = 20


def get_dialog_radio(request: gr.Request, name: str):
    username = request.username or request.session_hash
    logging.debug(f'Get history dialog for user: {username}')

    with TinyDB(_CONVERSATION_DB_FILE) as db:
        query = Query()
        user_items = db.search((query.username == username) & (query.delete == False))
        if not user_items:
            return [gr.Radio(choices=[name], value=name), []]
        sorted_user_items = sorted(user_items, key=lambda x: x["ctime"], reverse=True)
        
        all_names = []
        last_item = None
        for x in sorted_user_items:
            if x['name'] not in all_names:
                all_names.append(x['name'])
            if last_item is None or x['utime'] > last_item['utime']:
                last_item = x
        if last_item['name'] == name:
            history_dialog = None
        else:
            history_dialog = gr.Radio(choices=all_names, value=last_item['name'])
        return [history_dialog, last_item['conversation']]


def get_all_conversation_names(request: gr.Request) -> List[str]:
    username = request.username or request.session_hash
    logging.debug(f'Get all conversation name for user: {username}')

    with TinyDB(_CONVERSATION_DB_FILE) as db:
        query = Query()
        user_items = db.search((query.username == username) & (query.delete == False))
        if not user_items:
            return []
        sorted_user_items = sorted(user_items, key=lambda x: x["ctime"], reverse=True)
        return [x['name'] for x in sorted_user_items]


def get_last_conversation_content(request: gr.Request) -> str:
    username = request.username or request.session_hash
    logging.debug(f'Get last conversation content for user: {username}')

    with TinyDB(_CONVERSATION_DB_FILE) as db:
        query = Query()
        user_items = db.search(query.username == username)
        if not user_items:
            add_conversation(request)
        user_items = db.search(query.username == username)

        u_time = ''
        last_item = None
        for user_item in user_items:
            if user_item['utime'] > u_time:
                u_time = user_item['utime']
                last_item = user_item
        return last_item['conversation']


def get_last_conversation_name(request: gr.Request) -> str:
    username = request.username or request.session_hash
    logging.debug(f'Get last conversation name for user: {username}')

    with TinyDB(_CONVERSATION_DB_FILE) as db:
        query = Query()
        user_items = db.search(query.username == username)
        if not user_items:
            add_conversation(request)
        user_items = db.search(query.username == username)

        u_time = ''
        last_item = None
        for user_item in user_items:
            if user_item['utime'] > u_time:
                u_time = user_item['utime']
                last_item = user_item
        return last_item['name']


def get_selected_conversation_content(request: gr.Request, name: str):
    '''
    Get selected conversation content
    '''
    username = request.username or request.session_hash
    logging.debug(f'Get selected conversation `{name}` content for user: {username}')

    with TinyDB(_CONVERSATION_DB_FILE) as db:
        query = Query()
        query_condition = (query.username == username) & (query.name == name)
        user_items = db.search(query_condition)
        if not user_items:
            conversation = []
        else:
            name = user_items[0]['name']
            conversation = user_items[0]['conversation']
    return [name, conversation]


def add_conversation(request: gr.Request, name: str=None, conversation: List[List[Any]]=None):
    '''
    Create a new conversation
    '''
    username = request.username or request.session_hash
    logging.debug(f'Create a new conversation for user: {username}')

    # Update current conversation
    if name and conversation:
        update_conversation(request, name, conversation)

    with TinyDB(_CONVERSATION_DB_FILE) as db:
        query = Query()
        # Create a new conversation
        new = "New chat ({})"
        i, new_name = 0, None
        is_exist = True
        while is_exist:
            i += 1
            new_name = new.format(i)
            is_exist = db.contains((query.username == username) & (query.name == new_name))

        time_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        db.insert({
            'id': uuid.uuid4().hex,
            'username': username,
            'name': new_name,
            'conversation': [],
            'delete': False,
            'ctime': time_now,
            'utime': time_now
        })
    all_names = get_all_conversation_names(request)
    return [new_name, [], gr.Radio(choices=all_names, value=new_name)]


def add_conversation_user(request: gr.Request, prompt, name, conversation):
    username = request.username or request.session_hash
    logging.debug(f'Add user conversation for user: {username}')

    conversation.append({'role': 'user', 'content': prompt})
    with TinyDB(_CONVERSATION_DB_FILE) as db:
        if len(conversation) == 1 and re.match('^New chat \(\d+\)$', name.strip()):
            tmp_new_name = prompt.strip()[:CONVERSATION_NAME_MAX_LENGTH]
            query = Query()
            i = 1
            new_name = tmp_new_name
            while db.contains((query.username == username) & (query.name == new_name)):
                new_name = f'{tmp_new_name}_{i}'
                i += 1
            
            time_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            user_items = db.search((query.username == username) & (query.name == name))
            if user_items:
                user_item = user_items[0]
                user_item['utime'] = time_now
                user_item['name'] = new_name
                user_item['conversation'] = conversation
                db.update(user_item, query.id == user_item['id'])
            else:
                db.insert({
                    'id': uuid.uuid4().hex,
                    'username': username,
                    'name': new_name,
                    'conversation': conversation,
                    'delete': False,
                    'ctime': time_now,
                    'utime': time_now
                })
            name = new_name
        all_names = get_all_conversation_names(request)
        return [gr.Radio(choices=all_names, value=name), '', name, conversation]


def update_conversation(request: gr.Request, name: str, conversation: List[List[Any]]):
    username = request.username or request.session_hash
    logging.debug(f'Update conversation for user: {username}')

    with TinyDB(_CONVERSATION_DB_FILE) as db:
        query = Query()
        query_condition = (query.username == username) & (query.name == name)
        time_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Update current conversation
        user_item = db.search(query_condition)[0]
        user_item['conversation'] = conversation
        user_item['utime'] = time_now

        # Update db
        db.update(user_item, query.id == user_item['id'])


def delete_conversation(request: gr.Request, name: str):
    username = request.username or request.session_hash
    logging.debug(f'Delete conversation for user: {username}')

    with TinyDB(_CONVERSATION_DB_FILE) as db:
        query = Query()
        query_condition = (query.username == username) & (query.name == name) & (query.delete == False)
        user_items = db.search(query_condition)
        if not user_items:
            logger.error(f"The conversation '{name}' for user {username} is not exist.")
        for user_item in user_items:
            user_item['delete'] = True
            user_item['name'] = f'__delete_{name}_delete__'
            db.update(user_item, query.id == user_item['id'])
    
    all_names = get_all_conversation_names(request)
    if not all_names:
        add_conversation(request)
        all_names = get_all_conversation_names(request)
    new_name, conversation = get_selected_conversation_content(request, all_names[0])
    return [new_name, conversation, gr.Radio(choices=all_names, value=new_name)]


def rename_conversation(request: gr.Request, name: str, new_name: str):
    username = request.username or request.session_hash
    logging.debug(f'Rename conversation for user: {username}')
    
    with TinyDB(_CONVERSATION_DB_FILE) as db:
        query = Query()
        error_name = False
        if db.contains((query.username == username) & (query.name == new_name)):
            gr.Info("Duplicate name! Please rename it!(重复的名称！请您重新命名！)")
            error_name = True
        if new_name == "":
            gr.Info("The name can not be empty!(名称不能为空！)")
            error_name = True
        if not error_name:
            user_items = db.search((query.username == username) & (query.name == name))   
            for user_item in user_items:
                user_item['name'] = new_name
                db.update(user_item, query.id == user_item['id'])
    new_name = name if error_name else new_name
    all_names = get_all_conversation_names(request)
    return [gr.Radio(choices=all_names or [new_name], value=new_name), new_name]


if __name__=='__main__':
    request = gr.Request(username='sdfsfsd')

    # add_conversation(request, name='明天早上八点叫我', conversation=[['nihao', 'sdfsdfsdf']])
    # delete_conversation(request, name='明天早上八点叫我')
    # update_conversation(request, name='New chat (1)', conversation=[['nihao', 'New chat 234234324']])
    # rename_conversation(request, name='New chat (2)', new_name='chat23424')

    print(get_last_conversation_name(request))
    print(get_all_conversation_names(request))
