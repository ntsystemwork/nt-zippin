from odoo import models, fields, api
from odoo.exceptions import ValidationError
from odoo.addons.zippin.models.delivery_carrier import ID_CORREO_ARGENTINO, ID_OCA, ID_ANDREANI, APIURL, ID_PICKUP_DELIVERY, ID_STANDARD_DELIVERY
from requests.structures import CaseInsensitiveDict
import requests, base64
from datetime import date,datetime

class DeliveryCarrier(models.Model):
    _inherit = 'delivery.carrier'

    is_free = fields.Boolean('Es gratis?')

    def zippin_send_shipping(self, pickings):
        res = []
        for p in pickings:
            res = res + [{'exact_price': 0,
                          'tracking_number': False}]
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
        log_id = self.env['zippin.log'].create(vals_log)
        self.env.cr.commit()

        if r.status_code == 200:
            shipment_price = 0
            r= r.json()
            pickup_res = []
            pickup_address = ''
            logistic_type = ''

            for i in r["all_results"]:
                if self.zippin_shipment_type_is_pickup:
                    if i["carrier"]["id"] == int(self.zippin_shipment_type) and i["service_type"]["id"] == ID_PICKUP_DELIVERY:
                        shipment_price = i["amounts"]["price"]
                        logistic_type = i["logistic_type"]
                else:
                    if i["carrier"]["id"] == int(self.zippin_shipment_type) and i["service_type"]["id"] == ID_STANDARD_DELIVERY:
                        shipment_price = i["amounts"]["price"]
                        logistic_type = i["logistic_type"]

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
                'warning_message': False
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
            return {
                'success': False,
                'price': 0,
                'error_message': 'No disponible',
                'warning_message': False
            }
