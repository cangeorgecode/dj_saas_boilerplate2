from django.shortcuts import render, redirect, reverse, get_object_or_404
import stripe
from django.conf import settings
from .models import *
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from django.contrib import messages
from datetime import datetime

stripe.api_key = settings.STRIPE_SECRET_KEY



def index(request):
    # Getting the product name & price to display in template
    test_product_1_id = settings.TEST_PRODUCT_ID_1
    test_product_2_id = settings.TEST_PRODUCT_ID_2
    test_product_1 = stripe.Product.retrieve(test_product_1_id)
    test_product_2 = stripe.Product.retrieve(test_product_2_id)
    price_1 = stripe.Price.list(product=test_product_1_id).data[0]
    price_2 = stripe.Price.list(product=test_product_2_id).data[0]
    product_1_price = price_1.unit_amount / 100
    product_2_price = price_2.unit_amount / 100

    # Subscription
    subscription = {
        # price_id
        'test_subs_1': settings.TEST_SUBS_1,
        'test_subs_2': settings.TEST_SUBS_2,
        # product_id
        'test_product_1': test_product_1,
        'test_product_2': test_product_2,
        # price for display
        'product_1_price': product_1_price,
        'product_2_price': product_2_price,
    }
    
    if request.method == "POST":
        if not request.user.is_authenticated:
            messages.error(request, 'Please login first, thank you.')
            return redirect(f'{settings.BASE_URL}{reverse("account_login")}?next={request.get_full_path()}')

        price_id = request.POST.get('price_id')

        subscription = Subscription.objects.filter(user=request.user).first()

        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[
                {
                    'price': price_id,
                    'quantity': 1,
                },
            ],
            mode='subscription',
            success_url=f'{settings.BASE_URL}{reverse("payment_successful")}?session_id={{CHECKOUT_SESSION_ID}}',
            cancel_url=f'{settings.BASE_URL}{reverse("payment_cancelled")}',
            customer_email = request.user.email,
            metadata = {
                'user_id': request.user.id,
            },
        ) 
        return redirect(checkout_session.url, code=303)

    return render(request, 'core/index.html', {
        'subscription': subscription,
    })

def pricing(request):
    # Getting the product name & price to display in template
    test_product_1_id = settings.TEST_PRODUCT_ID_1
    test_product_2_id = settings.TEST_PRODUCT_ID_2
    test_product_1 = stripe.Product.retrieve(test_product_1_id)
    test_product_2 = stripe.Product.retrieve(test_product_2_id)
    price_1 = stripe.Price.list(product=test_product_1_id).data[0]
    price_2 = stripe.Price.list(product=test_product_2_id).data[0]
    product_1_price = price_1.unit_amount / 100
    product_2_price = price_2.unit_amount / 100

    # Subscription
    subscription = {
        # price_id
        'test_subs_1': settings.TEST_SUBS_1,
        'test_subs_2': settings.TEST_SUBS_2,
        # product_id
        'test_product_1': test_product_1,
        'test_product_2': test_product_2,
        # price for display
        'product_1_price': product_1_price,
        'product_2_price': product_2_price,
    }
    if request.method == "POST":
        if not request.user.is_authenticated:
            messages.error(request, 'Please login first, thank you.')
            return redirect(f'{settings.BASE_URL}{reverse("account_login")}?next={request.get_full_path()}')

        price_id = request.POST.get('price_id')

        # For switching subscription plan
        subscription = Subscription.objects.filter(user=request.user).first()
        if subscription:
            stripe_subscription = stripe.Subscription.retrieve(subscription.stripe_subscription_id)
            item = stripe_subscription['items']['data'][0]
            stripe.Subscription.modify(
                subscription.stripe_subscription_id,
                items = [{
                    'id': item['id'],
                    'price': price_id,
                }],
                cancel_at_period_end = False,
            )
            price = stripe.Price.retrieve(price_id)
            product = stripe.Product.retrieve(price['product'])

            subscription.start_date = now()
            subscription.product_name = product.name
            subscription.price = price['unit_amount'] / 100
            subscription.end_date = None
            subscription.canceled_at = None
            subscription.save()

            return redirect('profile')
        else:
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[
                    {
                        'price': price_id,
                        'quantity': 1,
                    },
                ],
                mode='subscription',
                success_url=f'{settings.BASE_URL}{reverse("payment_successful")}?session_id={{CHECKOUT_SESSION_ID}}',
                cancel_url=f'{settings.BASE_URL}{reverse("payment_cancelled")}',
                customer_email = request.user.email,
                metadata = {
                    'user_id': request.user.id,
                },
            ) 
            return redirect(checkout_session.url, code=303)
    return render(request, 'core/pricing.html', {'subscription': subscription})

