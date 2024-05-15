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
    'version': '16.0.4',
    'depends': ['zippin','delivery','account','stock','base'],
    'data': [
        'security/ir.model.access.csv',
        'views/sale_view.xml',
        'views/account_move_view.xml',
        'views/stock_picking_view.xml',
    ],
    'assets': {
    },
}
