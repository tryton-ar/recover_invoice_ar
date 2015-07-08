#! -*- coding: utf8 -*-
#This file is part of Tryton.  The COPYRIGHT file at the top level of
#this repository contains the full copyright notices and license terms.

from trytond.wizard import Wizard, StateView, StateTransition, Button
from trytond.model import fields, ModelView
from trytond.pyson import Eval
from trytond.pool import Pool, PoolMeta
from trytond.transaction import Transaction

__all__ = ['RecoverInvoice', 'RecoverInvoiceStart', 'RecoverInvoiceFactura']
__metaclass__ = PoolMeta

class RecoverInvoiceStart(ModelView):
    'RecoverInvoiceStart'
    __name__ = 'recover.invoice.start'
    pos = fields.Many2One('account.pos', 'Point of Sale')
    invoice_type = fields.Many2One('account.pos.sequence', 'Invoice Type',
        domain=([('pos', '=', Eval('pos'))]))

    cbte_nro = fields.Integer(u'Número comprobante')

class RecoverInvoiceFactura(ModelView):
    'RecoverInvoiceFactura'
    __name__ = 'recover.invoice.factura'
    message = fields.Text('Message', readonly=True)
    invoice = fields.Many2One('account.invoice', 'Invoice',
        domain=([('state', '=', 'draft')]))
    FechaCbte = fields.Char('FechaCbte')
    CbteNro = fields.Char('CbteNro')
    PuntoVenta = fields.Char('PuntoVenta')
    ImpTotal = fields.Char('ImpTotal')
    CAE = fields.Char('CAE')
    Vencimiento = fields.Char('Vencimiento')
    EmisionTipo = fields.Char('EmisionTipo')
    Cuit = fields.Char('Cuit')
    cuit_cliente = fields.Char('CUIT del CLIENTE')
    CbteNro = fields.Char('CbteNro')

