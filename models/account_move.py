from odoo import models, fields, api
from odoo.exceptions import ValidationError
from odoo.addons.zippin.models.delivery_carrier import ID_CORREO_ARGENTINO, ID_OCA, ID_ANDREANI, APIURL
from requests.structures import CaseInsensitiveDict
from datetime import datetime

class AccountMove(models.Model):
    _inherit = 'account.move'

    zippin_shipping_tracking_external = fields.Char('Zippin Shipping Tracking External')

