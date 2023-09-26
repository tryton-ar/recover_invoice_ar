# This file is part of the recover_invoice_ar module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from datetime import datetime

from trytond.wizard import Wizard, StateView, StateTransition, Button
from trytond.model import fields, ModelView
from trytond.pyson import Eval
from trytond.pool import Pool
from trytond.transaction import Transaction


class RecoverInvoiceStart(ModelView):
    'RecoverInvoiceStart'
    __name__ = 'recover.invoice.start'

    pos = fields.Many2One('account.pos', 'Point of Sale', required=True)
    invoice_type = fields.Many2One('account.pos.sequence', 'Invoice Type',
        domain=[('pos', '=', Eval('pos'))], required=True)
    cbte_nro = fields.Integer('Número comprobante')


class RecoverInvoiceFactura(ModelView):
    'RecoverInvoiceFactura'
    __name__ = 'recover.invoice.factura'

    message = fields.Text('Message', readonly=True)
    invoice = fields.Many2One('account.invoice', 'Invoice',
        domain=[('state', '=', 'draft')])
    FechaCbte = fields.Char('FechaCbte')
    CbteNro = fields.Char('CbteNro')
    PuntoVenta = fields.Char('PuntoVenta')
    ImpTotal = fields.Char('ImpTotal')
    CAE = fields.Char('CAE')
    Vencimiento = fields.Char('Vencimiento')
    EmisionTipo = fields.Char('EmisionTipo')
    Cuit = fields.Char('Cuit')
    cuit_cliente = fields.Char('CUIT del CLIENTE')


