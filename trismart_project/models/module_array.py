from odoo import models, fields, api, _


class ProjectModuleArray(models.Model):
    _name = 'project.module.array'
    _description = 'Module Array'

    qty = fields.Integer('Array (#) Module Quantity')
    tilt = fields.Integer('Array (#) Tilt')
    azimuth = fields.Integer('Array (#) Azimuth')
    max_modules = fields.Integer('Array (#) Max Modules')
    solar_access = fields.Integer('Array (#) Solar Access')
    year_1_production = fields.Float('Array (#) Year 1 Production')
