def execute_action(
    request,
    adapter,
):
    """
    Execute an authorized action through an adapter.

    This layer does not decide whether execution is allowed.
    Authorization must already exist before reaching here.
    """

    return adapter.execute(request)
