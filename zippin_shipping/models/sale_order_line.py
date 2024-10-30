from odoo import models, api
from odoo.exceptions import ValidationError


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    @api.model
    def create(self, vals):
        if 'product_id' in vals:
            product_id = vals.get('product_id')
            delivery = self.env['delivery.carrier'].search([('product_id','=',product_id),('is_free','=',True)])
            #if delivery:
            #    vals['discount'] = 100
        res = super(SaleOrderLine, self).create(vals)
        if 'product_id' in vals and delivery:
            #if res.product_id.property_account_income_id.id != self.env.ref('l10n_ar.1_base_prevision_gastos').id:
            #    raise ValidationError('Cuenta de Zippin mal configurada')
            vals_line = {
                    'order_id': vals.get('order_id'),
                    'product_id': self.env.ref('zippin_shipping.zippin_delivery_refund').id,
                    'name': self.env.ref('zippin_shipping.zippin_delivery_refund').name,
                    'price_unit': vals.get('price_unit') * (-1),
                    'product_uom_qty': 1,
                    'product_uom': self.env.ref('zippin_shipping.zippin_delivery_refund').uom_id.id,
                    }
            result = super(SaleOrderLine, self).create(vals_line)
        return res


    def delete_pickup_points(self):
        res = self.env['zippin.shipping'].search([('order_id','=', int(self.order_id.id))]).unlink()
        return(res)



    def delete_zippin_shipping(self):
        self.order_id.zippin_shipping_label_bin = None
        self.order_id.zippin_pickup_order_id = None
        self.order_id.zippin_pickup_carrier_id = None
        self.order_id.zippin_pickup_is_pickup = None
        self.order_id.zippin_pickup_point_id = None 
        self.order_id.zippin_pickup_name = None 
        self.order_id.zippin_pickup_address = None 
        self.order_id.zippin_logistic_type = None 
        self.order_id.zippin_shipping_id = None 
        self.order_id.zippin_shipping_delivery_id = None 
        self.order_id.zippin_shipping_carrier_tracking_id = None 
        self.order_id.zippin_shipping_carrier_tracking_id_alt = None 
        self.order_id.zippin_shipping_tracking = None 
        self.order_id.zippin_shipping_tracking_external = None 
        self.order_id.zippin_create_shipping_view = True
        self.order_id.zippin_create_label_view = True
        self.order_id.zippin_delete_shipping_view = True

    #Borra la informacion de envio cuando aun no se generó la etiqueta de envio.
    def delete_zippin_info(self):
        if self.order_id.zippin_shipping_id:
            raise ValidationError('No se puede borrar o actualizar un envío ya creado, primero cancele el envio.')
        else:
            self.delete_zippin_shipping()

    #Modifico la funcion unlink para que borre sucursales e informacion de envio en sale.order
    def unlink(self):
        for line in self:
            if line.is_delivery:
                self.delete_pickup_points()
                self.delete_zippin_info()
        res = super(SaleOrderLine, self).unlink()
        return res