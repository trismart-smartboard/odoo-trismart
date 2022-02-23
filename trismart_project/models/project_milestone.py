# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class SmartBoardProjectMilestone(models.Model):
    _name = 'smartboard.project.milestone'
    _description = 'SmartBoard Project Milestone'

    sb_id = fields.Integer('SmartBoard Id')
    name = fields.Char('Name')
