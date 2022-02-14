{
    'name': "TRISMART Project Template Improvement",
    'summary': "Improve the current OCA project template",
    'description': """
        Add Project Template menu in Configuration
        Hide the project template in the Kanban view by default
        Set project template default and let user set it in Project settings menu
""",
    'author': "Novobi LLC",
    'category': '',
    'version': '15.0.0',
    'depends': [
                'project',
                'project_template',
                ],
    'data': [
        'views/project_views.xml',
        'views/res_config_settings_views.xml',
    ],
    'demo': [],
    # 'application': False,
    'installable': True,
    # 'auto_install': False,

    'license': 'LGPL-3',
}

