import re
from odoo import models, fields, api

class ResCompany(models.Model):
    _inherit = 'res.company'

    zippin_id = fields.Char(string='Account ID', help='Ingresar Zippin Account ID. Obligatorio.')
    zippin_description_web = fields.Char(string='Descripcion Web', help='Identificador para los envios de Zippin', Default="Zippin")
    zippin_key = fields.Char(string='Zippin Key', help='Ingresar Zippin Key. Obligatorio')
    zippin_secret = fields.Char(string='Zippin Secret', help='Ingresar Zippin Secret. Obligatorio.')
    

    def replace_characters(self, string, char):
        # Reemplaza cualquier secuencia de uno o más espacios en blanco con el carácter una sola vez
        return re.sub(r'\s+', char, string)
    
    
    @api.onchange('zippin_description_web', 'zippin_id', 'zippin_key', 'zippin_secret')
    def zippin_get_description_web(self):
        self.ensure_one()
        for company in self:
            if company.zippin_description_web:
                company.zippin_description_web = self.replace_characters(company.zippin_description_web, '-')
                company.zippin_id = self.replace_characters(company.zippin_id, '')
                company.zippin_key = self.replace_characters(company.zippin_key, '')
                company.zippin_secret = self.replace_characters(company.zippin_secret, '')

                
