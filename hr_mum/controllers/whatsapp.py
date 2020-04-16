# from odoo import http
# from odoo.http import request, json, Response


# class ControllerREST(http.Controller):

#     def success_response(self, res):
#         mime = 'application/json'
#         body = json.dumps(res)
#         return Response(body, headers=[
#             ('Content-Type', mime),
#             ('Content-Length', len(body))])

#     @http.route('/api/notification', methods=['GET'], type="http", auth="none", csrf=False, cors='*')
#     def get_notif(self):
#         res = []
#         for message in request.env['mail.whatsapp'].sudo().search(
#                 [('sent', '=', False)], order='create_date ASC'):
#             res.append({
#                 'phone': message.name,
#                 'body': message.message,
#                 'id': message.id,
#             })
#             message.sent = True
#         return self.success_response(res)
