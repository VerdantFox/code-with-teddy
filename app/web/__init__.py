from app.web import monitoring

# Sentry needs to import before the sub-apps to ensure Sentry is initialized first.
monitoring.initialize_sentry()
