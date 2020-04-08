from odoo import models, fields, api, _
from odoo.exceptions import UserError

    
class Partner(models.Model):
    _inherit = 'res.partner'

    whatsapp = fields.Char(string='Whatsapp')

    @api.constrains('whatsapp')
    def _check_whatsapp(self):
        for partner in self:
            if partner.whatsapp and any(x not in ('0', '1', '2', '3', '4', '5', '6', '7', '8', '9') for x in partner.whatsapp):
                raise UserError(_("Wrong WhatsApp Number Format!"))

class MailWhatsapp(models.Model):
    _name = 'mail.whatsapp'
    _description = 'WhatsApp Temp Message'

    name = fields.Char('Number')
    message = fields.Char('Message')
    sent = fields.Boolean('Sent', index=True, default=False)