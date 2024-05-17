from odoo import models, fields, api
from odoo.exceptions import ValidationError
from odoo.addons.zippin.models.delivery_carrier import ID_CORREO_ARGENTINO, ID_OCA, ID_ANDREANI, APIURL
from requests.structures import CaseInsensitiveDict
import requests, base64
from datetime import datetime

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    zippin_log_ids = fields.One2many(comodel_name='zippin.log',inverse_name='order_id',string='Logs')
    zippin_estimated_delivery_time = fields.Char('Fecha de entrega estimada Zippin',copy= False)

    zippin_pickup_order_id = fields.Char(string="ID Orden",copy=False)
    zippin_pickup_carrier_id = fields.Char(string="ID Proveedor",copy=False)
    zippin_pickup_is_pickup = fields.Boolean(string="¿Es envio a Sucursal?",copy=False)
    zippin_pickup_point_id = fields.Char(string="ID Sucursal",copy=False)
    zippin_pickup_name = fields.Char(string="Nombre/Descripcion",copy=False)
    zippin_pickup_address = fields.Char(string="Direccion",copy=False)
    zippin_logistic_type = fields.Char(copy=False)

    zippin_shipping_id = fields.Char(copy=False)
    zippin_shipping_delivery_id = fields.Char(copy=False)
    zippin_shipping_carrier_tracking_id = fields.Char(copy=False)
    zippin_shipping_carrier_tracking_id_alt = fields.Char(copy=False)
    zippin_shipping_tracking = fields.Char(copy=False)
    zippin_shipping_tracking_external = fields.Char(copy=False)
    zippin_create_shipping_view = fields.Boolean(default='True',copy=False)
    zippin_create_label_view = fields.Boolean(default='True',copy=False)
    zippin_shipping_label_bin = fields.Binary(copy=False)
    zippin_shipping_label_filename = fields.Char(compute='_compute_shipping_label_filename')

    def _prepare_invoice(self):
        res = super(SaleOrder, self)._prepare_invoice()
        if self.zippin_shipping_tracking_external:
            res['zippin_shipping_tracking_external'] = self.zippin_shipping_tracking_external
        return res

    def _get_product_list(self,bom,r,qty):
        for bom_line in bom.bom_line_ids:
            if (bom_line.product_id.weight == False \
                or bom_line.product_id.product_height == False \
                or bom_line.product_id.product_width == False \
                or bom_line.product_id.product_length == False) \
                and bom_line.product_id.type == 'product' \
                and not bom_line.product_id.bom_ids:
                raise ValidationError('#5 Error: El producto ' + bom_line.product_id.name + ' debe tener peso y tamaño asignados.')
            if not bom_line.product_id.bom_ids:
                for i in range(int(qty * bom_line.product_qty)):
                    product_list = {
                        "weight": bom_line.product_id.weight * 1000,
                        "height": bom_line.product_id.product_height,
                        "width": bom_line.product_id.product_width,
                        "length": bom_line.product_id.product_length,
                        "description": bom_line.product_id.name,
                        "classification_id": 1
                        }
                    r.append(product_list)
            elif bom_line.product_id.bom_ids[0].type == 'normal':
                for i in range(int(qty * bom_line.product_qty)):
                    product_list = {
                        "weight": bom_line.product_id.weight * 1000,
                        "height": bom_line.product_id.product_height,
                        "width": bom_line.product_id.product_width,
                        "length": bom_line.product_id.product_length,
                        "description": bom_line.product_id.name,
                        "classification_id": 1
                        }
                    r.append(product_list)
            #else:
            #    bom = bom_line.product_id.bom_ids[0]
            #    if bom.type == 'phantom':
            #        qty = qty * bom_line.product_qty
            #        r = self._get_product_list(bom,r,qty)
        return r

    def _zippin_prepare_items(self):
        if self.order_line:
            r = []
            for p in self.order_line:
                if not p.product_id.bom_ids and (p.product_id.type == 'product'):
                    if p.product_id.weight == False \
                            or p.product_id.product_height == False \
                            or p.product_id.product_width == False \
                            or p.product_id.product_length == False:
                        raise ValidationError('#6 Error: El producto ' + p.product_id.name + ' debe tener peso y tamaño asignados.')

                    for i in range(int(p.product_uom_qty)):
                        product_list = {
                          "weight": p.product_id.weight * 1000,
                          "height": p.product_id.product_height,
                          "width": p.product_id.product_width,
                          "length": p.product_id.product_length,
                          "description": p.product_id.name,
                          "classification_id": 1
                        }
                        r.append(product_list)
                elif p.product_id.bom_ids:
                    for bom in p.product_id.bom_ids[0]:
                        r = self._get_product_list(bom,r,p.product_uom_qty)
        return(r)



    def action_zippin_create_shipping(self):

        url = APIURL + "/shipments"

        #VALOR DECLARADO EN CERO SI NO SE PONE SEGURO AL ENVIO
        if self.company_id.zippin_key == False or self.company_id.zippin_id == False or self.company_id.zippin_secret == False:
            raise ValidationError('Debe ingresar las credenciales de Zippin en ajustes de la Empresa')

        service_type = 'standard_delivery'
        if self.zippin_pickup_is_pickup:
            service_type = 'pickup_point'

        data = {
                #"external_id": str(self.company_id.zippin_description_web)+'-NT-'+str(self.id),
            "external_id": str(self.company_id.zippin_description_web)+'NT'+str(self.id),
            "account_id": self.company_id.zippin_id,
            "origin_id": self._zippin_get_origen_id(),
            "service_type": service_type,
            "logistic_type": self.zippin_logistic_type,
            "carrier_id": self.zippin_pickup_carrier_id,
            "declared_value": 0,
        }

        data["items"] = self._zippin_prepare_items()

        data["destination"]= self._zippin_to_shipping_data()
        r = requests.post(url, headers=self._zippin_api_headers(), json=data)

        vals_log = {
            'order_id': self.id,
            'dt_llamada': str(datetime.now())[:16],
            'llamada': 'shipments',
            'request': str(data),
            'response': r.text,
        }
        log_id = self.env['zippin.log'].create(vals_log)
        self.env.cr.commit()

        if r.status_code < 400:
            
            r= r.json()

            self.zippin_shipping_id = r["id"]
            self.zippin_shipping_delivery_id = r["delivery_id"]
            self.zippin_shipping_carrier_tracking_id = r["carrier_tracking_id"]
            self.zippin_shipping_carrier_tracking_id_alt = r["carrier_tracking_id_alt"]
            self.zippin_shipping_tracking = r["tracking"]
            self.zippin_shipping_tracking_external = r["tracking_external"]
            self.zippin_create_shipping_view = True
            self.zippin_create_label_view = False
            self.zippin_delete_shipping_view = False
            self.zippin_estimated_delivery_time = r.get('delivery_time') and r.get('delivery_time').get('estimated_delivery','')[:10] or ''

        else:
            r= r.json()
            raise ValidationError('Zippin Error: ' +r["message"]+'\n %s'%(r.get('error')))



    def action_zippin_get_label(self):
        if not self.zippin_shipping_id:
            raise ValidationError('Debe generar el envio de Zippin')
        url = APIURL + "/shipments/" + self.zippin_shipping_id +"/documentation?what=label&format=pdf"
        #url = APIURL + "/shipments/577722/documentation?what=label&format=pdf"

        r = requests.get(url, headers=self._zippin_api_headers())
        vals_log = {
            'order_id': self.id,
            'dt_llamada': str(datetime.now())[:16],
            'llamada': 'shipments',
            'request': str(url),
            'response': r.text,
        }
        log_id = self.env['zippin.log'].create(vals_log)
        self.env.cr.commit()

        if r.status_code == 403:
            raise ValidationError('Zippin: Error de autorización, revise sus credenciales.')
        else:
            r = r.json()
            if 'body' in r:
                self.zippin_shipping_label_bin = r["body"]
                self.zippin_create_label_view = True
            else:
                raise ValidationError('La etiqueta no esta disponible aun. Intente en un momento')



    def write(self, vals):
        res = super(SaleOrder, self).write(vals)
        for rec in self:
            if rec.team_id.id == self.env.ref('sales_team.salesteam_website_sales').id and rec.state == 'sent':
                if rec.zippin_pickup_order_id and not rec.zippin_shipping_id:
                    for order_line in rec.order_line:
                        if order_line.product_id.type == 'service':
                            carrier = self.env['delivery.carrier'].search([('product_id','=',order_line.product_id.id)])
                            if carrier:
                                order = order_line.order_id
                                order.action_zippin_create_shipping()
        return res

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
            if res.product_id.property_account_income_id.id != self.env.ref('l10n_ar.1_base_prevision_gastos').id:
                raise ValidationError('Cuenta de Zippin mal configurada')
            vals_line = {
                    'order_id': vals.get('order_id'),
                    'product_id': self.env.ref('nt-zippin.zippin_delivery_refund').id,
                    'name': self.env.ref('nt-zippin.zippin_delivery_refund').name,
                    'price_unit': vals.get('price_unit') * (-1),
                    'product_uom_qty': 1,
                    'product_uom': self.env.ref('nt-zippin.zippin_delivery_refund').uom_id.id,
                    }
            result = super(SaleOrderLine, self).create(vals_line)
        return res
