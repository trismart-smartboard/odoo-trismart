from odoo import Command, fields, models, api, _
class Task(models.Model):
    _inherit = "project.task"

    is_fsm_task = fields.Boolean("Field Service Task", default=False, help="Display tasks in the Field Service Task.")
