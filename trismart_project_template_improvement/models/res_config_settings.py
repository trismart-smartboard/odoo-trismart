from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    user_default_project_template = fields.Many2one(
        'project.project',
        default_model = 'project.project',
        string = 'Default Project Template',
        domain="[('is_template', '=', True)]",
        config_parameter='trismart_project_template_improvement.user_default_project_template',
        help='Project Template to use when create new project')

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        res.update(
            user_default_project_template = int(self.env['ir.config_parameter'].sudo().get_param('trismart_project_template_improvement.user_default_project_template')),
        )
        return res

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        param = self.env['ir.config_parameter'].sudo()
        value = self.user_default_project_template and self.user_default_project_template.id or False
        param.set_param('trismart_project_template_improvement.user_default_project_template', value)

