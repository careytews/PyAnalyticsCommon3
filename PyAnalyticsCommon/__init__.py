from PyAnalyticsCommon.qcomms import Subscriber, Publisher
import PyAnalyticsCommon.qcomms as _qcomms

def setup(analytic):
    if not _qcomms.analytic_configured:
        _qcomms.analytic_name = analytic
        _qcomms.run_metrics_server()
        _qcomms.analytic_configured = True
