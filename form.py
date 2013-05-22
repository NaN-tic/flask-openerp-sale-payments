#This file is part openerp-sale-payment app for Flask.
#The COPYRIGHT file at the top level of this repository contains
#the full copyright notices and license terms.
from flask.ext.wtf import Form, TextField, HiddenField, SubmitField, Required
from wtforms import fields, TextField, widgets


class OrderForm(Form):
    name = TextField("Name", validators=[Required()])
    submit = SubmitField("Submit")
