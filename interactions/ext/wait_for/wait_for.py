import asyncio
from inspect import isawaitable
from typing import Union, Callable, Optional
import types

import interactions
from interactions.api.dispatch import Listener  # just to avoid ide things


class ExtendedListener(interactions.api.dispatch.Listener):
    def __init__(self):
        super().__init__()
        self.extra_events: dict[str, list[asyncio.Future]] = {}

    def dispatch(self, name: str, *args, **kwargs) -> None:
        super().dispatch(name, *args, **kwargs)

        futs = self.extra_events.get(name, [])

        for fut in futs:
            fut.set_result(args)

            futs.remove(fut)

    def add(self, name: str):

        fut = asyncio.get_event_loop().create_future()
        try:
            futures = self.extra_events[name]
        except KeyError:
            futures = []
            self.extra_events[name] = futures
        futures.append(fut)
        return fut


interactions.api.dispatch.Listener = ExtendedListener


async def wait_for(self: interactions.Client, name: str,
                   check: Optional[Callable] = None, timeout: Optional[float] = None):  # TODO work on this next
    assert isinstance(self.websocket.dispatch, ExtendedListener)
    while True:
        fut = self.websocket.dispatch.add(name=name)
        try:
            res: list = await asyncio.wait_for(fut, timeout=timeout)
        except asyncio.TimeoutError:
            self.websocket.dispatch.extra_events[name].remove(fut)
            raise

        if check:
            checked = check(*res)
            if isawaitable(checked):
                checked = await checked
            if not checked:
                # The check failed, so try again next time
                continue

        # I feel like this needs more?
        # yes it did
        if not res:
            return
        elif len(res) == 1:
            return res[0]
        return res


# noinspection PyTypeHints
def setup(bot: Union[
    interactions.Client,
    # type(interactions.Client)
]):
    if isinstance(bot, type(interactions.Client)):  # class object
        bot.wait_for = wait_for

    elif isinstance(bot, interactions.Client):  # instance
        bot.wait_for = types.MethodType(wait_for, bot)  # untested

    else:
        raise TypeError(f"{bot.__class__.__name__} is not interactions.Client!")

    bot.websocket.dispatch = ExtendedListener()
