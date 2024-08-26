from odoo import models, fields, api
from odoo.exceptions import ValidationError
from odoo.addons.zippin.models.delivery_carrier import ID_CORREO_ARGENTINO, ID_OCA, ID_ANDREANI, APIURL, ID_PICKUP_DELIVERY, ID_STANDARD_DELIVERY
from requests.structures import CaseInsensitiveDict
import requests, base64
from datetime import date, datetime

import logging
_logger = logging.getLogger(__name__)

class DeliveryCarrier(models.Model):
    _inherit = 'delivery.carrier'

    is_free = fields.Boolean('Es gratis?')
    # zippin_estimated_delivery = fields.Datetime(string='Entrega estimada')


    def zippin_send_shipping(self, pickings):
        res = []
        for p in pickings:
            res = res + [{'exact_price': 0, 'tracking_number': False}]
        return res



    def _get_product_list(self,bom,r,qty):
        for bom_line in bom.bom_line_ids:
            if (bom_line.product_id.weight == False \
                or bom_line.product_id.product_height == False \
                or bom_line.product_id.product_width == False \
                or bom_line.product_id.product_length == False) \
                and not bom_line.product_id.bom_ids:
                raise ValidationError('#3 Error: El producto ' + bom_line.product_id.name + ' debe tener peso y tamaño asignados.')
            if not bom_line.product_id.bom_ids:
                if bom_line.product_id.type == 'product':
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



    def _zippin_prepare_items(self,order):
        if order.order_line:
            r = []
            for p in order.order_line:
                if not p.product_id.bom_ids:
                    if p.product_id.type == 'product' and (p.product_id.weight == False \
                            or p.product_id.product_height == False \
                            or p.product_id.product_width == False \
                            or p.product_id.product_length == False):
                        raise ValidationError('#4 Error: El producto ' + p.product_id.name + ' debe tener peso y tamaño asignados.')

                    for i in range(int(p.product_uom_qty)):
                        if p.product_id.type == 'product':
                            product_list = {
                              "weight": p.product_id.weight * 1000,
                              "height": p.product_id.product_height,
                              "width": p.product_id.product_width,
                              "length": p.product_id.product_length,
                              "description": p.product_id.name,
                              "classification_id": 1
                            }
                            r.append(product_list)
                else:
                    for bom in p.product_id.bom_ids[0]:
                        r = self._get_product_list(bom,r,p.product_uom_qty)
        return(r)



    def zippin_rate_shipment(self, order):

        url = APIURL + "/shipments/quote"
        #VALOR DECLARADO EN CERO SI NO SE PONE SEGURO AL ENVIO
        if order.company_id.zippin_key == False or order.company_id.zippin_id == False or order.company_id.zippin_secret == False:
            raise ValidationError('Debe ingresar las credenciales de Zippin en ajustes de la Empresa')

        data = {
            "account_id": order.company_id.zippin_id,
            "origin_id": self._zippin_get_origen_id(order),
            "declared_value": 0,
        }

        data["items"] = self._zippin_prepare_items(order)

        data["destination"]= self._zippin_to_shipping_data(order)

        r = requests.post(url, headers=self._zippin_api_headers(order), json=data)

        vals_log = {
            'order_id': order.id,
            'dt_llamada': str(datetime.now())[:16],
            'llamada': 'quote',
            'request': str(data),
            'response': r.text,
        }
        response = r.json()
        _logger.error('\n\n'.join([f'{key} ==> {response[key]}' for key in response]))
        log_id = self.env['zippin.log'].create(vals_log)
        self.env.cr.commit()

        if r.status_code == 200:
            shipment_price = 0
            r= r.json()
            pickup_res = []
            pickup_address = ''
            logistic_type = ''

            shipment_price = 99999999
            shipment_type = 208
            estimated_delivery = ''
            
            for i in r["all_results"]:
                
                # Hito_Ale: refactorizamos esta sección para que no tenga en cuenta shipping_type y obtenga el valor mas ba jo
                # de amounts->price de cada carriers informado en el response de la API de zippin
                                
                if self.zippin_shipment_type_is_pickup:
                    if i["service_type"]["id"] == ID_PICKUP_DELIVERY:# (i["carrier"]["id"] == int(self.zippin_shipment_type) or True) and 
                        if i["amounts"]["price"] < shipment_price and i["amounts"]["price"] > 0:
                            shipment_price = i["amounts"]["price"]
                            logistic_type = i["logistic_type"]
                            shipment_type = i["carrier"]["id"]
                            estimated_delivery = i['delivery_time']['estimated_delivery']
                            # raise ValidationError('ID_PICKUP_DELIVERY ' + str(i['delivery_time']['estimated_delivery']))
                # else:
                if i["service_type"]["id"] == ID_STANDARD_DELIVERY: #(i["carrier"]["id"] == int(self.zippin_shipment_type) or True) and 
                    if i["amounts"]["price"] < shipment_price and i["amounts"]["price"] > 0:
                        shipment_price = i["amounts"]["price"]
                        logistic_type = i["logistic_type"]
                        shipment_type = i["carrier"]["id"]
                        estimated_delivery = i['delivery_time']['estimated_delivery']
                        # raise ValidationError('ID_STANDARD_DELIVERY ' + str(i['delivery_time']['estimated_delivery']))
                            

                if i["service_type"]["id"] == ID_PICKUP_DELIVERY:
                    for f in i["pickup_points"]:
                        pickup_points = {
                            "order_id": order.id,
                            "carrier_id": i["carrier"]["id"],
                            "point_id": f["point_id"],
                            "name": f["description"],
                            "address": f["location"]["street"] + ' ' + f["location"]["street_number"] + ' ' + f["location"]["city"] + ' ' + f["location"]["state"],
                            "logistic_type": i["logistic_type"]
                        }
                        pickup_res.append(pickup_points)
            return {
                'success': True,
                'price': shipment_price,
                'zippin_pickup': pickup_res,
                'logistic_type': logistic_type,
                'error_message': False,
                'warning_message': False,
                'shipment_type': shipment_type,
                'zippin_estimated_delivery': estimated_delivery
            }

        elif r.status_code == 408:
            return {
                'success': False,
                'price': 0,
                'error_message': 'Error. La solicitud está tomando demasiado tiempo en procesarse, intente nuevamente.',
                'warning_message': False
            }
        elif r.status_code == 500:
            return {
                'success': False,
                'price': 0,
                'error_message': 'Error interno. Intente nuevamente.',
                'warning_message': False
            }
        elif r.status_code == 503:
            return {
                'success': False,
                'price': 0,
                'error_message': 'Error interno. El servidor se encuentra saturado, espere unos minutos y vuelva a intentarlo.',
                'warning_message': False
            }
        else:
            data = r.json()
            _logger.error(str(data))
            return {
                'success': False,
                'price': 0,
                'error_message': 'No disponible, revisar el log',
                'warning_message': False
            }



    def _zippin_api_headers(self, order):

        headers = CaseInsensitiveDict()
        headers["Content-Type"] = "application/json"
        headers["Accept"] = "application/json"
        
        zippin_auth = "%s:%s" % (order.company_id.zippin_key, order.company_id.zippin_secret)
        zippin_auth = base64.b64encode(zippin_auth.encode("utf-8")).decode("utf-8")

        headers["Authorization"] = "Basic " + zippin_auth

        return(headers)




    def _zippin_get_origen_id(self, order):

        url = APIURL + "/addresses?account_id=" + order.company_id.zippin_id

        r = requests.get(url, headers=self._zippin_api_headers(order))

        if r.status_code == 403:
            raise ValidationError('Zippin: Error de autorización, revise sus credenciales.')
        else:
            r = r.json()
            for i in r["data"]:
                if i["id"]:
                   resp = i["id"]
            return(resp)



    def _zippin_to_shipping_data(self, order):

        if order.partner_shipping_id.city == False:
            raise ValidationError('¡El Cliente debe tener Ciudad!')
        elif order.partner_shipping_id.state_id.name == False:
            raise ValidationError('¡El Cliente debe tener Estado/Provincia!')
        elif order.partner_shipping_id.zip == False:
            raise ValidationError('¡El Cliente debe tener Codigo Postal!')
        elif order.partner_shipping_id.street == False:
            raise ValidationError('¡El Cliente debe tener una calle!')
        elif order.partner_shipping_id.street2 == False:
            raise ValidationError('¡El Cliente debe tener un número de calle!')
        else:
            zp_phone = ''
            if order.partner_shipping_id.phone:
                zp_phone = zp_phone + order.partner_shipping_id.phone
            elif order.partner_shipping_id.mobile:
                zp_phone = ' - ' + order.partner_shipping_id.mobile
            r = {
                "city": order.partner_shipping_id.city,
                "state": order.partner_shipping_id.state_id.name,
                "zipcode": order.partner_shipping_id.zip,
                "name": order.partner_shipping_id.name,
                "document": order.partner_shipping_id.vat,
                "street": order.partner_shipping_id.street,
                "street_number": order.partner_shipping_id.street2,
                "street_extras": '',
                "phone": zp_phone,
                "email": order.partner_shipping_id.email,
            }
        return(r)
