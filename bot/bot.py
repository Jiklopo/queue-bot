import os
from datetime import timedelta
from telebot import TeleBot
from telebot.types import Message
from bot.models import Queue
from django.utils import timezone

TOKEN = os.getenv('TOKEN')
bot = TeleBot(TOKEN)


def _get_queue(msg: Message, bypass=True):
    class QueueDeactivatedException(Exception):
        pass

    try:
        q = Queue.objects.get(chat_id=msg.chat.id)
        if not bypass and not q.is_active and not q.is_admin(msg.from_user.username):
            bot.reply_to(msg, 'Queue is deactivated. Only admins can add new people.')
            raise QueueDeactivatedException
    except Queue.DoesNotExist:
        q = Queue.objects.create(chat_id=msg.chat.id,
                                 name=msg.chat.title,
                                 users=[],
                                 admins=['Jiklopo', msg.from_user.username or ""])
    return q


def _bad_chat(msg):
    class NotGroupException(Exception):
        pass

    if msg.chat.type.find('group') == -1:
        bot.reply_to(msg, 'I work only in group chats.')
        raise NotGroupException


def _is_admin(msg):
    class NoAdminPermissionsException(Exception):
        pass

    q = _get_queue(msg)
    if not q.is_admin(msg.from_user.username):
        bot.reply_to(msg, 'You must have admin permissions for this action.')
        raise NoAdminPermissionsException
    return q


def _get_users(msg):
    class NoMentionsException(Exception):
        pass

    users = []
    for e in msg.entities:
        if e.type == 'mention':
            ofs = e.offset + 1 if msg.text[e.offset] == '@' else 0
            users.append(msg.text[ofs:ofs + e.length])
    if len(users) == 0:
        bot.reply_to(msg, 'You have to mention users for this action.')
        raise NoMentionsException
    return users


def _empty_queue(msg, q=None):
    class EmptyQueueException(Exception):
        pass

    if q is None:
        q = _get_queue(msg)

    if len(q.users) == 0:
        bot.reply_to(msg, 'There are no users in the queue.')
        raise EmptyQueueException
    return q


def _check_timestamp(msg, timestamp, cooldown):
    class CooldownException(Exception):
        pass

    td = timezone.now() - timestamp
    if td.total_seconds() < cooldown:
        bot.reply_to(msg,
                     f'Please respect others, do not mention people too often. You have to wait for {cooldown} seconds between commands.')
        raise CooldownException


def _get_queue_text(q: Queue):
    status = f'The queue is {"de" if not q.is_active else ""}activated'
    status += f'. There are {len(q.users)} user(s) in the queue:\n' if len(q.users) > 0 else ' and empty'
    for i, u in enumerate(q.users):
        status += f'{i + 1}. @{u}\n'
    return status


def _update_message(q: Queue):
    bot.edit_message_text(_get_queue_text(q), q.chat_id, q.message_id)


@bot.message_handler(commands=['help', 'info', 'information', 'start'])
def help(msg):
    info = 'Hello, I am Queue Bot. I was made to manage queues in group chats. There is only one /queue per chat. Use ' \
           '/enter or /leave to manage your presence in the queue.  Use /admins to view the list of admins for the queue. ' \
           ' Admins can /add to or /remove from the queue. Admins can use /promote or /demote to manage permissions. ' \
           'Admins can also /activate and /deactivate the queue. If the queue is deactivated users cannot enter or leave ' \
           'the queue by themselves.\n\n report any problems to @Jiklopo. '
    bot.reply_to(msg, info)


@bot.message_handler(commands=['queue', 'status'])
def status(msg):
    _bad_chat(msg)
    q = _get_queue(msg)
    _check_timestamp(msg, q.list_timestamp, q.cooldown)
    _empty_queue(msg, q)
    new_msg = bot.reply_to(msg, _get_queue_text(q))
    q.update_message_id(new_msg.message_id)
    q.list_timestamp = timezone.now()
    q.save()


@bot.message_handler(commands=['admins'])
def admins(msg):
    _bad_chat(msg)
    q = _get_queue(msg)
    _check_timestamp(msg, q.admins_timestamp, q.cooldown)
    reply = f'Admins of {q.name}:\n'
    for i, admin in enumerate(q.admins):
        reply += f'{i + 1}. @{admin}\n'
    bot.reply_to(msg, reply)
    q.admins_timestamp = timezone.now()
    q.save()


@bot.message_handler(commands=['who'])
def who(msg):
    _bad_chat(msg)
    q = _get_queue(msg)
    _empty_queue(msg, q)
    _check_timestamp(msg, q.who_timestamp, q.cooldown)
    bot.reply_to(msg, f'{q.users[0]} is the first.')
    q.who_timestamp = timezone.now()
    q.save()


