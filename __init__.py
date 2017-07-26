# This file is part of the recover_invoice_ar module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.pool import Pool
from .invoice import *


def register():
    Pool.register(
        RecoverInvoiceStart,
        RecoverInvoiceFactura,
        module='recover_invoice_ar', type_='model')
    Pool.register(
        RecoverInvoice,
        module='recover_invoice_ar', type_='wizard')
