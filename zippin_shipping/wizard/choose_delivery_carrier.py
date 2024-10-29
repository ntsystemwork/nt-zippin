from odoo import models, fields, api
from odoo.exceptions import ValidationError
from odoo.addons.zippin.models.delivery_carrier import ID_CORREO_ARGENTINO, ID_OCA, ID_ANDREANI
from datetime import date, datetime
import logging
_logger = logging.getLogger(__name__)




class ChooseDeliveryCarrier(models.TransientModel):
    _inherit = 'choose.delivery.carrier'

    zippin_pickup_view_invisible = fields.Boolean(default='True')
    zippin_pickup_view_id = fields.Char()
    zippin_logistic_type = fields.Char()
    zippin_pickup = fields.Many2one('zippin.shipping', string="Sucursales")

    zippin_estimated_delivery = fields.Datetime(string='Entrega estimada')
    zippin_min_days = fields.Integer(string='Entrega estimada mínima')
    zippin_max_days = fields.Integer(string='Entrega estimada máxima')


    def set_only_the_date(self):
        if self.zippin_estimated_delivery not in ('', False):
            if self.delivery_type == 'zippin' and self.display_price > 1 and self.delivery_price > 1:
                if self.carrier_id.zippin_shipment_type_is_pickup:
                    self.order_id.write({
                        # 'zippin_estimated_delivery': self.zippin_estimated_delivery,
                        'zippin_min_date': self.order_id.add_days_to_current_date(self.zippin_min_days),
                        'zippin_max_date': self.order_id.add_days_to_current_date(self.zippin_max_days),
                        'commitment_date': self.zippin_estimated_delivery,
                        'zippin_latest_shipping_query': datetime.now(),
                        
                    })
                else:
                    self.order_id.write({
                        # 'zippin_estimated_delivery': self.zippin_estimated_delivery,
                        'zippin_min_date': self.order_id.add_days_to_current_date(self.zippin_min_days),
                        'zippin_max_date': self.order_id.add_days_to_current_date(self.zippin_max_days),
                        'commitment_date': self.zippin_estimated_delivery,
                        'zippin_latest_shipping_query': datetime.now(),
                    })
            else:
                if self.delivery_type not in ('fixed', 'base_on_rule'):
                    raise ValidationError('Primero debe obtener la tarifa')
            return {'type': 'ir.actions.act_window_close'}
        else:
            raise ValidationError('Primero debe obtener la tarifa')


    def _get_shipment_rate(self):
        res = super(ChooseDeliveryCarrier, self)._get_shipment_rate()
        self.delete_pickup_points()

        # Verifica si hay un tipo de envío de Zippin configurado
        if self.carrier_id.zippin_shipment or self.carrier_id.zippin_shipment_type:
            zp_vals = self.carrier_id.rate_shipment(self.order_id)
            
            if zp_vals.get('success'):
                # Actualiza el tipo de envío y el tipo logístico de Zippin
                self.carrier_id.zippin_shipment_type = str(zp_vals['shipment_type'])
                self.zippin_logistic_type = zp_vals['logistic_type']
                self.zippin_estimated_delivery = zp_vals['zippin_estimated_delivery'][:-15]
                self.zippin_min_days = int(zp_vals['min'])
                self.zippin_max_days = int(zp_vals['max'])
                # Crea los puntos de recogida en el modelo 'zippin.shipping'
                self.env['zippin.shipping'].create(zp_vals['zippin_pickup'])
        return res


    def delete_pickup_points(self):
        res = self.env['zippin.shipping'].search([('order_id','=', int(self.order_id))]).unlink()
        return(res)


    def button_confirm(self):
        res = super().button_confirm()

        if self.delivery_type == 'zippin' and self.display_price > 1 and self.delivery_price > 1:
            if self.carrier_id.zippin_shipment_type_is_pickup:
                self.order_id.write({
                    'zippin_pickup_order_id': self.zippin_pickup['order_id'],
                    'zippin_pickup_carrier_id': self.zippin_pickup['carrier_id'],
                    'zippin_pickup_is_pickup': True,
                    'zippin_pickup_point_id': self.zippin_pickup['point_id'],
                    'zippin_pickup_name': self.zippin_pickup['name'],
                    'zippin_pickup_address': self.zippin_pickup['address'],
                    'zippin_logistic_type': self.zippin_pickup['logistic_type'],
                    'zippin_create_shipping_view': False,
                    # 'zippin_estimated_delivery': self.zippin_estimated_delivery,
                    'zippin_min_date': self.order_id.add_days_to_current_date(self.zippin_min_days),
                    'zippin_max_date': self.order_id.add_days_to_current_date(self.zippin_max_days),
                    'commitment_date': self.zippin_estimated_delivery,
                    'zippin_latest_shipping_query': datetime.now(),
                })
            else:
                self.order_id.write({
                    'zippin_pickup_order_id': int(self.order_id),
                    'zippin_pickup_carrier_id': self.carrier_id.zippin_shipment_type,
                    'zippin_pickup_is_pickup': False,
                    'zippin_pickup_point_id': None,
                    'zippin_pickup_name': None,
                    'zippin_pickup_address': None,
                    'zippin_logistic_type': self.zippin_logistic_type,
                    'zippin_create_shipping_view': False,
                    # 'zippin_estimated_delivery': self.zippin_estimated_delivery,
                    'zippin_min_date': self.order_id.add_days_to_current_date(self.zippin_min_days),
                    'zippin_max_date': self.order_id.add_days_to_current_date(self.zippin_max_days),
                    'commitment_date': self.zippin_estimated_delivery,
                    'zippin_latest_shipping_query': datetime.now(),
                })
        else:
            if self.delivery_type not in ('fixed', 'base_on_rule'):
                raise ValidationError('Primero debe obtener la tarifa')

        return res


