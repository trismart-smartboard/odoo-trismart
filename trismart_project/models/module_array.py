from odoo import models, fields, api, _


class Incentive(models.Model):
    _name = 'project.incentive'
    _description = 'Project Incentive'

    qty = fields.Integer('Incentive (#) Quantity')
    cost = fields.Float('Incentive (#) Cost')
    name = fields.Char('Incentive (#) Name')
    # Relationship Field
    project_id = fields.Many2one('project.project', string='Project')


class Adder(models.Model):
    _name = 'project.adder'
    _description = 'Project Adder'

    size = fields.Integer('Adder (#) Size')
    qty = fields.Integer('Adder (#) Quantity')
    cost = fields.Float('Adder (#) Cost')
    name = fields.Char('Adder (#) Name')
    make = fields.Char('Adder (#) Make')
    model = fields.Char('Adder (#) Model')
    # Relationship Field
    project_id = fields.Many2one('project.project', string='Project')


class ProjectModuleArray(models.Model):
    _name = 'project.module.array'
    _description = 'Module Array'

    qty = fields.Integer('Array (#) Module Quantity')
    tilt = fields.Integer('Array (#) Tilt')
    azimuth = fields.Integer('Array (#) Azimuth')
    max_modules = fields.Integer('Array (#) Max Modules')
    solar_access = fields.Integer('Array (#) Solar Access')
    year_1_production = fields.Float('Array (#) Year 1 Production')
    # Relationship Field
    project_id = fields.Many2one('project.project', string='Project')
