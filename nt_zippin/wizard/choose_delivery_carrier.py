from odoo import models, fields, api
from odoo.exceptions import ValidationError
from odoo.addons.zippin.models.delivery_carrier import ID_CORREO_ARGENTINO, ID_OCA, ID_ANDREANI

class ChooseDeliveryCarrier(models.TransientModel):
    _inherit = 'choose.delivery.carrier'

    def _get_shipment_rate(self):
        res = super(ChooseDeliveryCarrier, self)._get_shipment_rate()
        self.delete_pickup_points()
        if self.carrier_id.zippin_shipment:
            result = None
            shipment_types = ['1','233','208']
            max_price = 999999999
            for shipment_type in shipment_types:
                self.carrier_id.zippin_shipment_type = shipment_type
                zp_vals = self.carrier_id.rate_shipment(self.order_id)
                if zp_vals.get('success') and zp_vals.get('price') != 0 and zp_vals.get('price') <  max_price:
                    max_price = zp_vals.get('price')
                    result = zp_vals
            if result and result.get('success'):
                self.zippin_logistic_type = result['logistic_type']
                self.env['zippin.shipping'].create(result['zippin_pickup'])
        return res
