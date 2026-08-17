from django.apps import AppConfig
from django.core.exceptions import ImproperlyConfigured


class KmdKcsapFtpDecoderConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = "adl_kmd_kcsap_ftp_decoder"
    
    def ready(self):
        try:
            from adl_ftp_plugin.registries import ftp_decoder_registry
        except ImportError as e:
            raise ImproperlyConfigured(
                "adl_kmd_kcsap_ftp_decoder is an ADL FTP decoder plugin and requires "
                "adl-ftp-plugin to be installed."
            ) from e
        
        from .decoders import KcsapDecoder
        
        ftp_decoder_registry.register(KcsapDecoder())
