import smtplib
import ssl

# Save the original starttls method
_original_starttls = smtplib.SMTP.starttls

def patched_starttls(self, keyfile=None, certfile=None, context=None):
    """
    Monkey-patch to make smtplib.SMTP.starttls compatible with older Django versions
    under Python 3.12+, where keyfile/certfile were removed.
    """
    if context is None:
        # Create a default context if none is provided
        context = ssl.create_default_context()
        if certfile or keyfile:
            context.load_cert_chain(certfile, keyfile)
    return _original_starttls(self, context=context)

# Apply the monkey patch
smtplib.SMTP.starttls = patched_starttls
