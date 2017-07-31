try:
    from trytond.modules.recover_invoice_ar.tests.tests import suite
except ImportError:
    from .tests import suite

__all__ = ['suite']
