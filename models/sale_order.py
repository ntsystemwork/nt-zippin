import re
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from odoo.addons.zippin.models.delivery_carrier import ID_CORREO_ARGENTINO, ID_OCA, ID_ANDREANI, APIURL
from requests.structures import CaseInsensitiveDict
import requests, base64
from datetime import date, datetime, timedelta

import math


import logging
_logger = logging.getLogger(__name__)

# TODO:
# 1- agregar un campo de ultima fecha consultada en el sale.order
# 2- utilizar la fecha antes mencionada del sale.order para validar que la fecha de entrega está actualizada,
#de lo contrario debe lanzarse una ventana solicitanto actualizar la fecha de entrega
# 3- si los campos de las fechas de entrega están vacíos, debe lanzarse una ventana para solicitar la fecha de entrega
#
#


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

    # zippin_estimated_delivery = fields.Date(string='Entrega estimada')

    zippin_min_date = fields.Date(string='Entrega estimada mínima', tracking=True)
    zippin_max_date = fields.Date(string='Entrega estimada máxima', tracking=True)
    zippin_latest_shipping_query = fields.Date(string='Última consulta de envío')



    def add_days_to_current_date(self, days_to_add):
        current_date = datetime.now()
        new_date = current_date + timedelta(days=days_to_add)
        return str(new_date)



    def _check_carrier_quotation(self, force_carrier_id=None, keep_carrier=False):
        res = super(SaleOrder, self)._check_carrier_quotation(force_carrier_id=None,keep_carrier=keep_carrier)

        zp_DeliveryCarrier = self.env['delivery.carrier']
        if self.only_services == False:
            zp_carrier = force_carrier_id and zp_DeliveryCarrier.browse(force_carrier_id) or self.carrier_id
            if zp_carrier:
                zp_res = zp_carrier.rate_shipment(self)
                if zp_res.get('success'):
                    self.env['zippin.shipping'].search([]).unlink()
                    self.set_delivery_line(zp_carrier, zp_res['price'])
                    self.delivery_rating_success = True
                    if self.carrier_id.zippin_shipment_type:
                        self.env['zippin.shipping'].create(zp_res['zippin_pickup'])
                        self.zippin_logistic_type = zp_res['logistic_type']
                    self.delivery_message = zp_res['warning_message']
                    self.zippin_pickup_order_id = self._origin.id
                    self.zippin_pickup_carrier_id = self.carrier_id.zippin_shipment_type
                    if self.carrier_id.zippin_shipment_type_is_pickup:
                        self.zippin_pickup_is_pickup = True
                    else:
                        self.zippin_pickup_is_pickup = False
        return res



    @api.depends('zippin_shipping_label_bin')
    def _compute_shipping_label_filename(self):
        self.ensure_one()
        name = ''
        if self.zippin_shipping_id:
            name = self.zippin_shipping_id
        name = name.replace('/', '_')
        name = name.replace('.', '_')
        name = name + '.pdf'
        self.zippin_shipping_label_filename = name



    def action_open_delivery_wizard(self):
        for rec in self:
            if rec.state not in ['draft','sent']:
                raise ValidationError('Accion deshabilitada para el estado %s'%(rec.state))
        return super(SaleOrder, self).action_open_delivery_wizard()



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
                        "weight": math.ceil(bom_line.product_id.weight * 1000),
                        "height": math.ceil(bom_line.product_id.product_height),
                        "width": math.ceil(bom_line.product_id.product_width),
                        "length": math.ceil(bom_line.product_id.product_length),
                        "description": bom_line.product_id.name,
                        "classification_id": 1
                        }
                    r.append(product_list)
            elif bom_line.product_id.bom_ids[0].type == 'normal':
                for i in range(int(qty * bom_line.product_qty)):
                    product_list = {
                        "weight": math.ceil(bom_line.product_id.weight * 1000),
                        "height": math.ceil(bom_line.product_id.product_height),
                        "width": math.ceil(bom_line.product_id.product_width),
                        "length": math.ceil(bom_line.product_id.product_length),
                        "description": bom_line.product_id.name,
                        "classification_id": 1
                        }
                    r.append(product_list)
            else:
                raise ValidationError('_get_product_list')
            #else:
            #    bom = bom_line.product_id.bom_ids[0]
            #    if bom.type == 'phantom':
            #        qty = qty * bom_line.product_qty
            #        r = self._get_product_list(bom,r,qty)
        return r



    def _zippin_prepare_items(self):
        r = []
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
                          "weight": math.ceil(p.product_id.weight * 1000),
                          "height": math.ceil(p.product_id.product_height),
                          "width": math.ceil(p.product_id.product_width),
                          "length": math.ceil(p.product_id.product_length),
                          "description": p.product_id.name,
                          "classification_id": 1
                        }
                        r.append(product_list)
                elif p.product_id.bom_ids:
                    for bom in p.product_id.bom_ids[0]:
                        r = self._get_product_list(bom,r,p.product_uom_qty)
        return(r)



    def _zippin_api_headers(self):
        headers = CaseInsensitiveDict()
        headers["Content-Type"] = "application/json"
        headers["Accept"] = "application/json"

        zippin_auth = "%s:%s" % (self.company_id.zippin_key, self.company_id.zippin_secret)
        zippin_auth = base64.b64encode(zippin_auth.encode("utf-8")).decode("utf-8")

        headers["Authorization"] = "Basic " + zippin_auth

        return(headers)



    def _zippin_get_origen_id(self):

        url = APIURL + "/addresses?account_id=" + self.company_id.zippin_id

        r = requests.get(url, headers=self._zippin_api_headers())

        if r.status_code == 403:
            raise ValidationError('Zippin: Error de autorización, revise sus credenciales.')
        else:
            r = r.json()
            for i in r["data"]:
                if i["id"]:
                   resp = i["id"]
            return(resp)



    def extract_street_and_number(self, address):
        if address in (False, None, ''):
            return False
        regex = r'^([A-Za-zÀ-ÖØ-öø-ÿ\s\d]+?)\s(\d{1,5})\b'
        match = re.match(regex, address)
        if match:
            return match.group(1).strip(), match.group(2)
        return False



    def _zippin_to_shipping_data(self):
        if self.partner_shipping_id.city == False:
            raise ValidationError('¡El Cliente debe tener Ciudad!')
        elif self.partner_shipping_id.state_id.name == False:
            raise ValidationError('¡El Cliente debe tener Estado/Provincia!')
        elif self.partner_shipping_id.zip == False:
            raise ValidationError('¡El Cliente debe tener Codigo Postal!')
        elif self.partner_shipping_id.street in (False, None, ''):
            raise ValidationError('¡Los campos calle en el contacto y la direccion de envío no pueden estár vacíos!')
        else:
            zp_phone = ''
            if self.partner_shipping_id.phone:
                zp_phone = zp_phone + self.partner_shipping_id.phone
            elif self.partner_shipping_id.mobile:
                zp_phone = ' - ' + self.partner_shipping_id.mobile

            if self.zippin_pickup_is_pickup:
                r = {
                    "name": self.partner_shipping_id.name,
                    "document": self.partner_shipping_id.vat,
                    "phone": zp_phone,
                    "email": self.partner_shipping_id.email,
                    "point_id": int(self.zippin_pickup_point_id),
                }
            else:
                home_address = self.extract_street_and_number(self.partner_shipping_id.street)
                
                if home_address == False:
                    raise ValidationError('El campo calle del contacto o la dirección de envio no tienen el formato correcto, se espera que el destino sea del siguiente formato "calle número"')
                
                street_name, street_number = home_address
                    
                r = {
                    "city": self.partner_shipping_id.city,
                    "state": self.partner_shipping_id.state_id.name,
                    "zipcode": self.partner_shipping_id.zip,
                    "name": self.partner_shipping_id.name,
                    "document": self.partner_shipping_id.vat,
                    # "street": self.partner_shipping_id.street,
                    # "street_number": self.partner_shipping_id.street2,
                    "street": str(street_name),
                    "street_number": str(street_number),
                    "street_extras": '',
                    "phone": zp_phone,
                    "email": self.partner_shipping_id.email,
                }
        return(r)



    def action_zippin_create_shipping(self):
        if self.zippin_latest_shipping_query:
            if date.today() > self.zippin_latest_shipping_query:
                raise ValidationError('Debe actualizar la fecha de entrega fecha de entrega para el envío')
        url = APIURL + "/shipments"

        #VALOR DECLARADO EN CERO SI NO SE PONE SEGURO AL ENVIO
        if self.company_id.zippin_key == False or self.company_id.zippin_id == False or self.company_id.zippin_secret == False:
            raise ValidationError('Debe ingresar las credenciales de Zippin en ajustes de la Empresa')

        service_type = 'standard_delivery'
        if self.zippin_pickup_is_pickup:
            service_type = 'pickup_point'

        data = {
                #"external_id": str(self.company_id.zippin_description_web)+'-NT-'+str(self.id),
            "external_id": str(self.company_id.zippin_description_web)+'NT'+str(self.id),#no debe contener espacios
            "account_id": self.company_id.zippin_id,
            "origin_id": self._zippin_get_origen_id(),
            "service_type": service_type,
            "logistic_type": self.zippin_logistic_type,
            "carrier_id": self.zippin_pickup_carrier_id,
            "declared_value": 0,
        }

        data["items"] = self._zippin_prepare_items()
        # raise ValidationError(str( data["items"] ))

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
            r = r.json()
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



    def action_zippin_delete_shipping(self):

        url = APIURL + "/shipments/" + self.zippin_shipping_id +"/cancel"
        r = requests.post(url, headers=self._zippin_api_headers())

        if r.status_code == 200:
            r = r.json()
            self.delete_zippin_shipping()
        elif r.status_code == 401:
            raise ValidationError('Zippin: Error, no se pudo cancelar el envío')
        else:
            raise ValidationError(r.status_code)



    def delete_zippin_shipping(self):
        self.zippin_shipping_label_bin = None
        self.zippin_pickup_order_id = None
        self.zippin_pickup_carrier_id = None
        self.zippin_pickup_is_pickup = None
        self.zippin_pickup_point_id = None 
        self.zippin_pickup_name = None 
        self.zippin_pickup_address = None 
        self.zippin_logistic_type = None 
        self.zippin_shipping_id = None 
        self.zippin_shipping_delivery_id = None 
        self.zippin_shipping_carrier_tracking_id = None 
        self.zippin_shipping_carrier_tracking_id_alt = None 
        self.zippin_shipping_tracking = None 
        self.zippin_shipping_tracking_external = None 
        self.zippin_create_shipping_view = True
        self.zippin_create_label_view = True
        self.zippin_delete_shipping_view = True



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



    @api.onchange('commitment_date', 'zippin_min_date', 'zippin_max_date')
    def update_dates(self):
        self.ensure_one()
        for rec in self:
            # Asegúrate de que rec.commitment_date sea datetime.date o datetime.datetime
            if isinstance(rec.commitment_date, datetime):
                commitment_date = rec.commitment_date.date()
            else:
                commitment_date = rec.commitment_date
            
            if isinstance(rec.zippin_min_date, datetime):
                zippin_min_date = rec.zippin_min_date.date()
            else:
                zippin_min_date = rec.zippin_min_date
            
            if isinstance(rec.zippin_max_date, datetime):
                zippin_max_date = rec.zippin_max_date.date()
            else:
                zippin_max_date = rec.zippin_max_date

            if zippin_min_date and zippin_max_date:
                if zippin_min_date > zippin_max_date:
                    raise ValidationError(_('La fecha de entrega estimada mínima debe ser menor o igual a la fecha de entrega estimada máxima'))

            if commitment_date and zippin_max_date:
                if commitment_date > zippin_max_date:
                    raise ValidationError(_('La fecha de entrega debe ser menor o igual a la fecha de entrega estimada máxima'))



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




