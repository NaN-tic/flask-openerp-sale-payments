#This file is part openerp-sale-payment app for Flask.
#The COPYRIGHT file at the top level of this repository contains
#the full copyright notices and license terms.
from flask import Blueprint, render_template, redirect, current_app, url_for, request, session
from flask.ext.babel import gettext
import erppeek

pay_paypal = Blueprint('pay_paypal', __name__, template_folder='templates')

def get_order():
    '''Get order info: id, number and amount'''
    order_id = session.get('order_id', None)
    order = session.get('order', None)
    amount = session.get('amount', 0.0)
    return order_id, order, amount

def set_order_null():
    '''Set order null - Reset order session'''
    session['order_id'] = None
    session['order'] = None
    session['amount'] = None

def erp_connect():
    '''OpenERP Connection'''
    server = current_app.config.get('OPENERP_SERVER')
    database = current_app.config.get('OPENERP_DATABASE')
    username = current_app.config.get('OPENERP_USERNAME')
    password = current_app.config.get('OPENERP_PASSWORD')
    openerp = erppeek.Client(server, db=database, user=username, password=password)
    return openerp

def get_paypal_account():
    from paypal import PayPalInterface, PayPalConfig

    PAYPAL_USERNAME = current_app.config.get('PAYPAL_USERNAME')
    PAYPAL_PASSWORD = current_app.config.get('PAYPAL_PASSWORD')
    PAYPAL_SIGNATURE = current_app.config.get('PAYPAL_SIGNATURE')

    PAYPAL_ENVIROMENT = 'PRODUCTION'
    if current_app.config.get('DEBUG'):
        PAYPAL_ENVIROMENT = 'SANDBOX'

    config = PayPalConfig(API_USERNAME = PAYPAL_USERNAME,
                          API_PASSWORD = PAYPAL_PASSWORD,
                          API_SIGNATURE = PAYPAL_SIGNATURE,
                          API_ENVIRONMENT = PAYPAL_ENVIROMENT,
                          DEBUG_LEVEL=0)
    interface = PayPalInterface(config=config)
    return interface

@pay_paypal.route('/')
def paypal():
    Openerp = erp_connect()
    order_id, order, amount = get_order()
    if not (order_id and order):
        return render_template('payment_error.html')

    currency = current_app.config.get('PAYPAL_CURRENCY', 'EUR')
    locale = current_app.config.get('LANGUAGE', 'EN')

    #  Create log in OpenERP payment
    values = {
        'order_id': order_id,
        'description': order,
        'state': 'pending',
    }
    Openerp.create('sale.payment.web', values)

    kw = {
        'amt': amount,
        'itemamt': amount,
        'currencycode': currency,
        'returnurl': url_for('pay_paypal.paypal_confirm', _external=True),
        'cancelurl': url_for('pay_paypal.paypal_confirm', _external=True),
        'paymentaction': 'Sale',
        'localecode': locale,
        'desc': gettext(u'Sale Order: %(order)s', order=order),
        'L_AMT0': amount,
        'L_QTY0': '1',
    }
    interface = get_paypal_account()
    setexp_response = interface.set_express_checkout(**kw)
    return redirect(interface.generate_express_checkout_redirect_url(setexp_response.token))  

@pay_paypal.route("/confirm")
def paypal_confirm():
    order_id, order, amount = get_order()
    if not (order_id and order):
        return render_template('payment_error.html')

    interface = get_paypal_account()
    getexp_response = interface.get_express_checkout_details(token=request.args.get('token', ''))

    paypal_do =url_for('pay_paypal.paypal_do', token=getexp_response['TOKEN'])
    if getexp_response['ACK'] == 'Success':
        token = getexp_response['TOKEN']
        return render_template('paypal_confirm.html', order=order, paypal_do=paypal_do)
    else:
        set_order_null()
        error = getexp_response['ACK']
        return render_template('paypal_error.html', order=order, error=error)

@pay_paypal.route("/paypal/do/<string:token>")
def paypal_do(token):
    interface = get_paypal_account()
    getexp_response = interface.get_express_checkout_details(token=token)
    kw = {
        'amt': getexp_response['AMT'],
        'paymentaction': 'Sale',
        'payerid': getexp_response['PAYERID'],
        'token': token,
        'currencycode': getexp_response['CURRENCYCODE']
    }
    interface.do_express_checkout_payment(**kw)   

    return redirect(url_for('pay_paypal.paypal_status', token=kw['token']))

@pay_paypal.route("/paypal/status/<string:token>")
def paypal_status(token):
    Openerp = erp_connect()
    order_id, order, amount = get_order()
    if not (order_id and order):
        return render_template('payment_error.html')

    interface = get_paypal_account()
    checkout_response = interface.get_express_checkout_details(token=token)

    set_order_null()

    if checkout_response['CHECKOUTSTATUS'] == 'PaymentActionCompleted':
        details = '%s %s' % (checkout_response['AMT'], checkout_response['CURRENCYCODE'])
        message = gettext(u'Your order %(order)s is payed successfully. Thank you for your sale payment: %(status)s', order=order, status=details)

        #  Create log in OpenERP payment
        values = {
            'order_id': order_id,
            'description': message,
            'state': 'done',
        }
        Openerp.create('sale.payment.web', values)

        try:
            Openerp.write('sale.order', [order_id], {'paid_in_web': True})
        except:
            return render_template('payment_error.html')

    else:
        message = gettext(u'PayPal does not acknowledge the transaction. Here is the status: %(status)s', status=checkout_response['CHECKOUTSTATUS'])

        #  Create log in OpenERP payment
        values = {
            'order_id': order_id,
            'description': message,
            'state': 'error',
        }
        Openerp.create('sale.payment.web', values)

    return render_template('paypal_status.html', order=order, message=message)

@pay_paypal.route("/cancel")
def paypal_cancel():
    Openerp = erp_connect()
    order_id, order, amount = get_order()
    if not (order_id and order):
        return render_template('payment_error.html')

    #  Create log in OpenERP payment
    values = {
        'order_id': order_id,
        'description': gettext(u'Your order %(order)s is cancelled.', order=order),
        'state': 'cancel',
    }
    Openerp.create('sale.payment.web', values)

    set_order_null()
    return render_template('paypal_cancel.html', order=order)