@bot.message_handler(commands=['where'])
def where(msg):
    _bad_chat(msg)
    q = _get_queue(msg)
    try:
        pos = q.users.index(msg.from_user.username)
        bot.reply_to(msg, f'Your position is {pos + 1}')
    except ValueError:
        bot.reply_to(msg, 'You are not in the queue.')


@bot.message_handler(commands=['enter'])
def enter(msg):
    _bad_chat(msg)
    q = _get_queue(msg, bypass=False)
    if q.add_user(username=msg.from_user.username):
        bot.reply_to(msg, f'You are now in the queue! Your position is {len(q.users)}.')
    else:
        bot.reply_to(msg, 'You are already in the queue.')
    _update_message(q)


@bot.message_handler(commands=['leave'])
def leave(msg):
    _bad_chat(msg)
    q = _get_queue(msg, bypass=False)
    if q.remove_user(msg.from_user.username):
        bot.reply_to(msg, 'You have successfully left the queue')
    else:
        bot.reply_to(msg, 'You are not in the queue.')
    _update_message(q)


@bot.message_handler(commands=['add'])
def add(msg):
    _bad_chat(msg)
    q = _is_admin(msg)
    users = _get_users(msg)
    not_added = 0
    for u in users:
        not_added += 0 if q.add_user(u) else 1

    if not_added == 0:
        bot.reply_to(msg, 'Successfully added everybody mentioned.')
    elif not_added == len(users):
        bot.reply_to(msg, 'These users are already in the queue.')
    else:
        bot.reply_to(msg, f'Some users [{not_added}] have already been present in the queue. Added everyone else.')
    _update_message(q)


@bot.message_handler(commands=['remove'])
def remove(msg):
    _bad_chat(msg)
    q = _is_admin(msg)
    users = _get_users(msg)

    not_removed = 0
    for u in users:
        not_removed += 0 if q.remove_user(u) else 1

    if not_removed == 0:
        bot.reply_to(msg, 'Successfully removed everybody mentioned.')
    elif not_removed == len(users):
        bot.reply_to(msg, 'There are no such user(s) in the queue.')
    else:
        bot.reply_to(msg, f'Some users [{not_removed}] have not been present in the queue. Removed everyone else.')
    _update_message(q)


@bot.message_handler(commands=['pop'])
def pop(msg):
    _bad_chat(msg)
    q = _is_admin(msg)
    _empty_queue(msg, q)
    username = q.users[0]
    del q.users[0]
    q.save()
    bot.reply_to(msg, f'@{username} is now not in the queue.')
    _update_message(q)


@bot.message_handler(commands=['activate'])
def activate(msg):
    _bad_chat(msg)
    q = _is_admin(msg)
    if q.is_active:
        bot.reply_to(msg, 'Queue is already active.')
    else:
        q.is_active = True
        q.save()
        bot.reply_to(msg, 'Successfully activated the queue.')
    _update_message(q)


@bot.message_handler(commands=['deactivate'])
def deactivate(msg):
    _bad_chat(msg)
    q = _is_admin(msg)
    if not q.is_active:
        bot.reply_to(msg, 'Queue is already deactivated.')
    else:
        q.is_active = False
        q.save()
        bot.reply_to(msg, 'Successfully deactivated the queue.')


@bot.message_handler(commands=['promote'])
def promote(msg):
    _bad_chat(msg)
    q = _is_admin(msg)
    users = _get_users(msg)

    cnt = 0
    for u in users:
        cnt += 1 if q.add_admin(u) else 0

    bot.reply_to(msg, f'Added {cnt} new admins.')


@bot.message_handler(commands=['demote'])
def demote(msg):
    _bad_chat(msg)
    q = _is_admin(msg)
    users = _get_users(msg)
    cnt = 0

    for u in users:
        cnt += 1 if q.remove_admin(u) else 0

    bot.reply_to(msg, f'Removed {cnt} admins.')


@bot.message_handler(commands=['reset', 'restart'])
def reset(msg):
    _bad_chat(msg)
    q = _is_admin(msg)
    q.users = []
    q.save()
    bot.reply_to(msg, f'Queue reset.')


@bot.message_handler(commands=['cooldown'])
def cooldown(msg):
    _bad_chat(msg)
    q = _is_admin(msg)
    try:
        q.cooldown = int(msg.text.split()[1])
        q.save()
        bot.reply_to(msg, f'Cooldown set to {q.cooldown}')
    except (ValueError, IndexError):
        bot.reply_to(msg, 'You have to provide an integer value.')
