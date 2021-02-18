from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.utils import timezone


class Queue(models.Model):
    chat_id = models.BigIntegerField(primary_key=True)
    name = models.CharField(max_length=100)
    users = ArrayField(models.CharField(max_length=33), blank=True, null=True)
    admins = ArrayField(models.CharField(max_length=33))
    is_active = models.BooleanField(default=True)
    cooldown = models.IntegerField(default=10)
    admins_timestamp = models.DateTimeField(default=timezone.now())
    list_timestamp = models.DateTimeField(default=timezone.now())
    message_id = models.IntegerField(default=0)

    def is_admin(self, username):
        return self.admins.__contains__(username)

    def add_user(self, username):
        try:
            self.users.index(username)
            return False
        except ValueError:
            self.users.append(username)
            self.save()
            return True

    def remove_user(self, username):
        try:
            self.users.remove(username)
            self.save()
            return True
        except ValueError:
            return False

    def add_admin(self, username):
        try:
            self.admins.index(username)
            return False
        except ValueError:
            self.admins.append(username)
            self.save()
            return True

    def remove_admin(self, username):
        try:
            self.admins.remove(username)
            self.save()
            return True
        except ValueError:
            return False

    def update_message_id(self, message_id):
        try:
            self.message_id = message_id
            self.save()
            return True
        except ValueError:
            return False
