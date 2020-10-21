from django.db import models
from django.contrib.auth.models import User

# Create your models here.

class Tokens(models.Model):
    user = models.ForeignKey(User, on_delete = models.CASCADE)
    access_tkn = models.CharField(max_length = 200, default = None)
    item_id = models.CharField(max_length = 200, default = None)
    webhook = models.CharField(max_length = 200, default = None)