import traceback


def format_exception(e, context):
    err_msg = "%s : " % e.__class__.__name__
    err_msg += "%s" % str(e)
    return err_msg
