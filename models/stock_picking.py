from odoo import models, fields, api
from odoo.exceptions import ValidationError
from odoo.addons.zippin.models.delivery_carrier import ID_CORREO_ARGENTINO, ID_OCA, ID_ANDREANI, APIURL
from requests.structures import CaseInsensitiveDict
from datetime import datetime

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def _compute_zippin_data(self):
        for rec in self:
            zippin_shipping_id = ''
            zippin_shipping_delivery_id = ''
            zippin_shipping_carrier_tracking_id = ''
            zippin_shipping_carrier_tracking_id_alt = ''
            zippin_shipping_tracking = ''
            zippin_shipping_tracking_external = ''
            zippin_estimated_delivery_time = ''
            if rec.picking_type_code == 'outgoing' and rec.sale_id:
                zippin_shipping_id = rec.sale_id.zippin_shipping_id
                zippin_shipping_delivery_id = rec.sale_id.zippin_shipping_delivery_id
                zippin_shipping_carrier_tracking_id = rec.sale_id.zippin_shipping_carrier_tracking_id
                zippin_shipping_carrier_tracking_id_alt = rec.sale_id.zippin_shipping_carrier_tracking_id_alt
                zippin_shipping_tracking = rec.sale_id.zippin_shipping_tracking
                zippin_shipping_tracking_external = rec.sale_id.zippin_shipping_tracking_external
                zippin_estimated_delivery_time = rec.zippin_estimated_delivery_time
            rec.zippin_shipping_id = zippin_shipping_id
            rec.zippin_shipping_delivery_id = zippin_shipping_delivery_id
            rec.zippin_shipping_carrier_tracking_id = zippin_shipping_carrier_tracking_id
            rec.zippin_shipping_carrier_tracking_id_alt = zippin_shipping_carrier_tracking_id_alt
            rec.zippin_shipping_tracking = zippin_shipping_tracking
            rec.zippin_shipping_tracking_external = zippin_shipping_tracking_external
            rec.zippin_estimated_delivery_time = zippin_estimated_delivery_time


    zippin_shipping_id = fields.Char('Zippin Shipping',compute=_compute_zippin_data)
    zippin_shipping_delivery_id = fields.Char('Zippin Shipping Delivery ID',compute=_compute_zippin_data)
    zippin_shipping_carrier_tracking_id = fields.Char('Zippin Shipping Carrier Tracking',compute=_compute_zippin_data)
    zippin_shipping_carrier_tracking_id_alt = fields.Char('Zippin Shipping Carrier Tracking Alt',compute=_compute_zippin_data)
    zippin_shipping_tracking = fields.Char('Zippin Shipping Tracking External',compute=_compute_zippin_data)
    zippin_shipping_tracking_external = fields.Char('Zippin Shipping Tracking External',compute=_compute_zippin_data)
    zippin_estimated_delivery_time = fields.Char('Zippin Estimated Delivery Time',compute=_compute_zippin_data)