class RecoverInvoice(Wizard):
    'RecoverInvoice'
    __name__ = 'recover.invoice'

    start = StateView(
        'recover.invoice.start',
        'recover_invoice_ar.recover_invoice_start_view', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Ask AFIP', 'ask_afip', 'tryton-forward', default=True),
        ])
    factura = StateView(
        'recover.invoice.factura',
        'recover_invoice_ar.recover_invoice_factura_view', [
            Button('Close', 'end', 'tryton-cancel'),
            Button('Previous', 'start', 'tryton-back', default=True),
            Button('Save Invoice', 'save_invoice', 'tryton-save'),
        ])
    ask_afip = StateTransition()
    save_invoice = StateTransition()

    def default_start(self, fields):
        res = {}
        if hasattr(self.start, 'invoice_type'):
            res['invoice_type'] = self.start.invoice_type.id
        if hasattr(self.start, 'pos'):
            res['pos'] = self.start.pos.id
        if hasattr(self.start, 'cbte_nro'):
            res['cbte_nro'] = self.start.cbte_nro
        return res

    def transition_ask_afip(self):
        # Generate Collect
        tipo_cbte = self.start.invoice_type.invoice_type
        punto_vta = self.start.pos.number
        service = self.start.pos.pyafipws_electronic_invoice_service

        # get the electronic invoice type, point of sale and service:
        pool = Pool()
        Company = pool.get('company.company')
        if Transaction().context.get('company'):
            company = Company(Transaction().context['company'])
        else:
            message = 'No hay companía:'
            self.factura.message = message
            return 'factura'

        # import the AFIP webservice helper for electronic invoice
        if service == 'wsfe':
            from pyafipws.wsfev1 import WSFEv1  # local market
            ws = WSFEv1()
            if company.pyafipws_mode_cert == 'homologacion':
                WSDL = 'https://wswhomo.afip.gov.ar/wsfev1/service.asmx?WSDL'
            elif company.pyafipws_mode_cert == 'produccion':
                WSDL = (
                    'https://servicios1.afip.gov.ar/wsfev1/service.asmx?WSDL')
        elif service == 'wsfex':
            from pyafipws.wsfexv1 import WSFEXv1  # foreign trade
            ws = WSFEXv1()
            if company.pyafipws_mode_cert == 'homologacion':
                WSDL = 'https://wswhomo.afip.gov.ar/wsfexv1/service.asmx?WSDL'
            elif company.pyafipws_mode_cert == 'produccion':
                WSDL = (
                    'https://servicios1.afip.gov.ar/wsfexv1/service.asmx?WSDL')
        else:
            message = 'WS no soportado: ' + repr(service)
            self.factura.message = message
            return 'factura'

        ws.LanzarExcepciones = True
        cache = company.get_cache_dir()

        # authenticate against AFIP:
        try:
            ta = company.pyafipws_authenticate(service=service, cache=cache)
        except Exception as e:
            message = 'Service no soportado:' + repr(e)
            self.factura.message = message
            return 'factura'

        # set AFIP webservice credentials:
        ws.SetTicketAcceso(ta)
        ws.Cuit = company.party.vat_number
        ws.Conectar(wsdl=WSDL, cache=cache, cacert=True)

        if self.start.cbte_nro is None:
            if service == 'wsfe' or service == 'wsmtxca':
                cbte_nro = ws.CompUltimoAutorizado(tipo_cbte, punto_vta)
            elif service == 'wsfex':
                cbte_nro = ws.GetLastCMP(tipo_cbte, punto_vta)
        else:
            cbte_nro = self.start.cbte_nro

        if service == 'wsfe' or service == 'wsmtxca':
            ws.CompConsultar(tipo_cbte, punto_vta, cbte_nro)
        elif service == 'wsfex':
            ws.GetCMP(tipo_cbte, punto_vta, cbte_nro)

        message = 'FechaCbte = ' + ws.FechaCbte + '\n'
        message += 'CbteNro = ' + str(ws.CbteNro) + '\n'
        message += 'PuntoVenta = ' + str(ws.PuntoVenta) + '\n'
        message += 'ImpTotal =' + str(ws.ImpTotal) + '\n'
        message += 'CAE = ' + str(ws.CAE) + '\n'
        message += 'Vencimiento = ' + str(ws.Vencimiento) + '\n'
        message += 'CUIT EMISOR = ' + str(ws.Cuit) + '\n'
        if ws.AnalizarXml('XmlResponse'):
            if service == 'wsfex':
                cuit_cliente = ws.ObtenerTagXml('Cuit_pais_cliente')
                emision_tipo = ws.ObtenerTagXml('Cbte_tipo')
            else:
                cuit_cliente = ws.ObtenerTagXml('DocNro')
                emision_tipo = ws.ObtenerTagXml('CbteTipo')
        message += 'CUIT CLIENTE = %s\n' % cuit_cliente
        message += 'Tipo comprobante = %s\n' % emision_tipo

        self.factura.FechaCbte = str(ws.FechaCbte)
        self.factura.CbteNro = str(ws.CbteNro)
        self.factura.CAE = str(ws.CAE)
        if service == 'wsfex':
            vto = str(ws.Vencimiento).split('/')
            self.factura.Vencimiento = '-'.join([vto[2], vto[1], vto[0]])
        else:
            self.factura.Vencimiento = str(ws.Vencimiento)
        self.factura.Cuit = str(ws.Cuit)

        self.factura.message = message
        return 'factura'

    def default_factura(self, fields):
        res = {}
        if hasattr(self.factura, 'message'):
            res['message'] = self.factura.message
        if hasattr(self.factura, 'CbteNro'):
            res['CbteNro'] = self.factura.CbteNro
        if hasattr(self.factura, 'CAE'):
            res['CAE'] = self.factura.CAE
        if hasattr(self.factura, 'FechaCbte'):
            res['FechaCbte'] = self.factura.FechaCbte
        if hasattr(self.factura, 'ImpTotal'):
            res['ImpTotal'] = self.factura.ImpTotal
        if hasattr(self.factura, 'cuit_cliente'):
            res['cuit_cliente'] = self.factura.cuit_cliente
        if hasattr(self.factura, 'Vencimiento'):
            res['Vencimiento'] = self.factura.Vencimiento
        if hasattr(self.factura, 'Cuit'):
            res['Cuit'] = self.factura.Cuit
        return res

    def transition_save_invoice(self):
        # Generate Collect
        pool = Pool()
        Invoice = pool.get('account.invoice')

        if not self.factura.invoice or not hasattr(self.factura, 'CAE'):
            return 'start'

        invoice = Invoice(self.factura.invoice.id)
        invoice.pos = self.start.pos
        invoice.invoice_type = self.start.invoice_type

        # store the results
        invoice_date = self.factura.FechaCbte or None
        if '-' not in invoice_date:
            fe = invoice_date
            invoice_date = '-'.join([fe[:4], fe[4:6], fe[6:8]])
        invoice.invoice_date = datetime.strptime(
            invoice_date, "%Y-%m-%d").date()

        invoice.number = '%05d-%08d' % (self.start.pos.number,
            int(self.factura.CbteNro))

        invoice.pyafipws_cae = self.factura.CAE

        cae_due_date = self.factura.Vencimiento or None
        if '-' not in cae_due_date:
            fe = cae_due_date
            cae_due_date = '-'.join([fe[:4], fe[4:6], fe[6:8]])
        invoice.pyafipws_cae_due_date = datetime.strptime(
            cae_due_date, "%Y-%m-%d").date()

        # calculate the barcode:
        tipo_cbte = self.start.invoice_type.invoice_type
        punto_vta = self.start.pos.number
        cae_due = ''.join([c for c in str(self.factura.Vencimiento or '')
                if c.isdigit()])
        bars = ''.join([str(self.factura.Cuit), '%03d' % int(tipo_cbte),
                '%05d' % int(punto_vta), str(self.factura.CAE), cae_due])
        bars = bars + invoice.pyafipws_verification_digit_modulo10(bars)
        invoice.pyafipws_barcode = bars

        Invoice.save([invoice])
        Invoice.validate_invoice([invoice])
        Invoice.post([invoice])
        return 'end'
