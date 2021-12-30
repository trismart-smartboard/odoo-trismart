{
    'name': "TM Survey Layout Customization",
    'summary': "Customize Survey Layout",
    'description': """
        Change the layout of survey in Survey app
""",
    'author': "Novobi LLC",
    'category': '',
    'version': '15.0.0',
    'depends': [
                'base',
                'survey',
                ],
    'data': [
        'views/custom_scss.xml',
    ],
    'demo': [],
    # 'application': False,
    'installable': True,
    # 'auto_install': False,

    'assets': {
        'survey.survey_assets': [
            'TM_survey_layout_customization/static/src/scss/survey_templates_form_custom.scss',
        ],
    },
    'license': 'LGPL-3',
}
