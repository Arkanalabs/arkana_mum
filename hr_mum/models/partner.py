from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.http import json
import requests, urllib
    
class Partner(models.Model):
    _inherit = 'res.partner'

    warkana_id = fields.Many2one('warkana.firebase', string='Warkana', domain="[('name', '=', 'Warkana Firebase')]")
    whatsapp = fields.Char(string='No Whatsapp')
    
    @api.constrains('whatsapp')
    def _check_whatsapp(self):
        for partner in self:
            if partner.whatsapp:
                if partner.whatsapp and any(x not in ('0', '1', '2', '3', '4', '5', '6', '7', '8', '9') for x in partner.whatsapp): 
                    raise UserError(_("Wrong WhatsApp Number Format!"))
                elif partner.whatsapp[0] == '0': 
                    raise UserError(_("Wrong WhatsApp Number Format!"))

    @api.model
    def send_wa_notification(self, body=False, flag=False):
        partner = self
        URL = 'https://fcm.googleapis.com/fcm/send'
        HEADERS = {
            'Authorization': '',
            'Content-Type': 'application/json'
        }
        if partner.whatsapp and body and partner.warkana_id.warkana_firebase_auth and partner.warkana_id.warkana_firebase_token:
            try:
                headers = HEADERS
                headers['Authorization'] = partner.warkana_id.warkana_firebase_auth
                payload = {
                    'to': partner.warkana_id.warkana_firebase_token,
                    'data': {
                        'phone': partner.whatsapp,
                        'body': body,
                    }
                }
                r = requests.post(URL, headers=headers, data=json.dumps(payload))
            except requests.exceptions.RequestException as e:
                return False

    class WarkanaFirebase(models.Model):
        _name = 'warkana.firebase'
    
        name = fields.Char(string='Name', default="Warkana Firebase")
        warkana_firebase_auth = fields.Text(string='Warkana Firebase Authorization')
        warkana_firebase_token = fields.Text(string='Warkana Firebase Token')

