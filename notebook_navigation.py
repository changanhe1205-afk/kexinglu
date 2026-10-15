"""Wait for native dialog dismissal before changing notebook routes.

Setting open=False starts a Flutter animation; it does not remove its route.
Keep Flet's managed on_dismiss callback intact so it also removes the control.
"""
import asyncio
import inspect


def after_dialog_closed(page, continuation):
    pending=getattr(page,'notebook_transition',None)
    if pending is not None and not pending.done():return pending

    async def transition():
        dialog=page.pop_dialog()
        if dialog is not None:
            dismissed=asyncio.get_running_loop().create_future()
            managed_dismiss=dialog.on_dismiss

            async def finish(event):
                try:
                    if managed_dismiss:
                        result=managed_dismiss(event)
                        if inspect.isawaitable(result):await result
                finally:
                    if not dismissed.done():dismissed.set_result(None)

            # No await between pop and installing this handler: the native
            # dismissal event cannot be dispatched on this loop in between.
            dialog.on_dismiss=finish
            await dismissed
        # Allow the continuation to start a second owned transition if needed.
        page.notebook_transition=None
        result=continuation()
        if inspect.isawaitable(result):await result

    task=page.run_task(transition)
    page.notebook_transition=task
    return task