class RecoverInvoice(Wizard):
    'RecoverInvoice'
    __name__ = 'recover.invoice'

    start = StateView(
        'recover.invoice.start',
        'recover_invoice_ar.recover_invoice_start_view', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Ask AFIP', 'ask_afip', 'tryton-ok', default=True),
        ])
    factura = StateView(
        'recover.invoice.factura',
        'recover_invoice_ar.recover_invoice_factura_view', [
            Button('Close', 'end', 'tryton-close'),
            Button('Previous', 'start', 'tryton-go-previous', default=True),
            Button('Save Invoice', 'save_invoice', 'tryton-close'),
        ])
    ask_afip = StateTransition()
    save_invoice = StateTransition()

    def default_start(self, fields):
        print '>>> default start...'
        res = {}

        if hasattr(self.start, 'invoice_type'):
            res['invoice_type'] = self.start.invoice_type.id

        if hasattr(self.start, 'pos'):
            res['pos'] = self.start.pos.id

        return res

    def default_factura(self, fields):
        res = {'message': self.factura.message}
        return res

    def transition_ask_afip(self):
        # Generate Collect
        print '>>> recover invoice...'
        tipo_cbte = self.start.invoice_type.invoice_type
        punto_vta = self.start.pos.number
        service = self.start.pos.pyafipws_electronic_invoice_service

        # get the electronic invoice type, point of sale and service:
        pool = Pool()

        Company = pool.get('company.company')
        company_id = Transaction().context.get('company')
        if not company_id:
            message = u'No hay companía:'
            self.factura.message = message
            return 'factura'

        company = Company(company_id)
        # import the AFIP webservice helper for electronic invoice
        if service == 'wsfe':
            from pyafipws.wsfev1 import WSFEv1  # local market
            ws = WSFEv1()
            if company.pyafipws_mode_cert == 'homologacion':
                WSDL = "https://wswhomo.afip.gov.ar/wsfev1/service.asmx?WSDL"
            elif company.pyafipws_mode_cert == 'produccion':
                WSDL = "https://servicios1.afip.gov.ar/wsfev1/service.asmx?WSDL"
        elif service == 'wsfex':
            message = u'WS no soportado: ' + repr(service)
            self.factura.message = message
            return 'factura'
        else:
            message = u'WS no soportado: ' + repr(service)
            self.factura.message = message
            return 'factura'

        # authenticate against AFIP:
        try:
            auth_data = company.pyafipws_authenticate(service=service)
        except Exception, e:
            message = u'Service no soportado:' + repr(e)
            self.factura.message = message
            return 'factura'

        # connect to the webservice and call to the test method
        ws.LanzarExcepciones = True
        ws.Conectar(wsdl=WSDL)
        # set AFIP webservice credentials:
        ws.Cuit = company.party.vat_number
        ws.Token = auth_data['token']
        ws.Sign = auth_data['sign']

        if self.start.cbte_nro is None:
            cbte_nro = ws.CompUltimoAutorizado(tipo_cbte, punto_vta)
        else:
            cbte_nro = self.start.cbte_nro

        ws.CompConsultar(tipo_cbte, punto_vta, cbte_nro)

        message = "FechaCbte = " + ws.FechaCbte + "\n"
        message += "CbteNro = " + str(ws.CbteNro) + "\n"
        message += "PuntoVenta = "+ str(ws.PuntoVenta) + "\n"
        message += "ImpTotal ="+ str(ws.ImpTotal) + "\n"
        message += "CAE = "+ str(ws.CAE) + "\n"
        message += "Vencimiento = "+ str(ws.Vencimiento) + "\n"
        message += "EmisionTipo = "+ str(ws.EmisionTipo) + "\n"
        message += "CUIT EMISOR = "+ str(ws.Cuit) + "\n"
        if ws.AnalizarXml("XmlResponse"):
            message += "CUIT CLIENTE = "+ ws.ObtenerTagXml("DocNro") + "\n"

        self.factura.CAE = str(ws.CAE)
        self.factura.Vencimiento = str(ws.Vencimiento)
        self.factura.Cuit = str(ws.Cuit)
        self.factura.CbteNro = str(ws.CbteNro)

        self.factura.message = message
        return 'factura'

    def transition_save_invoice(self):
        # Generate Collect
        print '>>> save invoice...'
        pool = Pool()
        Invoice = pool.get('account.invoice')
        if self.factura.invoice:
            invoice, = Invoice.search([('id', '=', self.factura.invoice.id)])

            #AFIP_Transaction = pool.get('account_invoice_ar.afip_transaction')
            #with Transaction().new_cursor():
            #    AFIP_Transaction.create([{'invoice': self,
            #                        'pyafipws_result': ws.Resultado,
            #                        'pyafipws_message': msg,
            #                        'pyafipws_xml_request': ws.XmlRequest,
            #                        'pyafipws_xml_response': ws.XmlResponse,
            #                        }])
            #    Transaction().cursor.commit()

            # calculate the barcode:
            tipo_cbte = self.start.invoice_type.invoice_type
            punto_vta = self.start.pos.number
            if self.factura.CAE:
                cae_due = ''.join([c for c in str(self.factura.Vencimiento or '')
                                        if c.isdigit()])
                bars = ''.join([str(self.factura.Cuit), "%02d" % int(tipo_cbte),
                                "%04d" % int(punto_vta),
                                str(self.factura.CAE), cae_due])
                bars = bars + invoice.pyafipws_verification_digit_modulo10(bars)
            else:
                bars = ""

            if self.factura.CAE:

                # store the results
                vals = {'pyafipws_cae': self.factura.CAE,
                    'pyafipws_cae_due_date': self.factura.Vencimiento or None,
                    'pyafipws_barcode': bars,
                    }
                if not '-' in vals['pyafipws_cae_due_date']:
                    fe = vals['pyafipws_cae_due_date']
                    vals['pyafipws_cae_due_date'] = '-'.join([fe[:4],fe[4:6],fe[6:8]])

            Move = pool.get('account.move')
            moves = []
            vals['number'] = '%04d-%08d' % (self.start.pos.number, int(self.factura.CbteNro))
            Invoice.write([invoice], vals)
            moves.append(invoice.create_move())
            Invoice.write([invoice], {
                'state': 'posted',
            })
            Move.post(moves)

        return 'end'
