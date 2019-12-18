def format_exception(e, context):
    err_msg = f"{e.__class__.__name__} : {str(e)}"
    return err_msg
