# -*- coding: utf-8 -*-
{
    'name': "Envíos Zippin",

    'summary': """
        permite hacer envíos y consultar tarifas desde los presupuestos en odoo""", 

    'description': """
        para instalar el módulo debe agregar el repositorio 
        https://github.com/OCA/product-attribute.git rama 16.0
    
        1) para instalar el modulo debe crear una cuenta en zippin
        2) crear las credenciales en la cuenta de zippin
        3) agregar las credenciales en odoo
    """,

    'author': "hitofusion",
    'website': "https://www.hitofusion.com",
    'category': 'Sales',

    'version': '16.0.1.2.6',
    'depends': [
        'base', 
        'account',
        'sale',
        'stock',
        'delivery',
        'product_dimension',
        'website_sale',
        'l10n_ar'
        ],
    
    'data': [
        'data/zippin_data.xml',
        'security/ir.model.access.csv',
        'views/res_company.xml',
        'views/sale_view.xml',
        'views/website_sale_delivery_templates.xml',
        'views/account_move_view.xml',
        'views/stock_picking_view.xml',
        'views/zippin_pickup_views.xml',
        'wizard/choose_delivery_carrier_form_view.xml',
        'reports/estimated_delivery_report.xml',
        'views/website_sale_view.xml',
        'views/view_product_variant_easy_edit.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'zippin/static/src/js/zippin_odoo.js',
            'zippin/static/src/scss/zippin_odoo.scss'
        ],
    },
}
