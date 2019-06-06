# This file is part of Tryton.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.

try:
    from trytond.modules.recover_invoice_ar.tests.test_recover_invoice_ar import suite
except ImportError:
    from .test_recover_invoice_ar import suite

__all__ = ['suite']
