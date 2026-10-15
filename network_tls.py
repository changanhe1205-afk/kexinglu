"""Verified HTTPS using bundled public roots plus available system roots."""
import logging
import ssl

import certifi


def https_context():
    # Load the shipped roots first, so an empty Windows certificate store works.
    context = ssl.create_default_context(cafile=certifi.where())
    try:
        context.load_default_certs()
    except (OSError, ssl.SSLError):
        logging.getLogger(__name__).warning("无法加载系统证书，使用随包附带的根证书")
    return context
