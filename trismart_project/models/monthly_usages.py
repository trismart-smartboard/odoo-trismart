from odoo import models, fields, api, _


class MonthlyUsage(models.Model):
    _name = 'monthly.usage'
    _description = 'Monthly Usage'

    project_id = fields.Many2one('project.project')
