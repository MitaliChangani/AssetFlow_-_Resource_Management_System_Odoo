{
    'name': 'Asset & Resource Management',
    'version': '19.0.1.0.0',
    'category': 'Inventory/Inventory',
    'summary': 'Internal Asset & Resource Management System',
    'description': """
        Manage company assets, allocations, transfers, resource bookings,
        maintenance requests, and audits with role-based access control.
    """,
    'author': 'AssetFlow',
    'website': '',
    'license': 'LGPL-3',
    'depends': ['base', 'mail'],
    'data': [
        'views/allocation_views.xml',
        'views/asset_views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
