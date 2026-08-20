class ConfigParameters:
    """
    Configuration settings names
    """

    TABPY_PWD_FILE = "TABPY_PWD_FILE"
    TABPY_PORT = "TABPY_PORT"
    TABPY_QUERY_OBJECT_PATH = "TABPY_QUERY_OBJECT_PATH"
    TABPY_STATE_PATH = "TABPY_STATE_PATH"
    TABPY_TRANSFER_PROTOCOL = "TABPY_TRANSFER_PROTOCOL"
    TABPY_CERTIFICATE_FILE = "TABPY_CERTIFICATE_FILE"
    TABPY_KEY_FILE = "TABPY_KEY_FILE"
    TABPY_MINIMUM_TLS_VERSION = "TABPY_MINIMUM_TLS_VERSION"
    TABPY_LOG_DETAILS = "TABPY_LOG_DETAILS"
    TABPY_STATIC_PATH = "TABPY_STATIC_PATH"
    TABPY_MAX_REQUEST_SIZE_MB = "TABPY_MAX_REQUEST_SIZE_MB"
    TABPY_EVALUATE_ENABLE = "TABPY_EVALUATE_ENABLE"
    TABPY_EVALUATE_TIMEOUT = "TABPY_EVALUATE_TIMEOUT"
    TABPY_GZIP_ENABLE = "TABPY_GZIP_ENABLE"

    # Arrow specific settings
    TABPY_ARROW_ENABLE = "TABPY_ARROW_ENABLE"
    TABPY_ARROWFLIGHT_PORT = "TABPY_ARROWFLIGHT_PORT"

    # OAuth/JWT specific settings
    TABPY_OAUTH_ENABLED = "TABPY_OAUTH_ENABLED"
    TABPY_OAUTH_ISSUER = "TABPY_OAUTH_ISSUER"
    TABPY_OAUTH_JWKS_URI = "TABPY_OAUTH_JWKS_URI"
    TABPY_OAUTH_AUDIENCE = "TABPY_OAUTH_AUDIENCE"
    TABPY_OAUTH_REQUIRED_SCOPES = "TABPY_OAUTH_REQUIRED_SCOPES"
    TABPY_OAUTH_ENFORCE_ENDPOINT_SCOPES = "TABPY_OAUTH_ENFORCE_ENDPOINT_SCOPES"
    TABPY_OAUTH_LOG_USER = "TABPY_OAUTH_LOG_USER"


class SettingsParameters:
    """
    Application (TabPyApp) settings names
    """

    TransferProtocol = "transfer_protocol"
    Port = "port"
    ServerVersion = "server_version"
    UploadDir = "upload_dir"
    CertificateFile = "certificate_file"
    KeyFile = "key_file"
    MinimumTLSVersion = "minimum_tls_version"
    StateFilePath = "state_file_path"
    ApiVersions = "versions"
    LogRequestContext = "log_request_context"
    StaticPath = "static_path"
    MaxRequestSizeInMb = "max_request_size_in_mb"
    EvaluateTimeout = "evaluate_timeout"
    EvaluateEnabled = "evaluate_enabled"
    GzipEnabled = "gzip_enabled"

    # Arrow specific settings
    ArrowEnabled = "arrow_enabled"
    ArrowFlightPort = "arrowflight_port"

    # OAuth/JWT specific settings
    OAuthEnabled = "oauth_enabled"
    OAuthIssuer = "oauth_issuer"
    OAuthJwksUri = "oauth_jwks_uri"
    OAuthAudience = "oauth_audience"
    OAuthRequiredScopes = "oauth_required_scopes"
    OAuthEnforceEndpointScopes = "oauth_enforce_endpoint_scopes"
    OAuthLogUser = "oauth_log_user"
