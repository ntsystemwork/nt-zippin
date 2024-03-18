from odoo import models, fields, api
from odoo.exceptions import ValidationError
from odoo.addons.zippin.models.delivery_carrier import ID_CORREO_ARGENTINO, ID_OCA, ID_ANDREANI, APIURL
from requests.structures import CaseInsensitiveDict
import requests, base64

class ZippinLog(models.Model):
    _name = 'zippin.log'
    _description = 'zippin.log'

    order_id = fields.Many2one('sale.order',string='Pedido')
    dt_llamada = fields.Datetime('Hora llamada')
    llamada = fields.Char('Llamada')
    request = fields.Text('Request')
    response = fields.Text('Response')
