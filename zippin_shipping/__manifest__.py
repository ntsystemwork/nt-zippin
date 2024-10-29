# -*- coding: utf-8 -*-
{
    'name': "NT Zippin Odoo Connector",

    'summary': """
        Connector Odoo-Zippin for Shipping Payment""",

    'description': """
        Connector Odoo-Zippin for Shipping Payment
    """,

    'author': "hitofusion",
    'website': "https://www.hitofusion.com",
    'category': 'Sales',

    'version': '16.0.1.2.5',
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

    # 'data': [
    #     'wizard/choose_delivery_carrier_form_view.xml', XXXXXXXX
    #     'security/ir.model.access.csv', xxxxxxx
    #     'data/zippin_data.xml', xxxxxxx
    
    #     'views/sale_view.xml',
    
    #     'views/account_move_view.xml',
    #     'views/stock_picking_view.xml',
    #     'reports/estimated_delivery_report.xml',
    #     'views/website_sale_view.xml',
    # ],
    
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
            #'zippin/static/src/scss/zippin_odoo.scss'
        ],
    },
}
