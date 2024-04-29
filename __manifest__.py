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
    'version': '0.1',

    'depends': ['zippin','delivery'],

    'data': [
        'security/ir.model.access.csv',
        'views/sale_view.xml',
    ],
    'assets': {
    },
}
