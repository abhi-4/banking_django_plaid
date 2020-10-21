from django.shortcuts import render, redirect
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.http import HttpResponse
from plaid import Client
from plaid.errors import APIError, ItemError, InvalidInputError, InvalidRequestError
import requests
import json

# Create your views here.
from .forms import UserSignupForm
from .models import Tokens
from .tasks import saveTask

plaid_client_id = "5da9e9d3470e370016651aa3"
plaid_secret = "1026c23bcd23fccd4f9dabb1f9f172"

client = Client(client_id=plaid_client_id,
                      secret=plaid_secret,
                      environment='sandbox')

def getAccessToken(user):
    user_details = User.objects.get(username=user)
    user_id = user_details.id
    token = Tokens.objects.get(user_id=user_id)
    access_token = token.access_tkn
    return access_token


def getAccountData(request):
    access_token = getAccessToken(request.user)
    context = dict()

    try:
        response = client.Auth.get(access_token)
        accounts = response['accounts']

        context = {
            'name': 'Accounts Data',
            'data': accounts,
        }

    except APIError as e:
        messages.info(request, 'APIError: Error getting accounts data')
        return redirect('users:account')
    except ItemError as e:
        messages.info(request, 'ItemError: Error getting accounts data')
        return redirect('users:account')
    except requests.Timeout:
        messages.info(request, 'Request timeout, please retry')
        return redirect('users:account')
    except InvalidInputError as e:
        messages.info(request, 'InvalidInputError: Wrong access token')
        return redirect('users:account')
    return render(request, 'showData.html', context)


def getTransactionData(request):
    access_token = getAccessToken(request.user)
    context = dict()
    try:
        response = client.Transactions.get(access_token, start_date='2020-01-01', end_date='2020-02-02')
        transactions = response['transactions']

        # the transactions in the response are paginated, so make multiple calls while increasing the offset to
        # retrieve all transactions
        while len(transactions) < response['total_transactions']:
            response = client.Transactions.get(access_token, start_date='2019-01-01', end_date='2020-01-01', offset=len(transactions))
            transactions.extend(response['transactions'])

        context = {
            'name' : 'Transactions Data',
            'data' : transactions,
        }

    except APIError as e:
        messages.info(request, 'APIError: Error getting transaction data')
        return redirect('users:account')
    except ItemError as e:
        messages.info(request, 'ItemError: Error getting transaction data')
        return redirect('users:account')
    except requests.Timeout:
        messages.info(request, 'Request timeout, please retry')
        return redirect('users:account')
    except InvalidInputError as e:
        messages.info(request, 'InvalidInputError: Wrong access token')
        return redirect('users:account')
    return render(request, 'showData.html', context)

def exchangeToken(public_token):
    response = client.Item.public_token.exchange(public_token)
    access_token = response['access_token']
    return access_token

def index(request):
	return render(request, 'login.html')

def signup(request):
    form = UserSignupForm()

    if request.method == 'POST':
        form = UserSignupForm(request.POST)
        if form.is_valid():
            form.save()
            user = form.cleaned_data.get('username')
            messages.success(request, 'Account was created for ' + user)
            return redirect('users:login')


    context = {'form': form}
    return render(request, 'signup.html', context)

def loginPage(request):
    print('login: ', request)
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            user_details = User.objects.get(username=username)
            user_id = user_details.id
            try:
                token = Tokens.objects.get(user_id=user_id)
                return redirect('users:account')
            except Tokens.DoesNotExist:
                return redirect('users:home')

        else:
            messages.info(request, 'Username OR Password is incorrect')
    
    return render(request, 'login.html')


def logoutUser(request):
    logout(request)
    return redirect('users:login')


def home(request):
    if request.method == 'POST':
        public_token = request.POST.get('public_token')
        generateAccessToken(request, public_token)

    if request.user.is_authenticated:
        return render(request, 'submitToken.html')
    else:
        return redirect('users:login')

def submitToken(request):
    if request.user.is_authenticated:
        return render(request, 'submitToken.html')
    else:
        return redirect('users:login')

def generateAccessToken(request, public_token):

    try:
        access_token = exchangeToken(public_token)
        saveDetails(request, access_token)
        return redirect('users:account')
    except ItemError as e:
        #check the code attribute of the error to determine the specific error
        if e.code == 'ITEM_LOGIN_REQUIRED':
            messages.info(request, "The user's login information has changed, Generate a public token")
        else:
            messages.info(request, 'ItemError')
        return redirect('users:submitToken')
    except APIError as e:
        if e.code == 'PLANNED_MAINTENANCE':
            messages.info(request, 'Plaid is under maintenance, please try after some time')
        else:
            messages.info(request, 'APIError')
        return redirect('users:submitToken')
    except requests.Timeout:
        messages.info(request, 'Request timeout, please retry')
        return redirect('users:submitToken')
    except InvalidInputError as e:
        messages.info(request, 'provided public token is in an invalid format. expected format: public-<environment>-<identifier>')
        return redirect('users:submitToken')
    except InvalidRequestError as e:
        messages.info(request, 'public_token must be a non-empty string')
        return redirect('users:submitToken')

def account(request):
    print('account: ', request)
    if request.user.is_authenticated:
        return render(request, 'userAccount.html')
    else:
        return redirect('users:login')


def saveDetails(request, access_token):
    item_response = client.Item.get(access_token)
    institution_response = client.Institutions.get_by_id(item_response['item']['institution_id'], 'US')
    print(item_response, ' : ', institution_response)
    item_id = item_response['item']['item_id']
    webhook = item_response['item']['webhook']

    token = Tokens.objects.create(user=request.user, access_tkn=access_token, item_id=item_id, webhook = webhook)
    token.save()
    messages.info(request, 'successfully submitted public token')
   
    