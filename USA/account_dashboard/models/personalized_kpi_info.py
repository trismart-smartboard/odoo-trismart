# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64

from odoo import api, models, fields, modules, tools, _
from .kpi_journal import CURRENCY,periods_type,units_type
from ..utils.time_utils import BY_YTD

LIST_KPI_COLOR_DEFAULT = ['#6fa8dc', '#ff9900', '#93c47d', '#ea9999', '#8e7cc3', '#7cc3a6']


class PersonalizedKPIInfo(models.Model):
    _name = "personalized.kpi.info"
    _inherit = "kpi.journal"
    _description = "Personalized KPIs Information"

    def _get_default_icon(self):
        return self.kpi_id.icon_kpi

    def _get_general_color(self):
        return self.kpi_id.color

    def _get_default_image(self, module, path, name):
        image_path = modules.get_module_resource(module, path, name)
        # return tools.image_resize_image_big(base64.b64encode(open(image_path, 'rb').read()))
        return tools.image_process(base64.b64encode(open(image_path, 'rb').read()), size=(1024, 1024))

    name = fields.Char('Name', related='kpi_id.name')
    kpi_id = fields.Many2one('kpi.journal', 'KPI ID', ondelete='cascade')
    company_id = fields.Many2one('res.company', string='Company', required=True, index=True,
                                 default=lambda self: self.env.company, help="Company related to this personalized KPI")
    user_id = fields.Many2one('res.users', string='KPI owner', default=lambda self: self.env.user)
    period_type = fields.Selection(periods_type, default=BY_YTD)
    unit = fields.Selection(units_type, default=CURRENCY)

    @api.model
    def kpi_header_render(self, new_user=True):
        """ Function check this user have create personal kpi ever.
        If not create for them and return the JSON used to render KPI
        header include KPI items and setting for it

        :return:
        Workflow:
        Company Insight -> render personalized KPI from general KPI -> kpi_header_render()
        """
        uid = self.env.user.id

        if new_user:
            # Generate kpi for new user have use dashboard at the first time
            self.generate_kpi_for_new_user(uid)

        kpis_info = self.search([('user_id', '=', uid), ('company_id', '=', self.env.company.id)])
        kpi_json = self.env['kpi.journal'].kpi_render(kpis_info)
        return kpi_json

    ########################################################
    # GENERAL FUNCTION
    ########################################################
    def generate_kpi_for_new_user(self, uid, company_id=0):
        """ The Function generate all the default kpi for new user,
        who don't have any kpis at the first time.

        :return:
        """
        if not company_id:
            company_id = self.env.company.id
        available_kpi = self.search([('user_id', '=', uid), ('company_id', '=', company_id)])
        kpi_default = self.env['kpi.journal'].search([('default_kpi', '=', True)])

        # Generate kpi item for user if number kpi of this user is 0
        # or less than the number of default kpis
        if len(available_kpi) == 0 or len(available_kpi) < len(kpi_default):
            avail_kpi_ids = available_kpi.mapped(lambda kpi: kpi.kpi_id.id)
            kpi_have_not_exist = kpi_default.filtered(lambda kpi: kpi.id not in avail_kpi_ids)
            for idx, kpi in enumerate(kpi_have_not_exist):
                self.create({
                    'selected': idx < len(kpi_default),
                    'order': idx if idx < len(kpi_default) else -1,
                    'color': kpi.color,
                    'icon_kpi': kpi.icon_kpi,
                    'kpi_id': kpi.id,
                    'green_on_positive': kpi.green_on_positive,
                    'user_id': uid,
                    'company_id': company_id
                })

    ########################################################
    # API FUNCTION
    ########################################################

    @api.model
    def update_kpi_selected(self, list_kpi_updated):
        """ Function update what kpi has selected and unselected to database
        used to save all kpi status. this also return the new data used to render
        to the header of dashboard

        :param list_kpi_updated:
        :return: dictionary is the data to render kpi header
        Workflow:
        When user change position or visibility of KPI Manage on Dashboard
        -> Change_kpi_selection in JS file is triggered -> update_kpi_selected in database
        """

        # Get all dictionaries which of the kpi have been selected
        # to show in kpi header in list list_kpi_updated
        data_kpi_selected_update = filter(lambda x: x['selected'], list_kpi_updated)

        # Get list name of kpi from the list have filter above
        kpi_selected_update = list(map(lambda x: x['name_kpi'], data_kpi_selected_update))

        # Search all the kpis were selected before and would be not selected
        # after change setting
        kpi_unselected = self.search([
            ('kpi_id.name', 'not in', kpi_selected_update),
            ('selected', '=', True),
            ('company_id', '=', self.env.company.id),
            ('user_id', '=', self.env.user.id)
        ])

        # Unselected all kpi above
        kpi_unselected.write(
            {
                'selected': False,
                'order': -1
            }
        )
        # Update all the kpis that have been selected to database and update the order of there also
        kpi_selected = self.search([
            ('kpi_id.name', 'in', kpi_selected_update),
            ('company_id', '=', self.env.company.id),
            ('user_id', '=', self.env.user.id)
        ], order='order ASC')
        order = 0
        for kpi in kpi_selected:
            kpi.write({
                'selected': True,
                'order': order
            })
            order += 1

        return self.kpi_header_render(new_user=False)

    @api.model
    def update_kpi_order(self, list_kpis_name):
        kpis_selected = self.search([
            ('kpi_id.name', 'in', list_kpis_name),
            ('company_id', '=', self.env.company.id),
            ('user_id', '=', self.env.user.id)])
        for kpi in kpis_selected:
            kpi.write({
                'order': list_kpis_name.index(kpi.kpi_id.name)
            })
        return self.kpi_header_render(new_user=False)
