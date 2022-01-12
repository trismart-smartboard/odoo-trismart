from odoo import models, fields, api, _


class MonthlyUsage(models.Model):
    _name = 'monthly.usage'
    _description = 'Monthly Usage'
    # Relationship fields
    project_id = fields.Many2one('project.project', 'Project')

    month = fields.Selection([
        ('jan', 'January'),
        ('feb', 'February'),
        ('mar', 'March'),
        ('apr', 'April'),
        ('may', 'May'),
        ('jun', 'June'),
        ('jul', 'July'),
        ('aug', 'August'),
        ('sep', 'September'),
        ('oct', 'October'),
        ('nov', 'November'),
        ('dec', 'December'),
    ], string='Month')
    billing_number = fields.Float('Billing Number', default=0.0)
    consumption_number = fields.Float('Consumption Number', default=0.0)
