# -*- coding: utf-8 -*-
{
    'name': "NT Zippin Odoo Connector",

    'summary': """
        Connector Odoo-Zippin for Shipping Payment""",

    'description': """
        Connector Odoo-Zippin for Shipping Payment
    """,

    'author': "InfotecLaPlata",
    'website': "https://www.InfotecLaPlata.com.ar",
    'category': 'Sales',
    'version': '16.0.1.2.5',
    'depends': ['zippin','delivery','account','stock','base','l10n_ar'],
    'data': [
        'data/zippin_data.xml',
        'security/ir.model.access.csv',
        'views/sale_view.xml',
        'views/account_move_view.xml',
        'views/stock_picking_view.xml',
        'wizard/choose_delivery_carrier_form_view.xml',
        'reports/estimated_delivery_report.xml',
        'views/website_sale_view.xml',
    ],
    'assets': {
    },
}
