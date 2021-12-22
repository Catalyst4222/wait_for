import asyncio
from inspect import isawaitable
from typing import Union, Callable, Optional, Any, Awaitable, Type
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

    def add(self, name: str) -> asyncio.Future:
        """
        Returns a Future that will resolve whenever the supplied event is dispatched

        :param name: The event to listen for
        :type name: str
        :return: A future that will be resolved on the next event dispatch with the data given
        :rtype: asyncio.Future
        """
        fut = asyncio.get_event_loop().create_future()
        try:
            futures = self.extra_events[name]
        except KeyError:
            futures = []
            self.extra_events[name] = futures
        futures.append(fut)
        return fut


interactions.api.dispatch.Listener = ExtendedListener


async def wait_for(bot: interactions.Client, name: str,
                   check: Optional[Callable[..., Union[bool, Awaitable[bool]]]] = None,
                   timeout: Optional[float] = None) -> Any:
    """
    Wait for an event once, and return the result.

    Unlike event decorators, this is not persistent, and can be used to only proceed in a command once an event happens.

    :param bot: The bot that will receive the event
    :type bot: interactions.Client
    :param name: The event to wait for
    :type name: str
    :param check: A function or coroutine to call, which should return a truthy value if the data should be returned
    :type check: Callable
    :param timeout: How long to wait for the event before raising an error
    :type timeout: float
    :return: The value of the dispatched event
    :rtype: Any
    """
    while True:
        fut = bot.websocket.dispatch.add(name=name)
        try:
            res: list = await asyncio.wait_for(fut, timeout=timeout)
        except asyncio.TimeoutError:
            bot.websocket.dispatch.extra_events[name].remove(fut)
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


def setup(bot: Union[
    interactions.Client,
    Type[interactions.Client]
]) -> None:
    """
    Apply hooks to a bot to add ``wait_for`` as a method.

    This function isn't strictly needed, as importing ``wait_for`` directly will do the same thing, but having methods
    applied to the class can be nice sometimes

    :param bot: The bot instance or class to apply hooks to
    :type bot:
    """
    if isinstance(bot, type(interactions.Client)):  # class object
        bot.wait_for = wait_for

    elif isinstance(bot, interactions.Client):  # instance
        bot.wait_for = types.MethodType(wait_for, bot)  # untested

    else:
        raise TypeError(f"{bot.__class__.__name__} is not interactions.Client!")

    bot.websocket.dispatch = ExtendedListener()
