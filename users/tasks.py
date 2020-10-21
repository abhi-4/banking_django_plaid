from celery import shared_task
from plaid import Client
from .models import Tokens

plaid_client_id = "5da9e9d3470e370016651aa3"
plaid_secret = "1026c23bcd23fccd4f9dabb1f9f172"

client = Client(client_id=plaid_client_id,
                      secret=plaid_secret,
                      environment='sandbox')

@shared_task
def add(x, y):
    print('sum: ', x+y)
    return x + y

@shared_task
def saveTask(user, access_token):
    item_response = client.Item.get(access_token)
    institution_response = client.Institutions.get_by_id(item_response['item']['institution_id'], 'US')
    
    item_id = item_response['item_id']
    webhook = item_response['webhook']

    token = Tokens.objects.create(user=user, access_tkn=access_token, item_id=item_id, webhook = webhook)
    token.save()