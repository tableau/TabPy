import traceback
def format_exception(e, context):
    err_msg = "%s : " % e.__class__.__name__
    err_msg += "%s" % str(e)
    return err_msg

def format_exception_DEBUG(e, context,detail=0):
    trace = traceback.format_exc()
    err_msg = "Traceback\n %s\n" % trace
    err_msg += "Error type    : %s\n" % e.__class__.__name__
    err_msg += "Error message : %s\n" % str(e)
    return "Error when %s: %s" % (context, err_msg)
