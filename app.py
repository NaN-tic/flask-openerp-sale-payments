#This file is part openerp-sale-payment app for Flask.
#The COPYRIGHT file at the top level of this repository contains
#the full copyright notices and license terms.
import os
import json
import ConfigParser
import erppeek

from flask import Flask, render_template, request, abort, session, redirect, url_for
from flask.ext.babel import Babel, gettext as _
from form import *

def get_config():
    '''Get values from cfg file'''
    conf_file = '%s/config.ini' % os.path.dirname(os.path.realpath(__file__))
    config = ConfigParser.ConfigParser()
    config.read(conf_file)

    results = {}
    for section in config.sections():
        results[section] = {}
        for option in config.options(section):
            results[section][option] = config.get(section, option)
    return results

def create_app(config=None):
    '''Create Flask APP'''
    cfg = get_config()
    app_name = cfg['flask']['app_name']
    app = Flask(app_name)
    app.config.from_pyfile(config)

    return app

def get_template(tpl):
    '''Get template'''
    return "%s/%s" % (app.config.get('TEMPLATE'), tpl)

def parse_setup(filename):
    globalsdict = {}  # put predefined things here
    localsdict = {}  # will be populated by executed script
    execfile(filename, globalsdict, localsdict)
    return localsdict

def get_lang():
    return app.config.get('LANGUAGE')

def erp_connect():
    '''OpenERP Connection'''
    server = app.config.get('OPENERP_SERVER')
    database = app.config.get('OPENERP_DATABASE')
    username = app.config.get('OPENERP_USERNAME')
    password = app.config.get('OPENERP_PASSWORD')
    openerp = erppeek.Client(server, db=database, user=username, password=password)
    return openerp

def get_payments():
    payments = app.config.get('PAYMENTS')
    if 'paypal' in payments:
        from payments.pay_paypal import pay_paypal
        app.register_blueprint(pay_paypal, url_prefix='/paypal')
    if 'sermepa' in payments:
        from payments.pay_sermepa import pay_sermepa
        app.register_blueprint(pay_sermepa, url_prefix='/sermepa')

conf_file = '%s/config.cfg' % os.path.dirname(os.path.realpath(__file__))
app = create_app(conf_file)
app.config['BABEL_DEFAULT_LOCALE'] = get_lang()
app.root_path = os.path.dirname(os.path.abspath(__file__))
babel = Babel(app)
get_payments()

@app.errorhandler(404)
def page_not_found(e):
    return render_template(get_template('404.html')), 404

@app.route('/', methods=['GET', 'POST'])
def index():
    '''Index Sale Order Payments'''
    error = None
    form = OrderForm()

    STATES = ['draft']

    #  Send form. Validate order and redirect payment method
    if request.method == 'POST' and form.validate():
        Openerp = erp_connect()
        order_name = request.form.get('name')
        domain = [
            ('name','=', order_name),
            ('paid_in_web', '!=', True),
            ('state', 'in', STATES),
            ]
        orders = Openerp.search('sale.order', domain)
        if len(orders):
            SaleOrder = Openerp.model('sale.order')
            order = SaleOrder.get(orders[0])
            session['order_id'] = order.id
            session['order'] = order.name
            session['amount'] = order.amount_total

            payment = request.form.get('payment')
            return redirect('%s/' % payment)
        error = _(u'Order %(num)s not available or is already paid.', num=order_name)

    #  Get order name ?order=1234
    if request.method == 'GET':
        if request.args.get('order'):
            form.name.data = request.args.get('order')

    payments = app.config.get('PAYMENTS')
    return render_template(get_template('index.html'), form=form, payments=payments, error=error)

if __name__ == "__main__":
    app.run()