def create_subscription(request):
    checkout_session_id = request.GET.get('session_id', None)

    # Note 1) In live, we cannot get request.user, but we can get it from the metadata
    session = stripe.checkout.Session.retrieve(checkout_session_id)
    user_id = session.metadata.get('user_id')
    user = User.objects.get(id=user_id)

    # Note 2) The product name is from the price object
    subscription = stripe.Subscription.retrieve(session.subscription)
    price = subscription['items']['data'][0]['price']
    product_id = price['product']
    product = stripe.Product.retrieve(product_id)

    # Create subscription object in db
    if checkout_session_id:
        Subscription.object.create(
            user = user, # See note 1 above
            customer_id = session.customer,
            subscription_id = session.subscription,
            product_name = product.name, # See note 2 above
            price = price['unit_amount'] / 100,
            interval = price['recurring']['interval'],
            start_date = datetime.fromtimestamp(subscription['current_period_start']),
        )

    return redirect('profile')

def cancel_subscription(request, subscription_id):
    subscription = get_object_or_404(Subscription, user=request.user, stripe_subscription_id=subscription_id)

    stripe.Subscription.modify(
        subscription_id,
        cancel_at_period_end=True,
    )

    subscription.canceled_at = now()
    stripe_subscription = stripe.Subscription.retrieve(subscription_id)
    subscription.end_date = datetime.fromtimestamp(stripe_subscription['current_period_end'])
    subscription.save()

    return redirect('profile')

def payment_successful(request):
    checkout_session_id = request.GET.get('session_id')

    if checkout_session_id:
        session = stripe.checkout.Session.retrieve(checkout_session_id)
        customer_id = session.customer
        customer = stripe.Customer.retrieve(customer_id)

        line_items = stripe.checkout.Session.list_line_items(checkout_session_id).data

        # Create a user payment object in the database. 
        if session.mode == 'payment':
            for line_item in line_items:
                # line_item = stripe.checkout.Session.list_line_items(checkout_session_id).data[0]
                UserPayment.objects.get_or_create(
                    user = request.user,
                    stripe_customer_id = customer_id,
                    stripe_checkout_id = checkout_session_id,
                    stripe_product_id = line_item.price.product,
                    product_name = line_item.description,
                    quantity = line_item.quantity,
                    price = line_item.price.unit_amount / 100,
                    currency = line_item.price.currency,
                    has_paid = True,
                )
        elif session.mode == 'subscription':
            for line_item in line_items:
                Subscription.objects.get_or_create(
                    user = request.user,
                    stripe_customer_id = customer_id,
                    stripe_subscription_id = session.subscription,
                    product_name = line_item.description,
                    price = line_item.price.unit_amount / 100,
                    interval = line_item.price.recurring.interval,
                )

    return render(request, 'core/payment_successful.html', {'customer': customer})

def payment_cancel(request):
    return render(request, 'core/payment_cancel.html')

@require_POST
@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META['HTTP_STRIPE_SIGNATURE']
    event = None

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_ENDPOINT_SECRET
        )
    except ValueError as e:
        # Invalid payload
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        return HttpResponse(status=400)

    # Handle the event
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        checkout_session_id = session.get('id')
        user_payment = UserPayment.objects.get(stripe_checkout_id=checkout_session_id)
        user_payment.has_paid = True
        user_payment.save()

    return HttpResponse(status=200)