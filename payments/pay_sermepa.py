#This file is part openerp-sale-payment app for Flask.
#The COPYRIGHT file at the top level of this repository contains
#the full copyright notices and license terms.
from flask import Blueprint, render_template, redirect, current_app, url_for, session
from flask.ext.babel import gettext
from sermepa import Client
import erppeek

pay_sermepa = Blueprint('pay_sermepa', __name__, template_folder='templates')

def get_order():
    '''Get order info: id, number and amount'''
    order_id = session.get('order_id', None)
    order = session.get('order', None)
    amount = session.get('amount', 0.0)
    return order_id, order, amount

def set_order_null():
    '''Set order null - Reset order session'''
    session.pop('order_id', None)
    session.pop('order', None)
    session.pop('amount', None)

def erp_connect():
    '''OpenERP Connection'''
    server = current_app.config.get('OPENERP_SERVER')
    database = current_app.config.get('OPENERP_DATABASE')
    username = current_app.config.get('OPENERP_USERNAME')
    password = current_app.config.get('OPENERP_PASSWORD')
    openerp = erppeek.Client(server, db=database, user=username, password=password)
    return openerp

@pay_sermepa.route('/')
def sermepa():
    Openerp = erp_connect()
    order_id, order, amount = get_order()
    if not (order_id and order):
        return render_template('payment_error.html')

    SERMEPA_MERCHANT_CODE = current_app.config.get('SERMEPA_MERCHANT_CODE')
    SERMEPA_SECRET_KEY = current_app.config.get('SERMEPA_SECRET_KEY')

    SANDBOX = False
    if current_app.config.get('DEBUG'):
        SANDBOX = True

    '''
    Sermepa don't like send same order name if a user back and return.
    Send to Sermepa name: order-x
    x is a increment number
    '''
    ordername = True
    order_base = order
    count = 0
    while ordername:
        domain = [
            ('description','=', order),
            ]
        orders = Openerp.search('sale.payment.web', domain)
        if len(orders):
            count = count+1
            order = '%s-%s' % (order_base, count)
        else:
            ordername = False

    #  Create log in OpenERP payment
    values = {
        'order_id': order_id,
        'description': order,
        'state': 'pending',
    }
    Openerp.create('sale.payment.web', values)

    values = {
        'Ds_Merchant_Amount': amount,
        'Ds_Merchant_Currency': current_app.config.get('SERMEPA_CURRENCY'),
        'Ds_Merchant_Order': order,
        'Ds_Merchant_ProductDescription': gettext(u'Sale Order: %(order)s', order=order),
        'Ds_Merchant_Titular': current_app.config.get('SERMEPA_MERCHANT_NAME'),
        'Ds_Merchant_MerchantCode': SERMEPA_MERCHANT_CODE,
        'Ds_Merchant_MerchantURL': current_app.config.get('SERMEPA_MERCHANT_URL'),
        'Ds_Merchant_UrlOK': url_for('pay_sermepa.sermepa_confirm', _external=True),
        'Ds_Merchant_UrlKO': url_for('pay_sermepa.sermepa_cancel', _external=True),
        'Ds_Merchant_MerchantName': current_app.config.get('SERMEPA_MERCHANT_NAME'),
        'Ds_Merchant_Terminal': current_app.config.get('SERMEPA_TERMINAL'),
        'Ds_Merchant_SumTotal': amount,
        'Ds_Merchant_TransactionType': current_app.config.get('SERMEPA_TRANS_TYPE'),
    }

    serpayment = Client(business_code=SERMEPA_MERCHANT_CODE, priv_key=SERMEPA_SECRET_KEY, sandbox=SANDBOX)
    sermepa_form = serpayment.get_pay_form_data(values)

    return render_template('sermepa.html', sermepa=sermepa_form)

@pay_sermepa.route('/confirm')
def sermepa_confirm():
    Openerp = erp_connect()
    order_id, order, amount = get_order()
    if not (order_id and order):
        return render_template('payment_error.html')

    message = gettext(u'Your order %(order)s is payed successfully.', order=order)

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

    set_order_null()
    return render_template('sermepa_confirm.html', order=order, message=message)

@pay_sermepa.route('/cancel')
def sermepa_cancel():
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
    return render_template('sermepa_cancel.html', order=order)
