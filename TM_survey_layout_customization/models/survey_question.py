from odoo import api, fields, models, tools, _


class SurveyQuestion(models.Model):
    _inherit = 'survey.question'

    column_nb = fields.Selection([
        ('12', '1'), ('6', '2'), ('4', '3'), ('3', '4'), ('2', '6'), ('1', '12')],
        string='Number of columns', default='12',
        help='These options refer to col-xx-[12|6|4|3|2|1] classes in Bootstrap for dropdown-based simple and multiple choice questions.')

