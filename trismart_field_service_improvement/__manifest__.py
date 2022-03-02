{
    'name': "TRISMART Field Service Improvement",
    'summary': "Improve the current Field Service app",
    'description': """
        Show all project created in field service project menu
        Allow to show field service tasks from non-field service project
    """,
    'author': "Novobi LLC",
    'category': '',
    'version': '15.0.0',
    'depends': [
                'project',
                'industry_fsm',
                ],
    'data': [
        'views/fsm_views.xml',
        'views/project_views.xml',
    ],
    'demo': [],
    # 'application': False,
    'installable': True,
    # 'auto_install': False,

    'license': 'LGPL-3',
}
